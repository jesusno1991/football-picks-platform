from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Match, Odds, Prediction
from app.repositories import queries
from app.services.goal_market_engine import (
    GoalLambdas,
    _merlin_score,
    _risk_level,
    _settlement_ev,
    estimate_goal_lambdas,
    probability_for_market,
)
from app.services.market_catalog import MarketSpec, base_market_catalog, merge_market_specs, supported_market_specs_from_odds
from app.services.settlement_engine import fair_odds_from_distribution
from app.utils.dates import local_date_from_utc_naive


@dataclass
class TipstrrMarketPick:
    match_id: int
    external_id: str
    match_name: str
    competition_name: str
    country: str
    kickoff_at: datetime
    kickoff_local_date: str
    match_status: str
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
    odds_collected_at: datetime | None
    expected_value: float | None
    merlin_score: float
    data_quality: float
    risk_level: str
    decision: str
    reason: str


def list_tipstrr_market_picks(db: Session, match_date: date, decision: str | None = None) -> list[TipstrrMarketPick]:
    matches = queries.list_matches(db, match_date)
    rows: list[TipstrrMarketPick] = []
    for match in matches:
        rows.extend(_rows_for_match(db, match))
    if decision:
        decision_normalized = _normalize_decision_filter(decision)
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


def build_daily_export(db: Session, match_date: date, now: datetime | None = None) -> dict:
    settings = get_settings()
    now = now or datetime.utcnow()
    max_odds_age = timedelta(hours=settings.export_max_odds_age_hours)
    matches = queries.list_matches(db, match_date, limit=5000)
    diagnostics = {
        "matches_found": len(matches),
        "future_matches": 0,
        "matches_with_recent_odds": 0,
        "matches_evaluated": 0,
        "discard_reasons": {},
        "max_odds_age_hours": settings.export_max_odds_age_hours,
    }
    rows: list[TipstrrMarketPick] = []
    for match in matches:
        reason = _match_export_block_reason(match, match_date, now, settings.app_timezone)
        if reason:
            _add_reason(diagnostics, reason)
            continue
        diagnostics["future_matches"] += 1
        match_rows = _rows_for_match(db, match)
        recent_rows = [row for row in match_rows if _has_recent_odds(row, now, max_odds_age)]
        if not recent_rows:
            _add_reason(diagnostics, "no_recent_odds")
            continue
        diagnostics["matches_with_recent_odds"] += 1
        diagnostics["matches_evaluated"] += 1
        rows.extend(recent_rows)

    rows = _sort_export_rows(rows)
    publicable = [row for row in rows if row.decision == "PUBLICABLE"]
    return {
        "export_type": "future_pre_match_picks_for_chatgpt",
        "date": match_date.isoformat(),
        "generated_at": now.isoformat(),
        "timezone": settings.app_timezone,
        "diagnostics": diagnostics,
        "publicable_picks": [_row_to_export(row) for row in publicable],
        "market_evaluations": [_row_to_export(row) for row in rows],
    }


def _normalize_decision_filter(decision: str) -> str:
    normalized = decision.strip().upper()
    return {
        "READY_TO_PUBLISH": "PUBLICABLE",
        "PUBLISH": "PUBLICABLE",
        "PUBLISHED": "PUBLICABLE",
        "PARA_PUBLICAR": "PUBLICABLE",
    }.get(normalized, normalized)


def _rows_for_match(db: Session, match: Match) -> list[TipstrrMarketPick]:
    home_form = queries.latest_team_form(db, match.home_team_id, match.competition_id)
    away_form = queries.latest_team_form(db, match.away_team_id, match.competition_id)
    lambdas = estimate_goal_lambdas(home_form, away_form)
    odds_rows = list(db.scalars(select(Odds).where(Odds.match_id == match.id)))
    specs = merge_market_specs(base_market_catalog(), supported_market_specs_from_odds(odds_rows))
    return [_row_for_spec(match, lambdas, spec, _best_odd(odds_rows, spec)) for spec in specs]


def build_tipstrr_predictions(db: Session, match: Match, system) -> list[Prediction]:
    rows = _rows_for_match(db, match)
    predictions: list[Prediction] = []
    for row in rows:
        predictions.append(
            Prediction(
                match_id=match.id,
                system_id=system.id,
                market=f"tipstrr:{row.family}:{row.period}:{row.team_scope}",
                selection=row.selection,
                line=row.line,
                predicted_probability=row.model_probability,
                fair_odds=row.fair_odds,
                available_odds=row.market_odds,
                expected_value=row.expected_value,
                confidence=max(0.2, min(0.9, row.data_quality / 100)),
                recommended_stake=2 if row.decision == "PUBLICABLE" and row.merlin_score >= 75 else 1,
                explanation=row.reason,
                feature_snapshot=json.dumps(
                    {
                        "group": row.group,
                        "label": row.label,
                        "family": row.family,
                        "period": row.period,
                        "team_scope": row.team_scope,
                        "risk_level": row.risk_level,
                        "data_quality": row.data_quality,
                        "merlin_score": row.merlin_score,
                        "bookmaker": row.bookmaker,
                    },
                    ensure_ascii=False,
                ),
                status="published" if row.decision == "PUBLICABLE" else "no_bet",
                published_at=datetime.utcnow() if row.decision == "PUBLICABLE" else None,
            )
        )
    return predictions


