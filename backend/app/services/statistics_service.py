from itertools import accumulate

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Competition, Match, Prediction, PredictionSystem
from app.schemas.schemas import PerformanceRow, ProfitPoint, StatisticsOverview


def sample_label(sample_size: int) -> str:
    if sample_size < 20:
        return "muestra insuficiente"
    if sample_size < 50:
        return "muestra preliminar"
    if sample_size < 100:
        return "muestra moderada"
    return "muestra relevante"


def overview(db: Session) -> StatisticsOverview:
    picks = list(db.scalars(select(Prediction).where(Prediction.status == "published")))
    settled = [p for p in picks if p.result in {"win", "loss", "void"}]
    wins = sum(1 for p in settled if p.result == "win")
    losses = sum(1 for p in settled if p.result == "loss")
    voids = sum(1 for p in settled if p.result == "void")
    stake = sum(float(p.recommended_stake or 0) for p in settled)
    profit = round(sum(float(p.profit or 0) for p in settled), 2)
    odds = [float(p.available_odds or 0) for p in picks if p.available_odds]
    return StatisticsOverview(
        total_picks=len(picks),
        wins=wins,
        losses=losses,
        voids=voids,
        hit_rate=round(wins / (wins + losses) * 100, 2) if wins + losses else 0,
        profit=profit,
        yield_percentage=round(profit / stake * 100, 2) if stake else 0,
        average_odds=round(sum(odds) / len(odds), 2) if odds else 0,
        total_stake=stake,
        maximum_drawdown=maximum_drawdown([float(p.profit or 0) for p in settled]),
    )


def performance_by_system(db: Session) -> list[PerformanceRow]:
    systems = list(db.scalars(select(PredictionSystem)))
    return [_performance_row(system.name, system.market, [p for p in system_predictions(db, system.id)]) for system in systems]


def performance_by_market(db: Session) -> list[PerformanceRow]:
    rows = []
    markets = {p.market for p in db.scalars(select(Prediction))}
    for market in markets:
        rows.append(_performance_row(market, market, list(db.scalars(select(Prediction).where(Prediction.market == market)))))
    return rows


def performance_by_competition(db: Session) -> list[PerformanceRow]:
    rows = []
    for competition in db.scalars(select(Competition)):
        picks = list(
            db.scalars(
                select(Prediction)
                .join(Match, Prediction.match_id == Match.id)
                .where(Match.competition_id == competition.id)
            )
        )
        rows.append(_performance_row(competition.name, None, picks))
    return rows


def profit_curve(db: Session) -> list[ProfitPoint]:
    settled = list(
        db.scalars(select(Prediction).where(Prediction.result.in_(["win", "loss", "void"])).order_by(Prediction.verified_at, Prediction.generated_at))
    )
    cumulative = list(accumulate(float(p.profit or 0) for p in settled))
    return [
        ProfitPoint(date=p.verified_at or p.generated_at, profit=float(p.profit or 0), cumulative_profit=round(cumulative[index], 2))
        for index, p in enumerate(settled)
    ]


def maximum_drawdown(profits: list[float]) -> float:
    peak = 0.0
    current = 0.0
    max_dd = 0.0
    for profit in profits:
        current += profit
        peak = max(peak, current)
        max_dd = min(max_dd, current - peak)
    return round(abs(max_dd), 2)


def system_predictions(db: Session, system_id: int) -> list[Prediction]:
    return list(db.scalars(select(Prediction).where(Prediction.system_id == system_id)))


def _performance_row(name: str, market: str | None, picks: list[Prediction]) -> PerformanceRow:
    settled = [p for p in picks if p.result in {"win", "loss", "void"}]
    wins = sum(1 for p in settled if p.result == "win")
    losses = sum(1 for p in settled if p.result == "loss")
    voids = sum(1 for p in settled if p.result == "void")
    stake = sum(float(p.recommended_stake or 0) for p in settled)
    profit = round(sum(float(p.profit or 0) for p in settled), 2)
    return PerformanceRow(
        name=name,
        market=market,
        sample_size=len(settled),
        wins=wins,
        losses=losses,
        voids=voids,
        profit=profit,
        yield_percentage=round(profit / stake * 100, 2) if stake else 0,
        hit_rate=round(wins / (wins + losses) * 100, 2) if wins + losses else 0,
        sample_label=sample_label(len(settled)),
    )
