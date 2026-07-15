from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Match, Prediction
from app.predictors.registry import get_predictors
from app.repositories.queries import get_prediction_system, latest_odds, latest_team_form, list_matches
from app.services.collection_service import upsert_prediction_systems
from app.services.tipstrr_market_service import build_tipstrr_predictions


def generate_predictions(db: Session) -> dict[str, int]:
    upsert_prediction_systems(db)
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
        system = get_prediction_system(db, "TIPSTRR_MARKET_ENGINE")
        if system and system.is_active:
            for prediction in build_tipstrr_predictions(db, match, system):
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
        _select_best_market_for_match(db, match.id)
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
    return db.scalar(
        select(Prediction).where(
            Prediction.match_id == prediction.match_id,
            Prediction.system_id == prediction.system_id,
            Prediction.market == prediction.market,
            Prediction.selection == prediction.selection,
            Prediction.line == prediction.line,
        )
    )


def _select_best_market_for_match(db: Session, match_id: int) -> None:
    predictions = list(db.scalars(select(Prediction).where(Prediction.match_id == match_id)))
    publishable = [prediction for prediction in predictions if _is_publishable_market_candidate(prediction)]
    if not publishable:
        for prediction in predictions:
            if prediction.status == "published":
                prediction.status = "no_bet"
                prediction.published_at = None
                prediction.explanation = _append_optimizer_reason(prediction.explanation, "No publicado: no supera el filtro global de EV/liquidez.")
        return

    publishable.sort(
        key=lambda prediction: (
            prediction.expected_value or -999,
            prediction.confidence or 0,
            prediction.predicted_probability or 0,
        ),
        reverse=True,
    )
    best = publishable[0]
    for prediction in predictions:
        if prediction.id == best.id or prediction is best:
            prediction.status = "published"
            prediction.explanation = _append_optimizer_reason(prediction.explanation, "Mercado optimo del partido por EV.")
            continue
        if prediction.status == "published":
            prediction.status = "no_bet"
            prediction.published_at = None
            prediction.explanation = _append_optimizer_reason(prediction.explanation, "No publicado: existe otro mercado del partido con mayor EV.")


def _is_publishable_market_candidate(prediction: Prediction) -> bool:
    if prediction.available_odds is None or prediction.available_odds < 1.25 or prediction.available_odds > 8:
        return False
    if prediction.expected_value is None or prediction.expected_value <= 0.03:
        return False
    if prediction.predicted_probability is None:
        return False
    return prediction.status == "published"


def _append_optimizer_reason(explanation: str, reason: str) -> str:
    if reason in explanation:
        return explanation
    return f"{explanation} {reason}"
