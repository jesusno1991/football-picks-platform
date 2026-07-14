from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Match, Odds
from app.repositories import queries
from app.services.goal_market_engine import (
    GoalLambdas,
    _merlin_score,
    _risk_level,
    _settlement_ev,
    estimate_goal_lambdas,
    probability_for_market,
)
from app.services.settlement_engine import fair_odds_from_distribution


@dataclass(frozen=True)
class TipstrrMarketSpec:
    group: str
    family: str
    period: str
    team_scope: str
    selection: str
    line: float | None
    label: str


@dataclass
class TipstrrMarketPick:
    match_id: int
    external_id: str
    match_name: str
    competition_name: str
    country: str
    kickoff_at: datetime
    group: str
    family: str
    period: str
    team_scope: str
    selection: str
    line: float | None
    label: str
    model_probability: float | None
    fair_odds: float | None
    market_odds: float | None
    bookmaker: str | None
    expected_value: float | None
    merlin_score: float
    data_quality: float
    risk_level: str
    decision: str
    reason: str


TIPSTRR_MARKETS: tuple[TipstrrMarketSpec, ...] = (
    TipstrrMarketSpec("1X2", "match_result", "full_time", "all", "home", None, "Gana local"),
    TipstrrMarketSpec("1X2", "match_result", "full_time", "all", "draw", None, "Empate"),
    TipstrrMarketSpec("1X2", "match_result", "full_time", "all", "away", None, "Gana visitante"),
    TipstrrMarketSpec("Empate no apuesta", "draw_no_bet", "full_time", "all", "home", None, "Local empate no apuesta"),
    TipstrrMarketSpec("Empate no apuesta", "draw_no_bet", "full_time", "all", "away", None, "Visitante empate no apuesta"),
    TipstrrMarketSpec("Goles partido", "total_goals", "full_time", "all", "over", 3.0, "Mas de 3.0 goles"),
    TipstrrMarketSpec("Goles partido", "total_goals", "full_time", "all", "under", 3.0, "Menos de 3.0 goles"),
    TipstrrMarketSpec("Goles partido", "total_goals", "full_time", "all", "over", 3.25, "Mas de 3.25 goles"),
    TipstrrMarketSpec("Goles partido", "total_goals", "full_time", "all", "under", 3.25, "Menos de 3.25 goles"),
    TipstrrMarketSpec("Marcador correcto", "correct_score", "full_time", "all", "1-0", None, "1-0"),
    TipstrrMarketSpec("Marcador correcto", "correct_score", "full_time", "all", "0-0", None, "0-0"),
    TipstrrMarketSpec("Marcador correcto", "correct_score", "full_time", "all", "0-1", None, "0-1"),
    TipstrrMarketSpec("Marcador correcto", "correct_score", "full_time", "all", "2-0", None, "2-0"),
    TipstrrMarketSpec("Marcador correcto", "correct_score", "full_time", "all", "1-1", None, "1-1"),
    TipstrrMarketSpec("Marcador correcto", "correct_score", "full_time", "all", "0-2", None, "0-2"),
    TipstrrMarketSpec("Marcador correcto", "correct_score", "full_time", "all", "2-1", None, "2-1"),
    TipstrrMarketSpec("Marcador correcto", "correct_score", "full_time", "all", "1-2", None, "1-2"),
    TipstrrMarketSpec("Marcador correcto", "correct_score", "full_time", "all", "2-2", None, "2-2"),
    TipstrrMarketSpec("Goles local", "total_goals", "full_time", "home", "over", 1.5, "Local mas de 1.5 goles"),
    TipstrrMarketSpec("Goles local", "total_goals", "full_time", "home", "under", 1.5, "Local menos de 1.5 goles"),
    TipstrrMarketSpec("Goles local", "total_goals", "full_time", "home", "over", 2.5, "Local mas de 2.5 goles"),
    TipstrrMarketSpec("Goles local", "total_goals", "full_time", "home", "under", 2.5, "Local menos de 2.5 goles"),
    TipstrrMarketSpec("Goles visitante", "total_goals", "full_time", "away", "over", 0.5, "Visitante mas de 0.5 goles"),
    TipstrrMarketSpec("Goles visitante", "total_goals", "full_time", "away", "under", 0.5, "Visitante menos de 0.5 goles"),
    TipstrrMarketSpec("Goles visitante", "total_goals", "full_time", "away", "over", 1.5, "Visitante mas de 1.5 goles"),
    TipstrrMarketSpec("Goles visitante", "total_goals", "full_time", "away", "under", 1.5, "Visitante menos de 1.5 goles"),
    TipstrrMarketSpec("1a parte local", "total_goals", "first_half", "home", "over", 0.5, "Local 1a parte mas de 0.5 goles"),
    TipstrrMarketSpec("1a parte local", "total_goals", "first_half", "home", "under", 0.5, "Local 1a parte menos de 0.5 goles"),
    TipstrrMarketSpec("1a parte visitante", "total_goals", "first_half", "away", "over", 0.5, "Visitante 1a parte mas de 0.5 goles"),
    TipstrrMarketSpec("1a parte visitante", "total_goals", "first_half", "away", "under", 0.5, "Visitante 1a parte menos de 0.5 goles"),
    TipstrrMarketSpec("Handicap asiatico", "asian_handicap", "full_time", "home", "handicap", -1.0, "Local -1.00"),
    TipstrrMarketSpec("Handicap asiatico", "asian_handicap", "full_time", "away", "handicap", 1.0, "Visitante +1.00"),
    TipstrrMarketSpec("Handicap asiatico", "asian_handicap", "full_time", "home", "handicap", -0.75, "Local -0.75"),
    TipstrrMarketSpec("Handicap asiatico", "asian_handicap", "full_time", "away", "handicap", 0.75, "Visitante +0.75"),
    TipstrrMarketSpec("Handicap asiatico 1a parte", "asian_handicap", "first_half", "home", "handicap", -0.5, "Local 1a parte -0.50"),
    TipstrrMarketSpec("Handicap asiatico 1a parte", "asian_handicap", "first_half", "away", "handicap", 0.5, "Visitante 1a parte +0.50"),
    TipstrrMarketSpec("Handicap asiatico 1a parte", "asian_handicap", "first_half", "home", "handicap", -0.25, "Local 1a parte -0.25"),
    TipstrrMarketSpec("Handicap asiatico 1a parte", "asian_handicap", "first_half", "away", "handicap", 0.25, "Visitante 1a parte +0.25"),
)


