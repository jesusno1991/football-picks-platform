from typing import Any

from app.models import Match, Odds, TeamForm
from app.predictors.base import Predictor, stake_from_confidence


class CornersOver95Predictor(Predictor):
    code = "CORNERS_OVER_95"
    market = "corners"
    selection = "over"
    line = 9.5

    def calculate_features(self, match: Match, home_form: TeamForm | None, away_form: TeamForm | None, odds: Odds | None) -> dict[str, Any]:
        if not home_form or not away_form:
            return {"data_status": "datos insuficientes", "combined_sample": 0}
        combined_sample = int(home_form.matches_sample or 0) + int(away_form.matches_sample or 0)
        expected_corners = (
            float(home_form.corners_for_avg or 0)
            + float(away_form.corners_against_avg or 0)
            + float(away_form.corners_for_avg or 0)
            + float(home_form.corners_against_avg or 0)
        ) / 2
        historical_rate = ((home_form.over_9_5_corners_rate or 0) + (away_form.over_9_5_corners_rate or 0)) / 2
        shot_volume = ((home_form.shots_avg or 0) + (away_form.shots_avg or 0)) / 2
        possession_balance = abs((home_form.possession_avg or 50) - (away_form.possession_avg or 50))
        return {
            "data_status": "ok" if combined_sample >= 10 else "datos insuficientes",
            "combined_sample": combined_sample,
            "expected_corners": expected_corners,
            "historical_rate": historical_rate,
            "shot_volume": shot_volume,
            "possession_balance": possession_balance,
            "available_odds": odds.odds if odds else None,
        }

    def calculate_probability(self, features: dict[str, Any]) -> float | None:
        if features.get("data_status") != "ok":
            return None
        expected_corners = float(features["expected_corners"])
        historical_rate = float(features["historical_rate"])
        shot_volume = float(features["shot_volume"])
        base = 0.42 + (expected_corners - 9.0) * 0.055 + (historical_rate - 0.50) * 0.35 + (shot_volume - 12.0) * 0.01
        return round(max(0.05, min(0.82, base)), 4)

    def calculate_confidence(self, features: dict[str, Any]) -> float:
        sample = min(int(features.get("combined_sample", 0)), 30)
        if sample < 10:
            return 0.25
        expected_corners = float(features.get("expected_corners", 0))
        distance = max(0, expected_corners - 9.5)
        return round(min(0.82, 0.52 + sample / 100 + distance * 0.04), 3)

    def generate_explanation(self, features: dict[str, Any]) -> str:
        if features.get("data_status") != "ok":
            return "Datos insuficientes: se necesitan al menos 10 partidos históricos combinados."
        return (
            "Pick basado en medias prepartido de córners a favor/en contra, frecuencia histórica del over 9,5, "
            f"volumen de tiros y muestra combinada de {features['combined_sample']} partidos."
        )

    def build_draft(self, match: Match, home_form: TeamForm | None, away_form: TeamForm | None, odds: Odds | None, system) -> Any:
        from datetime import datetime

        from app.predictors.base import PredictionDraft

        features = self.calculate_features(match, home_form, away_form, odds)
        probability = self.calculate_probability(features)
        fair_odds = self.calculate_fair_odds(probability)
        available_odds = odds.odds if odds else None
        expected_value = self.calculate_expected_value(probability, available_odds)
        confidence = self.calculate_confidence(features)
        draft = PredictionDraft(
            market=self.market,
            selection=self.selection,
            line=self.line,
            predicted_probability=probability,
            fair_odds=fair_odds,
            available_odds=available_odds,
            expected_value=expected_value,
            confidence=confidence,
            recommended_stake=stake_from_confidence(confidence),
            explanation=self.generate_explanation(features),
            status="candidate",
            published_at=None,
        )
        if self.should_publish(draft, match, system, features):
            draft.status = "published"
            draft.published_at = datetime.utcnow()
        elif features.get("data_status") != "ok":
            draft.status = "insufficient_data"
        else:
            draft.status = "not_published"
        return draft
