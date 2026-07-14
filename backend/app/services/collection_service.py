import logging
import hashlib
import json
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.factory import get_provider
from app.models import ApiUsage, Competition, Match, Odds, PredictionSystem, ProviderEntityMapping, ProviderRawResponse, SyncJob, Team, TeamForm


INITIAL_SYSTEMS = [
    ("GOALS_OVER15_V1", "Over 1.5 Goals", "Sistema principal de goles prepartido", "goals", 0.66, 0.03, True),
    ("GOALS_OVER25_V1", "Over 2.5 Goals", "Sistema principal de goles prepartido", "goals", 0.56, 0.03, True),
    ("GOALS_OVER35_V1", "Over 3.5 Goals", "Sistema agresivo de goles prepartido", "goals", 0.42, 0.04, True),
    ("BTTS_V1", "BTTS", "Ambos equipos marcan", "btts", 0.55, 0.03, True),
    ("BTTS_OVER25_V1", "BTTS + Over 2.5", "Pendiente de activar", "goals", 0.42, 0.04, False),
    ("HOME_GOALS_V1", "Home Team Goals", "Pendiente de activar", "team_goals", 0.62, 0.03, False),
    ("AWAY_GOALS_V1", "Away Team Goals", "Pendiente de activar", "team_goals", 0.58, 0.03, False),
    ("UNDER25_V1", "Under 2.5 Goals", "Pendiente de activar", "goals", 0.55, 0.03, False),
    ("UNDER35_V1", "Under 3.5 Goals", "Pendiente de activar", "goals", 0.62, 0.03, False),
    ("CORNERS_OVER_85", "Más de 8,5 córners", "Mercado secundario pendiente", "corners", 0.58, 0.03, False),
    ("CORNERS_OVER_95", "Más de 9,5 córners", "Mercado secundario de córners", "corners", 0.56, 0.03, True),
    ("CORNERS_OVER_105", "Más de 10,5 córners", "Mercado secundario pendiente", "corners", 0.58, 0.03, False),
    ("HOME_WIN", "Gana local", "Mercado secundario pendiente", "result", 0.48, 0.03, False),
    ("AWAY_WIN", "Gana visitante", "Mercado secundario pendiente", "result", 0.42, 0.03, False),
    (
        "TIPSTRR_MARKET_ENGINE",
        "Motor Tipstrr multi-mercado",
        "Genera y evalua mercados tipo Tipstrr con probabilidad, cuota justa y EV",
        "tipstrr",
        0.0,
        0.03,
        True,
    ),
]

logger = logging.getLogger(__name__)


def upsert_prediction_systems(db: Session) -> int:
    count = 0
    for code, name, description, market, minimum_probability, minimum_value, active in INITIAL_SYSTEMS:
        system = db.scalar(select(PredictionSystem).where(PredictionSystem.code == code))
        if not system:
            system = PredictionSystem(
                code=code,
                name=name,
                description=description,
                market=market,
                minimum_probability=minimum_probability,
                minimum_value=minimum_value,
                is_active=active,
            )
            db.add(system)
            count += 1
    db.commit()
    return count


def collect_mock_data(db: Session, match_date: date | None = None) -> dict[str, int]:
    provider = get_provider()
    match_date = match_date or date.today()
    competitions = 0
    teams = 0
    matches = 0
    forms = 0
    odds_count = 0

    competition_by_external = {}
    match_items = provider.get_matches(match_date)

    for item in provider.get_competitions():
        competition = db.scalar(select(Competition).where(Competition.external_id == item["external_id"]))
        if not competition:
            competition = Competition(**item, is_active=True)
            db.add(competition)
            competitions += 1
        competition_by_external[item["external_id"]] = competition
    db.flush()

    for item in match_items:
        home = _upsert_team(db, item["home_team"])
        away = _upsert_team(db, item["away_team"])
        teams += 2
        competition = competition_by_external.get(item["competition_external_id"])
        if not competition:
            competition_data = item.get(
                "competition",
                {
                    "external_id": item["competition_external_id"],
                    "name": "Unknown Competition",
                    "country": "Unknown",
                    "season": item.get("season", str(match_date.year)),
                    "logo_url": None,
                },
            )
            competition = Competition(**competition_data, is_active=True)
            db.add(competition)
            db.flush()
            competition_by_external[competition.external_id] = competition
            competitions += 1
        match = db.scalar(select(Match).where(Match.external_id == item["external_id"]))
        if not match:
            match = Match(
                external_id=item["external_id"],
                competition_id=competition.id,
                home_team_id=home.id,
                away_team_id=away.id,
                kickoff_at=item["kickoff_at"],
                status="scheduled",
                venue=item["venue"],
                round=item["round"],
                season=item["season"],
            )
            db.add(match)
            matches += 1
        else:
            _update_match(match, item, competition, home, away)
        db.flush()
        for team in (home, away):
            if hasattr(provider, "get_team_history_for_match"):
                history = provider.get_team_history_for_match(match.external_id, team.external_id)
            else:
                history = provider.get_team_history(team.external_id)
            form = db.scalar(
                select(TeamForm).where(
                    TeamForm.team_id == team.id,
                    TeamForm.competition_id == competition.id,
                    TeamForm.reference_date == datetime.combine(match_date, datetime.min.time()),
                )
            )
            if not form:
                form = TeamForm(
                    team_id=team.id,
                    competition_id=competition.id,
                    reference_date=datetime.combine(match_date, datetime.min.time()),
                    **history,
                )
                db.add(form)
                forms += 1
        for odd in provider.get_odds(match.external_id):
            existing = db.scalar(
                select(Odds).where(
                    Odds.match_id == match.id,
                    Odds.bookmaker == odd["bookmaker"],
                    Odds.market == odd["market"],
                    Odds.selection == odd["selection"],
                    Odds.line == odd["line"],
                    Odds.period == odd.get("period"),
                    Odds.team_scope == odd.get("team_scope"),
                )
            )
            if not existing:
                db.add(Odds(match_id=match.id, **odd))
                odds_count += 1
    upsert_prediction_systems(db)
    db.commit()
    return {"competitions": competitions, "teams": teams, "matches": matches, "forms": forms, "odds": odds_count}


