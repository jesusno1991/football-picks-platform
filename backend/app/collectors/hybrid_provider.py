from __future__ import annotations

from datetime import date
from typing import Any

from app.collectors.api_football_provider import ApiFootballProvider
from app.collectors.base import FootballDataProvider
from app.collectors.flashscore_provider import FlashScoreRapidApiProvider
from app.core.config import get_settings


class HybridFootballDataProvider(FootballDataProvider):
    """API-Football primary provider with FlashScore as secondary calendar fallback."""

    def __init__(self) -> None:
        self.primary = ApiFootballProvider()
        self.settings = get_settings()
        self.secondary = FlashScoreRapidApiProvider() if self.settings.rapidapi_key else None
        self._last_match_source = "api_football"
        self._last_primary_error: str | None = None
        self._last_secondary_error: str | None = None

    def get_competitions(self) -> list[dict[str, Any]]:
        competitions = {item["external_id"]: item for item in self.primary.get_competitions()}
        if self.secondary:
            competitions.update({item["external_id"]: item for item in self.secondary.get_competitions()})
        return list(competitions.values())

    def get_matches(self, match_date: date) -> list[dict[str, Any]]:
        try:
            matches = self.primary.get_matches(match_date)
            if matches:
                self._last_match_source = "api_football"
                return matches
        except Exception as exc:
            self._last_primary_error = str(exc)
        if not self.secondary:
            if self._last_primary_error:
                raise RuntimeError(self._last_primary_error)
            return []
        try:
            matches = self.secondary.get_matches(match_date)
            self._last_match_source = "flashscore"
            return matches
        except Exception as exc:
            self._last_secondary_error = str(exc)
            if self._last_primary_error:
                raise RuntimeError(f"Primary failed: {self._last_primary_error}; secondary failed: {exc}") from exc
            raise

    def get_match(self, match_id: str) -> dict[str, Any] | None:
        if match_id.startswith("flashscore-") and self.secondary:
            return self.secondary.get_match(match_id)
        return self.primary.get_match(match_id)

    def get_team_history(self, team_id: str) -> dict[str, Any]:
        if team_id.startswith("flashscore-team-") and self.secondary:
            return self.secondary.get_team_history(team_id)
        return self.primary.get_team_history(team_id)

    def get_team_history_for_match(self, match_id: str, team_id: str) -> dict[str, Any]:
        if match_id.startswith("flashscore-") and self.secondary:
            return self.secondary.get_team_history_for_match(match_id, team_id)
        return self.primary.get_team_history(team_id)

    def get_match_statistics(self, match_id: str) -> list[dict[str, Any]]:
        if match_id.startswith("flashscore-") and self.secondary:
            return self.secondary.get_match_statistics(match_id)
        return self.primary.get_match_statistics(match_id)

    def get_odds(self, match_id: str) -> list[dict[str, Any]]:
        if match_id.startswith("flashscore-") and self.secondary:
            return self.secondary.get_odds(match_id)
        return self.primary.get_odds(match_id)

    def get_results(self, match_date: date) -> list[dict[str, Any]]:
        return self.primary.get_results(match_date)

    def get_events(self, match_id: str) -> list[dict[str, Any]]:
        if match_id.startswith("flashscore-") and self.secondary:
            return self.secondary.get_events(match_id)
        return self.primary.get_events(match_id)

    def get_lineups(self, match_id: str) -> list[dict[str, Any]]:
        if match_id.startswith("flashscore-") and self.secondary:
            return self.secondary.get_lineups(match_id)
        return self.primary.get_lineups(match_id)

    def get_standings(self, competition_external_id: str, season: str) -> list[dict[str, Any]]:
        if competition_external_id.startswith("flashscore-") and self.secondary:
            return self.secondary.get_standings(competition_external_id, season)
        return self.primary.get_standings(competition_external_id, season)

    def diagnostics(self, match_date: date) -> dict[str, Any]:
        primary = self.primary.diagnostics(match_date)
        secondary = self.secondary.diagnostics(match_date) if self.secondary and hasattr(self.secondary, "diagnostics") else None
        return {
            "provider": "hybrid",
            "primary": primary,
            "secondary": secondary,
            "last_match_source": self._last_match_source,
            "last_primary_error": self._last_primary_error,
            "last_secondary_error": self._last_secondary_error,
            "ok": bool(primary.get("ok")) or bool(secondary and secondary.get("ok")),
        }
