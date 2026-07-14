from datetime import date

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


def test_statistics_overview_empty_is_safe(client):
    data = client.get("/api/statistics/overview").json()
    assert data["total_picks"] == 0
    assert data["yield_percentage"] == 0


def test_service_flow_direct(db):
    collect_mock_data(db, date.today())
    result = generate_predictions(db)
    assert result["created"] >= 1
