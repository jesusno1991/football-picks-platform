import json
from typing import Any

from app.models import Match, Odds, TeamForm
from app.predictors.base import PredictionDraft, Predictor, stake_from_confidence
from app.utils.time import utc_now_naive


class GoalsMarketPredictor(Predictor):
    def __init__(
        self,
        code: str,
        market: str,
        selection: str,
        line: float | None,
        rate_field: str,
        minimum_sample: int = 10,
    ) -> None:
        self.code = code
        self.market = market
        self.selection = selection
        self.line = line
        self.rate_field = rate_field
        self.minimum_sample = minimum_sample

    def calculate_features(self, match: Match, home_form: TeamForm | None, away_form: TeamForm | None, odds: Odds | None) -> dict[str, Any]:
        if not home_form or not away_form:
            return {"data_status": "datos insuficientes", "combined_sample": 0}
        combined_sample = int(home_form.matches_sample or 0) + int(away_form.matches_sample or 0)
        expected_goals = (
            float(home_form.goals_for_avg or 0)
            + float(away_form.goals_against_avg or 0)
            + float(away_form.goals_for_avg or 0)
            + float(home_form.goals_against_avg or 0)
        ) / 2
        expected_xg = (
            float(home_form.xg_avg or 0)
            + float(away_form.xga_avg or 0)
            + float(away_form.xg_avg or 0)
            + float(home_form.xga_avg or 0)
        ) / 2
        shot_volume = ((home_form.shots_avg or 0) + (away_form.shots_avg or 0)) / 2
        sot_volume = ((home_form.shots_on_target_avg or 0) + (away_form.shots_on_target_avg or 0)) / 2
        big_chances = ((home_form.big_chances_avg or 0) + (away_form.big_chances_avg or 0)) / 2
        historical_rate = (float(getattr(home_form, self.rate_field) or 0) + float(getattr(away_form, self.rate_field) or 0)) / 2
        btts_support = ((home_form.btts_rate or 0) + (away_form.btts_rate or 0)) / 2
        return {
            "data_status": "ok" if combined_sample >= self.minimum_sample else "datos insuficientes",
            "combined_sample": combined_sample,
            "expected_goals": round(expected_goals, 3),
            "expected_xg": round(expected_xg, 3),
            "shot_volume": round(shot_volume, 3),
            "sot_volume": round(sot_volume, 3),
            "big_chances": round(big_chances, 3),
            "historical_rate": round(historical_rate, 3),
            "btts_support": round(btts_support, 3),
            "available_odds": odds.odds if odds else None,
        }

    def calculate_probability(self, features: dict[str, Any]) -> float | None:
        if features.get("data_status") != "ok":
            return None
        if self.market == "btts":
            base = 0.30 + features["btts_support"] * 0.42 + (features["expected_goals"] - 2.3) * 0.08
        elif self.line == 1.5:
            base = 0.42 + features["historical_rate"] * 0.35 + (features["expected_goals"] - 2.2) * 0.08 + (features["expected_xg"] - 2.1) * 0.05
        elif self.line == 2.5:
            base = 0.28 + features["historical_rate"] * 0.38 + (features["expected_goals"] - 2.5) * 0.10 + (features["sot_volume"] - 4.5) * 0.025
        elif self.line == 3.5:
            base = 0.15 + features["historical_rate"] * 0.35 + (features["expected_goals"] - 3.0) * 0.11 + (features["big_chances"] - 2.0) * 0.035
        else:
            base = features["historical_rate"]
        return round(max(0.05, min(0.86, base)), 4)

    def calculate_confidence(self, features: dict[str, Any]) -> float:
        sample = min(int(features.get("combined_sample", 0)), 40)
        if sample < self.minimum_sample:
            return 0.2
        data_strength = (features.get("shot_volume", 0) / 20) + (features.get("sot_volume", 0) / 8) + (features.get("expected_xg", 0) / 4)
        return round(min(0.86, 0.48 + sample / 120 + data_strength * 0.08), 3)

    def generate_explanation(self, features: dict[str, Any]) -> str:
        if features.get("data_status") != "ok":
            return "NO BET: datos insuficientes para estimar una ventaja estadística fiable."
        return (
            "Este pick se genera por combinación de media de goles, xG, tiros, tiros a puerta, grandes ocasiones, "
            f"frecuencia histórica del mercado y muestra de {features['combined_sample']} partidos."
        )

    def build_draft(self, match: Match, home_form: TeamForm | None, away_form: TeamForm | None, odds: Odds | None, system) -> PredictionDraft:
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
        draft.feature_snapshot = json.dumps(features, ensure_ascii=False)  # type: ignore[attr-defined]
        if self.should_publish(draft, match, system, features):
            draft.status = "published"
            draft.published_at = utc_now_naive()
        elif features.get("data_status") != "ok":
            draft.status = "insufficient_data"
        else:
            draft.status = "no_bet"
        return draft


def goals_predictors() -> list[GoalsMarketPredictor]:
    return [
        GoalsMarketPredictor("GOALS_OVER15_V1", "goals", "over", 1.5, "over_1_5_goals_rate"),
        GoalsMarketPredictor("GOALS_OVER25_V1", "goals", "over", 2.5, "over_2_5_goals_rate"),
        GoalsMarketPredictor("GOALS_OVER35_V1", "goals", "over", 3.5, "over_3_5_goals_rate"),
        GoalsMarketPredictor("BTTS_V1", "btts", "yes", None, "btts_rate"),
    ]
