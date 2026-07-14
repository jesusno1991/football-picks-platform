from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isclose


class SettlementStatus(str, Enum):
    WIN = "win"
    HALF_WIN = "half_win"
    PUSH = "push"
    HALF_LOSS = "half_loss"
    LOSS = "loss"


@dataclass(frozen=True)
class SettlementDistribution:
    probability_full_win: float = 0.0
    probability_half_win: float = 0.0
    probability_push: float = 0.0
    probability_half_loss: float = 0.0
    probability_full_loss: float = 0.0

    def normalized(self) -> "SettlementDistribution":
        total = (
            self.probability_full_win
            + self.probability_half_win
            + self.probability_push
            + self.probability_half_loss
            + self.probability_full_loss
        )
        if total <= 0:
            return self
        return SettlementDistribution(
            self.probability_full_win / total,
            self.probability_half_win / total,
            self.probability_push / total,
            self.probability_half_loss / total,
            self.probability_full_loss / total,
        )


def settle_total_goals(total_goals: int, line: float, selection: str) -> SettlementStatus:
    if selection not in {"over", "under"}:
        raise ValueError("selection must be over or under")
    components = _quarter_components(line)
    statuses = [_settle_half_or_integer_total(total_goals, component, selection) for component in components]
    return _combine_split_statuses(statuses)


def settle_team_total(team_goals: int, line: float, selection: str) -> SettlementStatus:
    return settle_total_goals(team_goals, line, selection)


def settle_asian_handicap(home_goals: int, away_goals: int, team_scope: str, line: float) -> SettlementStatus:
    if team_scope not in {"home", "away"}:
        raise ValueError("team_scope must be home or away")
    margin = home_goals - away_goals if team_scope == "home" else away_goals - home_goals
    statuses = [_settle_half_or_integer_handicap(margin, component) for component in _quarter_components(line)]
    return _combine_split_statuses(statuses)


def settle_draw_no_bet(home_goals: int, away_goals: int, selection: str) -> SettlementStatus:
    if selection == "home":
        return settle_asian_handicap(home_goals, away_goals, "home", 0.0)
    if selection == "away":
        return settle_asian_handicap(home_goals, away_goals, "away", 0.0)
    raise ValueError("selection must be home or away")


def settle_btts(home_goals: int, away_goals: int, selection: str) -> SettlementStatus:
    yes_wins = home_goals >= 1 and away_goals >= 1
    if selection == "yes":
        return SettlementStatus.WIN if yes_wins else SettlementStatus.LOSS
    if selection == "no":
        return SettlementStatus.LOSS if yes_wins else SettlementStatus.WIN
    raise ValueError("selection must be yes or no")


def settle_result(home_goals: int, away_goals: int, selection: str) -> SettlementStatus:
    if home_goals > away_goals:
        result = "home"
    elif away_goals > home_goals:
        result = "away"
    else:
        result = "draw"
    return SettlementStatus.WIN if result == selection else SettlementStatus.LOSS


def settle_double_chance(home_goals: int, away_goals: int, selection: str) -> SettlementStatus:
    if home_goals > away_goals:
        result = "home"
    elif away_goals > home_goals:
        result = "away"
    else:
        result = "draw"
    valid = {
        "1x": {"home", "draw"},
        "x2": {"away", "draw"},
        "12": {"home", "away"},
    }
    if selection not in valid:
        raise ValueError("selection must be 1x, x2 or 12")
    return SettlementStatus.WIN if result in valid[selection] else SettlementStatus.LOSS


def settle_ht_ft(ht_home: int, ht_away: int, ft_home: int, ft_away: int, selection: str) -> SettlementStatus:
    expected = selection.lower().split("/")
    if len(expected) != 2:
        raise ValueError("selection must use ht/ft format")
    actual = [_result_label(ht_home, ht_away), _result_label(ft_home, ft_away)]
    return SettlementStatus.WIN if actual == expected else SettlementStatus.LOSS


def settle_winner_and_btts(home_goals: int, away_goals: int, selection: str) -> SettlementStatus:
    if settle_btts(home_goals, away_goals, "yes") != SettlementStatus.WIN:
        return SettlementStatus.LOSS
    return settle_result(home_goals, away_goals, selection)


