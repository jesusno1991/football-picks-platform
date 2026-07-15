import json
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    ApiUsage,
    AutomationRun,
    CalibrationRun,
    Competition,
    DataQualitySnapshot,
    HistoricalSyncWindow,
    MarketRanking,
    Match,
    Player,
    Prediction,
    ProviderDataCoverage,
    ProviderEntityMapping,
    ProviderRawResponse,
    PublicationQueue,
    Referee,
    SquadMember,
    Standing,
    SyncJob,
    Team,
)
from app.utils.time import utc_now_naive


def rank_predictions(db: Session, limit: int = 500) -> dict:
    run = AutomationRun(engine="market_engine", task_name="rank_predictions", status="running")
    db.add(run)
    db.flush()
    created = 0
    updated = 0
    queued = 0
    predictions = list(
        db.scalars(
            select(Prediction)
            .where(Prediction.predicted_probability.is_not(None))
            .order_by(Prediction.generated_at.desc())
            .limit(limit)
        )
    )
    for prediction in predictions:
        score = _ranking_score(prediction)
        grade = _grade(score)
        decision = _publish_decision(prediction, grade, score)
        factors = {
            "probability": prediction.predicted_probability,
            "expected_value": prediction.expected_value,
            "confidence": prediction.confidence,
            "available_odds": prediction.available_odds,
            "stake": prediction.recommended_stake,
            "status": prediction.status,
        }
        ranking = db.scalar(select(MarketRanking).where(MarketRanking.prediction_id == prediction.id))
        if ranking:
            ranking.rank_score = score
            ranking.grade = grade
            ranking.publish_decision = decision
            ranking.factors_json = json.dumps(factors, ensure_ascii=False)
            ranking.ranked_at = utc_now_naive()
            updated += 1
        else:
            ranking = MarketRanking(
                prediction_id=prediction.id,
                match_id=prediction.match_id,
                market=prediction.market,
                selection=prediction.selection,
                line=prediction.line,
                rank_score=score,
                grade=grade,
                publish_decision=decision,
                factors_json=json.dumps(factors, ensure_ascii=False),
            )
            db.add(ranking)
            db.flush()
            created += 1
        if decision == "READY_FOR_REVIEW" and not db.scalar(select(PublicationQueue).where(PublicationQueue.prediction_id == prediction.id)):
            db.add(
                PublicationQueue(
                    prediction_id=prediction.id,
                    market_ranking_id=ranking.id,
                    channel="manual_review",
                    status="pending",
                    priority=max(1, int(100 - score)),
                    payload_json=json.dumps({"prediction_id": prediction.id, "grade": grade, "score": score}, ensure_ascii=False),
                )
            )
            queued += 1
    run.status = "success"
    run.finished_at = utc_now_naive()
    run.records_processed = len(predictions)
    run.summary_json = json.dumps({"created": created, "updated": updated, "queued": queued}, ensure_ascii=False)
    db.commit()
    return {"processed": len(predictions), "created": created, "updated": updated, "queued": queued}


def list_rankings(db: Session, limit: int = 100) -> list[dict]:
    rows = db.execute(
        select(MarketRanking, Prediction, Match)
        .join(Prediction, Prediction.id == MarketRanking.prediction_id)
        .join(Match, Match.id == MarketRanking.match_id)
        .order_by(MarketRanking.rank_score.desc(), MarketRanking.ranked_at.desc())
        .limit(limit)
    ).all()
    result = []
    for ranking, prediction, match in rows:
        result.append(
            {
                "prediction_id": prediction.id,
                "match_id": match.id,
                "market": ranking.market,
                "selection": ranking.selection,
                "line": ranking.line,
                "rank_score": round(ranking.rank_score, 2),
                "grade": ranking.grade,
                "publish_decision": ranking.publish_decision,
                "expected_value": prediction.expected_value,
                "confidence": prediction.confidence,
                "probability": prediction.predicted_probability,
                "ranked_at": ranking.ranked_at.isoformat(),
            }
        )
    if result:
        return result
    return _live_rankings_from_predictions(db, limit)


