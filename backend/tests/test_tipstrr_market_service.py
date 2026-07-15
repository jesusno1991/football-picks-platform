from datetime import date, datetime, timedelta

from app.models import Competition, Match, Odds, Prediction, PredictionSystem, Team, TeamForm, TeamMatchStatistics
from app.services.collection_service import upsert_prediction_systems
from app.repositories.queries import get_prediction_system
from app.services.prediction_service import _select_best_market_for_match
from app.services.tipstrr_market_service import build_daily_export, list_tipstrr_market_picks
from app.services.tipstrr_market_service import build_tipstrr_predictions
from app.utils.time import utc_now_naive


def test_tipstrr_market_picks_include_requested_market_groups(db):
    match = _create_match_with_forms(db)

    rows = list_tipstrr_market_picks(db, match.kickoff_at.date())

    groups = {row.group for row in rows}
    assert "1X2" in groups
    assert "Empate no apuesta" in groups
    assert "Doble oportunidad" in groups
    assert "Gana + ambos marcan" in groups
    assert "Goles partido" in groups
    assert "Goles al descanso" in groups
    assert "Resultado al descanso" in groups
    assert "Marcador correcto" in groups
    assert "Goles local" in groups
    assert "Goles visitante" in groups
    assert "1a parte local" in groups
    assert "1a parte visitante" in groups
    assert "Handicap asiatico" in groups
    assert "Handicap asiatico 1a parte" in groups
    assert "Primer gol" in groups
    assert "Se clasificara" in groups


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
    db.add(
        Odds(
            match_id=match.id,
            bookmaker="Bet365",
            market="goals",
            market_family="total_goals",
            period="full_time",
            team_scope="all",
            selection="over",
            line=2.5,
            odds=3.6,
            provider="test",
            validation_status="mapped",
        )
    )
    db.commit()

    rows = list_tipstrr_market_picks(db, match.kickoff_at.date(), "PUBLICABLE")

    assert any(row.group == "Goles partido" and row.family == "total_goals" and row.selection == "over" and row.line == 3.0 for row in rows)
    assert any(row.group == "Goles partido" and row.family == "total_goals" and row.selection == "over" and row.line == 2.5 for row in rows)


def test_tipstrr_decision_filter_accepts_ready_to_publish_alias(db):
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

    rows = list_tipstrr_market_picks(db, match.kickoff_at.date(), "ready_to_publish")

    assert rows
    assert all(row.decision == "PUBLICABLE" for row in rows)


def test_tipstrr_market_pick_includes_audit_rules(db):
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
            line=2.5,
            odds=3.6,
            provider="test",
            validation_status="mapped",
        )
    )
    db.commit()

    rows = list_tipstrr_market_picks(db, match.kickoff_at.date())
    row = next(item for item in rows if item.family == "total_goals" and item.line == 2.5 and item.selection == "over")

    assert row.passed_rules
    assert row.odds_quality_score > 0
    assert row.safety_mode in {"normal", "conservative", "aggressive"}
    assert row.publish_blocked_by_odds is False


def test_extreme_goal_under_line_is_not_publicable(db):
    match = _create_match_with_forms(db)
    db.add(
        Odds(
            match_id=match.id,
            bookmaker="Bet365",
            market="goals",
            market_family="total_goals",
            period="full_time",
            team_scope="all",
            selection="under",
            line=9.5,
            odds=1.25,
            provider="test",
            validation_status="mapped",
        )
    )
    db.commit()

    rows = list_tipstrr_market_picks(db, match.kickoff_at.date())
    row = next(item for item in rows if item.family == "total_goals" and item.selection == "under" and item.line == 9.5)
    publicable = list_tipstrr_market_picks(db, match.kickoff_at.date(), "PUBLICABLE")

    assert row.decision == "WATCH"
    assert row.publish_blocked_by_config is True
    assert "Linea fuera de rango profesional para publicacion" in row.failed_rules
    assert all(not (item.family == "total_goals" and item.selection == "under" and item.line == 9.5) for item in publicable)


def test_tipstrr_generator_creates_prediction_rows_for_new_markets(db):
    match = _create_match_with_forms(db)
    upsert_prediction_systems(db)
    system = get_prediction_system(db, "TIPSTRR_MARKET_ENGINE")

    predictions = build_tipstrr_predictions(db, match, system)
    markets = {prediction.market for prediction in predictions}

    assert "tipstrr:match_result:full_time:all" in markets
    assert "tipstrr:draw_no_bet:full_time:all" in markets
    assert "tipstrr:double_chance:full_time:all" in markets
    assert "tipstrr:asian_handicap:first_half:home" in markets
    assert "tipstrr:win_btts:full_time:all" in markets
    assert "tipstrr:first_goal:full_time:all" in markets
    assert any(prediction.market == "tipstrr:total_goals:full_time:all" and prediction.selection == "over" and prediction.line in {1.5, 2.5} for prediction in predictions)


