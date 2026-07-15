from datetime import date

from datetime import datetime, timedelta

from sqlalchemy import Select, and_, func, not_, or_, select
from sqlalchemy.orm import Session, aliased, joinedload

from app.core.config import get_settings
from app.models import (
    ApiUsage,
    Competition,
    FixtureEvent,
    FixtureLineup,
    FixturePlayerStatistic,
    Match,
    Odds,
    Player,
    Prediction,
    PredictionSystem,
    ProviderEntityMapping,
    ProviderRawResponse,
    Standing,
    SyncJob,
    Team,
    TeamForm,
    TeamMatchStatistics,
)
from app.utils.dates import local_day_bounds_utc_naive, local_range_bounds_utc_naive


def match_query() -> Select[tuple[Match]]:
    return select(Match).options(
        joinedload(Match.competition),
        joinedload(Match.home_team),
        joinedload(Match.away_team),
        joinedload(Match.predictions),
    )


def list_matches(
    db: Session,
    match_date: date | None = None,
    country: str | None = None,
    competition_id: int | None = None,
    team: str | None = None,
    limit: int = 500,
    offset: int = 0,
) -> list[Match]:
    stmt = match_query()
    if match_date:
        start, end = local_day_bounds_utc_naive(match_date, get_settings().app_timezone)
        stmt = stmt.where(Match.kickoff_at >= start, Match.kickoff_at < end)
    if country:
        stmt = stmt.join(Match.competition).where(Competition.country == country)
    if competition_id:
        stmt = stmt.where(Match.competition_id == competition_id)
    if team:
        like = f"%{team}%"
        stmt = stmt.join(Match.home_team.of_type(Team), isouter=True).where(
            (Team.name.ilike(like)) | (Team.short_name.ilike(like))
        )
    return list(db.scalars(stmt.order_by(Match.kickoff_at).offset(offset).limit(limit)).unique())


def list_matches_range(db: Session, date_from: date, date_to: date, limit: int = 5000, offset: int = 0) -> list[Match]:
    start, end = local_range_bounds_utc_naive(date_from, date_to, get_settings().app_timezone)
    return list(
        db.scalars(
            match_query()
            .where(Match.kickoff_at >= start, Match.kickoff_at < end)
            .order_by(Match.kickoff_at)
            .offset(offset)
            .limit(limit)
        ).unique()
    )


def list_matches_by_statuses(db: Session, statuses: set[str], limit: int = 100) -> list[Match]:
    normalized = {status.lower() for status in statuses}
    stmt = match_query().where(func.lower(Match.status).in_(normalized)).order_by(Match.kickoff_at).limit(limit)
    return list(db.scalars(stmt).unique())


def list_h2h_matches(db: Session, home_team_id: int, away_team_id: int, exclude_match_id: int, limit: int = 10) -> list[Match]:
    stmt = (
        match_query()
        .where(
            or_(
                and_(Match.home_team_id == home_team_id, Match.away_team_id == away_team_id),
                and_(Match.home_team_id == away_team_id, Match.away_team_id == home_team_id),
            ),
            Match.id != exclude_match_id,
        )
        .order_by(Match.kickoff_at.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt).unique())


def get_match(db: Session, match_id: int) -> Match | None:
    return db.scalar(match_query().where(Match.id == match_id))


def list_competitions(db: Session) -> list[Competition]:
    return list(db.scalars(select(Competition).order_by(Competition.country, Competition.name)))


def get_competition(db: Session, competition_id: int) -> Competition | None:
    return db.get(Competition, competition_id)


def list_teams(db: Session, q: str | None = None, limit: int = 100) -> list[Team]:
    stmt = select(Team).order_by(Team.name).limit(limit)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Team.name.ilike(like), Team.short_name.ilike(like), Team.country.ilike(like)))
    return list(db.scalars(stmt))


