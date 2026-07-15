from datetime import date, datetime, timedelta

from app.models import Competition, Match, Odds, Prediction, PredictionSystem, Team
from app.core.config import Settings, get_settings
from app.main import _rate_buckets
from app.repositories.queries import latest_odds
from app.services.collection_service import collect_mock_data
from app.services.prediction_service import generate_predictions
from app.utils.time import utc_now_naive


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_settings_load_env_from_root_or_backend():
    assert "../.env" in Settings.model_config["env_file"]


def test_api_responses_include_security_headers(client):
    response = client.get("/api/health")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "camera=()" in response.headers["Permissions-Policy"]


def test_rate_limit_uses_current_settings(client, monkeypatch):
    _rate_buckets.clear()
    monkeypatch.setenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "1")
    get_settings.cache_clear()

    first = client.get("/api/health")
    second = client.get("/api/health")

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["detail"] == "rate_limit_exceeded"
    assert second.headers["Retry-After"] == "60"

    _rate_buckets.clear()
    monkeypatch.delenv("RATE_LIMIT_REQUESTS_PER_MINUTE", raising=False)
    get_settings.cache_clear()


def test_hsts_only_enabled_in_production(client, monkeypatch):
    _rate_buckets.clear()
    monkeypatch.setenv("ENVIRONMENT", "production")
    get_settings.cache_clear()

    response = client.get("/api/health")

    assert response.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"

    _rate_buckets.clear()
    monkeypatch.setenv("ENVIRONMENT", "test")
    get_settings.cache_clear()


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


def test_admin_collect_uses_real_provider_when_not_mock(client, monkeypatch):
    monkeypatch.setenv("DATA_PROVIDER", "api_football")
    monkeypatch.setenv("API_FOOTBALL_KEY", "test-key")
    get_settings.cache_clear()

    def fake_collect_schedule(db, match_date=None):
        return {"provider": "real", "matches": 0}

    def forbidden_mock(db, match_date=None):
        raise AssertionError("mock collector must not run for real provider")

    monkeypatch.setattr("app.api.routes.collect_schedule_data", fake_collect_schedule)
    monkeypatch.setattr("app.api.routes.collect_mock_data", forbidden_mock)
    response = client.post("/api/admin/collect", headers={"X-Admin-Token": "test-secret"})

    assert response.status_code == 200
    assert response.json()["provider"] == "real"
    get_settings.cache_clear()


