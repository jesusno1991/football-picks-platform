from abc import ABC, abstractmethod
from datetime import date
from typing import Any


class FootballDataProvider(ABC):
    @abstractmethod
    def get_competitions(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_matches(self, match_date: date) -> list[dict[str, Any]]:
        raise NotImplementedError

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