def list_players(db: Session, q: str | None = None, limit: int = 100) -> list[Player]:
    stmt = select(Player).order_by(Player.name).limit(limit)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Player.name.ilike(like), Player.firstname.ilike(like), Player.lastname.ilike(like), Player.nationality.ilike(like)))
    return list(db.scalars(stmt))


def get_team(db: Session, team_id: int) -> Team | None:
    return db.get(Team, team_id)


def get_player(db: Session, player_id: int) -> Player | None:
    return db.get(Player, player_id)


def list_team_matches(db: Session, team_id: int, before: bool | None = None, limit: int = 10) -> list[Match]:
    now = datetime.utcnow()
    stmt = match_query().where((Match.home_team_id == team_id) | (Match.away_team_id == team_id))
    if before is True:
        stmt = stmt.where(Match.kickoff_at < now).order_by(Match.kickoff_at.desc())
    elif before is False:
        stmt = stmt.where(Match.kickoff_at >= now).order_by(Match.kickoff_at)
    else:
        stmt = stmt.order_by(Match.kickoff_at.desc())
    return list(db.scalars(stmt.limit(limit)).unique())


def list_competition_matches(db: Session, competition_id: int, before: bool | None = None, limit: int = 20) -> list[Match]:
    now = datetime.utcnow()
    stmt = match_query().where(Match.competition_id == competition_id)
    if before is True:
        stmt = stmt.where(Match.kickoff_at < now).order_by(Match.kickoff_at.desc())
    elif before is False:
        stmt = stmt.where(Match.kickoff_at >= now).order_by(Match.kickoff_at)
    else:
        stmt = stmt.order_by(Match.kickoff_at.desc())
    return list(db.scalars(stmt.limit(limit)).unique())


def count_competition_teams(db: Session, competition_id: int) -> int:
    rows = db.execute(
        select(Match.home_team_id).where(Match.competition_id == competition_id).union(
            select(Match.away_team_id).where(Match.competition_id == competition_id)
        )
    ).all()
    return len({row[0] for row in rows})


def count_competition_picks(db: Session, competition_id: int) -> int:
    return int(
        db.scalar(
            select(func.count(Prediction.id)).join(Prediction.match).where(Match.competition_id == competition_id)
        )
        or 0
    )


def latest_team_form(db: Session, team_id: int, competition_id: int) -> TeamForm | None:
    return db.scalar(
        select(TeamForm)
        .where(TeamForm.team_id == team_id, TeamForm.competition_id == competition_id)
        .order_by(TeamForm.reference_date.desc())
        .limit(1)
    )


def latest_any_team_form(db: Session, team_id: int) -> TeamForm | None:
    return db.scalar(select(TeamForm).where(TeamForm.team_id == team_id).order_by(TeamForm.reference_date.desc()).limit(1))


def list_match_statistics(db: Session, match_id: int) -> list[TeamMatchStatistics]:
    return list(db.scalars(select(TeamMatchStatistics).where(TeamMatchStatistics.match_id == match_id)))


def list_match_events(db: Session, match_id: int) -> list[FixtureEvent]:
    return list(db.scalars(select(FixtureEvent).where(FixtureEvent.match_id == match_id).order_by(FixtureEvent.minute, FixtureEvent.id)))


def list_match_lineups(db: Session, match_id: int) -> list[FixtureLineup]:
    return list(db.scalars(select(FixtureLineup).where(FixtureLineup.match_id == match_id).order_by(FixtureLineup.team_id, FixtureLineup.line_type, FixtureLineup.id)))


def list_match_player_statistics(db: Session, match_id: int) -> list[FixturePlayerStatistic]:
    return list(db.scalars(select(FixturePlayerStatistic).where(FixturePlayerStatistic.match_id == match_id)))


def list_match_odds(db: Session, match_id: int) -> list[Odds]:
    return list(db.scalars(select(Odds).where(Odds.match_id == match_id).order_by(Odds.market, Odds.selection, Odds.line)))


