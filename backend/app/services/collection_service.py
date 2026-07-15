import logging
import hashlib
import json
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.flashscore_provider import FlashScoreRapidApiProvider
from app.collectors.factory import get_provider
from app.core.config import get_settings
from app.models import (
    ApiUsage,
    Competition,
    FixtureEvent,
    FixtureLineup,
    Match,
    Odds,
    Player,
    PredictionSystem,
    ProviderEntityMapping,
    ProviderRawResponse,
    Standing,
    SyncJob,
    Team,
    TeamForm,
    TeamMatchStatistics,
)
from app.repositories import queries
from app.utils.time import utc_now_naive


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
                    home_score=item.get("home_score"),
                    away_score=item.get("away_score"),
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


def collect_flashscore_live_data(db: Session, limit: int = 50) -> dict[str, int]:
    if not get_settings().rapidapi_key:
        return {"matches": 0, "statistics": 0, "events": 0, "errors": 0}
    provider = FlashScoreRapidApiProvider()
    provider_name = provider.__class__.__name__
    job = _start_sync_job(db, "flashscore_live", provider_name, date.today())
    totals = {"matches": 0, "statistics": 0, "events": 0, "errors": 0}
    try:
        match_items = provider.get_live_matches()[:limit]
        _record_api_usage(db, provider_name, "get_live_matches", success=True)
        _record_raw_snapshot(db, provider_name, "get_live_matches", date.today().isoformat(), match_items)
        competition_by_external: dict[str, Competition] = {}
        for item in match_items:
            home = _upsert_team(db, item["home_team"], provider_name)
            away = _upsert_team(db, item["away_team"], provider_name)
            competition = competition_by_external.get(item["competition_external_id"])
            if not competition:
                competition_data = item.get(
                    "competition",
                    {
                        "external_id": item["competition_external_id"],
                        "name": "Unknown Competition",
                        "country": "Unknown",
                        "season": item.get("season", str(date.today().year)),
                        "logo_url": None,
                    },
                )
                competition = db.scalar(select(Competition).where(Competition.external_id == competition_data["external_id"]))
                if not competition:
                    competition = Competition(**competition_data, is_active=True)
                    db.add(competition)
                    db.flush()
                competition_by_external[competition.external_id] = competition
                _upsert_mapping(db, "competition", provider_name, competition.external_id, competition.name, competition.id)

            match = db.scalar(select(Match).where(Match.external_id == item["external_id"]))
            if not match:
                match = Match(
                    external_id=item["external_id"],
                    competition_id=competition.id,
                    home_team_id=home.id,
                    away_team_id=away.id,
                    kickoff_at=item["kickoff_at"],
                    status=item.get("status", "live"),
                    home_score=item.get("home_score"),
                    away_score=item.get("away_score"),
                    venue=item.get("venue"),
                    round=item.get("round"),
                    season=item.get("season", str(date.today().year)),
                )
                db.add(match)
                totals["matches"] += 1
            else:
                _update_match(match, item, competition, home, away)
            db.flush()
            _upsert_mapping(db, "fixture", provider_name, item["external_id"], f"{home.name} vs {away.name}", match.id)

            try:
                stats_payload = provider.get_match_statistics(match.external_id)
                totals["statistics"] += _upsert_match_statistics(db, match, stats_payload)
                _record_api_usage(db, provider_name, "get_live_match_statistics", success=True)
            except Exception:
                totals["errors"] += 1
                _record_api_usage(db, provider_name, "get_live_match_statistics", success=False)
                logger.exception("flashscore live stats failed match_id=%s", match.external_id)
            try:
                events_payload = provider.get_events(match.external_id)
                totals["events"] += _upsert_events(db, match, events_payload, provider_name)
                _record_api_usage(db, provider_name, "get_live_events", success=True)
            except Exception:
                totals["errors"] += 1
                _record_api_usage(db, provider_name, "get_live_events", success=False)
                logger.exception("flashscore live events failed match_id=%s", match.external_id)
        _finish_sync_job(job, sum(totals.values()), totals["errors"], "ok")
        db.commit()
        return totals
    except Exception as exc:
        totals["errors"] += 1
        _record_api_usage(db, provider_name, "get_live_matches", success=False)
        _finish_sync_job(job, sum(totals.values()), totals["errors"], str(exc))
        db.commit()
        logger.exception("flashscore live sync failed")
        return totals


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