def test_tipstrr_endpoint_returns_all_markets(client):
    response = client.post("/api/admin/collect", headers={"X-Admin-Token": "test-secret"})
    assert response.status_code == 200

    data = client.get("/api/tipstrr-market-picks").json()

    assert data
    assert {"1X2", "Doble oportunidad", "Goles partido", "Marcador correcto"}.issubset({row["group"] for row in data})


def test_tipstrr_endpoint_supports_limit(client):
    response = client.post("/api/admin/collect", headers={"X-Admin-Token": "test-secret"})
    assert response.status_code == 200

    data = client.get("/api/tipstrr-market-picks", params={"limit": 5}).json()

    assert len(data) == 5


def test_live_picks_endpoint_returns_live_value(client, db):
    match = _create_match_with_forms_at(db, utc_now_naive() - timedelta(minutes=35), "match-live")
    match.status = "1H"
    match.home_score = 0
    match.away_score = 0
    db.add_all(
        [
            TeamMatchStatistics(match_id=match.id, team_id=match.home_team_id, is_home=True, possession=62, shots=9, shots_on_target=4, corners=5, dangerous_attacks=36, goals=0, xg=0.9),
            TeamMatchStatistics(match_id=match.id, team_id=match.away_team_id, is_home=False, possession=38, shots=3, shots_on_target=1, corners=1, dangerous_attacks=10, goals=0, xg=0.2),
        ]
    )
    _add_publicable_odd(db, match, utc_now_naive() - timedelta(minutes=5))
    db.commit()

    data = client.get("/api/live-picks", params={"limit": 20}).json()
    center = client.get("/api/live-match-center", params={"limit": 20}).json()

    assert any(row["external_id"] == "match-live" for row in data)
    target = next(row for row in data if row["external_id"] == "match-live" and row["family"] == "total_goals")
    assert target["decision"] == "LIVE_VALUE"
    assert target["reason"] == "Live: valor positivo con cuota real"
    snapshot = next(row for row in center if row["external_id"] == "match-live")
    assert snapshot["momentum"]["leader"] == match.home_team.name
    assert snapshot["top_signal"]["priority"] >= 4
    assert snapshot["stats"]["home"]["shots_on_target"] == 4
    assert snapshot["minute"] == 35


def test_live_match_center_caps_second_half_elapsed_without_events(client, db):
    match = _create_match_with_forms_at(db, utc_now_naive() - timedelta(minutes=150), "match-live-old")
    match.status = "2H"
    db.commit()

    center = client.get("/api/live-match-center", params={"limit": 20}).json()

    snapshot = next(row for row in center if row["external_id"] == "match-live-old")
    assert snapshot["minute"] == 90


def test_market_optimizer_keeps_only_best_ev_per_match(db):
    match = _create_match_with_forms(db)
    system = PredictionSystem(
        code="TEST_MARKET_OPTIMIZER",
        name="Test optimizer",
        description="test",
        market="tipstrr",
        minimum_probability=0,
        minimum_value=0.03,
        is_active=True,
    )
    db.add(system)
    db.flush()
    low_ev = Prediction(
        match_id=match.id,
        system_id=system.id,
        market="tipstrr:total_goals:full_time:all",
        selection="over",
        line=3.0,
        predicted_probability=0.55,
        fair_odds=1.82,
        available_odds=2.0,
        expected_value=0.08,
        confidence=0.72,
        recommended_stake=1,
        explanation="low",
        status="published",
    )
    high_ev = Prediction(
        match_id=match.id,
        system_id=system.id,
        market="tipstrr:asian_handicap:full_time:home",
        selection="handicap",
        line=-0.75,
        predicted_probability=0.58,
        fair_odds=1.72,
        available_odds=2.2,
        expected_value=0.18,
        confidence=0.7,
        recommended_stake=1,
        explanation="high",
        status="published",
    )
    db.add_all([low_ev, high_ev])
    db.commit()

    _select_best_market_for_match(db, match.id)
    db.commit()

    assert high_ev.status == "published"
    assert low_ev.status == "no_bet"
    assert "mayor EV" in low_ev.explanation


