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
from app.services.runtime_config import get_pick_safety_mode
from app.services.settlement_engine import fair_odds_from_distribution
from app.utils.dates import local_date_from_utc_naive
from app.utils.time import utc_now_naive


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
    odds_validation_status: str | None
    expected_value: float | None
    merlin_score: float
    data_quality: float
    risk_level: str
    decision: str
    reason: str
    passed_rules: list[str]
    failed_rules: list[str]
    filter_reasons: list[str]
    odds_quality_score: float
    price_age_minutes: float | None
    publish_blocked_by_config: bool
    publish_blocked_by_risk: bool
    publish_blocked_by_data_quality: bool
    publish_blocked_by_ev: bool
    publish_blocked_by_odds: bool
    safety_mode: str


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
    now = now or utc_now_naive()
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
                published_at=utc_now_naive() if row.decision == "PUBLICABLE" else None,
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
    decision, reason, audit = _decision_for_market(match, spec, odd, lambdas, model_probability, expected_value, risk, settlement_type)
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
        odds_validation_status=odd.validation_status if odd else None,
        expected_value=expected_value,
        merlin_score=merlin,
        data_quality=lambdas.data_quality,
        risk_level=risk,
        decision=decision,
        reason=reason,
        passed_rules=audit["passed_rules"],
        failed_rules=audit["failed_rules"],
        filter_reasons=audit["filter_reasons"],
        odds_quality_score=audit["odds_quality_score"],
        price_age_minutes=audit["price_age_minutes"],
        publish_blocked_by_config=audit["publish_blocked_by_config"],
        publish_blocked_by_risk=audit["publish_blocked_by_risk"],
        publish_blocked_by_data_quality=audit["publish_blocked_by_data_quality"],
        publish_blocked_by_ev=audit["publish_blocked_by_ev"],
        publish_blocked_by_odds=audit["publish_blocked_by_odds"],
        safety_mode=audit["safety_mode"],
    )


def _decision_for_market(
    match: Match,
    spec: MarketSpec,
    odd: Odds | None,
    lambdas: GoalLambdas,
    model_probability: float | None,
    expected_value: float | None,
    risk: str,
    settlement_type: str,
) -> tuple[str, str, dict]:
    audit = _base_audit()
    settings = get_settings()
    thresholds = _safety_thresholds(get_pick_safety_mode())
    audit["safety_mode"] = thresholds["mode"]
    if settlement_type == "unsupported":
        _fail(audit, "Mercado no soportado por el motor")
        audit["publish_blocked_by_config"] = True
        return "DESCARTADO", "Mercado no soportado por el motor", audit
    _pass(audit, "Mercado soportado por el modelo")
    if not odd:
        _fail(audit, "Falta cuota real del proveedor")
        audit["publish_blocked_by_odds"] = True
        return "SIN_CUOTA", "Modelo disponible, falta cuota real del proveedor", audit
    now = utc_now_naive()
    odds_audit = _validate_real_odd(odd, now, timedelta(hours=settings.export_max_odds_age_hours))
    audit["odds_quality_score"] = odds_audit["quality_score"]
    audit["price_age_minutes"] = odds_audit["price_age_minutes"]
    for rule in odds_audit["passed_rules"]:
        _pass(audit, rule)
    for rule in odds_audit["failed_rules"]:
        _fail(audit, rule)
    if odds_audit["failed_rules"]:
        audit["publish_blocked_by_odds"] = True
        return "WATCH", "Cuota no verificada o desactualizada", audit
    if match.kickoff_at <= now:
        _fail(audit, "Partido ya iniciado o cerrado")
        audit["publish_blocked_by_config"] = True
        return "WATCH", "Partido ya iniciado o cerrado", audit
    _pass(audit, "Partido futuro")
    if odd.odds < 1.25 or odd.odds > 8:
        _fail(audit, "Cuota fuera de rango profesional")
        audit["publish_blocked_by_odds"] = True
        return "WATCH", "Cuota fuera de rango profesional", audit
    _pass(audit, "Cuota dentro de rango profesional")
    if spec.family in {"correct_score", "first_goal", "qualification"}:
        _fail(audit, "Mercado reservado para estudio por alta varianza")
        audit["publish_blocked_by_config"] = True
        return "WATCH", "Mercado de alta varianza o contexto especial, no publicacion automatica", audit
    _pass(audit, "Mercado permitido para publicacion")
    if not _market_line_is_professional(spec):
        _fail(audit, "Linea fuera de rango profesional para publicacion")
        audit["publish_blocked_by_config"] = True
        return "WATCH", "Linea demasiado extrema para publicacion automatica", audit
    _pass(audit, "Linea dentro de rango profesional")
    if model_probability is None or model_probability < thresholds["min_probability"]:
        _fail(audit, f"Probabilidad inferior al minimo {thresholds['min_probability']:.2f}")
        audit["publish_blocked_by_ev"] = True
        return "WATCH", "Probabilidad insuficiente para publicar", audit
    _pass(audit, "Probabilidad minima superada")
    if lambdas.sample_size < thresholds["min_sample"] or lambdas.data_quality < thresholds["min_data_quality"]:
        _fail(audit, f"Calidad de datos inferior al minimo {thresholds['min_data_quality']:.0f}")
        audit["publish_blocked_by_data_quality"] = True
        return "WATCH", "Falta historico suficiente", audit
    _pass(audit, "Calidad de datos suficiente")
    if risk not in thresholds["allowed_risk"]:
        _fail(audit, f"Riesgo {risk} no permitido en modo {thresholds['mode']}")
        audit["publish_blocked_by_risk"] = True
        return "WATCH", "Riesgo alto", audit
    _pass(audit, "Riesgo permitido")
    if expected_value is None or expected_value < thresholds["min_ev"]:
        _fail(audit, f"EV inferior al minimo {thresholds['min_ev']:.3f}")
        audit["publish_blocked_by_ev"] = True
        return "WATCH", "Sin valor suficiente", audit
    _pass(audit, "EV minimo superado")
    return "PUBLICABLE", "Valor positivo con cuota real", audit


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
    if (row.odds_validation_status or "").lower() not in {"mapped", "verified", "valid"}:
        return False
    if row.odds_collected_at > now + timedelta(minutes=5):
        return False
    return now - row.odds_collected_at <= max_age


