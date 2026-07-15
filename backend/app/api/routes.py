import calendar
from dataclasses import replace
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.collectors.factory import get_provider
from app.database import get_db, init_db
from app.models import (
    CacheEntry,
    AutomationRun,
    CalibrationRun,
    Competition,
    DataQualitySnapshot,
    FixtureEvent,
    HistoricalSyncWindow,
    Match,
    MarketRanking,
    MarketEvaluation,
    ModelAuditLog,
    Odds,
    Player,
    PlayerSeasonStatistic,
    Prediction,
    ProviderRawResponse,
    ProviderDataCoverage,
    PublicationQueue,
    Referee,
    SquadMember,
    Standing,
    SyncError,
    SyncJob,
    SystemPerformance,
    Team,
    TeamForm,
    TeamMatchStatistics,
    TeamSeasonStatistic,
)
from app.repositories import queries
from app.schemas.schemas import (
    AdminStatusRead,
    CalendarDayRead,
    CompetitionRead,
    CompetitionDetailRead,
    GenericInfoRead,
    MarketEvaluationRead,
    MarketRankingRead,
    MatchDetailRead,
    MatchListRead,
    ModelHealthRead,
    OddsRead,
    PredictionRead,
    SearchResultRead,
    StandingRowRead,
    TeamDetailRead,
    TeamRead,
    TipstrrMarketPickRead,
)
from app.services.collection_service import collect_deep_data_for_date, collect_flashscore_live_data, collect_match_deep_data, collect_mock_data, collect_schedule_data, collect_schedule_range
from app.services.goal_market_engine import evaluate_match_markets
from app.services.prediction_service import generate_predictions
from app.services.runtime_config import get_pick_safety_mode, set_pick_safety_mode
from app.services.settlement_service import verify_results
from app.services.statistics_service import (
    overview,
    performance_by_competition,
    performance_by_market,
    performance_by_system,
    profit_curve,
)
from app.services.tipstrr_market_service import build_daily_export, list_tipstrr_market_picks
from app.services.ultimate_engine import foundation_report, list_rankings, rank_predictions
from app.tasks.scheduled import run_maintenance
from app.core.config import get_settings
from app.utils.dates import local_date_from_utc_naive
from app.utils.time import utc_now_naive

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


@router.get("/pick-safety-mode")
def pick_safety_mode() -> dict:
    return {
        "mode": get_pick_safety_mode(),
        "available_modes": ["conservative", "normal", "aggressive"],
        "description": {
            "conservative": "Menos picks, exige mas EV, mas datos y riesgo bajo/medio.",
            "normal": "Equilibrio entre valor, calidad de datos y volumen.",
            "aggressive": "Permite mas candidatos con EV menor y mas riesgo.",
        },
    }


@router.get("/system-alerts")
def system_alerts(db: Session = Depends(get_db)) -> list[dict]:
    init_db()
    settings = get_settings()
    now = utc_now_naive()
    alerts: list[dict] = []
    latest_job = db.scalar(select(SyncJob).order_by(SyncJob.created_at.desc()).limit(1))
    recent_errors = int(
        db.scalar(select(func.count(SyncError.id)).where(SyncError.created_at >= now - timedelta(hours=24))) or 0
    )
    future_matches = queries.list_matches_range(db, date.today(), date.today() + timedelta(days=7), limit=5000)
    future_match_ids = [match.id for match in future_matches if match.kickoff_at > now]
    availability = queries.data_availability_by_match(db, future_match_ids)
    future_with_odds = sum(1 for item in availability.values() if item.get("odds"))
    future_with_stats = _count_matches_with_prematch_data(db, future_match_ids)

    def add(level: str, title: str, message: str, action: str) -> None:
        alerts.append({"level": level, "title": title, "message": message, "action": action})

    if not (settings.api_football_key or settings.football_api_key or settings.rapidapi_key):
        add("critical", "APIs sin credenciales", "No hay credenciales reales configuradas para descargar datos.", "Configurar variables de entorno en Railway.")
    if latest_job is None:
        add("warning", "Sin sincronizaciones", "Todavia no hay jobs de sincronizacion registrados.", "Ejecutar sincronizar fecha o mantenimiento.")
    elif latest_job.created_at < now - timedelta(hours=12):
        add("warning", "Sincronizacion antigua", "La ultima sincronizacion tiene mas de 12 horas.", "Ejecutar mantenimiento completo antes de revisar picks.")
    if recent_errors:
        add("warning", "Errores recientes", f"Hay {recent_errors} errores de proveedor en las ultimas 24 horas.", "Revisar errores en Administracion.")
    if future_match_ids and future_with_odds == 0:
        add("warning", "Faltan cuotas futuras", "Hay partidos futuros, pero ninguno tiene cuotas guardadas.", "Sincronizar cuotas o revisar proveedor.")
    if future_match_ids and future_with_stats == 0:
        add("info", "Faltan datos prepartido", "Hay partidos futuros sin estadisticas/historicos suficientes.", "Ejecutar enriquecimiento de fecha.")
    if not alerts:
        add("ok", "Sistema estable", "No se detectan bloqueos operativos principales.", "Continuar monitorizando calendario, cuotas y predicciones.")
    return alerts