def collect_deep_data_for_date(db: Session, match_date: date) -> dict[str, int]:
    collect_schedule_data(db, match_date)
    matches = queries.list_matches(db, match_date, limit=5000)
    totals = {"matches": 0, "statistics": 0, "forms": 0, "odds": 0, "events": 0, "lineups": 0, "standings": 0, "errors": 0}
    for match in matches:
        try:
            result = collect_match_deep_data(db, match.id)
            for key in totals:
                totals[key] += int(result.get(key, 0))
        except Exception:
            totals["errors"] += 1
            logger.exception("deep sync failed match_id=%s", match.id)
    db.commit()
    return totals


def collect_match_deep_data(db: Session, match_id: int) -> dict[str, int]:
    provider = get_provider()
    provider_name = provider.__class__.__name__
    match = db.get(Match, match_id)
    if not match:
        raise ValueError(f"Match not found: {match_id}")
    totals = {"matches": 1, "statistics": 0, "forms": 0, "odds": 0, "events": 0, "lineups": 0, "standings": 0, "errors": 0}

    try:
        totals["forms"] += _upsert_team_forms_for_match(db, provider, match)
        _record_api_usage(db, provider_name, "get_team_history", success=True)
    except Exception:
        totals["errors"] += 1
        _record_api_usage(db, provider_name, "get_team_history", success=False)
        logger.exception("team form sync failed match_id=%s", match.id)

    try:
        stats_payload = provider.get_match_statistics(match.external_id)
        _record_api_usage(db, provider_name, "get_match_statistics", success=True)
        _record_raw_snapshot(db, provider_name, "get_match_statistics", match.external_id, stats_payload)
        totals["statistics"] += _upsert_match_statistics(db, match, stats_payload)
    except Exception:
        totals["errors"] += 1
        _record_api_usage(db, provider_name, "get_match_statistics", success=False)
        logger.exception("statistics sync failed match_id=%s", match.id)

    try:
        odds_payload = provider.get_odds(match.external_id)
        _record_api_usage(db, provider_name, "get_odds", success=True)
        _record_raw_snapshot(db, provider_name, "get_odds", match.external_id, odds_payload)
        totals["odds"] += _upsert_odds(db, match, odds_payload)
    except Exception:
        totals["errors"] += 1
        _record_api_usage(db, provider_name, "get_odds", success=False)
        logger.exception("odds sync failed match_id=%s", match.id)

    try:
        events_payload = provider.get_events(match.external_id)
        _record_api_usage(db, provider_name, "get_events", success=True)
        _record_raw_snapshot(db, provider_name, "get_events", match.external_id, events_payload)
        totals["events"] += _upsert_events(db, match, events_payload, provider_name)
    except Exception:
        totals["errors"] += 1
        _record_api_usage(db, provider_name, "get_events", success=False)
        logger.exception("events sync failed match_id=%s", match.id)

    try:
        lineups_payload = provider.get_lineups(match.external_id)
        _record_api_usage(db, provider_name, "get_lineups", success=True)
        _record_raw_snapshot(db, provider_name, "get_lineups", match.external_id, lineups_payload)
        totals["lineups"] += _upsert_lineups(db, match, lineups_payload, provider_name)
    except Exception:
        totals["errors"] += 1
        _record_api_usage(db, provider_name, "get_lineups", success=False)
        logger.exception("lineups sync failed match_id=%s", match.id)

    try:
        standings_payload = provider.get_standings(match.competition.external_id, match.season)
        if standings_payload:
            _record_api_usage(db, provider_name, "get_standings", success=True)
            _record_raw_snapshot(db, provider_name, "get_standings", match.competition.external_id, standings_payload)
            totals["standings"] += _upsert_standings(db, match.competition_id, match.season, standings_payload, provider_name)
    except Exception:
        totals["errors"] += 1
        _record_api_usage(db, provider_name, "get_standings", success=False)
        logger.exception("standings sync failed competition_id=%s", match.competition_id)

    db.commit()
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
    if item.get("home_score") is not None:
        match.home_score = item.get("home_score")
    if item.get("away_score") is not None:
        match.away_score = item.get("away_score")
    match.venue = item.get("venue")
    match.round = item.get("round")
    match.season = item.get("season", match.season)


