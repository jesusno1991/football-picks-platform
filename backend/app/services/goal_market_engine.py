from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import MarketDefinition, MarketEvaluation, Match, Odds, TeamForm
from app.repositories.queries import latest_team_form
from app.services.settlement_engine import SettlementDistribution, fair_odds_from_distribution


@dataclass(frozen=True)
class GoalLambdas:
    home_full_time: float
    away_full_time: float
    home_first_half: float
    away_first_half: float
    home_second_half: float
    away_second_half: float
    confidence: float
    data_quality: float
    sample_size: int


@dataclass
class MarketEvaluationRow:
    code: str
    family: str
    period: str
    team_scope: str
    selection: str
    line: float | None
    settlement_type: str
    probability_full_win: float
    probability_half_win: float
    probability_push: float
    probability_half_loss: float
    probability_full_loss: float
    model_probability: float | None
    fair_odds: float | None
    market_odds: float | None
    bookmaker: str | None
    expected_value: float | None
    merlin_score: float
    data_quality: float
    risk_level: str
    validation_status: str
    decision: str
    reasons: list[str]
    alerts: list[str]


def evaluate_match_markets(db: Session, match_id: int) -> list[MarketEvaluationRow]:
    match = db.get(Match, match_id)
    if not match:
        return []
    home_form = latest_team_form(db, match.home_team_id, match.competition_id)
    away_form = latest_team_form(db, match.away_team_id, match.competition_id)
    lambdas = estimate_goal_lambdas(home_form, away_form)
    odds_rows = list(db.scalars(select(Odds).where(Odds.match_id == match.id)))
    evaluations = [_evaluate_odd(db, match, odd, lambdas) for odd in odds_rows]
    evaluations = [row for row in evaluations if row is not None]
    _select_publishable(evaluations)
    _persist_evaluations(db, match, evaluations)
    return evaluations


def estimate_goal_lambdas(home_form: TeamForm | None, away_form: TeamForm | None) -> GoalLambdas:
    if not home_form or not away_form:
        return GoalLambdas(1.1, 1.0, 0.47, 0.43, 0.63, 0.57, 0.2, 20, 0)

    sample = int(home_form.matches_sample or 0) + int(away_form.matches_sample or 0)
    home_ft = max(0.15, (float(home_form.goals_for_avg or 1.1) + float(away_form.goals_against_avg or 1.1)) / 2)
    away_ft = max(0.15, (float(away_form.goals_for_avg or 1.0) + float(home_form.goals_against_avg or 1.0)) / 2)
    first_half_total = float(home_form.first_half_goals_avg or 0) + float(away_form.first_half_goals_avg or 0)
    second_half_total = float(home_form.second_half_goals_avg or 0) + float(away_form.second_half_goals_avg or 0)
    half_share = first_half_total / (first_half_total + second_half_total) if first_half_total + second_half_total > 0 else 0.43
    half_share = min(0.5, max(0.35, half_share))
    data_quality = min(100.0, sample * 2.5)
    confidence = min(0.82, 0.25 + sample / 100)
    return GoalLambdas(
        home_full_time=round(home_ft, 4),
        away_full_time=round(away_ft, 4),
        home_first_half=round(home_ft * half_share, 4),
        away_first_half=round(away_ft * half_share, 4),
        home_second_half=round(home_ft * (1 - half_share), 4),
        away_second_half=round(away_ft * (1 - half_share), 4),
        confidence=round(confidence, 4),
        data_quality=round(data_quality, 2),
        sample_size=sample,
    )


def score_matrix(home_lambda: float, away_lambda: float, max_goals: int = 10) -> dict[tuple[int, int], float]:
    home_probs = _poisson_probs(home_lambda, max_goals)
    away_probs = _poisson_probs(away_lambda, max_goals)
    matrix: dict[tuple[int, int], float] = {}
    total = 0.0
    for home_goals, home_probability in enumerate(home_probs):
        for away_goals, away_probability in enumerate(away_probs):
            probability = home_probability * away_probability
            matrix[(home_goals, away_goals)] = probability
            total += probability
    if total > 0:
        matrix = {score: probability / total for score, probability in matrix.items()}
    return matrix


