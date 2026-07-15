from datetime import datetime, timedelta

from app.models import Match, Odds, PredictionSystem, TeamForm
from app.predictors.corners_over_95 import CornersOver95Predictor
from app.utils.time import utc_now_naive


def test_corners_predictor_returns_insufficient_data_without_sample():
    predictor = CornersOver95Predictor()
    features = predictor.calculate_features(match=None, home_form=None, away_form=None, odds=None)  # type: ignore[arg-type]

    assert features["data_status"] == "datos insuficientes"
    assert predictor.calculate_probability(features) is None


def test_corners_predictor_can_publish_with_value():
    predictor = CornersOver95Predictor()
    match = Match(
        external_id="m1",
        competition_id=1,
        home_team_id=1,
        away_team_id=2,
        kickoff_at=utc_now_naive() + timedelta(hours=3),
        status="scheduled",
        season="2026",
    )
    home_form = TeamForm(
        team_id=1,
        competition_id=1,
        reference_date=utc_now_naive(),
        matches_sample=10,
        corners_for_avg=6.5,
        corners_against_avg=4.5,
        shots_avg=15,
        over_9_5_corners_rate=0.66,
    )
    away_form = TeamForm(
        team_id=2,
        competition_id=1,
        reference_date=utc_now_naive(),
        matches_sample=10,
        corners_for_avg=5.9,
        corners_against_avg=5.2,
        shots_avg=14,
        over_9_5_corners_rate=0.62,
    )
    odds = Odds(match_id=1, bookmaker="Mock", market="corners", selection="over", line=9.5, odds=2.05)
    system = PredictionSystem(
        code="CORNERS_OVER_95",
        name="Over corners",
        description="test",
        market="corners",
        minimum_probability=0.56,
        minimum_value=0.03,
    )

    draft = predictor.build_draft(match, home_form, away_form, odds, system)

    assert draft.predicted_probability is not None
    assert draft.fair_odds == round(1 / draft.predicted_probability, 3)
    assert draft.expected_value is not None
