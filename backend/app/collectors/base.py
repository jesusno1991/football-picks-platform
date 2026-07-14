from abc import ABC, abstractmethod
from datetime import date, timedelta
from typing import Any


class FootballDataProvider(ABC):
    @abstractmethod
    def get_competitions(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_matches(self, match_date: date) -> list[dict[str, Any]]:
        raise NotImplementedError

    def get_matches_by_date(self, match_date: date) -> list[dict[str, Any]]:
        return self.get_matches(match_date)

    def get_matches_by_range(self, date_from: date, date_to: date) -> list[dict[str, Any]]:
        matches: list[dict[str, Any]] = []
        current = date_from
        while current <= date_to:
            matches.extend(self.get_matches_by_date(current))
            current += timedelta(days=1)
        return matches

    def get_matches_by_competition_season(self, competition_id: str, season: str) -> list[dict[str, Any]]:
        return []

    @abstractmethod
    def get_match(self, match_id: str) -> dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    def get_team_history(self, team_id: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_match_statistics(self, match_id: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_odds(self, match_id: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_results(self, match_date: date) -> list[dict[str, Any]]:
        raise NotImplementedError