def _row_for_spec(match: Match, lambdas: GoalLambdas, spec: MarketSpec, odd: Odds | None) -> TipstrrMarketPick:
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
        kickoff_local_date=local_date_from_utc_naive(match.kickoff_at, get_settings().app_timezone).isoformat(),
        match_status=match.status,
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
        odds_collected_at=odd.collected_at if odd else None,
        expected_value=expected_value,
        merlin_score=merlin,
        data_quality=lambdas.data_quality,
        risk_level=risk,
        decision=decision,
        reason=reason,
    )


def _decision_for_market(
    match: Match,
    spec: MarketSpec,
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
    if odd.odds < 1.25 or odd.odds > 8:
        return "WATCH", "Cuota fuera de rango profesional"
    if spec.family in {"correct_score", "first_goal", "qualification"}:
        return "WATCH", "Mercado de alta varianza o contexto especial, no publicacion automatica"
    if _is_blocked_low_goal_publish(spec):
        return "WATCH", "Linea de goles bloqueada para publicacion"
    if lambdas.sample_size < 20 or lambdas.data_quality < 50:
        return "WATCH", "Falta historico suficiente"
    if risk == "high":
        return "WATCH", "Riesgo alto"
    if expected_value is None or expected_value < 0.03:
        return "WATCH", "Sin valor suficiente"
    return "PUBLICABLE", "Valor positivo con cuota real"


def _best_odd(odds_rows: list[Odds], spec: MarketSpec) -> Odds | None:
    candidates = [odd for odd in odds_rows if _odd_matches_spec(odd, spec)]
    if not candidates:
        return None
    return max(candidates, key=lambda odd: odd.odds)


def _odd_matches_spec(odd: Odds, spec: MarketSpec) -> bool:
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


def _sort_export_rows(rows: list[TipstrrMarketPick]) -> list[TipstrrMarketPick]:
    return sorted(
        rows,
        key=lambda row: (
            0 if row.decision == "PUBLICABLE" else 1 if row.decision == "WATCH" else 2,
            row.kickoff_at,
            -(row.expected_value if row.expected_value is not None else -999),
            -row.merlin_score,
        ),
    )


def _match_export_block_reason(match: Match, match_date: date, now: datetime, timezone_name: str) -> str | None:
    if local_date_from_utc_naive(match.kickoff_at, timezone_name) != match_date:
        return "local_date_mismatch"
    if match.kickoff_at <= now:
        return "already_started_or_closed"
    normalized_status = (match.status or "").strip().lower().replace("-", "_")
    allowed = {"scheduled", "not_started", "not started", "ns", "tbd"}
    if normalized_status not in allowed:
        return f"invalid_status:{match.status or 'unknown'}"
    return None


def _has_recent_odds(row: TipstrrMarketPick, now: datetime, max_age: timedelta) -> bool:
    if row.market_odds is None or row.odds_collected_at is None:
        return False
    if row.odds_collected_at > now + timedelta(minutes=5):
        return False
    return now - row.odds_collected_at <= max_age


def _add_reason(diagnostics: dict, reason: str) -> None:
    reasons = diagnostics["discard_reasons"]
    reasons[reason] = int(reasons.get(reason, 0)) + 1


def _row_to_export(row: TipstrrMarketPick) -> dict:
    return {
        "match_id": row.match_id,
        "external_id": row.external_id,
        "match_name": row.match_name,
        "kickoff_at": row.kickoff_at.isoformat(),
        "kickoff_local_date": row.kickoff_local_date,
        "match_status": row.match_status,
        "country": row.country,
        "competition": row.competition_name,
        "group": row.group,
        "market_family": row.family,
        "market_label": row.label,
        "period": row.period,
        "team_scope": row.team_scope,
        "selection": row.selection,
        "line": row.line,
        "model_probability": row.model_probability,
        "fair_odds": row.fair_odds,
        "market_odds": row.market_odds,
        "bookmaker": row.bookmaker,
        "odds_collected_at": row.odds_collected_at.isoformat() if row.odds_collected_at else None,
        "expected_value": row.expected_value,
        "merlin_score": row.merlin_score,
        "data_quality": row.data_quality,
        "risk_level": row.risk_level,
        "decision": row.decision,
        "reason": row.reason,
    }