def list_tipstrr_market_picks(db: Session, match_date: date, decision: str | None = None) -> list[TipstrrMarketPick]:
    matches = queries.list_matches(db, match_date)
    rows: list[TipstrrMarketPick] = []
    for match in matches:
        rows.extend(_rows_for_match(db, match))
    if decision:
        decision_normalized = decision.upper()
        rows = [row for row in rows if row.decision == decision_normalized]
    return sorted(
        rows,
        key=lambda row: (
            0 if row.decision == "PUBLICABLE" else 1 if row.decision == "WATCH" else 2,
            -(row.expected_value if row.expected_value is not None else -999),
            -row.merlin_score,
            row.kickoff_at,
        ),
    )


def _rows_for_match(db: Session, match: Match) -> list[TipstrrMarketPick]:
    home_form = queries.latest_team_form(db, match.home_team_id, match.competition_id)
    away_form = queries.latest_team_form(db, match.away_team_id, match.competition_id)
    lambdas = estimate_goal_lambdas(home_form, away_form)
    odds_rows = list(db.scalars(select(Odds).where(Odds.match_id == match.id)))
    return [_row_for_spec(match, lambdas, spec, _best_odd(odds_rows, spec)) for spec in TIPSTRR_MARKETS]


def _row_for_spec(match: Match, lambdas: GoalLambdas, spec: TipstrrMarketSpec, odd: Odds | None) -> TipstrrMarketPick:
    distribution, model_probability, settlement_type = probability_for_market(
        spec.family,
        spec.period,
        spec.team_scope,
        spec.selection,
        spec.line,
        lambdas,
    )
    fair_odds = fair_odds_from_distribution(distribution)
    expected_value = round(_settlement_ev(distribution, odd.odds), 6) if odd and fair_odds is not None else None
    risk = _risk_level(spec.family, spec.line)
    merlin = _merlin_score(expected_value, lambdas.data_quality, risk)
    decision, reason = _decision_for_market(match, spec, odd, lambdas, expected_value, risk, settlement_type)
    return TipstrrMarketPick(
        match_id=match.id,
        external_id=match.external_id,
        match_name=f"{match.home_team.name} vs {match.away_team.name}",
        competition_name=match.competition.name,
        country=match.competition.country,
        kickoff_at=match.kickoff_at,
        group=spec.group,
        family=spec.family,
        period=spec.period,
        team_scope=spec.team_scope,
        selection=spec.selection,
        line=spec.line,
        label=spec.label,
        model_probability=model_probability,
        fair_odds=fair_odds,
        market_odds=odd.odds if odd else None,
        bookmaker=odd.bookmaker if odd else None,
        expected_value=expected_value,
        merlin_score=merlin,
        data_quality=lambdas.data_quality,
        risk_level=risk,
        decision=decision,
        reason=reason,
    )