def settle_correct_score(home_goals: int, away_goals: int, selection: str) -> SettlementStatus:
    try:
        expected_home, expected_away = [int(value) for value in selection.split("-")]
    except (ValueError, AttributeError):
        raise ValueError("selection must be a score like 2-1") from None
    return SettlementStatus.WIN if (home_goals, away_goals) == (expected_home, expected_away) else SettlementStatus.LOSS


def calculate_binary_market_ev(probability: float, odds: float) -> float:
    return round(probability * odds - 1, 6)


def calculate_integer_line_ev(distribution: SettlementDistribution, odds: float) -> float:
    return calculate_settlement_ev(distribution, odds)


def calculate_half_line_ev(distribution: SettlementDistribution, odds: float) -> float:
    return calculate_settlement_ev(distribution, odds)


def calculate_quarter_line_ev(distribution: SettlementDistribution, odds: float) -> float:
    return calculate_settlement_ev(distribution, odds)


def calculate_asian_handicap_ev(distribution: SettlementDistribution, odds: float) -> float:
    return calculate_settlement_ev(distribution, odds)


def calculate_draw_no_bet_ev(distribution: SettlementDistribution, odds: float) -> float:
    return calculate_settlement_ev(distribution, odds)


def calculate_settlement_ev(distribution: SettlementDistribution, odds: float) -> float:
    d = distribution.normalized()
    profit = (
        d.probability_full_win * (odds - 1)
        + d.probability_half_win * ((odds - 1) / 2)
        - d.probability_half_loss * 0.5
        - d.probability_full_loss
    )
    return round(profit, 6)


def fair_odds_from_distribution(distribution: SettlementDistribution) -> float | None:
    d = distribution.normalized()
    win_weight = d.probability_full_win + 0.5 * d.probability_half_win
    loss_weight = d.probability_full_loss + 0.5 * d.probability_half_loss
    if win_weight <= 0:
        return None
    return round(1 + (loss_weight / win_weight), 6)


def _quarter_components(line: float) -> tuple[float, ...]:
    doubled = round(line * 2, 6)
    if isclose(doubled, round(doubled), abs_tol=1e-6):
        return (round(line, 2),)
    lower = int(line * 2) / 2
    if line < 0 and not isclose(line * 2, int(line * 2), abs_tol=1e-6):
        lower = int(line * 2 - 1) / 2
    upper = lower + 0.5
    return (round(lower, 2), round(upper, 2))


def _settle_half_or_integer_total(total_goals: int, line: float, selection: str) -> SettlementStatus:
    diff = total_goals - line
    if selection == "under":
        diff = -diff
    if diff > 0:
        return SettlementStatus.WIN
    if isclose(diff, 0, abs_tol=1e-9):
        return SettlementStatus.PUSH
    return SettlementStatus.LOSS


def _settle_half_or_integer_handicap(margin: int, line: float) -> SettlementStatus:
    adjusted = margin + line
    if adjusted > 0:
        return SettlementStatus.WIN
    if isclose(adjusted, 0, abs_tol=1e-9):
        return SettlementStatus.PUSH
    return SettlementStatus.LOSS


def _combine_split_statuses(statuses: list[SettlementStatus]) -> SettlementStatus:
    if len(statuses) == 1:
        return statuses[0]
    units = sum(_status_units(status) for status in statuses) / len(statuses)
    if units == 1:
        return SettlementStatus.WIN
    if units == 0.5:
        return SettlementStatus.HALF_WIN
    if units == 0:
        return SettlementStatus.PUSH
    if units == -0.5:
        return SettlementStatus.HALF_LOSS
    return SettlementStatus.LOSS


def _status_units(status: SettlementStatus) -> float:
    return {
        SettlementStatus.WIN: 1.0,
        SettlementStatus.HALF_WIN: 0.5,
        SettlementStatus.PUSH: 0.0,
        SettlementStatus.HALF_LOSS: -0.5,
        SettlementStatus.LOSS: -1.0,
    }[status]


def _result_label(home_goals: int, away_goals: int) -> str:
    if home_goals > away_goals:
        return "home"
    if away_goals > home_goals:
        return "away"
    return "draw"
