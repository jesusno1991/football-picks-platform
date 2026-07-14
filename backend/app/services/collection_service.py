from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.factory import get_provider
from app.models import Competition, Match, Odds, PredictionSystem, Team, TeamForm


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
    match_date = match_date or date.today()
    competitions = 0
    teams = 0
    matches = 0

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
            db.add(
                Match(
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
            )
            matches += 1
    upsert_prediction_systems(db)
    db.commit()
    return {"competitions": competitions, "teams": teams, "matches": matches, "forms": 0, "odds": 0}


def _upsert_team(db: Session, data: dict) -> Team:
    team = db.scalar(select(Team).where(Team.external_id == data["external_id"]))
    if team:
        return team
    team = Team(**data)
    db.add(team)
    db.flush()
    return team
