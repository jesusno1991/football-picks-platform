from app.services.goal_market_engine import GoalLambdas, probability_for_market


def test_full_time_and_first_half_probabilities_are_not_reused():
    lambdas = GoalLambdas(1.5, 1.1, 0.55, 0.45, 0.95, 0.65, 0.7, 80, 30)
    _, ft_probability, _ = probability_for_market("total_goals", "full_time", "all", "over", 1.5, lambdas)
    _, fh_probability, _ = probability_for_market("total_goals", "first_half", "all", "over", 1.5, lambdas)
    assert ft_probability != fh_probability
    assert ft_probability > fh_probability


def test_team_total_does_not_reuse_match_total_probability():
    lambdas = GoalLambdas(1.8, 0.7, 0.75, 0.25, 1.05, 0.45, 0.7, 80, 30)
    _, match_total_probability, _ = probability_for_market("total_goals", "full_time", "all", "over", 1.5, lambdas)
    _, home_total_probability, _ = probability_for_market("total_goals", "full_time", "home", "over", 1.5, lambdas)
    assert match_total_probability != home_total_probability


def test_btts_comes_from_joint_score_matrix():
    lambdas = GoalLambdas(1.4, 1.2, 0.6, 0.5, 0.8, 0.7, 0.7, 80, 30)
    _, yes_probability, _ = probability_for_market("btts", "full_time", "all", "yes", None, lambdas)
    _, no_probability, _ = probability_for_market("btts", "full_time", "all", "no", None, lambdas)
    assert round((yes_probability or 0) + (no_probability or 0), 6) == 1


def test_period_specific_btts_is_different():
    lambdas = GoalLambdas(1.4, 1.2, 0.45, 0.35, 0.95, 0.85, 0.7, 80, 30)
    _, ft_probability, _ = probability_for_market("btts", "full_time", "all", "yes", None, lambdas)
    _, fh_probability, _ = probability_for_market("btts", "first_half", "all", "yes", None, lambdas)
    assert ft_probability != fh_probability


def test_asian_handicap_has_partial_settlement_distribution():
    lambdas = GoalLambdas(1.6, 0.9, 0.7, 0.35, 0.9, 0.55, 0.7, 80, 30)
    distribution, probability, settlement = probability_for_market("asian_handicap", "full_time", "home", "handicap", -0.75, lambdas)
    assert settlement == "asian_handicap"
    assert probability is not None
    assert distribution.probability_half_win > 0
    assert distribution.probability_full_loss > 0


def test_correct_score_uses_exact_score_cell():
    lambdas = GoalLambdas(1.2, 0.8, 0.5, 0.3, 0.7, 0.5, 0.7, 80, 30)
    distribution, probability, settlement = probability_for_market("correct_score", "full_time", "all", "1-0", None, lambdas)
    assert settlement == "binary"
    assert probability is not None
    assert probability == distribution.probability_full_win
    assert 0 < probability < 1