def probability_for_market(
    family: str,
    period: str,
    team_scope: str,
    selection: str,
    line: float | None,
    lambdas: GoalLambdas,
) -> tuple[SettlementDistribution, float | None, str]:
    matrix = _matrix_for_period(period, lambdas)
    if family == "total_goals" and line is not None:
        distribution = _total_distribution(matrix, team_scope, selection, line)
        return distribution, _binary_probability_from_distribution(distribution), "asian_total" if _is_push_line(line) else "binary"
    if family == "btts":
        probability = _btts_probability(matrix)
        probability = probability if selection == "yes" else 1 - probability
        return SettlementDistribution(probability_full_win=probability, probability_full_loss=1 - probability), probability, "binary"
    if family == "match_result":
        probability = _result_probability(matrix, selection)
        return SettlementDistribution(probability_full_win=probability, probability_full_loss=1 - probability), probability, "binary"
    if family == "double_chance":
        probability = _double_chance_probability(matrix, selection)
        return SettlementDistribution(probability_full_win=probability, probability_full_loss=1 - probability), probability, "binary"
    if family == "draw_no_bet":
        win = _result_probability(matrix, selection)
        push = _result_probability(matrix, "draw")
        return SettlementDistribution(probability_full_win=win, probability_push=push, probability_full_loss=max(0, 1 - win - push)), win, "draw_no_bet"
    return SettlementDistribution(), None, "unsupported"


def _evaluate_odd(db: Session, match: Match, odd: Odds, lambdas: GoalLambdas) -> MarketEvaluationRow | None:
    family = odd.market_family or _legacy_family(odd.market)
    period = odd.period or "full_time"
    team_scope = odd.team_scope or "all"
    distribution, model_probability, settlement_type = probability_for_market(family, period, team_scope, odd.selection, odd.line, lambdas)
    if settlement_type == "unsupported":
        return None
    fair_odds = fair_odds_from_distribution(distribution)
    expected_value = None if fair_odds is None else round(_settlement_ev(distribution, odd.odds), 6)
    definition = upsert_market_definition(db, family, period, team_scope, odd.selection, odd.line, settlement_type)
    validation, reasons, alerts = _validate_market(match, odd, lambdas, expected_value)
    risk = _risk_level(family, odd.line)
    merlin_score = _merlin_score(expected_value, lambdas.data_quality, risk)
    return MarketEvaluationRow(
        code=definition.code,
        family=family,
        period=period,
        team_scope=team_scope,
        selection=odd.selection,
        line=odd.line,
        settlement_type=settlement_type,
        probability_full_win=round(distribution.probability_full_win, 6),
        probability_half_win=round(distribution.probability_half_win, 6),
        probability_push=round(distribution.probability_push, 6),
        probability_half_loss=round(distribution.probability_half_loss, 6),
        probability_full_loss=round(distribution.probability_full_loss, 6),
        model_probability=model_probability,
        fair_odds=fair_odds,
        market_odds=odd.odds,
        bookmaker=odd.bookmaker,
        expected_value=expected_value,
        merlin_score=merlin_score,
        data_quality=lambdas.data_quality,
        risk_level=risk,
        validation_status=validation,
        decision="pending_validation",
        reasons=reasons,
        alerts=alerts,
    )


def upsert_market_definition(
    db: Session,
    family: str,
    period: str,
    team_scope: str,
    selection: str,
    line: float | None,
    settlement_type: str,
) -> MarketDefinition:
    code = _market_code(family, period, team_scope, selection, line)
    definition = db.scalar(select(MarketDefinition).where(MarketDefinition.code == code))
    if definition:
        return definition
    definition = MarketDefinition(
        code=code,
        family=family,
        period=period,
        team_scope=team_scope,
        selection=selection,
        line=line,
        settlement_type=settlement_type,
        is_supported=True,
        is_publishable=family not in {"correct_score"},
    )
    db.add(definition)
    db.flush()
    return definition


