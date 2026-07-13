from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Match, Prediction
from app.predictors.registry import get_predictors
from app.repositories.queries import get_prediction_system, latest_odds, latest_team_form, list_matches


def generate_predictions(db: Session) -> dict[str, int]:
    created = 0
    updated = 0
    skipped = 0
    for match in list_matches(db):
        for predictor in get_predictors():
            system = get_prediction_system(db, predictor.code)
            if not system or not system.is_active:
                skipped += 1
                continue
            prediction = _build_prediction(db, match, predictor, system)
            existing = _find_existing(db, prediction)
            if existing:
                for field in (
                    "predicted_probability",
                    "fair_odds",
                    "available_odds",
                    "expected_value",
                    "confidence",
                    "recommended_stake",
                    "explanation",
                    "feature_snapshot",
                    "status",
                    "published_at",
                ):
                    setattr(existing, field, getattr(prediction, field))
                updated += 1
            else:
                db.add(prediction)
                try:
                    db.flush()
                    created += 1
                except IntegrityError:
                    db.rollback()
                    skipped += 1
    db.commit()
    return {"created": created, "updated": updated, "skipped": skipped}


def _build_prediction(db: Session, match: Match, predictor, system) -> Prediction:
    home_form = latest_team_form(db, match.home_team_id, match.competition_id)
    away_form = latest_team_form(db, match.away_team_id, match.competition_id)
    odds = latest_odds(db, match.id, predictor.market, predictor.selection, predictor.line)
    draft = predictor.build_draft(match, home_form, away_form, odds, system)
    return Prediction(
        match_id=match.id,
        system_id=system.id,
        market=draft.market,
        selection=draft.selection,
        line=draft.line,
        predicted_probability=draft.predicted_probability,
        fair_odds=draft.fair_odds,
        available_odds=draft.available_odds,
        expected_value=draft.expected_value,
        confidence=draft.confidence,
        recommended_stake=draft.recommended_stake,
        explanation=draft.explanation,
        feature_snapshot=draft.feature_snapshot,
        status=draft.status,
        published_at=draft.published_at,
    )


def _find_existing(db: Session, prediction: Prediction) -> Prediction | None:
    from sqlalchemy import select

    return db.scalar(
        select(Prediction).where(
            Prediction.match_id == prediction.match_id,
            Prediction.system_id == prediction.system_id,
            Prediction.market == prediction.market,
            Prediction.selection == prediction.selection,
            Prediction.line == prediction.line,
        )
    )
