import calendar
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.collectors.factory import get_provider
from app.database import get_db, init_db
from app.models import Competition, Match, Odds, Prediction, SystemPerformance, Team, TeamForm, TeamMatchStatistics
from app.repositories import queries
from app.schemas.schemas import (
    CalendarDayRead,
    CompetitionRead,
    MarketEvaluationRead,
    MatchDetailRead,
    MatchListRead,
    PredictionRead,
    TeamRead,
    TipstrrMarketPickRead,
)
from app.services.collection_service import collect_mock_data, collect_schedule_data, collect_schedule_range
from app.services.goal_market_engine import evaluate_match_markets
from app.services.prediction_service import generate_predictions
from app.services.settlement_service import verify_results
from app.services.statistics_service import (
    overview,
    performance_by_competition,
    performance_by_market,
    performance_by_system,
    profit_curve,
)
from app.services.tipstrr_market_service import list_tipstrr_market_picks
from app.core.config import get_settings
from app.utils.dates import local_date_from_utc_naive

router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/provider/status")
def provider_status(match_date: date | None = Query(default=None, alias="date")) -> dict:
    provider = get_provider()
    if hasattr(provider, "diagnostics"):
        return provider.diagnostics(match_date or date.today())
    return {"provider": provider.__class__.__name__, "ok": True}


@router.get("/matches", response_model=list[MatchListRead])
def get_matches(
    match_date: date | None = Query(default=None, alias="date"),
    country: str | None = None,
    competition_id: int | None = None,
    team: str | None = None,
    db: Session = Depends(get_db),
) -> list[MatchListRead]:
    if match_date:
        _ensure_date_loaded(db, match_date)
    matches = queries.list_matches(db, match_date, country, competition_id, team)
    pick_counts = queries.pick_counts_by_match(db)
    return [_match_list_read(match, pick_counts.get(match.id, 0)) for match in matches]


@router.get("/matches/range", response_model=list[MatchListRead])
def get_matches_range(
    date_from: date,
    date_to: date,
    db: Session = Depends(get_db),
) -> list[MatchListRead]:
    if date_to < date_from:
        raise HTTPException(status_code=400, detail="date_to debe ser mayor o igual que date_from")
    matches = queries.list_matches_range(db, date_from, date_to)
    pick_counts = queries.pick_counts_by_match(db)
    return [_match_list_read(match, pick_counts.get(match.id, 0)) for match in matches]


@router.get("/calendar/month", response_model=list[CalendarDayRead])
def get_calendar_month(year: int, month: int, db: Session = Depends(get_db)) -> list[CalendarDayRead]:
    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="Mes no valido")
    last_day = calendar.monthrange(year, month)[1]
    start = date(year, month, 1)
    end = date(year, month, last_day)
    matches = queries.list_matches_range(db, start, end)
    timezone_name = get_settings().app_timezone
    grouped: dict[date, dict[str, set | int]] = {
        date(year, month, day): {"matches": 0, "picks": 0, "published": 0, "competitions": set()} for day in range(1, last_day + 1)
    }
    for match in matches:
        local_day = local_date_from_utc_naive(match.kickoff_at, timezone_name)
        if local_day not in grouped:
            continue
        grouped[local_day]["matches"] = int(grouped[local_day]["matches"]) + 1
        grouped[local_day]["competitions"].add(match.competition_id)  # type: ignore[union-attr]
        grouped[local_day]["picks"] = int(grouped[local_day]["picks"]) + len(match.predictions)
        grouped[local_day]["published"] = int(grouped[local_day]["published"]) + len([p for p in match.predictions if p.status == "published"])
    return [
        CalendarDayRead(
            date=day.isoformat(),
            match_count=int(values["matches"]),
            pick_count=int(values["picks"]),
            published_pick_count=int(values["published"]),
            competition_count=len(values["competitions"]),  # type: ignore[arg-type]
        )
        for day, values in sorted(grouped.items())
    ]