def test_model_health_reports_provider_configuration_error(client, monkeypatch):
    monkeypatch.setenv("DATA_PROVIDER", "api_football")
    monkeypatch.setenv("API_FOOTBALL_KEY", "")
    monkeypatch.setenv("FOOTBALL_API_KEY", "")
    get_settings.cache_clear()

    response = client.get("/api/model-health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "Proveedor mal configurado" in data["data_status"]
    get_settings.cache_clear()


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
    assert "publishable_pick_count" in calendar_rows[0]


def test_match_list_marks_only_recent_valid_odds_as_available(client, db):
    competition, home, away = _seed_calendar_entities(db)
    match = Match(
        external_id="stale-odds-match",
        competition_id=competition.id,
        home_team_id=home.id,
        away_team_id=away.id,
        kickoff_at=utc_now_naive() + timedelta(days=1),
        status="scheduled",
        venue=None,
        round=None,
        season="2026",
    )
    db.add(match)
    db.flush()
    db.add(
        Odds(
            match_id=match.id,
            bookmaker="OldBook",
            market="goals",
            selection="over",
            line=3.0,
            odds=2.0,
            provider="test",
            validation_status="mapped",
            collected_at=utc_now_naive() - timedelta(hours=30),
        )
    )
    db.commit()

    rows = client.get("/api/matches", params={"date": match.kickoff_at.date().isoformat()}).json()
    target = next(row for row in rows if row["external_id"] == "stale-odds-match")

    assert target["has_odds"] is False


def test_latest_odds_ignores_stale_or_unverified_prices(db):
    competition, home, away = _seed_calendar_entities(db)
    match = Match(
        external_id="latest-odds-stale",
        competition_id=competition.id,
        home_team_id=home.id,
        away_team_id=away.id,
        kickoff_at=utc_now_naive() + timedelta(days=1),
        status="scheduled",
        venue=None,
        round=None,
        season="2026",
    )
    db.add(match)
    db.flush()
    db.add_all(
        [
            Odds(
                match_id=match.id,
                bookmaker="OldBook",
                market="goals",
                selection="over",
                line=3.0,
                odds=9.0,
                provider="test",
                validation_status="mapped",
                collected_at=utc_now_naive() - timedelta(hours=30),
            ),
            Odds(
                match_id=match.id,
                bookmaker="BadBook",
                market="goals",
                selection="over",
                line=3.0,
                odds=2.2,
                provider="test",
                validation_status="unverified",
                collected_at=utc_now_naive(),
            ),
        ]
    )
    db.commit()

    assert latest_odds(db, match.id, "goals", "over", 3.0) is None


def test_calendar_month_counts_publishable_picks(client, db):
    competition, home, away = _seed_calendar_entities(db)
    system = PredictionSystem(
        code="TEST_SYSTEM",
        name="Test",
        description="Test system",
        market="test",
        minimum_probability=0.0,
        minimum_value=0.0,
        is_active=True,
    )
    db.add(system)
    db.flush()
    match = Match(
        external_id="publishable-calendar",
        competition_id=competition.id,
        home_team_id=home.id,
        away_team_id=away.id,
        kickoff_at=datetime(2026, 8, 3, 10),
        status="scheduled",
        venue=None,
        round=None,
        season="2026",
    )
    db.add(match)
    db.flush()
    db.add(
        Prediction(
            match_id=match.id,
            system_id=system.id,
            market="goals",
            selection="over",
            line=3.5,
            predicted_probability=0.7,
            fair_odds=1.43,
            available_odds=2.0,
            expected_value=0.4,
            confidence=0.8,
            recommended_stake=1,
            explanation="test",
            status="ready_to_publish",
        )
    )
    db.commit()

    calendar_rows = client.get("/api/calendar/month", params={"year": 2026, "month": 8}).json()
    target = next(row for row in calendar_rows if row["date"] == "2026-08-03")
    assert target["pick_count"] == 1
    assert target["publishable_pick_count"] == 1


def test_generate_predictions_creates_prematch_pick(client):
    client.post("/api/admin/collect", headers={"X-Admin-Token": "test-secret"})
    response = client.post("/api/admin/generate-predictions", headers={"X-Admin-Token": "test-secret"})
    assert response.status_code == 200
    assert response.json()["created"] >= 1

    predictions = client.get("/api/predictions").json()
    assert predictions
    assert any(prediction["market"] == "goals" for prediction in predictions)
    assert any(prediction["line"] in {1.5, 2.5, 3.5} for prediction in predictions)


def test_publishable_picks_can_include_over_15_and_over_25(client):
    client.post("/api/admin/collect", headers={"X-Admin-Token": "test-secret"})
    client.post("/api/admin/generate-predictions", headers={"X-Admin-Token": "test-secret"})

    predictions = client.get("/api/predictions", params={"status": "published"}).json()
    low_goal_lines = [
        prediction
        for prediction in predictions
        if prediction["market"] == "goals" and prediction["selection"] == "over" and prediction["line"] in {1.5, 2.5}
    ]
    assert low_goal_lines
    assert all("bloqueado" not in prediction["explanation"].lower() for prediction in low_goal_lines)


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


def test_model_health_endpoint_reports_operational_counts(client):
    client.post("/api/admin/collect", headers={"X-Admin-Token": "test-secret"})
    client.post("/api/admin/generate-predictions", headers={"X-Admin-Token": "test-secret"})

    response = client.get("/api/model-health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] in {"operativo", "degradado", "error"}
    assert data["matches_downloaded"] >= 1
    assert data["candidate_picks"] >= 1
    assert data["markets_evaluated"] >= data["candidate_picks"]
    assert "matches_without_odds" in data


def test_readiness_endpoint_reports_launch_checks(client):
    response = client.get("/api/readiness")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] in {"ready", "degraded", "blocked"}
    assert data["checks"]
    assert "future_matches_7d" in data["metrics"]


def test_pick_safety_mode_can_be_read_and_changed(client):
    read = client.get("/api/pick-safety-mode")
    blocked = client.post("/api/admin/pick-safety-mode", params={"mode": "aggressive"})
    changed = client.post(
        "/api/admin/pick-safety-mode",
        params={"mode": "conservative"},
        headers={"X-Admin-Token": "test-secret"},
    )
    restored = client.post(
        "/api/admin/pick-safety-mode",
        params={"mode": "normal"},
        headers={"X-Admin-Token": "test-secret"},
    )

    assert read.status_code == 200
    assert read.json()["mode"] in {"conservative", "normal", "aggressive"}
    assert blocked.status_code == 401
    assert changed.status_code == 200
    assert changed.json()["mode"] == "conservative"
    assert restored.json()["mode"] == "normal"


def test_system_alerts_endpoint_returns_actionable_items(client):
    response = client.get("/api/system-alerts")

    assert response.status_code == 200
    data = response.json()
    assert data
    assert {"level", "title", "message", "action"} <= set(data[0])


def test_deep_sync_day_persists_match_odds(client):
    response = client.post(
        "/api/admin/sync-day-deep",
        params={"date": date.today().isoformat()},
        headers={"X-Admin-Token": "test-secret"},
    )

    assert response.status_code == 200
    assert response.json()["forms"] >= 2
    assert response.json()["odds"] >= 1
    match = client.get(f"/api/matches?date={date.today().isoformat()}").json()[0]
    odds = client.get(f"/api/matches/{match['id']}/odds").json()
    assert odds


def test_clear_data_requires_explicit_confirmation(client):
    client.post("/api/admin/collect", headers={"X-Admin-Token": "test-secret"})

    blocked = client.post("/api/admin/clear-data", headers={"X-Admin-Token": "test-secret"})
    confirmed = client.post(
        "/api/admin/clear-data",
        params={"confirm": "CONFIRM_CLEAR_ALL_DATA"},
        headers={"X-Admin-Token": "test-secret"},
    )

    assert blocked.status_code == 400
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "cleared"


def test_prediction_export_reports_refresh_error_instead_of_crashing(client, monkeypatch):
    def broken_refresh(db, match_date):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr("app.api.routes.collect_deep_data_for_date", broken_refresh)
    response = client.get("/api/predictions/export", params={"date": "2026-07-15", "refresh": "true"})

    assert response.status_code == 200
    data = response.json()
    assert data["diagnostics"]["refresh_status"] == "failed_using_cached_data"
    assert "provider unavailable" in data["diagnostics"]["refresh_error"]


def test_admin_maintenance_runs_protected_flow(client):
    response = client.post(
        "/api/admin/run-maintenance",
        params={"days_back": 0, "days_forward": 0, "deep_today": "true"},
        headers={"X-Admin-Token": "test-secret"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "calendar" in data
    assert "predictions" in data


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
