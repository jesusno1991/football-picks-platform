from datetime import date

from app.collectors.hybrid_provider import HybridFootballDataProvider
from app.core.config import get_settings


def test_hybrid_provider_prefers_api_football(monkeypatch):
    monkeypatch.setenv("API_FOOTBALL_KEY", "test-key")
    monkeypatch.setenv("RAPIDAPI_KEY", "rapid-key")
    get_settings.cache_clear()

    class Primary:
        def get_matches(self, match_date):
            return [{"external_id": "api-football-1"}]

        def get_competitions(self):
            return []

        def diagnostics(self, match_date):
            return {"ok": True}

    class Secondary:
        def get_matches(self, match_date):
            raise AssertionError("secondary should not be used when primary has matches")

        def get_competitions(self):
            return []

        def diagnostics(self, match_date):
            return {"ok": True}

    monkeypatch.setattr("app.collectors.hybrid_provider.ApiFootballProvider", Primary)
    monkeypatch.setattr("app.collectors.hybrid_provider.FlashScoreRapidApiProvider", Secondary)

    provider = HybridFootballDataProvider()

    assert provider.get_matches(date(2026, 7, 15)) == [{"external_id": "api-football-1"}]
    assert provider.diagnostics(date(2026, 7, 15))["last_match_source"] == "api_football"


def test_hybrid_provider_falls_back_to_flashscore_when_primary_empty(monkeypatch):
    monkeypatch.setenv("API_FOOTBALL_KEY", "test-key")
    monkeypatch.setenv("RAPIDAPI_KEY", "rapid-key")
    get_settings.cache_clear()

    class Primary:
        def get_matches(self, match_date):
            return []

        def get_competitions(self):
            return []

        def diagnostics(self, match_date):
            return {"ok": True}

    class Secondary:
        def get_matches(self, match_date):
            return [{"external_id": "flashscore-1"}]

        def get_competitions(self):
            return []

        def diagnostics(self, match_date):
            return {"ok": True}

    monkeypatch.setattr("app.collectors.hybrid_provider.ApiFootballProvider", Primary)
    monkeypatch.setattr("app.collectors.hybrid_provider.FlashScoreRapidApiProvider", Secondary)

    provider = HybridFootballDataProvider()

    assert provider.get_matches(date(2026, 7, 15)) == [{"external_id": "flashscore-1"}]
    assert provider.diagnostics(date(2026, 7, 15))["last_match_source"] == "flashscore"
