from datetime import date

from sqlalchemy import Select, and_, func, not_, select
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.models import Competition, Match, Odds, Prediction, PredictionSystem, Team, TeamForm
from app.utils.dates import local_day_bounds_utc_naive, local_range_bounds_utc_naive


def match_query() -> Select[tuple[Match]]:
    return select(Match).options(
        joinedload(Match.competition),
        joinedload(Match.home_team),
        joinedload(Match.away_team),
    )


def list_matches(
    db: Session,
    match_date: date | None = None,
    country: str | None = None,
    competition_id: int | None = None,
    team: str | None = None,
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
    return list(db.scalars(stmt.order_by(Match.kickoff_at)).unique())


def list_matches_range(db: Session, date_from: date, date_to: date) -> list[Match]:
    start, end = local_range_bounds_utc_naive(date_from, date_to, get_settings().app_timezone)
    return list(db.scalars(match_query().where(Match.kickoff_at >= start, Match.kickoff_at < end).order_by(Match.kickoff_at)).unique())


def get_match(db: Session, match_id: int) -> Match | None:
    return db.scalar(match_query().where(Match.id == match_id))


def list_competitions(db: Session) -> list[Competition]:
    return list(db.scalars(select(Competition).order_by(Competition.country, Competition.name)))


def get_team(db: Session, team_id: int) -> Team | None:
    return db.get(Team, team_id)


def latest_team_form(db: Session, team_id: int, competition_id: int) -> TeamForm | None:
    return db.scalar(
        select(TeamForm)
        .where(TeamForm.team_id == team_id, TeamForm.competition_id == competition_id)
        .order_by(TeamForm.reference_date.desc())
        .limit(1)
    )


def latest_odds(db: Session, match_id: int, market: str, selection: str, line: float | None) -> Odds | None:
    stmt = (
        select(Odds)
        .where(Odds.match_id == match_id, Odds.market == market, Odds.selection == selection)
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


def _not_blocked_publish_market():
    return not_(
        and_(
            Prediction.market == "goals",
            Prediction.selection == "over",
            Prediction.line.in_([1.5, 2.5]),
        )
    )