def list_standings(db: Session, competition_id: int | None = None) -> list[Standing]:
    stmt = select(Standing).order_by(Standing.competition_id, Standing.group_name, Standing.rank)
    if competition_id:
        stmt = stmt.where(Standing.competition_id == competition_id)
    return list(db.scalars(stmt))


def list_provider_raw_responses(db: Session, limit: int = 20) -> list[ProviderRawResponse]:
    return list(db.scalars(select(ProviderRawResponse).order_by(ProviderRawResponse.requested_at.desc()).limit(limit)))


def list_sync_jobs(db: Session, limit: int = 20) -> list[SyncJob]:
    return list(db.scalars(select(SyncJob).order_by(SyncJob.created_at.desc()).limit(limit)))


def list_api_usage(db: Session, limit: int = 20) -> list[ApiUsage]:
    return list(db.scalars(select(ApiUsage).order_by(ApiUsage.period_start.desc()).limit(limit)))


def count_unmatched_mappings(db: Session) -> int:
    return int(db.scalar(select(func.count(ProviderEntityMapping.id)).where(ProviderEntityMapping.match_status != "matched")) or 0)


def search_all(db: Session, q: str, limit: int = 8) -> list[dict]:
    like = f"%{q}%"
    results: list[dict] = []
    for team in db.scalars(select(Team).where(or_(Team.name.ilike(like), Team.short_name.ilike(like))).limit(limit)):
        results.append({"type": "team", "id": team.id, "title": team.name, "subtitle": team.country, "url": f"/teams/{team.id}"})
    for competition in db.scalars(select(Competition).where(or_(Competition.name.ilike(like), Competition.country.ilike(like))).limit(limit)):
        results.append({
            "type": "competition",
            "id": competition.id,
            "title": competition.name,
            "subtitle": f"{competition.country} · {competition.season}",
            "url": f"/competitions/{competition.id}",
        })
    for player in db.scalars(select(Player).where(Player.name.ilike(like)).limit(limit)):
        results.append({"type": "player", "id": player.id, "title": player.name, "subtitle": player.nationality, "url": f"/players/{player.id}"})
    home = aliased(Team)
    away = aliased(Team)
    match_stmt = (
        match_query()
        .join(home, Match.home_team_id == home.id)
        .join(away, Match.away_team_id == away.id)
        .where(or_(home.name.ilike(like), away.name.ilike(like), Match.external_id.ilike(like)))
        .limit(limit)
    )
    for match in db.scalars(match_stmt).unique():
        results.append({
            "type": "match",
            "id": match.id,
            "title": f"{match.home_team.name} vs {match.away_team.name}",
            "subtitle": f"{match.competition.name} · {match.kickoff_at:%d/%m/%Y %H:%M}",
            "url": f"/matches/{match.id}",
        })
    return results[:limit * 4]


def latest_odds(db: Session, match_id: int, market: str, selection: str, line: float | None) -> Odds | None:
    min_collected_at = datetime.utcnow() - timedelta(hours=get_settings().export_max_odds_age_hours)
    stmt = (
        select(Odds)
        .where(
            Odds.match_id == match_id,
            Odds.market == market,
            Odds.selection == selection,
            Odds.odds > 1,
            Odds.validation_status.in_(["mapped", "verified", "valid"]),
            Odds.collected_at >= min_collected_at,
        )
        .order_by(Odds.collected_at.desc())
        .limit(1)
    )
    if line is None:
        stmt = stmt.where(Odds.line.is_(None))
    else:
        stmt = stmt.where(Odds.line == line)
    return db.scalar(stmt)


def get_prediction_system(db: Session, code: str) -> PredictionSystem | None:
    return db.scalar(select(PredictionSystem).where(PredictionSystem.code == code))


