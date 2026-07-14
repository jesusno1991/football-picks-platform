from datetime import date, datetime

from app.models import Competition, Match, Team
from app.services.collection_service import collect_mock_data
from app.services.prediction_service import generate_predictions


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_admin_requires_token(client):
    response = client.post("/api/admin/collect")
    assert response.status_code == 401


def test_collect_and_list_matches(client):
    response = client.post("/api/admin/collect", headers={"X-Admin-Token": "test-secret"})
    assert response.status_code == 200
    assert response.json()["matches"] == 2

    matches = client.get(f"/api/matches?date={date.today().isoformat()}").json()
    assert len(matches) == 2
    assert matches[0]["home_team"]["name"]


def test_matches_date_uses_madrid_timezone(client, db):
    competition, home, away = _seed_calendar_entities(db)
    db.add(
        Match(
            external_id="late-utc",
            competition_id=competition.id,
            home_team_id=home.id,
            away_team_id=away.id,
            kickoff_at=datetime(2026, 7, 14, 23, 30),
            status="scheduled",
            venue=None,
            round=None,
            season="2026",
        )
    )
    db.commit()

    july_14 = client.get("/api/matches/range", params={"date_from": "2026-07-14", "date_to": "2026-07-14"}).json()
    july_15 = client.get("/api/matches/range", params={"date_from": "2026-07-15", "date_to": "2026-07-15"}).json()

    assert [match["external_id"] for match in july_14] == []
    assert [match["external_id"] for match in july_15] == ["late-utc"]


def test_matches_range_and_calendar_month(client, db):
    competition, home, away = _seed_calendar_entities(db)
    for index, kickoff in enumerate((datetime(2026, 8, 1, 10), datetime(2026, 8, 15, 18), datetime(2026, 9, 1, 10))):
        db.add(
            Match(
                external_id=f"range-{index}",
                competition_id=competition.id,
                home_team_id=home.id,
                away_team_id=away.id,
                kickoff_at=kickoff,
                status="scheduled",
                venue=None,
                round=None,
                season="2026",
            )
        )
    db.commit()

    range_rows = client.get("/api/matches/range", params={"date_from": "2026-08-01", "date_to": "2026-08-31"}).json()
    calendar_rows = client.get("/api/calendar/month", params={"year": 2026, "month": 8}).json()

    assert {match["external_id"] for match in range_rows} == {"range-0", "range-1"}
    assert len(calendar_rows) == 31
    assert calendar_rows[0]["date"] == "2026-08-01"
    assert calendar_rows[0]["match_count"] == 1


def test_generate_predictions_creates_prematch_pick(client):
    client.post("/api/admin/collect", headers={"X-Admin-Token": "test-secret"})
    response = client.post("/api/admin/generate-predictions", headers={"X-Admin-Token": "test-secret"})
    assert response.status_code == 200
    assert response.json()["created"] >= 1

    predictions = client.get("/api/predictions").json()
    assert predictions
    assert any(prediction["market"] == "goals" for prediction in predictions)
    assert any(prediction["line"] in {1.5, 2.5, 3.5} for prediction in predictions)


def test_publishable_picks_exclude_over_15_and_over_25(client):
    client.post("/api/admin/collect", headers={"X-Admin-Token": "test-secret"})
    client.post("/api/admin/generate-predictions", headers={"X-Admin-Token": "test-secret"})

    predictions = client.get("/api/predictions", params={"status": "published"}).json()
    blocked = [
        prediction
        for prediction in predictions
        if prediction["market"] == "goals" and prediction["selection"] == "over" and prediction["line"] in {1.5, 2.5}
    ]
    assert blocked == []


def test_match_detail_contains_forms_and_predictions(client):
    client.post("/api/admin/collect", headers={"X-Admin-Token": "test-secret"})
    client.post("/api/admin/generate-predictions", headers={"X-Admin-Token": "test-secret"})
    match_id = client.get("/api/matches").json()[0]["id"]

    detail = client.get(f"/api/matches/{match_id}")
    assert detail.status_code == 200
    data = detail.json()
    assert data["home_form"]["matches_sample"] >= 10
    assert "predictions" in data
    assert data["availability"]["predicciones"] == "Disponible"


def test_information_platform_endpoints_are_available(client):
    client.post("/api/admin/collect", headers={"X-Admin-Token": "test-secret"})
    client.post("/api/admin/generate-predictions", headers={"X-Admin-Token": "test-secret"})
    match = client.get("/api/matches").json()[0]
    team_id = match["home_team"]["id"]
    competition_id = match["competition"]["id"]

    assert client.get(f"/api/matches/{match['id']}/statistics").status_code == 200
    assert client.get(f"/api/matches/{match['id']}/events").json()["message"] == "No disponible"
    assert client.get(f"/api/matches/{match['id']}/lineups").json()["message"] == "No disponible"
    assert client.get(f"/api/matches/{match['id']}/odds").status_code == 200
    assert client.get(f"/api/matches/{match['id']}/predictions").status_code == 200
    assert client.get(f"/api/matches/{match['id']}/h2h").status_code == 200

    team_detail = client.get(f"/api/teams/{team_id}/detail")
    assert team_detail.status_code == 200
    assert team_detail.json()["name"]

    competition_detail = client.get(f"/api/competitions/{competition_id}")
    assert competition_detail.status_code == 200
    assert competition_detail.json()["match_count"] >= 1

    standings = client.get(f"/api/competitions/{competition_id}/standings")
    assert standings.status_code == 200
    assert isinstance(standings.json(), list)

    search = client.get("/api/search", params={"q": match["home_team"]["name"][:3]})
    assert search.status_code == 200
    assert search.json()

    admin = client.get("/api/admin/status")
    assert admin.status_code == 200
    assert admin.json()["matches"] >= 1


def test_statistics_overview_empty_is_safe(client):
    data = client.get("/api/statistics/overview").json()
    assert data["total_picks"] == 0
    assert data["yield_percentage"] == 0


def test_service_flow_direct(db):
    collect_mock_data(db, date.today())
    result = generate_predictions(db)
    assert result["created"] >= 1


def _seed_calendar_entities(db):
    competition = Competition(
        external_id="calendar-comp",
        name="Calendar League",
        country="Spain",
        logo_url=None,
        season="2026",
        is_active=True,
    )
    home = Team(external_id="calendar-home", name="Calendar Home", short_name="HOM", country="Spain", logo_url=None)
    away = Team(external_id="calendar-away", name="Calendar Away", short_name="AWA", country="Spain", logo_url=None)
    db.add_all([competition, home, away])
    db.flush()
    return competition, home, away
