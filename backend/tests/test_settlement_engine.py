from app.services.settlement_engine import (
    SettlementDistribution,
    SettlementStatus,
    calculate_asian_handicap_ev,
    fair_odds_from_distribution,
    settle_asian_handicap,
    settle_btts,
    settle_correct_score,
    settle_draw_no_bet,
    settle_ht_ft,
    settle_result,
    settle_team_total,
    settle_total_goals,
    settle_winner_and_btts,
)


def test_over_3_exactly_3_is_push():
    assert settle_total_goals(3, 3.0, "over") == SettlementStatus.PUSH


def test_over_325_with_3_goals_is_half_loss():
    assert settle_total_goals(3, 3.25, "over") == SettlementStatus.HALF_LOSS


def test_over_375_with_4_goals_is_half_win():
    assert settle_total_goals(4, 3.75, "over") == SettlementStatus.HALF_WIN


def test_under_325_with_3_goals_is_half_win():
    assert settle_total_goals(3, 3.25, "under") == SettlementStatus.HALF_WIN


def test_handicap_minus_075_winning_by_one_is_half_win():
    assert settle_asian_handicap(2, 1, "home", -0.75) == SettlementStatus.HALF_WIN


def test_handicap_plus_025_drawing_is_half_win():
    assert settle_asian_handicap(1, 1, "home", 0.25) == SettlementStatus.HALF_WIN


def test_dnb_drawing_is_push():
    assert settle_draw_no_bet(1, 1, "home") == SettlementStatus.PUSH


def test_btts_1_1_is_win():
    assert settle_btts(1, 1, "yes") == SettlementStatus.WIN


def test_btts_3_0_is_loss():
    assert settle_btts(3, 0, "yes") == SettlementStatus.LOSS


def test_first_half_over_15_with_1_1_is_win():
    assert settle_total_goals(2, 1.5, "over") == SettlementStatus.WIN


def test_first_half_over_15_with_1_0_is_loss():
    assert settle_total_goals(1, 1.5, "over") == SettlementStatus.LOSS


def test_home_team_over_15_with_2_0_is_win():
    assert settle_team_total(2, 1.5, "over") == SettlementStatus.WIN


def test_away_team_over_05_with_2_1_is_win():
    assert settle_team_total(1, 0.5, "over") == SettlementStatus.WIN


def test_half_time_result():
    assert settle_result(1, 0, "home") == SettlementStatus.WIN


def test_ht_ft():
    assert settle_ht_ft(0, 0, 2, 1, "draw/home") == SettlementStatus.WIN


def test_winner_and_btts():
    assert settle_winner_and_btts(2, 1, "home") == SettlementStatus.WIN


def test_correct_score():
    assert settle_correct_score(2, 1, "2-1") == SettlementStatus.WIN


def test_fair_odds_for_partial_settlement_distribution():
    distribution = SettlementDistribution(probability_full_win=0.4, probability_push=0.2, probability_full_loss=0.4)
    assert fair_odds_from_distribution(distribution) == 2.0
    assert calculate_asian_handicap_ev(distribution, 2.0) == 0.0