def list_predictions(db: Session, status: str | None = None, market: str | None = None) -> list[Prediction]:
    stmt = select(Prediction).options(
        joinedload(Prediction.match).joinedload(Match.competition),
        joinedload(Prediction.match).joinedload(Match.home_team),
        joinedload(Prediction.match).joinedload(Match.away_team),
        joinedload(Prediction.system),
    )
    if status:
        stmt = stmt.where(Prediction.status == status)
        if status == "published":
            stmt = stmt.where(_not_blocked_publish_market())
    if market:
        stmt = stmt.where(Prediction.market == market)
    return list(db.scalars(stmt.order_by(Prediction.generated_at.desc())).unique())


def list_predictions_for_date(
    db: Session,
    match_date: date,
    status: str | None = None,
    market: str | None = None,
) -> list[Prediction]:
    start, end = local_day_bounds_utc_naive(match_date, get_settings().app_timezone)
    stmt = (
        select(Prediction)
        .join(Prediction.match)
        .options(
            joinedload(Prediction.match).joinedload(Match.competition),
            joinedload(Prediction.match).joinedload(Match.home_team),
            joinedload(Prediction.match).joinedload(Match.away_team),
            joinedload(Prediction.system),
        )
        .where(Match.kickoff_at >= start, Match.kickoff_at < end)
    )
    if status:
        stmt = stmt.where(Prediction.status == status)
        if status == "published":
            stmt = stmt.where(_not_blocked_publish_market())
    if market:
        stmt = stmt.where(Prediction.market == market)
    return list(db.scalars(stmt.order_by(Prediction.generated_at.desc())).unique())


def get_prediction(db: Session, prediction_id: int) -> Prediction | None:
    return db.get(Prediction, prediction_id)


def pick_counts_by_match(db: Session) -> dict[int, int]:
    rows = db.execute(
        select(Prediction.match_id, func.count(Prediction.id))
        .where(Prediction.predicted_probability.is_not(None))
        .group_by(Prediction.match_id)
    ).all()
    return {int(match_id): int(count) for match_id, count in rows}


def publishable_counts_by_match(db: Session) -> dict[int, int]:
    rows = db.execute(
        select(Prediction.match_id, func.count(Prediction.id))
        .where(
            Prediction.status.in_(["published", "ready_to_publish", "publishable"]),
            _not_blocked_publish_market(),
        )
        .group_by(Prediction.match_id)
    ).all()
    return {int(match_id): int(count) for match_id, count in rows}


def data_availability_by_match(db: Session, match_ids: list[int]) -> dict[int, dict[str, bool]]:
    if not match_ids:
        return {}
    availability = {
        match_id: {"statistics": False, "lineups": False, "odds": False}
        for match_id in match_ids
    }
    for match_id, count in db.execute(
        select(TeamMatchStatistics.match_id, func.count(TeamMatchStatistics.id))
        .where(TeamMatchStatistics.match_id.in_(match_ids))
        .group_by(TeamMatchStatistics.match_id)
    ):
        availability[int(match_id)]["statistics"] = int(count) > 0
    for match_id, count in db.execute(
        select(FixtureLineup.match_id, func.count(FixtureLineup.id))
        .where(FixtureLineup.match_id.in_(match_ids))
        .group_by(FixtureLineup.match_id)
    ):
        availability[int(match_id)]["lineups"] = int(count) > 0
    max_age = timedelta(hours=get_settings().export_max_odds_age_hours)
    min_collected_at = datetime.utcnow() - max_age
    for match_id, count in db.execute(
        select(Odds.match_id, func.count(Odds.id))
        .where(
            Odds.match_id.in_(match_ids),
            Odds.odds > 1,
            Odds.validation_status.in_(["mapped", "verified", "valid"]),
            Odds.collected_at >= min_collected_at,
        )
        .group_by(Odds.match_id)
    ):
        availability[int(match_id)]["odds"] = int(count) > 0
    return availability


def _not_blocked_publish_market():
    return not_(
        and_(
            Prediction.market == "goals",
            Prediction.selection == "over",
            Prediction.line.in_([1.5, 2.5]),
        )
    )
