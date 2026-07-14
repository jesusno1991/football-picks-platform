from datetime import date

import pytest

from app.collectors.api_football_provider import ApiFootballProvider
from app.core.config import get_settings


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("http error")

    def json(self):
        return self.payload


@pytest.fixture(autouse=True)
def api_football_settings(monkeypatch):
    monkeypatch.setenv("API_FOOTBALL_KEY", "test-key")
    monkeypatch.setenv("DATA_PROVIDER", "api_football")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_api_football_normalizes_matches(monkeypatch):
    def fake_get(url, headers, params, timeout):
        assert headers["x-apisports-key"] == "test-key"
        assert url.endswith("/fixtures")
        return FakeResponse(
            {
                "errors": [],
                "response": [
                    {
                        "fixture": {
                            "id": 123,
                            "date": "2026-07-13T18:00:00+00:00",
                            "venue": {"name": "Test Stadium"},
                        },
                        "league": {
                            "id": 99,
                            "name": "Test League",
                            "country": "Spain",
                            "season": 2026,
                            "round": "Regular Season",
                            "logo": "https://example.test/logo.png",
                        },
                        "teams": {
                            "home": {"id": 1, "name": "Home FC", "logo": "home.png"},
                            "away": {"id": 2, "name": "Away FC", "logo": "away.png"},
                        },
                    }
                ],
            }
        )

    monkeypatch.setattr("app.collectors.api_football_provider.httpx.get", fake_get)
    provider = ApiFootballProvider()
    matches = provider.get_matches(date(2026, 7, 13))

    assert matches[0]["external_id"] == "api-football-123"
    assert matches[0]["competition"]["name"] == "Test League"
    assert matches[0]["home_team"]["external_id"] == "api-football-team-1"
    assert provider.get_competitions()[0]["country"] == "Spain"


def test_api_football_builds_team_history(monkeypatch):
    def fake_get(url, headers, params, timeout):
        return FakeResponse(
            {
                "errors": [],
                "response": [
                    {
                        "fixture": {"status": {"short": "FT"}},
                        "teams": {"home": {"id": 1}, "away": {"id": 2}},
                        "goals": {"home": 2, "away": 1},
                        "score": {"halftime": {"home": 1, "away": 0}},
                    },
                    {
                        "fixture": {"status": {"short": "FT"}},
                        "teams": {"home": {"id": 3}, "away": {"id": 1}},
                        "goals": {"home": 0, "away": 0},
                        "score": {"halftime": {"home": 0, "away": 0}},
                    },
                ],
            }
        )

    monkeypatch.setattr("app.collectors.api_football_provider.httpx.get", fake_get)
    history = ApiFootballProvider().get_team_history("api-football-team-1")

    assert history["matches_sample"] == 2
    assert history["goals_for_avg"] == 1.0
    assert history["over_1_5_goals_rate"] == 0.5
    assert history["btts_rate"] == 0.5


def test_api_football_maps_goal_odds(monkeypatch):
    def fake_get(url, headers, params, timeout):
        return FakeResponse(
            {
                "errors": [],
                "response": [
                    {
                        "bookmakers": [
                            {
                                "name": "Bet365",
                                "bets": [
                                    {
                                        "name": "Goals Over/Under",
                                        "values": [
                                            {"value": "Over 1.5", "odd": "1.70"},
                                            {"value": "Under 1.5", "odd": "2.10"},
                                        ],
                                    },
                                    {"name": "Both Teams Score", "values": [{"value": "Yes", "odd": "1.95"}]},
                                ],
                            }
                        ]
                    }
                ],
            }
        )

    monkeypatch.setattr("app.collectors.api_football_provider.httpx.get", fake_get)
    odds = ApiFootballProvider().get_odds("api-football-123")

    goals = [odd for odd in odds if odd["market"] == "goals" and odd["selection"] == "over" and odd["line"] == 1.5][0]
    btts = [odd for odd in odds if odd["market"] == "btts" and odd["selection"] == "yes"][0]
    assert goals["bookmaker"] == "Bet365"
    assert goals["market_family"] == "total_goals"
    assert goals["period"] == "full_time"
    assert goals["team_scope"] == "all"
    assert goals["odds"] == 1.7
    assert btts["bookmaker"] == "Bet365"
    assert btts["market_family"] == "btts"
    assert btts["odds"] == 1.95
