from datetime import datetime, timedelta

from app.models import Competition, Match, Odds, Team, TeamForm
from app.services.tipstrr_market_service import list_tipstrr_market_picks


def test_tipstrr_market_picks_include_requested_market_groups(db):
    match = _create_match_with_forms(db)

    rows = list_tipstrr_market_picks(db, match.kickoff_at.date())

    groups = {row.group for row in rows}
    assert "1X2" in groups
    assert "Empate no apuesta" in groups
    assert "Goles partido" in groups
    assert "Marcador correcto" in groups
    assert "Goles local" in groups
    assert "Goles visitante" in groups
    assert "1a parte local" in groups
    assert "1a parte visitante" in groups
    assert "Handicap asiatico" in groups
    assert "Handicap asiatico 1a parte" in groups


def test_tipstrr_market_picks_find_publicable_real_odds(db):
    match = _create_match_with_forms(db)
    db.add(
        Odds(
            match_id=match.id,
            bookmaker="Bet365",
            market="goals",
            market_family="total_goals",
            period="full_time",
            team_scope="all",
            selection="over",
            line=3.0,
            odds=4.5,
            provider="test",
            validation_status="mapped",
        )
    )
    db.commit()

    rows = list_tipstrr_market_picks(db, match.kickoff_at.date(), "PUBLICABLE")

    assert any(row.group == "Goles partido" and row.label == "Mas de 3.0 goles" for row in rows)
    assert all(not (row.family == "total_goals" and row.team_scope == "all" and row.selection == "over" and row.line in {1.5, 2.5}) for row in rows)


def test_tipstrr_endpoint_returns_all_markets(client):
    response = client.post("/api/admin/collect", headers={"X-Admin-Token": "test-secret"})
    assert response.status_code == 200

    data = client.get("/api/tipstrr-market-picks").json()

    assert data
    assert {"1X2", "Goles partido", "Marcador correcto"}.issubset({row["group"] for row in data})


def _create_match_with_forms(db):
    kickoff = datetime.utcnow() + timedelta(days=1)
    competition = Competition(
        external_id="comp-1",
        name="Test League",
        country="Spain",
        logo_url=None,
        season="2026",
        is_active=True,
    )
    home = Team(external_id="team-home", name="Home FC", short_name="HOM", country="Spain", logo_url=None)
    away = Team(external_id="team-away", name="Away FC", short_name="AWA", country="Spain", logo_url=None)
    db.add_all([competition, home, away])
    db.flush()
    match = Match(
        external_id="match-1",
        competition_id=competition.id,
        home_team_id=home.id,
        away_team_id=away.id,
        kickoff_at=kickoff,
        status="scheduled",
        venue=None,
        round=None,
        season="2026",
    )
    db.add(match)
    db.flush()
    for team_id, goals_for, goals_against in ((home.id, 2.1, 1.0), (away.id, 1.3, 1.6)):
        db.add(
            TeamForm(
                team_id=team_id,
                competition_id=competition.id,
                reference_date=kickoff.replace(hour=0, minute=0, second=0, microsecond=0),
                matches_sample=20,
                goals_for_avg=goals_for,
                goals_against_avg=goals_against,
                first_half_goals_avg=0.8,
                second_half_goals_avg=1.2,
                corners_for_avg=5.0,
                corners_against_avg=4.5,
                shots_avg=12.0,
                shots_on_target_avg=5.0,
                possession_avg=52.0,
                over_9_5_corners_rate=0.5,
            )
        )
    db.commit()
    return match