def _upsert_team_forms_for_match(db: Session, provider: object, match: Match) -> int:
    count = 0
    reference_date = datetime.combine(match.kickoff_at.date(), datetime.min.time())
    for team in (match.home_team, match.away_team):
        if hasattr(provider, "get_team_history_for_match"):
            history = provider.get_team_history_for_match(match.external_id, team.external_id)
        else:
            history = provider.get_team_history(team.external_id)
        existing = db.scalar(
            select(TeamForm).where(
                TeamForm.team_id == team.id,
                TeamForm.competition_id == match.competition_id,
                TeamForm.reference_date == reference_date,
            )
        )
        if existing:
            for key, value in history.items():
                setattr(existing, key, value)
            count += 1
        else:
            db.add(
                TeamForm(
                    team_id=team.id,
                    competition_id=match.competition_id,
                    reference_date=reference_date,
                    **history,
                )
            )
            count += 1
    return count


def _upsert_match_statistics(db: Session, match: Match, payload: list[dict]) -> int:
    count = 0
    for index, row in enumerate(payload):
        team_raw = row.get("team") or {}
        stats_raw = row.get("statistics") or []
        team_id = _internal_team_id_for_provider_team(match, team_raw)
        if not team_id:
            continue
        existing = db.scalar(select(TeamMatchStatistics).where(TeamMatchStatistics.match_id == match.id, TeamMatchStatistics.team_id == team_id))
        values = _statistics_values(stats_raw)
        if not existing:
            existing = TeamMatchStatistics(match_id=match.id, team_id=team_id, is_home=team_id == match.home_team_id, **values)
            db.add(existing)
            count += 1
        else:
            for key, value in values.items():
                setattr(existing, key, value)
        if index == 0 and values.get("corners") is not None:
            match.home_corners = int(values["corners"]) if team_id == match.home_team_id else match.home_corners
        if index == 1 and values.get("corners") is not None:
            match.away_corners = int(values["corners"]) if team_id == match.away_team_id else match.away_corners
    return count


def _upsert_odds(db: Session, match: Match, payload: list[dict]) -> int:
    count = 0
    for odd in payload:
        existing = db.scalar(
            select(Odds).where(
                Odds.match_id == match.id,
                Odds.bookmaker == odd["bookmaker"],
                Odds.market == odd["market"],
                Odds.selection == odd["selection"],
                Odds.line == odd.get("line"),
                Odds.period == odd.get("period"),
                Odds.team_scope == odd.get("team_scope"),
            )
        )
        if existing:
            existing.odds = odd["odds"]
            existing.collected_at = utc_now_naive()
            existing.validation_status = odd.get("validation_status", existing.validation_status)
            count += 1
        else:
            db.add(Odds(match_id=match.id, **odd))
            count += 1
    return count