def test_generate_predictions_publishes_max_one_market_per_match(client):
    client.post("/api/admin/collect", headers={"X-Admin-Token": "test-secret"})
    client.post("/api/admin/generate-predictions", headers={"X-Admin-Token": "test-secret"})

    predictions = client.get("/api/predictions", params={"status": "published"}).json()
    match_ids = [prediction["match_id"] for prediction in predictions]
    assert len(match_ids) == len(set(match_ids))


def test_daily_export_for_july_15_does_not_include_july_14_matches(db):
    selected_day = date(2026, 7, 15)
    now = datetime(2026, 7, 15, 8, 0, 0)
    july_15_match = _create_match_with_forms_at(db, datetime(2026, 7, 15, 18, 0, 0), "match-july-15")
    july_14_match = _create_match_with_forms_at(db, datetime(2026, 7, 14, 18, 0, 0), "match-july-14")
    _add_publicable_odd(db, july_15_match, now)
    _add_publicable_odd(db, july_14_match, now)

    export = build_daily_export(db, selected_day, now=now)

    assert export["market_evaluations"]
    assert {row["external_id"] for row in export["market_evaluations"]} == {"match-july-15"}
    assert all(row["kickoff_local_date"] == "2026-07-15" for row in export["market_evaluations"])


def test_daily_export_excludes_started_matches_and_stale_odds(db):
    selected_day = date(2026, 7, 15)
    now = datetime(2026, 7, 15, 12, 0, 0)
    started_match = _create_match_with_forms_at(db, datetime(2026, 7, 15, 9, 0, 0), "match-started")
    stale_odds_match = _create_match_with_forms_at(db, datetime(2026, 7, 15, 18, 0, 0), "match-stale-odds")
    _add_publicable_odd(db, started_match, now)
    _add_publicable_odd(db, stale_odds_match, now - timedelta(hours=25))

    export = build_daily_export(db, selected_day, now=now)

    assert export["market_evaluations"] == []
    assert export["diagnostics"]["discard_reasons"]["already_started_or_closed"] == 1
    assert export["diagnostics"]["discard_reasons"]["no_recent_odds"] == 1


def test_tipstrr_prefers_professional_odd_over_outlier(db):
    match = _create_match_with_forms(db)
    for odds in (2.05, 45.0):
        db.add(
            Odds(
                match_id=match.id,
                bookmaker=f"Book {odds}",
                market="handicap",
                market_family="asian_handicap",
                period="full_time",
                team_scope="away",
                selection="handicap",
                line=2.0,
                odds=odds,
                provider="test",
                validation_status="mapped",
            )
        )
    db.commit()

    rows = list_tipstrr_market_picks(db, match.kickoff_at.date())
    row = next(item for item in rows if item.family == "asian_handicap" and item.team_scope == "away" and item.line == 2.0)

    assert row.market_odds == 2.05
    assert row.bookmaker == "Book 2.05"


def test_started_match_does_not_show_ev_or_rank_above_future_watch(db):
    now = utc_now_naive()
    started = _create_match_with_forms_at(db, now - timedelta(hours=2), "match-started-ranking")
    future = _create_match_with_forms_at(db, now + timedelta(hours=4), "match-future-ranking")
    _add_publicable_odd(db, started, now)
    _add_publicable_odd(db, future, now)

    rows = list_tipstrr_market_picks(db, now.date())
    started_row = next(item for item in rows if item.external_id == "match-started-ranking" and item.family == "total_goals" and item.selection == "over" and item.line == 3.0)
    future_row = next(item for item in rows if item.external_id == "match-future-ranking" and item.family == "total_goals" and item.selection == "over" and item.line == 3.0)

    assert started_row.expected_value is None
    assert "Partido ya iniciado o cerrado" in started_row.failed_rules
    assert rows.index(future_row) < rows.index(started_row)


def _create_match_with_forms(db):
    kickoff = utc_now_naive() + timedelta(days=1)
    return _create_match_with_forms_at(db, kickoff, "match-1")


def _create_match_with_forms_at(db, kickoff: datetime, external_id: str):
    competition = Competition(
        external_id=f"comp-{external_id}",
        name="Test League",
        country="Spain",
        logo_url=None,
        season="2026",
        is_active=True,
    )
    home = Team(external_id=f"team-home-{external_id}", name=f"Home FC {external_id}", short_name="HOM", country="Spain", logo_url=None)
    away = Team(external_id=f"team-away-{external_id}", name=f"Away FC {external_id}", short_name="AWA", country="Spain", logo_url=None)
    db.add_all([competition, home, away])
    db.flush()
    match = Match(
        external_id=external_id,
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


def _add_publicable_odd(db, match: Match, collected_at: datetime) -> None:
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
            collected_at=collected_at,
        )
    )
    db.commit()
