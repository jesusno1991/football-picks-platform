from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from app.models import Match, Odds, PredictionSystem, TeamForm


@dataclass
class PredictionDraft:
    market: str
    selection: str
    line: float | None
    predicted_probability: float | None
    fair_odds: float | None
    available_odds: float | None
    expected_value: float | None
    confidence: float | None
    recommended_stake: float
    explanation: str
    status: str
    published_at: datetime | None
    feature_snapshot: str | None = None


class Predictor(ABC):
    code: str

    @abstractmethod
    def calculate_features(self, match: Match, home_form: TeamForm | None, away_form: TeamForm | None, odds: Odds | None) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def calculate_probability(self, features: dict[str, Any]) -> float | None:
        raise NotImplementedError

    def calculate_fair_odds(self, probability: float | None) -> float | None:
        if probability is None or probability <= 0:
            return None
        return round(1 / probability, 3)

    def calculate_expected_value(self, probability: float | None, available_odds: float | None) -> float | None:
        if probability is None or available_odds is None:
            return None
        return round(probability * available_odds - 1, 4)

    @abstractmethod
    def calculate_confidence(self, features: dict[str, Any]) -> float:
        raise NotImplementedError

    @abstractmethod
    def generate_explanation(self, features: dict[str, Any]) -> str:
        raise NotImplementedError

    def should_publish(self, draft: PredictionDraft, match: Match, system: PredictionSystem, features: dict[str, Any]) -> bool:
        if match.kickoff_at <= datetime.utcnow() + timedelta(minutes=15):
            return False
        if int(features.get("combined_sample", 0)) < 10:
            return False
        if draft.predicted_probability is None or draft.predicted_probability < system.minimum_probability:
            return False
        if draft.available_odds is None or draft.fair_odds is None or draft.available_odds <= draft.fair_odds:
            return False
        if draft.expected_value is None or draft.expected_value <= system.minimum_value:
            return False
        if draft.available_odds < 1.4 or draft.available_odds > 3.5:
            return False
        return True


def stake_from_confidence(confidence: float) -> float:
    if confidence >= 0.82:
        return 2
    return 1