@router.get("/matches", response_model=list[MatchListRead])
def get_matches(
    match_date: date | None = Query(default=None, alias="date"),
    country: str | None = None,
    competition_id: int | None = None,
    team: str | None = None,
    limit: int = Query(default=500, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[MatchListRead]:
    if match_date:
        _ensure_date_loaded(db, match_date)
    matches = queries.list_matches(db, match_date, country, competition_id, team, limit=limit, offset=offset)
    pick_counts = queries.pick_counts_by_match(db)
    publishable_counts = queries.publishable_counts_by_match(db)
    availability = queries.data_availability_by_match(db, [match.id for match in matches])
    return [
        _match_list_read(match, pick_counts.get(match.id, 0), publishable_counts.get(match.id, 0), availability.get(match.id))
        for match in matches
    ]


@router.get("/matches/live", response_model=list[MatchListRead])
def get_live_matches(db: Session = Depends(get_db)) -> list[MatchListRead]:
    matches = queries.list_matches_by_statuses(db, {"live", "1h", "2h", "ht", "et", "p", "in_play"}, limit=100)
    pick_counts = queries.pick_counts_by_match(db)
    publishable_counts = queries.publishable_counts_by_match(db)
    availability = queries.data_availability_by_match(db, [match.id for match in matches])
    return [_match_list_read(match, pick_counts.get(match.id, 0), publishable_counts.get(match.id, 0), availability.get(match.id)) for match in matches]


@router.get("/matches/upcoming", response_model=list[MatchListRead])
def get_upcoming_matches(db: Session = Depends(get_db)) -> list[MatchListRead]:
    matches = queries.list_matches_by_statuses(db, {"scheduled", "not_started", "NS", "TBD"}, limit=100)
    pick_counts = queries.pick_counts_by_match(db)
    publishable_counts = queries.publishable_counts_by_match(db)
    availability = queries.data_availability_by_match(db, [match.id for match in matches])
    return [_match_list_read(match, pick_counts.get(match.id, 0), publishable_counts.get(match.id, 0), availability.get(match.id)) for match in matches]


@router.get("/matches/results", response_model=list[MatchListRead])
def get_result_matches(db: Session = Depends(get_db)) -> list[MatchListRead]:
    matches = queries.list_matches_by_statuses(db, {"finished", "FT", "AET", "PEN"}, limit=100)
    pick_counts = queries.pick_counts_by_match(db)
    publishable_counts = queries.publishable_counts_by_match(db)
    availability = queries.data_availability_by_match(db, [match.id for match in matches])
    return [_match_list_read(match, pick_counts.get(match.id, 0), publishable_counts.get(match.id, 0), availability.get(match.id)) for match in matches]


@router.get("/matches/range", response_model=list[MatchListRead])
def get_matches_range(
    date_from: date,
    date_to: date,
    limit: int = Query(default=1000, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[MatchListRead]:
    if date_to < date_from:
        raise HTTPException(status_code=400, detail="date_to debe ser mayor o igual que date_from")
    matches = queries.list_matches_range(db, date_from, date_to, limit=limit, offset=offset)
    pick_counts = queries.pick_counts_by_match(db)
    publishable_counts = queries.publishable_counts_by_match(db)
    availability = queries.data_availability_by_match(db, [match.id for match in matches])
    return [_match_list_read(match, pick_counts.get(match.id, 0), publishable_counts.get(match.id, 0), availability.get(match.id)) for match in matches]


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
        grouped[local_day]["publishable"] = int(grouped[local_day].get("publishable", 0)) + len(
            [p for p in match.predictions if p.status in {"published", "ready_to_publish", "publishable"}]
        )
        grouped[local_day]["published"] = int(grouped[local_day]["published"]) + len([p for p in match.predictions if p.status == "published"])
    return [
        CalendarDayRead(
            date=day.isoformat(),
            match_count=int(values["matches"]),
            pick_count=int(values["picks"]),
            publishable_pick_count=int(values.get("publishable", 0)),
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
    row = _match_list_read(
        match,
        len([prediction for prediction in match.predictions if prediction.predicted_probability is not None]),
        len([prediction for prediction in match.predictions if prediction.status in {"published", "ready_to_publish", "publishable"}]),
        _match_availability_flags(db, match.id),
    )
    return MatchDetailRead(
        **row.model_dump(),
        home_form=queries.latest_team_form(db, match.home_team_id, match.competition_id),
        away_form=queries.latest_team_form(db, match.away_team_id, match.competition_id),
        predictions=match.predictions,
        availability=_match_availability(db, match.id),
    )


@router.get("/matches/{match_id}/statistics", response_model=GenericInfoRead)
def get_match_statistics(match_id: int, db: Session = Depends(get_db)) -> GenericInfoRead:
    if not queries.get_match(db, match_id):
        raise HTTPException(status_code=404, detail="Partido no encontrado")
    rows = []
    for row in queries.list_match_statistics(db, match_id):
        rows.append(
            {
                "team_id": row.team_id,
                "is_home": row.is_home,
                "posesion": row.possession,
                "tiros": row.shots,
                "tiros_a_puerta": row.shots_on_target,
                "corners": row.corners,
                "ataques_peligrosos": row.dangerous_attacks,
                "goles": row.goals,
                "xg": row.xg,
                "amarillas": row.yellow_cards,
                "rojas": row.red_cards,
            }
        )
    return _generic(rows)


@router.get("/matches/{match_id}/events", response_model=GenericInfoRead)
def get_match_events(match_id: int, db: Session = Depends(get_db)) -> GenericInfoRead:
    if not queries.get_match(db, match_id):
        raise HTTPException(status_code=404, detail="Partido no encontrado")
    rows = [
        {
            "minuto": event.minute,
            "extra": event.extra_minute,
            "equipo_id": event.team_id,
            "jugador_id": event.player_id,
            "asistente_id": event.assist_player_id,
            "tipo": event.event_type,
            "detalle": event.detail,
            "marcador": f"{event.score_home}-{event.score_away}" if event.score_home is not None and event.score_away is not None else "No disponible",
            "proveedor": event.source_provider,
        }
        for event in queries.list_match_events(db, match_id)
    ]
    return _generic(rows)


@router.get("/matches/{match_id}/lineups", response_model=GenericInfoRead)
def get_match_lineups(match_id: int, db: Session = Depends(get_db)) -> GenericInfoRead:
    if not queries.get_match(db, match_id):
        raise HTTPException(status_code=404, detail="Partido no encontrado")
    rows = [
        {
            "equipo_id": row.team_id,
            "jugador_id": row.player_id,
            "entrenador_id": row.coach_id,
            "formacion": row.formation,
            "tipo": row.line_type,
            "posicion": row.position,
            "dorsal": row.shirt_number,
            "capitan": row.is_captain,
            "valoracion": row.rating,
            "proveedor": row.source_provider,
        }
        for row in queries.list_match_lineups(db, match_id)
    ]
    return _generic(rows)


@router.get("/matches/{match_id}/player-statistics", response_model=GenericInfoRead)
def get_match_player_statistics(match_id: int, db: Session = Depends(get_db)) -> GenericInfoRead:
    if not queries.get_match(db, match_id):
        raise HTTPException(status_code=404, detail="Partido no encontrado")
    rows = [
        {
            "equipo_id": row.team_id,
            "jugador_id": row.player_id,
            "minutos": row.minutes,
            "goles": row.goals,
            "asistencias": row.assists,
            "tiros": row.shots,
            "tiros_a_puerta": row.shots_on_target,
            "pases": row.passes,
            "precision_pase": row.pass_accuracy,
            "xg": row.xg,
            "xa": row.xa,
            "valoracion": row.rating,
            "proveedor": row.source_provider,
        }
        for row in queries.list_match_player_statistics(db, match_id)
    ]
    return _generic(rows)


@router.get("/matches/{match_id}/odds", response_model=list[OddsRead])
def get_match_odds(match_id: int, db: Session = Depends(get_db)) -> list[OddsRead]:
    if not queries.get_match(db, match_id):
        raise HTTPException(status_code=404, detail="Partido no encontrado")
    return [OddsRead.model_validate(odd, from_attributes=True) for odd in queries.list_match_odds(db, match_id)]


@router.get("/matches/{match_id}/predictions", response_model=list[PredictionRead])
def get_match_predictions(match_id: int, db: Session = Depends(get_db)) -> list[PredictionRead]:
    match = queries.get_match(db, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Partido no encontrado")
    return match.predictions


@router.get("/matches/{match_id}/h2h", response_model=GenericInfoRead)
def get_match_h2h(match_id: int, db: Session = Depends(get_db)) -> GenericInfoRead:
    match = queries.get_match(db, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Partido no encontrado")
    rows = [
        {
            "id": item.id,
            "fecha": item.kickoff_at.isoformat(),
            "local": item.home_team.name,
            "visitante": item.away_team.name,
            "marcador": _score_label(item),
            "competicion": item.competition.name,
        }
        for item in queries.list_h2h_matches(db, match.home_team_id, match.away_team_id, match.id)
    ][:10]
    return _generic(rows)


@router.get("/matches/{match_id}/markets", response_model=list[MarketEvaluationRead])
def get_match_markets(match_id: int, db: Session = Depends(get_db)) -> list[MarketEvaluationRead]:
    if not queries.get_match(db, match_id):
        raise HTTPException(status_code=404, detail="Partido no encontrado")
    return evaluate_match_markets(db, match_id)


@router.get("/tipstrr-market-picks", response_model=list[TipstrrMarketPickRead])
def get_tipstrr_market_picks(
    match_date: date | None = Query(default=None, alias="date"),
    decision: str | None = None,
    limit: int = Query(default=1000, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[TipstrrMarketPickRead]:
    target_date = match_date or date.today()
    _ensure_date_loaded(db, target_date)
    rows = list_tipstrr_market_picks(db, target_date, decision)
    return rows[offset : offset + limit]


@router.get("/live-picks", response_model=list[TipstrrMarketPickRead])
def get_live_picks(
    limit: int = Query(default=500, ge=1, le=2000),
    db: Session = Depends(get_db),
) -> list[TipstrrMarketPickRead]:
    _ensure_date_loaded(db, date.today())
    live_statuses = _live_statuses()
    rows = [
        _live_pick_row(row)
        for row in list_tipstrr_market_picks(db, date.today(), None)
        if row.match_status.strip().lower() in live_statuses
    ]
    rows.sort(
        key=lambda row: (
            0 if row.decision == "LIVE_VALUE" else 1 if row.decision == "WATCH" else 2,
            -(row.expected_value if row.expected_value is not None else -999),
            -row.merlin_score,
        )
    )
    return rows[:limit]


@router.get("/live-match-center")
def get_live_match_center(limit: int = Query(default=100, ge=1, le=500), db: Session = Depends(get_db)) -> list[dict]:
    _ensure_date_loaded(db, date.today())
    collect_flashscore_live_data(db, limit=min(limit, 50))
    live_matches = queries.list_matches_by_statuses(db, _live_statuses(), limit=limit)
    all_live_pick_rows = [_live_pick_row(row) for row in list_tipstrr_market_picks(db, date.today(), None)]
    rows = []
    for match in live_matches:
        stats = queries.list_match_statistics(db, match.id)
        events = queries.list_match_events(db, match.id)
        picks = [row for row in all_live_pick_rows if row.match_id == match.id]
        rows.append(_live_match_snapshot(match, stats, events, picks))
    rows.sort(
        key=lambda row: (
            1 if row["live_data_source"] == "FlashScore RapidAPI" else 0,
            row["top_signal"]["priority"],
            row["momentum"]["total_pressure"],
            row["minute"],
        ),
        reverse=True,
    )
    return rows


@router.get("/market-rankings", response_model=list[MarketRankingRead])
def get_market_rankings(limit: int = 100, db: Session = Depends(get_db)) -> list[MarketRankingRead]:
    return [MarketRankingRead(**row) for row in list_rankings(db, limit)]


@router.get("/competitions", response_model=list[CompetitionRead])
def get_competitions(db: Session = Depends(get_db)):
    return queries.list_competitions(db)


@router.get("/competitions/{competition_id}", response_model=CompetitionDetailRead)
def get_competition(competition_id: int, db: Session = Depends(get_db)) -> CompetitionDetailRead:
    competition = queries.get_competition(db, competition_id)
    if not competition:
        raise HTTPException(status_code=404, detail="Competicion no encontrada")
    pick_counts = queries.pick_counts_by_match(db)
    upcoming_matches = queries.list_competition_matches(db, competition_id, before=False, limit=8)
    recent_matches = queries.list_competition_matches(db, competition_id, before=True, limit=8)
    availability = queries.data_availability_by_match(db, [match.id for match in upcoming_matches + recent_matches])
    publishable_counts = queries.publishable_counts_by_match(db)
    upcoming = [_match_list_read(match, pick_counts.get(match.id, 0), publishable_counts.get(match.id, 0), availability.get(match.id)) for match in upcoming_matches]
    recent = [_match_list_read(match, pick_counts.get(match.id, 0), publishable_counts.get(match.id, 0), availability.get(match.id)) for match in recent_matches]
    return CompetitionDetailRead(
        **CompetitionRead.model_validate(competition).model_dump(),
        match_count=len(queries.list_competition_matches(db, competition_id, limit=500)),
        teams_count=queries.count_competition_teams(db, competition_id),
        next_matches=upcoming,
        recent_results=recent,
        standings_available=bool(queries.list_standings(db, competition_id)),
        picks_count=queries.count_competition_picks(db, competition_id),
    )


@router.get("/competitions/{competition_id}/matches", response_model=list[MatchListRead])
def get_competition_matches(competition_id: int, db: Session = Depends(get_db)) -> list[MatchListRead]:
    if not queries.get_competition(db, competition_id):
        raise HTTPException(status_code=404, detail="Competicion no encontrada")
    pick_counts = queries.pick_counts_by_match(db)
    matches = queries.list_competition_matches(db, competition_id, limit=100)
    publishable_counts = queries.publishable_counts_by_match(db)
    availability = queries.data_availability_by_match(db, [match.id for match in matches])
    return [_match_list_read(match, pick_counts.get(match.id, 0), publishable_counts.get(match.id, 0), availability.get(match.id)) for match in matches]


@router.get("/competitions/{competition_id}/standings", response_model=list[StandingRowRead])
def get_competition_standings(competition_id: int, db: Session = Depends(get_db)) -> list[StandingRowRead]:
    if not queries.get_competition(db, competition_id):
        raise HTTPException(status_code=404, detail="Competicion no encontrada")
    return [_standing_read(db, row) for row in queries.list_standings(db, competition_id)]


@router.get("/competitions/{competition_id}/teams", response_model=list[TeamRead])
def get_competition_teams(competition_id: int, db: Session = Depends(get_db)) -> list[TeamRead]:
    if not queries.get_competition(db, competition_id):
        raise HTTPException(status_code=404, detail="Competicion no encontrada")
    team_ids: set[int] = set()
    for match in queries.list_competition_matches(db, competition_id, limit=1000):
        team_ids.add(match.home_team_id)
        team_ids.add(match.away_team_id)
    teams = [db.get(Team, team_id) for team_id in sorted(team_ids)]
    return [TeamRead.model_validate(team) for team in teams if team]


@router.get("/competitions/{competition_id}/statistics", response_model=GenericInfoRead)
def get_competition_statistics(competition_id: int, db: Session = Depends(get_db)) -> GenericInfoRead:
    competition = queries.get_competition(db, competition_id)
    if not competition:
        raise HTTPException(status_code=404, detail="Competicion no encontrada")
    matches = queries.list_competition_matches(db, competition_id, limit=1000)
    finished = [match for match in matches if match.home_score is not None and match.away_score is not None]
    goals = sum((match.home_score or 0) + (match.away_score or 0) for match in finished)
    rows = [{
        "partidos": len(matches),
        "finalizados": len(finished),
        "media_goles": round(goals / len(finished), 2) if finished else None,
        "picks": queries.count_competition_picks(db, competition_id),
        "temporada": competition.season,
    }]
    return GenericInfoRead(available=True, message="Disponible", rows=rows)


@router.get("/competitions/{competition_id}/players", response_model=GenericInfoRead)
def get_competition_players(competition_id: int, db: Session = Depends(get_db)) -> GenericInfoRead:
    if not queries.get_competition(db, competition_id):
        raise HTTPException(status_code=404, detail="Competicion no encontrada")
    return GenericInfoRead(available=False, message="No disponible: el proveedor aun no ha sincronizado jugadores de esta competicion", rows=[])


@router.get("/teams", response_model=list[TeamRead])
def get_teams(q: str | None = None, db: Session = Depends(get_db)):
    return queries.list_teams(db, q)


@router.get("/teams/{team_id}", response_model=TeamRead)
def get_team(team_id: int, db: Session = Depends(get_db)):
    team = queries.get_team(db, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    return team


@router.get("/teams/{team_id}/detail", response_model=TeamDetailRead)
def get_team_detail(team_id: int, db: Session = Depends(get_db)) -> TeamDetailRead:
    team = queries.get_team(db, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    pick_counts = queries.pick_counts_by_match(db)
    recent_matches = queries.list_team_matches(db, team_id, before=True)
    upcoming_matches = queries.list_team_matches(db, team_id, before=False)
    publishable_counts = queries.publishable_counts_by_match(db)
    availability = queries.data_availability_by_match(db, [match.id for match in recent_matches + upcoming_matches])
    recent = [_match_list_read(match, pick_counts.get(match.id, 0), publishable_counts.get(match.id, 0), availability.get(match.id)) for match in recent_matches]
    upcoming = [_match_list_read(match, pick_counts.get(match.id, 0), publishable_counts.get(match.id, 0), availability.get(match.id)) for match in upcoming_matches]
    form = queries.latest_any_team_form(db, team_id)
    statistics = {
        "muestra": form.matches_sample if form else None,
        "goles_favor_media": form.goals_for_avg if form else None,
        "goles_contra_media": form.goals_against_avg if form else None,
        "corners_favor_media": form.corners_for_avg if form else None,
        "over_9_5_corners": form.over_9_5_corners_rate if form else None,
    }
    return TeamDetailRead(
        **TeamRead.model_validate(team).model_dump(),
        recent_matches=recent,
        upcoming_matches=upcoming,
        form=form,
        injuries=GenericInfoRead(available=False, message="No disponible: lesiones no sincronizadas todavia", rows=[]),
        squad=GenericInfoRead(available=False, message="No disponible: plantilla no sincronizada todavia", rows=[]),
        statistics=statistics,
    )


@router.get("/teams/{team_id}/matches", response_model=list[MatchListRead])
def get_team_matches(team_id: int, db: Session = Depends(get_db)) -> list[MatchListRead]:
    if not queries.get_team(db, team_id):
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    pick_counts = queries.pick_counts_by_match(db)
    matches = queries.list_team_matches(db, team_id, limit=100)
    publishable_counts = queries.publishable_counts_by_match(db)
    availability = queries.data_availability_by_match(db, [match.id for match in matches])
    return [_match_list_read(match, pick_counts.get(match.id, 0), publishable_counts.get(match.id, 0), availability.get(match.id)) for match in matches]


@router.get("/teams/{team_id}/statistics", response_model=GenericInfoRead)
def get_team_statistics(team_id: int, db: Session = Depends(get_db)) -> GenericInfoRead:
    team = queries.get_team(db, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    form = queries.latest_any_team_form(db, team_id)
    if not form:
        return GenericInfoRead(available=False, message="No disponible: estadisticas historicas no sincronizadas", rows=[])
    return GenericInfoRead(available=True, message="Disponible", rows=[TeamDetailRead.model_fields["statistics"].default_factory() if False else {
        "muestra": form.matches_sample,
        "goles_favor_media": form.goals_for_avg,
        "goles_contra_media": form.goals_against_avg,
        "tiros_media": form.shots_avg,
        "tiros_puerta_media": form.shots_on_target_avg,
        "posesion_media": form.possession_avg,
        "btts": form.btts_rate,
        "over_1_5": form.over_1_5_goals_rate,
        "over_2_5": form.over_2_5_goals_rate,
    }])


@router.get("/teams/{team_id}/squad", response_model=GenericInfoRead)
def get_team_squad(team_id: int, db: Session = Depends(get_db)) -> GenericInfoRead:
    if not queries.get_team(db, team_id):
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    players = db.scalars(select(Player).where(Player.current_team_id == team_id).order_by(Player.name)).all()
    rows = [{"id": player.id, "nombre": player.name, "posicion": player.position, "nacionalidad": player.nationality} for player in players]
    return _generic(rows, empty_message="No disponible: plantilla no sincronizada todavia")


@router.get("/teams/{team_id}/injuries", response_model=GenericInfoRead)
def get_team_injuries(team_id: int, db: Session = Depends(get_db)) -> GenericInfoRead:
    if not queries.get_team(db, team_id):
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    return GenericInfoRead(available=False, message="No disponible: lesiones no sincronizadas todavia", rows=[])


@router.get("/players", response_model=list[dict])
def get_players(q: str | None = None, db: Session = Depends(get_db)) -> list[dict]:
    return [_player_read(player) for player in queries.list_players(db, q)]


@router.get("/players/{player_id}", response_model=dict)
def get_player(player_id: int, db: Session = Depends(get_db)) -> dict:
    player = queries.get_player(db, player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Jugador no encontrado")
    return _player_read(player)


@router.get("/players/{player_id}/statistics", response_model=GenericInfoRead)
def get_player_statistics(player_id: int, db: Session = Depends(get_db)) -> GenericInfoRead:
    if not queries.get_player(db, player_id):
        raise HTTPException(status_code=404, detail="Jugador no encontrado")
    return GenericInfoRead(available=False, message="No disponible: estadisticas de jugador no sincronizadas todavia", rows=[])


@router.get("/players/{player_id}/matches", response_model=GenericInfoRead)
def get_player_matches(player_id: int, db: Session = Depends(get_db)) -> GenericInfoRead:
    if not queries.get_player(db, player_id):
        raise HTTPException(status_code=404, detail="Jugador no encontrado")
    return GenericInfoRead(available=False, message="No disponible: partidos de jugador no sincronizados todavia", rows=[])


@router.get("/standings", response_model=list[StandingRowRead])
def get_standings(competition_id: int | None = None, db: Session = Depends(get_db)) -> list[StandingRowRead]:
    return [_standing_read(db, row) for row in queries.list_standings(db, competition_id)]


@router.get("/search", response_model=list[SearchResultRead])
def search(q: str = Query(min_length=2), db: Session = Depends(get_db)) -> list[SearchResultRead]:
    return [SearchResultRead(**row) for row in queries.search_all(db, q)]


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


@router.get("/predictions/export")
def export_predictions(match_date: date = Query(alias="date"), refresh: bool = True, db: Session = Depends(get_db)) -> dict:
    refresh_error: str | None = None
    if refresh:
        try:
            collect_deep_data_for_date(db, match_date)
        except Exception as exc:
            refresh_error = str(exc)
            db.rollback()
    else:
        try:
            _ensure_date_loaded(db, match_date)
        except Exception as exc:
            refresh_error = str(exc)
            db.rollback()
    payload = build_daily_export(db, match_date)
    payload["diagnostics"]["refresh_error"] = refresh_error
    payload["diagnostics"]["refresh_status"] = "failed_using_cached_data" if refresh_error else "ok" if refresh else "not_requested"
    return payload


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


@router.get("/admin/status", response_model=AdminStatusRead)
def admin_status(db: Session = Depends(get_db)) -> AdminStatusRead:
    settings = get_settings()
    provider = get_provider()
    jobs = [
        {
            "id": job.id,
            "tipo": job.job_type,
            "proveedor": job.provider,
            "estado": job.status,
            "procesados": job.records_processed,
            "errores": job.error_count,
            "mensaje": job.message,
        }
        for job in queries.list_sync_jobs(db)
    ]
    usage = [
        {
            "proveedor": row.provider,
            "endpoint": row.endpoint,
            "peticiones": row.requests_count,
            "ok": row.success_count,
            "errores": row.error_count,
            "restante": row.rate_limit_remaining,
        }
        for row in queries.list_api_usage(db)
    ]
    return AdminStatusRead(
        active_provider=provider.__class__.__name__,
        api_football_configured=bool(settings.api_football_key),
        flashscore_configured=bool(settings.rapidapi_key),
        matches=int(db.scalar(select(func.count(Match.id))) or 0),
        competitions=int(db.scalar(select(func.count(Competition.id))) or 0),
        teams=int(db.scalar(select(func.count(Team.id))) or 0),
        players=int(db.scalar(select(func.count(Player.id))) or 0),
        standings_rows=int(db.scalar(select(func.count(Standing.id))) or 0),
        raw_responses=int(db.scalar(select(func.count(ProviderRawResponse.id))) or 0),
        mappings_unmatched=queries.count_unmatched_mappings(db),
        referees=int(db.scalar(select(func.count(Referee.id))) or 0),
        squad_members=int(db.scalar(select(func.count(SquadMember.id))) or 0),
        team_season_statistics=int(db.scalar(select(func.count(TeamSeasonStatistic.id))) or 0),
        player_season_statistics=int(db.scalar(select(func.count(PlayerSeasonStatistic.id))) or 0),
        data_quality_snapshots=int(db.scalar(select(func.count(DataQualitySnapshot.id))) or 0),
        cache_entries=int(db.scalar(select(func.count(CacheEntry.id))) or 0),
        model_audit_logs=int(db.scalar(select(func.count(ModelAuditLog.id))) or 0),
        market_rankings=int(db.scalar(select(func.count(MarketRanking.id))) or 0),
        publication_queue=int(db.scalar(select(func.count(PublicationQueue.id))) or 0),
        automation_runs=int(db.scalar(select(func.count(AutomationRun.id))) or 0),
        historical_sync_windows=int(db.scalar(select(func.count(HistoricalSyncWindow.id))) or 0),
        calibration_runs=int(db.scalar(select(func.count(CalibrationRun.id))) or 0),
        provider_data_coverage=int(db.scalar(select(func.count(ProviderDataCoverage.id))) or 0),
        latest_sync_jobs=jobs,
        api_usage=usage,
    )


@router.get("/admin/ultimate-report")
def admin_ultimate_report(db: Session = Depends(get_db)):
    return foundation_report(db)


@router.get("/admin/errors", dependencies=[Depends(require_admin)])
def admin_errors(limit: int = Query(default=50, ge=1, le=200), db: Session = Depends(get_db)):
    return [
        {
            "id": row.id,
            "provider": row.provider,
            "endpoint": row.endpoint,
            "entity_type": row.entity_type,
            "external_id": row.external_id,
            "message": row.message,
            "created_at": row.created_at.isoformat(),
        }
        for row in db.scalars(select(SyncError).order_by(SyncError.created_at.desc()).limit(limit))
    ]


@router.get("/admin/mappings", dependencies=[Depends(require_admin)])
def admin_mappings(status: str | None = None, limit: int = Query(default=100, ge=1, le=500), db: Session = Depends(get_db)):
    from app.models import ProviderEntityMapping

    stmt = select(ProviderEntityMapping).order_by(ProviderEntityMapping.updated_at.desc()).limit(limit)
    if status:
        stmt = stmt.where(ProviderEntityMapping.match_status == status)
    return [
        {
            "id": row.id,
            "entity_type": row.entity_type,
            "provider": row.provider,
            "provider_external_id": row.provider_external_id,
            "provider_name": row.provider_name,
            "internal_id": row.internal_id,
            "match_status": row.match_status,
            "confidence": row.confidence,
        }
        for row in db.scalars(stmt)
    ]


@router.get("/model-health", response_model=ModelHealthRead)
def model_health(db: Session = Depends(get_db)) -> ModelHealthRead:
    settings = get_settings()
    provider_name = settings.data_provider
    provider_error: str | None = None
    try:
        provider_name = get_provider().__class__.__name__
    except Exception as exc:
        provider_error = str(exc)
    latest_job = db.scalar(select(SyncJob).order_by(SyncJob.created_at.desc()).limit(1))
    recent_errors = [
        {
            "id": row.id,
            "provider": row.provider,
            "endpoint": row.endpoint,
            "entity_type": row.entity_type,
            "message": row.message[:240],
            "created_at": row.created_at.isoformat(),
        }
        for row in db.scalars(select(SyncError).order_by(SyncError.created_at.desc()).limit(10))
    ]
    matches_downloaded = int(db.scalar(select(func.count(Match.id))) or 0)
    matches_analyzed = int(db.scalar(select(func.count(func.distinct(Prediction.match_id)))) or 0)
    candidate_picks = int(db.scalar(select(func.count(Prediction.id)).where(Prediction.predicted_probability.is_not(None))) or 0)
    stored_market_evaluations = int(db.scalar(select(func.count(MarketEvaluation.id))) or 0)
    markets_evaluated = max(stored_market_evaluations, candidate_picks)
    rejected_picks = int(db.scalar(select(func.count(Prediction.id)).where(Prediction.status.in_(["rejected", "not_published", "no_bet"]))) or 0)
    publishable_picks = int(db.scalar(select(func.count(Prediction.id)).where(Prediction.status.in_(["published", "ready_to_publish", "publishable"]))) or 0)
    matches_without_odds = int(
        db.scalar(
            select(func.count(Match.id))
            .outerjoin(Odds, Odds.match_id == Match.id)
            .where(Odds.id.is_(None))
        )
        or 0
    )
    matches_with_prematch_data = _count_matches_with_prematch_data(db)
    matches_without_statistics = max(0, matches_downloaded - matches_with_prematch_data)
    incomplete_competitions = int(
        db.scalar(
            select(func.count(Competition.id))
            .outerjoin(Standing, Standing.competition_id == Competition.id)
            .where(Standing.id.is_(None))
        )
        or 0
    )
    usage_rows = queries.list_api_usage(db, limit=20)
    rate_limits = [
        {"provider": row.provider, "endpoint": row.endpoint, "remaining": row.rate_limit_remaining}
        for row in usage_rows
        if row.rate_limit_remaining is not None
    ]
    if provider_error:
        status = "error"
        data_status = f"Proveedor mal configurado: {provider_error}"
    elif recent_errors:
        status = "degradado"
        data_status = "Datos con errores recientes"
    elif matches_without_odds and matches_downloaded and matches_without_odds / max(matches_downloaded, 1) > 0.75:
        status = "degradado"
        data_status = "Muchas cuotas pendientes"
    else:
        status = "operativo"
        data_status = "Datos disponibles"
    return ModelHealthRead(
        status=status,
        data_status=data_status,
        active_provider=provider_name,
        api_football_configured=bool(settings.api_football_key),
        flashscore_configured=bool(settings.rapidapi_key),
        last_sync_at=latest_job.finished_at if latest_job else None,
        next_sync_hint="Usar Admin > sincronizar fecha o backfill programado",
        matches_downloaded=matches_downloaded,
        matches_analyzed=matches_analyzed,
        markets_evaluated=markets_evaluated,
        candidate_picks=candidate_picks,
        rejected_picks=rejected_picks,
        publishable_picks=publishable_picks,
        average_calculation_time_ms=None,
        recent_errors=recent_errors,
        unmapped_entities=queries.count_unmatched_mappings(db),
        matches_without_odds=matches_without_odds,
        matches_without_statistics=matches_without_statistics,
        incomplete_competitions=incomplete_competitions,
        api_usage=[
            {
                "provider": row.provider,
                "endpoint": row.endpoint,
                "requests": row.requests_count,
                "success": row.success_count,
                "errors": row.error_count,
                "period_start": row.period_start.isoformat(),
            }
            for row in usage_rows
        ],
        rate_limits=rate_limits,
    )


@router.get("/readiness")
def readiness(db: Session = Depends(get_db)) -> dict:
    settings = get_settings()
    checks: list[dict] = []
    actions: list[str] = []
    provider_error: str | None = None
    try:
        provider_name = get_provider().__class__.__name__
    except Exception as exc:
        provider_name = settings.data_provider
        provider_error = str(exc)

    is_mock = settings.data_provider.strip().lower() == "mock"
    api_configured = bool(settings.api_football_key or settings.football_api_key or settings.rapidapi_key)
    today = date.today()
    future_window = queries.list_matches_range(db, today, today + timedelta(days=7), limit=5000)
    future_match_ids = [match.id for match in future_window if match.kickoff_at > utc_now_naive()]
    availability = queries.data_availability_by_match(db, future_match_ids)
    future_with_odds = sum(1 for item in availability.values() if item.get("odds"))
    future_with_stats = _count_matches_with_prematch_data(db, future_match_ids)
    recent_errors = int(db.scalar(select(func.count(SyncError.id))) or 0)

    def add_check(name: str, ok: bool, detail: str, action: str | None = None) -> None:
        checks.append({"name": name, "ok": ok, "detail": detail})
        if not ok and action:
            actions.append(action)

    add_check("Proveedor real", not is_mock, f"Proveedor activo: {settings.data_provider}", "Configurar DATA_PROVIDER=api_football o flashscore.")
    add_check("Credenciales API", api_configured and not provider_error, provider_error or "Credenciales presentes", "Configurar API_FOOTBALL_KEY o RAPIDAPI_KEY.")
    add_check("Partidos futuros", len(future_match_ids) > 0, f"{len(future_match_ids)} partidos futuros en 7 dias", "Sincronizar calendario de hoy + 7 dias.")
    add_check("Cuotas recientes", future_with_odds > 0, f"{future_with_odds} partidos futuros con cuotas recientes", "Sincronizar cuotas y revisar proveedor de odds.")
    add_check("Datos prepartido", future_with_stats > 0, f"{future_with_stats} partidos futuros con historicos o estadisticas", "Sincronizar estadisticas/historicos.")
    add_check("Errores de sync", recent_errors == 0, f"{recent_errors} errores registrados", "Revisar Admin > errores y reintentar tareas fallidas.")

    failed = [check for check in checks if not check["ok"]]
    if any(check["name"] in {"Proveedor real", "Credenciales API"} for check in failed):
        status = "blocked"
    elif failed:
        status = "degraded"
    else:
        status = "ready"
    return {
        "status": status,
        "provider": provider_name,
        "generated_at": utc_now_naive().isoformat(),
        "checks": checks,
        "actions": actions,
        "metrics": {
            "future_matches_7d": len(future_match_ids),
            "future_matches_with_recent_odds": future_with_odds,
            "future_matches_with_statistics": future_with_stats,
            "future_matches_with_prematch_data": future_with_stats,
            "sync_errors": recent_errors,
        },
    }


@router.post("/admin/collect", dependencies=[Depends(require_admin)])
def admin_collect(match_date: date | None = None, db: Session = Depends(get_db)):
    init_db()
    try:
        if get_settings().data_provider.strip().lower() == "mock":
            return collect_mock_data(db, match_date)
        return collect_schedule_data(db, match_date)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/admin/import-range", dependencies=[Depends(require_admin)])
def admin_import_range(date_from: date, date_to: date, db: Session = Depends(get_db)):
    if date_to < date_from:
        raise HTTPException(status_code=400, detail="date_to debe ser mayor o igual que date_from")
    init_db()
    return collect_schedule_range(db, date_from, date_to)


@router.post("/admin/sync-day", dependencies=[Depends(require_admin)])
def admin_sync_day(match_date: date = Query(alias="date"), db: Session = Depends(get_db)):
    init_db()
    return collect_schedule_data(db, match_date)


@router.post("/admin/sync-day-deep", dependencies=[Depends(require_admin)])
def admin_sync_day_deep(match_date: date = Query(alias="date"), db: Session = Depends(get_db)):
    init_db()
    return collect_deep_data_for_date(db, match_date)


@router.post("/admin/sync-match-deep", dependencies=[Depends(require_admin)])
def admin_sync_match_deep(match_id: int, db: Session = Depends(get_db)):
    init_db()
    return collect_match_deep_data(db, match_id)


@router.post("/admin/generate-predictions", dependencies=[Depends(require_admin)])
def admin_generate_predictions(db: Session = Depends(get_db)):
    return generate_predictions(db)


@router.post("/admin/pick-safety-mode", dependencies=[Depends(require_admin)])
def admin_pick_safety_mode(mode: str = Query(...)):
    try:
        selected = set_pick_safety_mode(mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "ok", "mode": selected}


@router.post("/admin/rank-markets", dependencies=[Depends(require_admin)])
def admin_rank_markets(limit: int = 500, db: Session = Depends(get_db)):
    return rank_predictions(db, limit)


@router.post("/admin/verify-results", dependencies=[Depends(require_admin)])
def admin_verify_results(db: Session = Depends(get_db)):
    return verify_results(db)


@router.post("/admin/recalculate-statistics", dependencies=[Depends(require_admin)])
def admin_recalculate_statistics(db: Session = Depends(get_db)):
    return overview(db)


@router.post("/admin/run-maintenance", dependencies=[Depends(require_admin)])
def admin_run_maintenance(
    days_back: int = Query(default=1, ge=0, le=30),
    days_forward: int = Query(default=7, ge=0, le=60),
    deep_today: bool = True,
):
    return run_maintenance(days_back=days_back, days_forward=days_forward, deep_today=deep_today)


@router.post("/admin/clear-data", dependencies=[Depends(require_admin)])
def admin_clear_data(confirm: str = Query(default=""), db: Session = Depends(get_db)):
    if confirm != "CONFIRM_CLEAR_ALL_DATA":
        raise HTTPException(status_code=400, detail="Confirmacion requerida para borrar datos")
    for model in (SystemPerformance, Prediction, Odds, TeamMatchStatistics, TeamForm, Match, Team, Competition):
        db.execute(delete(model))
    db.commit()
    return {"status": "cleared"}


def _match_list_read(match, pick_count: int, publishable_pick_count: int = 0, availability: dict[str, bool] | None = None) -> MatchListRead:
    published = [prediction for prediction in match.predictions if prediction.status == "published"]
    candidates = [prediction for prediction in match.predictions if prediction.predicted_probability is not None]
    candidates.sort(key=lambda prediction: (prediction.expected_value or -999, prediction.confidence or 0), reverse=True)
    best = published[0] if published else (candidates[0] if candidates else None)
    availability = availability or {}
    data_flags = [
        bool(availability.get("statistics")),
        bool(availability.get("lineups")),
        bool(availability.get("odds")),
        bool(candidates),
    ]
    data_quality_score = round(sum(1 for flag in data_flags if flag) / len(data_flags) * 100, 1)
    return MatchListRead(
        id=match.id,
        external_id=match.external_id,
        kickoff_at=match.kickoff_at,
        status=match.status,
        home_score=match.home_score,
        away_score=match.away_score,
        venue=match.venue,
        round=match.round,
        season=match.season,
        competition=CompetitionRead.model_validate(match.competition),
        home_team=TeamRead.model_validate(match.home_team),
        away_team=TeamRead.model_validate(match.away_team),
        pick_count=pick_count,
        publishable_pick_count=publishable_pick_count,
        main_probability=best.predicted_probability if best else None,
        best_odds=best.available_odds if best else None,
        confidence=best.confidence if best else None,
        best_market=_prediction_label(best) if best else None,
        merlin_score=_prediction_merlin_score(best) if best else None,
        data_quality_score=data_quality_score,
        has_statistics=bool(availability.get("statistics")),
        has_lineups=bool(availability.get("lineups")),
        has_odds=bool(availability.get("odds")),
        has_prediction=bool(candidates),
        has_pick=publishable_pick_count > 0,
    )


def _match_availability_flags(db: Session, match_id: int) -> dict[str, bool]:
    return queries.data_availability_by_match(db, [match_id]).get(match_id, {})


def _count_matches_with_prematch_data(db: Session, match_ids: list[int] | None = None) -> int:
    if match_ids == []:
        return 0
    statistics_exists = exists(select(1).where(TeamMatchStatistics.match_id == Match.id))
    home_form_exists = exists(
        select(1).where(
            and_(
                TeamForm.team_id == Match.home_team_id,
                TeamForm.competition_id == Match.competition_id,
            )
        )
    )
    away_form_exists = exists(
        select(1).where(
            and_(
                TeamForm.team_id == Match.away_team_id,
                TeamForm.competition_id == Match.competition_id,
            )
        )
    )
    stmt = select(func.count(Match.id)).where(or_(statistics_exists, and_(home_form_exists, away_form_exists)))
    if match_ids is not None:
        stmt = stmt.where(Match.id.in_(match_ids))
    return int(db.scalar(stmt) or 0)


def _prediction_label(prediction) -> str:
    line = f" {prediction.line:g}" if prediction.line is not None else ""
    return f"{prediction.market} {prediction.selection}{line}".strip()


def _live_pick_row(row):
    if row.market_odds is None:
        return replace(row, decision="SIN_CUOTA", reason="Live: falta cuota real")
    if not _live_line_is_professional(row):
        return replace(row, decision="WATCH", reason="Live: linea fuera de rango profesional")
    if row.publish_blocked_by_odds or (row.price_age_minutes is not None and row.price_age_minutes > 120):
        return replace(row, decision="WATCH", reason="Live: cuota no verificada o desactualizada")
    if row.risk_level == "high":
        return replace(row, decision="WATCH", reason="Live: riesgo alto")
    if row.data_quality < 40:
        return replace(row, decision="WATCH", reason="Live: datos insuficientes")
    if row.model_probability is None or row.model_probability < 0.35:
        return replace(row, decision="WATCH", reason="Live: probabilidad insuficiente")
    if row.expected_value is None or row.expected_value < 0.03:
        return replace(row, decision="WATCH", reason="Live: sin valor suficiente")
    return replace(row, decision="LIVE_VALUE", reason="Live: valor positivo con cuota real")


def _live_match_snapshot(match: Match, stats: list[TeamMatchStatistics], events: list[FixtureEvent], picks: list) -> dict:
    home_stats = next((row for row in stats if row.team_id == match.home_team_id or row.is_home), None)
    away_stats = next((row for row in stats if row.team_id == match.away_team_id or not row.is_home), None)
    minute = _live_minute(match, events)
    home_pressure = _pressure_score(home_stats)
    away_pressure = _pressure_score(away_stats)
    total_pressure = home_pressure + away_pressure
    pressure_gap = home_pressure - away_pressure
    recent_events = [
        {
            "minute": event.minute,
            "type": event.event_type,
            "detail": event.detail,
            "team": _event_team_name(match, event.team_id),
        }
        for event in events[-5:]
    ]
    live_value = [pick for pick in picks if pick.decision == "LIVE_VALUE"]
    watch = [pick for pick in picks if pick.decision == "WATCH"]
    top_signal = _top_live_signal(match, minute, home_stats, away_stats, home_pressure, away_pressure, live_value)
    return {
        "match_id": match.id,
        "external_id": match.external_id,
        "match_name": f"{match.home_team.name} vs {match.away_team.name}",
        "competition": match.competition.name,
        "country": match.competition.country,
        "live_data_source": "FlashScore RapidAPI" if str(match.external_id).startswith("flashscore-") else "Base interna",
        "status": match.status,
        "minute": minute,
        "score": {
            "home": match.home_score,
            "away": match.away_score,
        },
        "teams": {
            "home": match.home_team.name,
            "away": match.away_team.name,
        },
        "stats": {
            "home": _stats_payload(home_stats),
            "away": _stats_payload(away_stats),
        },
        "momentum": {
            "home_pressure": round(home_pressure, 1),
            "away_pressure": round(away_pressure, 1),
            "total_pressure": round(total_pressure, 1),
            "leader": match.home_team.name if pressure_gap > 8 else match.away_team.name if pressure_gap < -8 else "Equilibrado",
            "pressure_gap": round(pressure_gap, 1),
            "temperature": _temperature(total_pressure, minute),
        },
        "top_signal": top_signal,
        "recent_events": recent_events,
        "picks": {
            "live_value": len(live_value),
            "watch": len(watch),
            "total": len(picks),
            "best": _pick_summary(live_value[0] if live_value else watch[0] if watch else None),
        },
    }


def _pressure_score(stats: TeamMatchStatistics | None) -> float:
    if not stats:
        return 0.0
    return (
        _num(stats.dangerous_attacks) * 0.45
        + _num(stats.shots_on_target) * 5.5
        + _num(stats.shots) * 1.8
        + _num(stats.corners) * 2.6
        + _num(stats.possession) * 0.12
        + _num(stats.xg) * 18
    )


def _top_live_signal(
    match: Match,
    minute: int,
    home_stats: TeamMatchStatistics | None,
    away_stats: TeamMatchStatistics | None,
    home_pressure: float,
    away_pressure: float,
    live_value: list,
) -> dict:
    total_goals = (match.home_score or 0) + (match.away_score or 0)
    total_sot = _num(home_stats.shots_on_target if home_stats else None) + _num(away_stats.shots_on_target if away_stats else None)
    total_shots = _num(home_stats.shots if home_stats else None) + _num(away_stats.shots if away_stats else None)
    total_corners = _num(home_stats.corners if home_stats else None) + _num(away_stats.corners if away_stats else None)
    total_pressure = home_pressure + away_pressure
    pressure_gap = home_pressure - away_pressure
    if live_value:
        pick = live_value[0]
        return {
            "label": "Valor live detectado",
            "market": pick.label,
            "confidence": min(95, max(55, int(pick.merlin_score))),
            "priority": 5,
            "reason": pick.reason,
        }
    if total_pressure > 85 and total_sot >= 4 and minute <= 75:
        leader = match.home_team.name if pressure_gap >= 0 else match.away_team.name
        return {
            "label": f"Ritmo alto de gol: {leader} empuja mas",
            "market": "Gol / Over live",
            "confidence": min(88, int(55 + total_sot * 5 + min(total_pressure, 120) / 8)),
            "priority": 4,
            "reason": f"{int(total_sot)} tiros a puerta, {int(total_shots)} tiros y presion total {round(total_pressure, 1)}.",
        }
    if abs(pressure_gap) > 25 and max(home_pressure, away_pressure) > 55:
        leader = match.home_team.name if pressure_gap > 0 else match.away_team.name
        return {
            "label": f"Dominio live claro: {leader}",
            "market": "Equipo siguiente gol / equipo marca",
            "confidence": min(82, int(52 + abs(pressure_gap) / 2)),
            "priority": 3,
            "reason": f"Diferencia de presion {round(abs(pressure_gap), 1)}.",
        }
    if total_corners >= max(4, minute / 12) and minute <= 80:
        return {
            "label": "Ritmo de corners activo",
            "market": "Corners live",
            "confidence": min(80, int(48 + total_corners * 4)),
            "priority": 2,
            "reason": f"{int(total_corners)} corners acumulados en minuto {minute}.",
        }
    return {
        "label": "Sin lectura fuerte",
        "market": "Esperar",
        "confidence": 0,
        "priority": 1,
        "reason": "Faltan estadisticas live suficientes o ritmo claro.",
    }


def _stats_payload(stats: TeamMatchStatistics | None) -> dict:
    return {
        "possession": _num_or_none(stats.possession if stats else None),
        "shots": _num_or_none(stats.shots if stats else None),
        "shots_on_target": _num_or_none(stats.shots_on_target if stats else None),
        "corners": _num_or_none(stats.corners if stats else None),
        "dangerous_attacks": _num_or_none(stats.dangerous_attacks if stats else None),
        "xg": _num_or_none(stats.xg if stats else None),
        "yellow_cards": _num_or_none(stats.yellow_cards if stats else None),
        "red_cards": _num_or_none(stats.red_cards if stats else None),
    }


def _pick_summary(pick) -> dict | None:
    if not pick:
        return None
    return {
        "label": pick.label,
        "decision": pick.decision,
        "probability": pick.model_probability,
        "odds": pick.market_odds,
        "ev": pick.expected_value,
        "reason": pick.reason,
    }


def _temperature(total_pressure: float, minute: int) -> str:
    if total_pressure > 95 and minute < 80:
        return "Muy caliente"
    if total_pressure > 65:
        return "Activa"
    if total_pressure > 35:
        return "Media"
    return "Fria"


def _live_minute(match: Match, events: list[FixtureEvent]) -> int:
    event_minutes = [event.minute for event in events if event.minute is not None]
    if event_minutes:
        return max(event_minutes)
    elapsed = int(max(0, (utc_now_naive() - match.kickoff_at).total_seconds() // 60))
    status = (match.status or "").lower()
    if status in {"1h", "first_half"}:
        return min(45, elapsed)
    if status in {"ht", "halftime"}:
        return 45
    if status in {"2h", "second_half", "live", "in_play"}:
        return min(90, max(46, elapsed))
    if status in {"et"}:
        return min(120, max(91, elapsed))
    if status in {"p"}:
        return 120
    return min(120, elapsed)


def _event_team_name(match: Match, team_id: int | None) -> str | None:
    if team_id == match.home_team_id:
        return match.home_team.name
    if team_id == match.away_team_id:
        return match.away_team.name
    return None


def _num(value) -> float:
    return float(value or 0)


def _num_or_none(value) -> float | None:
    return None if value is None else float(value)


def _live_line_is_professional(row) -> bool:
    if row.line is None:
        return True
    line = abs(float(row.line))
    if row.family == "total_goals":
        if row.period == "first_half" and row.team_scope == "all":
            return 0.5 <= line <= 2.5
        if row.period == "first_half" and row.team_scope in {"home", "away"}:
            return 0.5 <= line <= 1.5
        if row.team_scope in {"home", "away"}:
            return 0.5 <= line <= 3.5
        return 0.5 <= line <= 4.5
    if row.family == "asian_handicap":
        return line <= (1.5 if row.period == "first_half" else 3.0)
    return True


def _prediction_merlin_score(prediction) -> float:
    probability = prediction.predicted_probability or 0
    confidence = prediction.confidence or 0
    value = max(prediction.expected_value or 0, 0)
    return round(min(100, probability * 45 + confidence * 35 + value * 200), 1)


def _match_availability(db: Session, match_id: int) -> dict[str, str]:
    return {
        "estadisticas": "Disponible" if queries.list_match_statistics(db, match_id) else "No disponible",
        "eventos": "Disponible" if queries.list_match_events(db, match_id) else "No disponible",
        "alineaciones": "Disponible" if queries.list_match_lineups(db, match_id) else "No disponible",
        "cuotas": "Disponible" if queries.list_match_odds(db, match_id) else "No disponible",
        "predicciones": "Disponible",
        "picks": "Disponible",
    }


def _generic(rows: list[dict], empty_message: str = "No disponible") -> GenericInfoRead:
    return GenericInfoRead(available=bool(rows), message="Disponible" if rows else empty_message, rows=rows)


def _standing_read(db: Session, row) -> StandingRowRead:
    team = db.get(Team, row.team_id)
    return StandingRowRead(
        rank=row.rank,
        team_id=row.team_id,
        team_name=team.name if team else "No disponible",
        played=row.played,
        wins=row.wins,
        draws=row.draws,
        losses=row.losses,
        goals_for=row.goals_for,
        goals_against=row.goals_against,
        goal_difference=row.goal_difference,
        points=row.points,
        form=row.form,
        group_name=row.group_name,
        source_provider=row.source_provider,
    )


def _player_read(player: Player) -> dict:
    return {
        "id": player.id,
        "external_id": player.external_id,
        "nombre": player.name,
        "nacionalidad": player.nationality or "No disponible",
        "posicion": player.position or "No disponible",
        "foto": player.photo_url,
        "equipo_actual_id": player.current_team_id,
    }


def _score_label(match: Match) -> str:
    if match.home_score is None or match.away_score is None:
        return "No disponible"
    return f"{match.home_score}-{match.away_score}"


def _is_live_status(status: str | None) -> bool:
    return (status or "").lower() in _live_statuses()


def _live_statuses() -> set[str]:
    return {"live", "1h", "2h", "ht", "et", "p", "in_play", "first_half", "second_half", "halftime"}


def _ensure_date_loaded(db: Session, match_date: date) -> None:
    if queries.list_matches(db, match_date):
        return
    collect_schedule_data(db, match_date)