def collect_schedule_data(db: Session, match_date: date | None = None) -> dict[str, int]:
    provider = get_provider()
    provider_name = provider.__class__.__name__
    match_date = match_date or date.today()
    job = _start_sync_job(db, "schedule_day", provider_name, match_date)
    competitions = 0
    teams = 0
    matches = 0

    competition_by_external = {}
    try:
        match_items = provider.get_matches(match_date)
        _record_api_usage(db, provider_name, "get_matches", success=True)
        _record_raw_snapshot(db, provider_name, "get_matches", match_date.isoformat(), match_items)

        competition_items = provider.get_competitions()
        _record_api_usage(db, provider_name, "get_competitions", success=True)
        _record_raw_snapshot(db, provider_name, "get_competitions", match_date.isoformat(), competition_items)

        for item in competition_items:
            competition = db.scalar(select(Competition).where(Competition.external_id == item["external_id"]))
            if not competition:
                competition = Competition(**item, is_active=True)
                db.add(competition)
                competitions += 1
            competition_by_external[item["external_id"]] = competition
            _upsert_mapping(db, "competition", provider_name, item["external_id"], item.get("name"), competition.id)
        db.flush()

        for item in match_items:
            home = _upsert_team(db, item["home_team"], provider_name)
            away = _upsert_team(db, item["away_team"], provider_name)
            teams += 2
            competition = competition_by_external.get(item["competition_external_id"])
            if not competition:
                competition_data = item.get(
                    "competition",
                    {
                        "external_id": item["competition_external_id"],
                        "name": "Unknown Competition",
                        "country": "Unknown",
                        "season": item.get("season", str(match_date.year)),
                        "logo_url": None,
                    },
                )
                competition = Competition(**competition_data, is_active=True)
                db.add(competition)
                db.flush()
                competition_by_external[competition.external_id] = competition
                competitions += 1
                _upsert_mapping(db, "competition", provider_name, competition.external_id, competition.name, competition.id)
            match = db.scalar(select(Match).where(Match.external_id == item["external_id"]))
            if not match:
                match = Match(
                    external_id=item["external_id"],
                    competition_id=competition.id,
                    home_team_id=home.id,
                    away_team_id=away.id,
                    kickoff_at=item["kickoff_at"],
                    status=item.get("status", "scheduled"),
                    venue=item["venue"],
                    round=item["round"],
                    season=item["season"],
                )
                db.add(match)
                matches += 1
            else:
                _update_match(match, item, competition, home, away)
            db.flush()
            _upsert_mapping(db, "fixture", provider_name, item["external_id"], f"{home.name} vs {away.name}", match.id)
        upsert_prediction_systems(db)
        _finish_sync_job(job, matches + competitions + teams, 0, "ok")
        db.commit()
        return {"competitions": competitions, "teams": teams, "matches": matches, "forms": 0, "odds": 0}
    except Exception as exc:
        _record_api_usage(db, provider_name, "schedule_day", success=False)
        _finish_sync_job(job, matches + competitions + teams, 1, str(exc))
        db.commit()
        raise