def _decision_for_market(
    match: Match,
    spec: TipstrrMarketSpec,
    odd: Odds | None,
    lambdas: GoalLambdas,
    expected_value: float | None,
    risk: str,
    settlement_type: str,
) -> tuple[str, str]:
    if settlement_type == "unsupported":
        return "DESCARTADO", "Mercado no soportado por el motor"
    if not odd:
        return "SIN_CUOTA", "Modelo disponible, falta cuota real del proveedor"
    if match.kickoff_at <= datetime.utcnow():
        return "WATCH", "Partido ya iniciado o cerrado"
    if spec.family == "correct_score":
        return "WATCH", "Marcador correcto se muestra para estudio, no para publicacion automatica"
    if _is_blocked_low_goal_publish(spec):
        return "WATCH", "Linea de goles bloqueada para publicacion"
    if lambdas.sample_size < 20 or lambdas.data_quality < 50:
        return "WATCH", "Falta historico suficiente"
    if risk == "high":
        return "WATCH", "Riesgo alto"
    if expected_value is None or expected_value < 0.03:
        return "WATCH", "Sin valor suficiente"
    return "PUBLICABLE", "Valor positivo con cuota real"


def _best_odd(odds_rows: list[Odds], spec: TipstrrMarketSpec) -> Odds | None:
    candidates = [odd for odd in odds_rows if _odd_matches_spec(odd, spec)]
    if not candidates:
        return None
    return max(candidates, key=lambda odd: odd.odds)


def _odd_matches_spec(odd: Odds, spec: TipstrrMarketSpec) -> bool:
    family = odd.market_family or _legacy_family(odd.market)
    period = odd.period or "full_time"
    team_scope = odd.team_scope or "all"
    if family != spec.family or period != spec.period or team_scope != spec.team_scope:
        return False
    if odd.selection != spec.selection:
        return False
    if spec.line is None:
        return odd.line is None
    return odd.line is not None and abs(float(odd.line) - spec.line) < 1e-9


def _legacy_family(market: str) -> str:
    return {"goals": "total_goals", "team_goals": "total_goals", "btts": "btts", "result": "match_result"}.get(market, market)


def _is_blocked_low_goal_publish(spec: TipstrrMarketSpec) -> bool:
    return (
        spec.family == "total_goals"
        and spec.period == "full_time"
        and spec.team_scope == "all"
        and spec.selection == "over"
        and spec.line in {1.5, 2.5}
    )


def has_matches_for_date(db: Session, match_date: date) -> bool:
    start = datetime.combine(match_date, time.min)
    end = datetime.combine(match_date, time.max)
    return db.scalar(select(Match.id).where(Match.kickoff_at.between(start, end)).limit(1)) is not None