def _upsert_events(db: Session, match: Match, payload: list[dict], provider_name: str) -> int:
    count = 0
    for row in payload:
        team_id = _internal_team_id_for_provider_team(match, row.get("team") or {})
        player = _upsert_player_from_event(db, row.get("player") or {}, team_id)
        assist = _upsert_player_from_event(db, row.get("assist") or {}, team_id)
        time_data = row.get("time") or {}
        score_data = row.get("score") or {}
        minute = _to_int(time_data.get("elapsed"))
        detail = row.get("detail")
        event_type = row.get("type") or "event"
        duplicate = db.scalar(
            select(FixtureEvent).where(
                FixtureEvent.match_id == match.id,
                FixtureEvent.minute == minute,
                FixtureEvent.team_id == team_id,
                FixtureEvent.event_type == str(event_type),
                FixtureEvent.detail == detail,
            )
        )
        if duplicate:
            continue
        db.add(
            FixtureEvent(
                match_id=match.id,
                team_id=team_id,
                player_id=player.id if player else None,
                assist_player_id=assist.id if assist else None,
                minute=minute,
                extra_minute=_to_int(time_data.get("extra")),
                event_type=str(event_type),
                detail=detail,
                comments=row.get("comments"),
                score_home=_to_int((score_data.get("home") if isinstance(score_data, dict) else None)),
                score_away=_to_int((score_data.get("away") if isinstance(score_data, dict) else None)),
                source_provider=provider_name,
                raw_payload=json.dumps(row, ensure_ascii=False, default=str),
            )
        )
        count += 1
    return count


def _upsert_lineups(db: Session, match: Match, payload: list[dict], provider_name: str) -> int:
    count = 0
    for team_row in payload:
        team_id = _internal_team_id_for_provider_team(match, team_row.get("team") or {})
        if not team_id:
            continue
        formation = team_row.get("formation")
        for line_type, players in (("starting", team_row.get("startXI") or []), ("substitute", team_row.get("substitutes") or [])):
            for item in players:
                player_raw = item.get("player") or item
                player = _upsert_player_from_event(db, player_raw, team_id)
                if not player:
                    continue
                existing = db.scalar(select(FixtureLineup).where(FixtureLineup.match_id == match.id, FixtureLineup.team_id == team_id, FixtureLineup.player_id == player.id))
                if existing:
                    existing.formation = formation
                    existing.line_type = line_type
                    existing.position = player_raw.get("pos")
                    existing.grid = player_raw.get("grid")
                    existing.shirt_number = _to_int(player_raw.get("number"))
                else:
                    db.add(
                        FixtureLineup(
                            match_id=match.id,
                            team_id=team_id,
                            player_id=player.id,
                            coach_id=None,
                            formation=formation,
                            line_type=line_type,
                            position=player_raw.get("pos"),
                            grid=player_raw.get("grid"),
                            shirt_number=_to_int(player_raw.get("number")),
                            is_captain=False,
                            rating=None,
                            source_provider=provider_name,
                            raw_payload=json.dumps(item, ensure_ascii=False, default=str),
                        )
                    )
                    count += 1
    return count


def _upsert_standings(db: Session, competition_id: int, season: str, payload: list[dict], provider_name: str) -> int:
    count = 0
    for row in payload:
        team_raw = row.get("team") or {}
        team_external = f"api-football-team-{team_raw.get('id')}" if team_raw.get("id") is not None else None
        team = db.scalar(select(Team).where(Team.external_id == team_external)) if team_external else None
        if not team and team_raw.get("name"):
            team = _upsert_team(db, {"external_id": team_external or f"{provider_name}-team-{team_raw.get('name')}", "name": team_raw.get("name"), "short_name": str(team_raw.get("name"))[:3].upper(), "country": None, "logo_url": team_raw.get("logo")}, provider_name)
        if not team:
            continue
        existing = db.scalar(select(Standing).where(Standing.competition_id == competition_id, Standing.season == season, Standing.group_name == row.get("group"), Standing.team_id == team.id))
        values = {
            "rank": _to_int(row.get("rank")) or 0,
            "played": _to_int((row.get("all") or {}).get("played")),
            "wins": _to_int((row.get("all") or {}).get("win")),
            "draws": _to_int((row.get("all") or {}).get("draw")),
            "losses": _to_int((row.get("all") or {}).get("lose")),
            "goals_for": _to_int(((row.get("all") or {}).get("goals") or {}).get("for")),
            "goals_against": _to_int(((row.get("all") or {}).get("goals") or {}).get("against")),
            "goal_difference": _to_int(row.get("goalsDiff")),
            "points": _to_int(row.get("points")),
            "form": row.get("form"),
            "description": row.get("description"),
            "source_provider": provider_name,
            "source_updated_at": utc_now_naive(),
        }
        if existing:
            for key, value in values.items():
                setattr(existing, key, value)
        else:
            db.add(Standing(competition_id=competition_id, season=season, group_name=row.get("group"), team_id=team.id, **values))
            count += 1
    return count