def _select_publishable(rows: list[MarketEvaluationRow]) -> None:
    eligible = [
        row
        for row in rows
        if row.validation_status == "ready_to_publish"
        and row.expected_value is not None
        and row.expected_value > 0
        and row.risk_level != "high"
    ]
    eligible.sort(key=lambda row: (row.merlin_score, row.expected_value or -1), reverse=True)
    selected_by_match = eligible[:1]
    for row in rows:
        row.decision = "ready_to_publish" if row in selected_by_match else row.validation_status


def _persist_evaluations(db: Session, match: Match, rows: list[MarketEvaluationRow]) -> None:
    for row in rows:
        definition = upsert_market_definition(db, row.family, row.period, row.team_scope, row.selection, row.line, row.settlement_type)
        existing = db.scalar(
            select(MarketEvaluation).where(
                MarketEvaluation.match_id == match.id,
                MarketEvaluation.market_definition_id == definition.id,
                MarketEvaluation.bookmaker == row.bookmaker,
            )
        )
        payload = {
            "fixture_id": match.external_id,
            "probability_full_win": row.probability_full_win,
            "probability_half_win": row.probability_half_win,
            "probability_push": row.probability_push,
            "probability_half_loss": row.probability_half_loss,
            "probability_full_loss": row.probability_full_loss,
            "fair_odds": row.fair_odds,
            "market_odds": row.market_odds,
            "expected_value": row.expected_value,
            "bookmaker": row.bookmaker,
            "merlin_score": row.merlin_score,
            "data_quality": row.data_quality,
            "risk_level": row.risk_level,
            "validation_status": row.validation_status,
            "decision": row.decision,
            "reasons": json.dumps(row.reasons, ensure_ascii=False),
            "alerts": json.dumps(row.alerts, ensure_ascii=False),
            "evaluated_at": datetime.utcnow(),
        }
        if existing:
            for key, value in payload.items():
                setattr(existing, key, value)
        else:
            db.add(MarketEvaluation(match_id=match.id, market_definition_id=definition.id, **payload))
    db.commit()


def _poisson_probs(lambda_value: float, max_goals: int) -> list[float]:
    return [math.exp(-lambda_value) * lambda_value**goals / math.factorial(goals) for goals in range(max_goals + 1)]


def _matrix_for_period(period: str, lambdas: GoalLambdas) -> dict[tuple[int, int], float]:
    if period == "first_half":
        return score_matrix(lambdas.home_first_half, lambdas.away_first_half)
    if period == "second_half":
        return score_matrix(lambdas.home_second_half, lambdas.away_second_half)
    return score_matrix(lambdas.home_full_time, lambdas.away_full_time)


def _total_distribution(matrix: dict[tuple[int, int], float], team_scope: str, selection: str, line: float) -> SettlementDistribution:
    full_win = half_win = push = half_loss = full_loss = 0.0
    for (home_goals, away_goals), probability in matrix.items():
        goals = home_goals + away_goals
        if team_scope == "home":
            goals = home_goals
        elif team_scope == "away":
            goals = away_goals
        units = _settlement_units_for_total(goals, line, selection)
        if units == 1:
            full_win += probability
        elif units == 0.5:
            half_win += probability
        elif units == 0:
            push += probability
        elif units == -0.5:
            half_loss += probability
        else:
            full_loss += probability
    return SettlementDistribution(full_win, half_win, push, half_loss, full_loss).normalized()


def _settlement_units_for_total(goals: int, line: float, selection: str) -> float:
    components = _quarter_components(line)
    units = 0.0
    for component in components:
        diff = goals - component
        if selection == "under":
            diff = -diff
        units += 1 if diff > 0 else 0 if diff == 0 else -1
    return units / len(components)