def _validate_real_odd(odd: Odds, now: datetime, max_age: timedelta) -> dict:
    passed_rules: list[str] = []
    failed_rules: list[str] = []
    price_age_minutes: float | None = None
    if odd.odds <= 1:
        failed_rules.append("Cuota menor o igual a 1")
    else:
        passed_rules.append("Cuota numerica valida")
    if (odd.validation_status or "").lower() not in {"mapped", "verified", "valid"}:
        failed_rules.append("Cuota sin validacion de mapeo")
    else:
        passed_rules.append("Mapeo de cuota validado")
    if not odd.collected_at:
        failed_rules.append("Cuota sin timestamp")
    else:
        price_age_minutes = round((now - odd.collected_at).total_seconds() / 60, 2)
        if odd.collected_at > now + timedelta(minutes=5):
            failed_rules.append("Timestamp de cuota en el futuro")
        elif now - odd.collected_at > max_age:
            failed_rules.append("Cuota desactualizada")
        else:
            passed_rules.append("Cuota reciente")
    quality_score = max(0.0, 100.0 - len(failed_rules) * 35.0)
    if price_age_minutes is not None and price_age_minutes > 60:
        quality_score = max(0.0, quality_score - min(35.0, (price_age_minutes - 60) / 30))
    return {
        "passed_rules": passed_rules,
        "failed_rules": failed_rules,
        "quality_score": round(quality_score, 1),
        "price_age_minutes": price_age_minutes,
    }


def _is_valid_real_odd(odd: Odds, now: datetime, max_age: timedelta) -> bool:
    return not _validate_real_odd(odd, now, max_age)["failed_rules"]


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
        "odds_validation_status": row.odds_validation_status,
        "expected_value": row.expected_value,
        "merlin_score": row.merlin_score,
        "data_quality": row.data_quality,
        "risk_level": row.risk_level,
        "decision": row.decision,
        "reason": row.reason,
        "passed_rules": row.passed_rules,
        "failed_rules": row.failed_rules,
        "filter_reasons": row.filter_reasons,
        "odds_quality_score": row.odds_quality_score,
        "price_age_minutes": row.price_age_minutes,
        "publish_blocked_by_config": row.publish_blocked_by_config,
        "publish_blocked_by_risk": row.publish_blocked_by_risk,
        "publish_blocked_by_data_quality": row.publish_blocked_by_data_quality,
        "publish_blocked_by_ev": row.publish_blocked_by_ev,
        "publish_blocked_by_odds": row.publish_blocked_by_odds,
        "safety_mode": row.safety_mode,
    }


def _base_audit() -> dict:
    return {
        "passed_rules": [],
        "failed_rules": [],
        "filter_reasons": [],
        "odds_quality_score": 0.0,
        "price_age_minutes": None,
        "publish_blocked_by_config": False,
        "publish_blocked_by_risk": False,
        "publish_blocked_by_data_quality": False,
        "publish_blocked_by_ev": False,
        "publish_blocked_by_odds": False,
        "safety_mode": "normal",
    }


def _pass(audit: dict, rule: str) -> None:
    if rule not in audit["passed_rules"]:
        audit["passed_rules"].append(rule)


def _fail(audit: dict, rule: str) -> None:
    if rule not in audit["failed_rules"]:
        audit["failed_rules"].append(rule)
    if rule not in audit["filter_reasons"]:
        audit["filter_reasons"].append(rule)


def _safety_thresholds(mode: str) -> dict:
    normalized = (mode or "normal").strip().lower()
    if normalized == "conservative":
        return {
            "mode": "conservative",
            "min_probability": 0.58,
            "min_ev": 0.06,
            "min_data_quality": 70.0,
            "min_sample": 30,
            "allowed_risk": {"low", "medium"},
        }
    if normalized == "aggressive":
        return {
            "mode": "aggressive",
            "min_probability": 0.45,
            "min_ev": 0.015,
            "min_data_quality": 40.0,
            "min_sample": 12,
            "allowed_risk": {"low", "medium", "high"},
        }
    settings = get_settings()
    return {
        "mode": "normal",
        "min_probability": settings.min_publish_probability,
        "min_ev": settings.min_publish_ev,
        "min_data_quality": settings.min_publish_data_quality,
        "min_sample": 20,
        "allowed_risk": {"low", "medium"},
    }


def _market_line_is_professional(spec: MarketSpec) -> bool:
    if spec.line is None:
        return True
    line = abs(float(spec.line))
    if spec.family == "total_goals":
        if spec.period == "first_half" and spec.team_scope == "all":
            return 0.5 <= line <= 2.5
        if spec.period == "first_half" and spec.team_scope in {"home", "away"}:
            return 0.5 <= line <= 1.5
        if spec.team_scope in {"home", "away"}:
            return 0.5 <= line <= 3.5
        return 0.5 <= line <= 4.5
    if spec.family == "asian_handicap":
        if spec.period == "first_half":
            return line <= 1.5
        return line <= 3.0
    return True
