from datetime import date

from app.collectors.flashscore_provider import FlashScoreRapidApiProvider
from app.core.config import get_settings


class Response:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.text = str(payload)

    def json(self):
        return self._payload


def test_flashscore_live_matches_normalize_status_and_score(monkeypatch):
    monkeypatch.setenv("RAPIDAPI_KEY", "rapid-key")
    get_settings.cache_clear()

    def fake_get(url, headers=None, timeout=20):
        assert "x-rapidapi-key" in headers
        return Response(
            {
                "matches": [
                    {
                        "id": "abc123",
                        "homeTeam": {"id": "h1", "name": "Home FC"},
                        "awayTeam": {"id": "a1", "name": "Away FC"},
                        "tournament": {"id": "t1", "name": "Live League"},
                        "country": {"name": "World"},
                        "match_status": {"stage": "2nd Half", "is_in_progress": True, "live_minute": 56},
                        "status": {"type": "inprogress", "description": "2nd half"},
                        "homeScore": {"current": 2},
                        "awayScore": {"current": 1},
                        "startTimestamp": 1784131200,
                    }
                ]
            }
        )

    monkeypatch.setattr("app.collectors.flashscore_provider.httpx.get", fake_get)

    matches = FlashScoreRapidApiProvider().get_live_matches()

    assert matches[0]["external_id"] == "flashscore-abc123"
    assert matches[0]["status"] == "2H"
    assert matches[0]["live_minute"] == 56
    assert matches[0]["home_score"] == 2
    assert matches[0]["away_score"] == 1


def test_flashscore_match_stats_normalize_to_internal_statistics(monkeypatch):
    monkeypatch.setenv("RAPIDAPI_KEY", "rapid-key")
    get_settings.cache_clear()

    def fake_get(url, headers=None, timeout=20):
        return Response(
            [
                {"name": "Shots on target", "home": 5, "away": 2},
                {"name": "Shots", "home": 12, "away": 6},
                {"name": "Corners", "home": 7, "away": 3},
                {"name": "Dangerous attacks", "home": 42, "away": 18},
            ]
        )

    monkeypatch.setattr("app.collectors.flashscore_provider.httpx.get", fake_get)

    stats = FlashScoreRapidApiProvider().get_match_statistics("flashscore-abc123")

    home = {row["type"]: row["value"] for row in stats[0]["statistics"]}
    away = {row["type"]: row["value"] for row in stats[1]["statistics"]}
    assert home["Shots on Goal"] == 5
    assert away["Shots on Goal"] == 2
    assert home["Corner Kicks"] == 7
    assert home["Dangerous Attacks"] == 42