def _internal_team_id_for_provider_team(match: Match, team_raw: dict) -> int | None:
    raw_id = team_raw.get("id")
    if raw_id == "home":
        return match.home_team_id
    if raw_id == "away":
        return match.away_team_id
    if raw_id is not None:
        external = f"api-football-team-{raw_id}"
        if match.home_team.external_id == external:
            return match.home_team_id
        if match.away_team.external_id == external:
            return match.away_team_id
        flashscore_external = f"flashscore-team-{raw_id}"
        if match.home_team.external_id == flashscore_external:
            return match.home_team_id
        if match.away_team.external_id == flashscore_external:
            return match.away_team_id
    name = str(team_raw.get("name") or "").strip().lower()
    if name and match.home_team.name.strip().lower() == name:
        return match.home_team_id
    if name and match.away_team.name.strip().lower() == name:
        return match.away_team_id
    return None


def _statistics_values(stats_raw: list[dict]) -> dict:
    values = {str(item.get("type") or "").lower(): item.get("value") for item in stats_raw if isinstance(item, dict)}
    return {
        "possession": _percent(values.get("ball possession")),
        "shots": _to_float(values.get("total shots")),
        "shots_on_target": _to_float(values.get("shots on goal")),
        "corners": _to_float(values.get("corner kicks")),
        "dangerous_attacks": _to_float(values.get("dangerous attacks")),
        "goals": None,
        "xg": _to_float(values.get("expected goals")),
        "yellow_cards": _to_float(values.get("yellow cards")),
        "red_cards": _to_float(values.get("red cards")),
    }


def _upsert_player_from_event(db: Session, raw: dict, team_id: int | None) -> Player | None:
    player_id = raw.get("id")
    name = raw.get("name")
    if not player_id and not name:
        return None
    external_id = f"api-football-player-{player_id}" if player_id is not None else None
    player = db.scalar(select(Player).where(Player.external_id == external_id)) if external_id else None
    if not player and name:
        player = Player(external_id=external_id, name=str(name), firstname=None, lastname=None, nationality=None, birth_date=None, position=raw.get("pos"), height=None, weight=None, photo_url=None, current_team_id=team_id)
        db.add(player)
        db.flush()
    elif player and team_id and not player.current_team_id:
        player.current_team_id = team_id
    return player


def _percent(value) -> float | None:
    if isinstance(value, str) and value.endswith("%"):
        return _to_float(value[:-1])
    return _to_float(value)


def _to_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _to_float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _start_sync_job(db: Session, job_type: str, provider: str, target_date: date) -> SyncJob:
    job = SyncJob(
        job_type=job_type,
        provider=provider,
        status="running",
        target_date=datetime.combine(target_date, datetime.min.time()),
        started_at=utc_now_naive(),
        records_processed=0,
        error_count=0,
    )
    db.add(job)
    db.flush()
    return job


def _finish_sync_job(job: SyncJob, records: int, errors: int, message: str) -> None:
    job.status = "failed" if errors else "success"
    job.finished_at = utc_now_naive()
    job.records_processed = records
    job.error_count = errors
    job.message = message[:1000]


def _record_api_usage(db: Session, provider: str, endpoint: str, success: bool) -> None:
    now = utc_now_naive()
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
            expires_at=utc_now_naive() + timedelta(days=7),
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