def collect_schedule_range(db: Session, date_from: date, date_to: date) -> dict[str, int]:
    totals = {"competitions": 0, "teams": 0, "matches": 0, "forms": 0, "odds": 0, "days": 0, "errors": 0}
    current = date_from
    while current <= date_to:
        try:
            result = collect_schedule_data(db, current)
            logger.info("calendar backfill date=%s result=%s", current.isoformat(), result)
            for key in ("competitions", "teams", "matches", "forms", "odds"):
                totals[key] += int(result.get(key, 0))
            totals["days"] += 1
        except Exception:
            totals["errors"] += 1
            logger.exception("calendar backfill failed date=%s", current.isoformat())
        current += timedelta(days=1)
    logger.info("calendar backfill complete date_from=%s date_to=%s totals=%s", date_from.isoformat(), date_to.isoformat(), totals)
    return totals


def _upsert_team(db: Session, data: dict, provider_name: str | None = None) -> Team:
    team = db.scalar(select(Team).where(Team.external_id == data["external_id"]))
    if team:
        if provider_name:
            _upsert_mapping(db, "team", provider_name, data["external_id"], data.get("name"), team.id)
        return team
    team = Team(**data)
    db.add(team)
    db.flush()
    if provider_name:
        _upsert_mapping(db, "team", provider_name, data["external_id"], data.get("name"), team.id)
    return team


def _update_match(match: Match, item: dict, competition: Competition, home: Team, away: Team) -> None:
    match.competition_id = competition.id
    match.home_team_id = home.id
    match.away_team_id = away.id
    match.kickoff_at = item["kickoff_at"]
    match.status = item.get("status", match.status or "scheduled")
    match.venue = item.get("venue")
    match.round = item.get("round")
    match.season = item.get("season", match.season)


def _start_sync_job(db: Session, job_type: str, provider: str, target_date: date) -> SyncJob:
    job = SyncJob(
        job_type=job_type,
        provider=provider,
        status="running",
        target_date=datetime.combine(target_date, datetime.min.time()),
        started_at=datetime.utcnow(),
        records_processed=0,
        error_count=0,
    )
    db.add(job)
    db.flush()
    return job


def _finish_sync_job(job: SyncJob, records: int, errors: int, message: str) -> None:
    job.status = "failed" if errors else "success"
    job.finished_at = datetime.utcnow()
    job.records_processed = records
    job.error_count = errors
    job.message = message[:1000]


def _record_api_usage(db: Session, provider: str, endpoint: str, success: bool) -> None:
    now = datetime.utcnow()
    period_start = datetime(now.year, now.month, now.day, now.hour)
    period_end = period_start + timedelta(hours=1)
    usage = db.scalar(
        select(ApiUsage).where(
            ApiUsage.provider == provider,
            ApiUsage.endpoint == endpoint,
            ApiUsage.period_start == period_start,
            ApiUsage.period_end == period_end,
        )
    )
    if not usage:
        usage = ApiUsage(
            provider=provider,
            endpoint=endpoint,
            period_start=period_start,
            period_end=period_end,
            requests_count=0,
            success_count=0,
            error_count=0,
        )
        db.add(usage)
    usage.requests_count += 1
    if success:
        usage.success_count += 1
    else:
        usage.error_count += 1


def _record_raw_snapshot(db: Session, provider: str, endpoint: str, external_id: str, payload: object) -> None:
    payload_json = json.dumps(payload, default=str, ensure_ascii=False)
    checksum = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
    existing = db.scalar(
        select(ProviderRawResponse).where(
            ProviderRawResponse.provider == provider,
            ProviderRawResponse.endpoint == endpoint,
            ProviderRawResponse.external_id == external_id,
            ProviderRawResponse.checksum == checksum,
        )
    )
    if existing:
        return
    db.add(
        ProviderRawResponse(
            provider=provider,
            endpoint=endpoint,
            external_id=external_id,
            response_status="normalized_snapshot",
            payload_json=payload_json,
            checksum=checksum,
            expires_at=datetime.utcnow() + timedelta(days=7),
        )
    )


def _upsert_mapping(db: Session, entity_type: str, provider: str, provider_external_id: str, name: str | None, internal_id: int | None) -> None:
    mapping = db.scalar(
        select(ProviderEntityMapping).where(
            ProviderEntityMapping.entity_type == entity_type,
            ProviderEntityMapping.provider == provider,
            ProviderEntityMapping.provider_external_id == provider_external_id,
        )
    )
    if not mapping:
        mapping = ProviderEntityMapping(
            entity_type=entity_type,
            provider=provider,
            provider_external_id=provider_external_id,
            provider_name=name,
            normalized_name=(name or "").strip().lower() or None,
            internal_id=internal_id,
            match_status="matched" if internal_id else "unmatched",
            confidence=1.0 if internal_id else None,
        )
        db.add(mapping)
    else:
        mapping.provider_name = name or mapping.provider_name
        mapping.normalized_name = (name or mapping.provider_name or "").strip().lower() or None
        mapping.internal_id = internal_id or mapping.internal_id
        mapping.match_status = "matched" if mapping.internal_id else mapping.match_status
        mapping.confidence = 1.0 if mapping.internal_id else mapping.confidence