def foundation_report(db: Session) -> dict:
    counts = {
        "matches": _count(db, Match),
        "competitions": _count(db, Competition),
        "teams": _count(db, Team),
        "players": _count(db, Player),
        "referees": _count(db, Referee),
        "squad_members": _count(db, SquadMember),
        "standings": _count(db, Standing),
        "raw_responses": _count(db, ProviderRawResponse),
        "provider_mappings": _count(db, ProviderEntityMapping),
        "api_usage": _count(db, ApiUsage),
        "sync_jobs": _count(db, SyncJob),
        "historical_sync_windows": _count(db, HistoricalSyncWindow),
        "data_quality_snapshots": _count(db, DataQualitySnapshot),
        "provider_data_coverage": _count(db, ProviderDataCoverage),
        "market_rankings": _count(db, MarketRanking),
        "publication_queue": _count(db, PublicationQueue),
        "calibration_runs": _count(db, CalibrationRun),
    }
    modules = {
        "frontend": "React/Vite information hub with picks and predictions preserved",
        "backend_api": "FastAPI resource API",
        "providers": "API-Football and FlashScore provider adapters",
        "scheduler_ready": "sync_jobs and historical_sync_windows tables prepared",
        "market_engine": "market definitions, evaluations and rankings",
        "publication_engine": "publication_queue prepared; no automatic publish changed",
        "calibration_engine": "calibration tables prepared",
        "audit": "raw snapshots, mappings, api usage and model audit tables",
    }
    missing_or_unpopulated = [key for key, value in counts.items() if value == 0]
    production_notes = [
        "The system stores canonical fields plus raw JSON snapshots for future API fields.",
        "No unavailable provider data is invented; UI must show No disponible.",
        "Publication behavior remains unchanged; queue is review-first.",
        "Historical sync is ready, but full backfill depends on API quota and admin token.",
    ]
    return {
        "generated_at": utc_now_naive().isoformat(),
        "counts": counts,
        "modules": modules,
        "missing_or_unpopulated": missing_or_unpopulated,
        "production_notes": production_notes,
    }


def seed_historical_windows(db: Session, provider: str, date_from: datetime, date_to: datetime, scope: str = "fixtures") -> dict:
    existing = db.scalar(
        select(HistoricalSyncWindow).where(
            HistoricalSyncWindow.provider == provider,
            HistoricalSyncWindow.date_from == date_from,
            HistoricalSyncWindow.date_to == date_to,
            HistoricalSyncWindow.scope == scope,
        )
    )
    if existing:
        return {"created": 0, "existing": 1}
    db.add(HistoricalSyncWindow(provider=provider, scope=scope, date_from=date_from, date_to=date_to, status="pending", priority=50))
    db.commit()
    return {"created": 1, "existing": 0}


def _ranking_score(prediction: Prediction) -> float:
    probability = (prediction.predicted_probability or 0) * 100
    ev = max(-0.25, min(0.5, prediction.expected_value or 0)) * 80
    confidence = (prediction.confidence or 0) * 100
    odds_bonus = 8 if prediction.available_odds and prediction.available_odds > 1.01 else -18
    stake_bonus = min(8, max(0, prediction.recommended_stake or 0))
    return max(0, min(100, probability * 0.32 + confidence * 0.28 + ev + odds_bonus + stake_bonus))


def _grade(score: float) -> str:
    if score >= 92:
        return "S+"
    if score >= 85:
        return "S"
    if score >= 75:
        return "A"
    if score >= 62:
        return "B"
    if score >= 45:
        return "C"
    return "NO_PUBLICAR"


def _publish_decision(prediction: Prediction, grade: str, score: float) -> str:
    if prediction.status == "published" and grade in {"S+", "S", "A"} and (prediction.expected_value or 0) > 0:
        return "READY_FOR_REVIEW"
    if grade in {"S+", "S", "A"} and (prediction.expected_value or 0) > 0:
        return "WATCH"
    return "NO_PUBLICAR"


def _live_rankings_from_predictions(db: Session, limit: int) -> list[dict]:
    rows = db.execute(
        select(Prediction, Match)
        .join(Match, Match.id == Prediction.match_id)
        .where(Prediction.predicted_probability.is_not(None))
        .order_by(Prediction.generated_at.desc())
        .limit(limit)
    ).all()
    result = []
    for prediction, match in rows:
        score = _ranking_score(prediction)
        grade = _grade(score)
        result.append(
            {
                "prediction_id": prediction.id,
                "match_id": match.id,
                "market": prediction.market,
                "selection": prediction.selection,
                "line": prediction.line,
                "rank_score": round(score, 2),
                "grade": grade,
                "publish_decision": _publish_decision(prediction, grade, score),
                "expected_value": prediction.expected_value,
                "confidence": prediction.confidence,
                "probability": prediction.predicted_probability,
                "ranked_at": utc_now_naive().isoformat(),
            }
        )
    return sorted(result, key=lambda item: item["rank_score"], reverse=True)


def _count(db: Session, model) -> int:
    return int(db.scalar(select(func.count(model.id))) or 0)