def _quarter_components(line: float) -> tuple[float, ...]:
    doubled = round(line * 2, 6)
    if abs(doubled - round(doubled)) < 1e-6:
        return (round(line, 2),)
    lower = math.floor(line * 2) / 2
    return (round(lower, 2), round(lower + 0.5, 2))


def _binary_probability_from_distribution(distribution: SettlementDistribution) -> float:
    return round(distribution.probability_full_win + 0.5 * distribution.probability_half_win, 6)


def _btts_probability(matrix: dict[tuple[int, int], float]) -> float:
    return round(sum(probability for (home, away), probability in matrix.items() if home >= 1 and away >= 1), 6)


def _result_probability(matrix: dict[tuple[int, int], float], selection: str) -> float:
    if selection == "home":
        return round(sum(probability for (home, away), probability in matrix.items() if home > away), 6)
    if selection == "away":
        return round(sum(probability for (home, away), probability in matrix.items() if away > home), 6)
    if selection == "draw":
        return round(sum(probability for (home, away), probability in matrix.items() if home == away), 6)
    return 0.0


def _double_chance_probability(matrix: dict[tuple[int, int], float], selection: str) -> float:
    if selection == "1x":
        return _result_probability(matrix, "home") + _result_probability(matrix, "draw")
    if selection == "x2":
        return _result_probability(matrix, "away") + _result_probability(matrix, "draw")
    if selection == "12":
        return _result_probability(matrix, "home") + _result_probability(matrix, "away")
    return 0.0


def _settlement_ev(distribution: SettlementDistribution, odds: float) -> float:
    return (
        distribution.probability_full_win * (odds - 1)
        + distribution.probability_half_win * ((odds - 1) / 2)
        - distribution.probability_half_loss * 0.5
        - distribution.probability_full_loss
    )


def _validate_market(match: Match, odd: Odds, lambdas: GoalLambdas, expected_value: float | None) -> tuple[str, list[str], list[str]]:
    reasons: list[str] = []
    alerts: list[str] = []
    if match.kickoff_at <= datetime.utcnow():
        reasons.append("partido ya iniciado")
    if odd.validation_status not in {None, "mapped"}:
        reasons.append("mapeo de cuota no validado")
    if lambdas.sample_size < 20:
        reasons.append("muestra insuficiente")
    if expected_value is None or expected_value <= 0:
        reasons.append("EV no positivo")
    if lambdas.data_quality < 50:
        reasons.append("calidad de datos baja")
    if odd.odds < 1.25 or odd.odds > 8:
        alerts.append("cuota fuera de rango normal")
    return ("ready_to_publish" if not reasons and expected_value is not None and expected_value >= 0.03 else "pending_validation", reasons, alerts)


def _risk_level(family: str, line: float | None) -> str:
    if family == "correct_score":
        return "high"
    if line is not None and line >= 4.0:
        return "medium"
    return "low"


def _merlin_score(expected_value: float | None, data_quality: float, risk_level: str) -> float:
    risk_penalty = {"low": 0, "medium": 8, "high": 25}.get(risk_level, 15)
    ev_score = max(0.0, min(35.0, (expected_value or 0) * 350))
    return round(max(0.0, min(100.0, ev_score + data_quality * 0.65 - risk_penalty)), 2)


def _legacy_family(market: str) -> str:
    return {"goals": "total_goals", "team_goals": "total_goals", "btts": "btts", "result": "match_result"}.get(market, market)


def _market_code(family: str, period: str, team_scope: str, selection: str, line: float | None) -> str:
    line_part = "NONE" if line is None else str(line).replace(".", "_").replace("-", "MINUS_")
    return f"{family}_{period}_{team_scope}_{selection}_{line_part}".upper()


def _is_push_line(line: float) -> bool:
    return abs(line - round(line)) < 1e-9 or abs(line * 4 - round(line * 4)) < 1e-9