@router.get("/matches/{match_id}", response_model=MatchDetailRead)
def get_match(match_id: int, db: Session = Depends(get_db)) -> MatchDetailRead:
    match = queries.get_match(db, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Partido no encontrado")
    row = _match_list_read(match, len([prediction for prediction in match.predictions if prediction.status == "published"]))
    return MatchDetailRead(
        **row.model_dump(),
        home_form=queries.latest_team_form(db, match.home_team_id, match.competition_id),
        away_form=queries.latest_team_form(db, match.away_team_id, match.competition_id),
        predictions=match.predictions,
    )


@router.get("/matches/{match_id}/markets", response_model=list[MarketEvaluationRead])
def get_match_markets(match_id: int, db: Session = Depends(get_db)) -> list[MarketEvaluationRead]:
    if not queries.get_match(db, match_id):
        raise HTTPException(status_code=404, detail="Partido no encontrado")
    return evaluate_match_markets(db, match_id)


@router.get("/tipstrr-market-picks", response_model=list[TipstrrMarketPickRead])
def get_tipstrr_market_picks(
    match_date: date | None = Query(default=None, alias="date"),
    decision: str | None = None,
    db: Session = Depends(get_db),
) -> list[TipstrrMarketPickRead]:
    target_date = match_date or date.today()
    _ensure_date_loaded(db, target_date)
    return list_tipstrr_market_picks(db, target_date, decision)


@router.get("/competitions", response_model=list[CompetitionRead])
def get_competitions(db: Session = Depends(get_db)):
    return queries.list_competitions(db)


@router.get("/teams/{team_id}", response_model=TeamRead)
def get_team(team_id: int, db: Session = Depends(get_db)):
    team = queries.get_team(db, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    return team


@router.get("/predictions", response_model=list[PredictionRead])
def get_predictions(
    status: str | None = None,
    market: str | None = None,
    match_date: date | None = Query(default=None, alias="date"),
    db: Session = Depends(get_db),
):
    if match_date:
        _ensure_date_loaded(db, match_date)
        return queries.list_predictions_for_date(db, match_date, status, market)
    return queries.list_predictions(db, status, market)


@router.get("/predictions/{prediction_id}", response_model=PredictionRead)
def get_prediction(prediction_id: int, db: Session = Depends(get_db)):
    prediction = queries.get_prediction(db, prediction_id)
    if not prediction:
        raise HTTPException(status_code=404, detail="Predicción no encontrada")
    return prediction


@router.get("/statistics/overview")
def statistics_overview(db: Session = Depends(get_db)):
    return overview(db)


@router.get("/statistics/systems")
def statistics_systems(db: Session = Depends(get_db)):
    return performance_by_system(db)


@router.get("/statistics/markets")
def statistics_markets(db: Session = Depends(get_db)):
    return performance_by_market(db)


@router.get("/statistics/competitions")
def statistics_competitions(db: Session = Depends(get_db)):
    return performance_by_competition(db)


@router.get("/statistics/profit-curve")
def statistics_profit_curve(db: Session = Depends(get_db)):
    return profit_curve(db)


@router.post("/admin/collect", dependencies=[Depends(require_admin)])
def admin_collect(match_date: date | None = None, db: Session = Depends(get_db)):
    init_db()
    try:
        return collect_mock_data(db, match_date)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/admin/import-range", dependencies=[Depends(require_admin)])
def admin_import_range(date_from: date, date_to: date, db: Session = Depends(get_db)):
    if date_to < date_from:
        raise HTTPException(status_code=400, detail="date_to debe ser mayor o igual que date_from")
    init_db()
    return collect_schedule_range(db, date_from, date_to)


@router.post("/admin/generate-predictions", dependencies=[Depends(require_admin)])
def admin_generate_predictions(db: Session = Depends(get_db)):
    return generate_predictions(db)


@router.post("/admin/verify-results", dependencies=[Depends(require_admin)])
def admin_verify_results(db: Session = Depends(get_db)):
    return verify_results(db)


@router.post("/admin/recalculate-statistics", dependencies=[Depends(require_admin)])
def admin_recalculate_statistics(db: Session = Depends(get_db)):
    return overview(db)


@router.post("/admin/clear-data", dependencies=[Depends(require_admin)])
def admin_clear_data(db: Session = Depends(get_db)):
    for model in (SystemPerformance, Prediction, Odds, TeamMatchStatistics, TeamForm, Match, Team, Competition):
        db.execute(delete(model))
    db.commit()
    return {"status": "cleared"}


def _match_list_read(match, pick_count: int) -> MatchListRead:
    published = [prediction for prediction in match.predictions if prediction.status == "published"]
    candidates = [prediction for prediction in match.predictions if prediction.predicted_probability is not None]
    candidates.sort(key=lambda prediction: (prediction.expected_value or -999, prediction.confidence or 0), reverse=True)
    best = published[0] if published else (candidates[0] if candidates else None)
    return MatchListRead(
        id=match.id,
        external_id=match.external_id,
        kickoff_at=match.kickoff_at,
        status=match.status,
        venue=match.venue,
        round=match.round,
        season=match.season,
        competition=CompetitionRead.model_validate(match.competition),
        home_team=TeamRead.model_validate(match.home_team),
        away_team=TeamRead.model_validate(match.away_team),
        pick_count=pick_count,
        main_probability=best.predicted_probability if best else None,
        best_odds=best.available_odds if best else None,
        confidence=best.confidence if best else None,
    )


def _ensure_date_loaded(db: Session, match_date: date) -> None:
    if queries.list_matches(db, match_date):
        return
    collect_schedule_data(db, match_date)
