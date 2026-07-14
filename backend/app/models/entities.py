from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def now_utc() -> datetime:
    return datetime.utcnow()


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, onupdate=now_utc)


class Competition(TimestampMixin, Base):
    __tablename__ = "competitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(180), index=True)
    country: Mapped[str] = mapped_column(String(120), index=True)
    logo_url: Mapped[str | None] = mapped_column(String(500))
    season: Mapped[str] = mapped_column(String(40), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    matches: Mapped[list["Match"]] = relationship(back_populates="competition")


class Team(TimestampMixin, Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(180), index=True)
    short_name: Mapped[str | None] = mapped_column(String(80))
    country: Mapped[str | None] = mapped_column(String(120), index=True)
    logo_url: Mapped[str | None] = mapped_column(String(500))


class Match(TimestampMixin, Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    competition_id: Mapped[int] = mapped_column(ForeignKey("competitions.id"), index=True)
    home_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    away_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    kickoff_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    status: Mapped[str] = mapped_column(String(40), default="scheduled", index=True)
    home_score: Mapped[int | None] = mapped_column(Integer)
    away_score: Mapped[int | None] = mapped_column(Integer)
    home_corners: Mapped[int | None] = mapped_column(Integer)
    away_corners: Mapped[int | None] = mapped_column(Integer)
    venue: Mapped[str | None] = mapped_column(String(180))
    round: Mapped[str | None] = mapped_column(String(80))
    season: Mapped[str] = mapped_column(String(40), index=True)

    competition: Mapped[Competition] = relationship(back_populates="matches")
    home_team: Mapped[Team] = relationship(foreign_keys=[home_team_id])
    away_team: Mapped[Team] = relationship(foreign_keys=[away_team_id])
    predictions: Mapped[list["Prediction"]] = relationship(back_populates="match")


class TeamMatchStatistics(Base):
    __tablename__ = "team_match_statistics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), index=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    is_home: Mapped[bool] = mapped_column(Boolean)
    possession: Mapped[float | None] = mapped_column(Float)
    shots: Mapped[float | None] = mapped_column(Float)
    shots_on_target: Mapped[float | None] = mapped_column(Float)
    corners: Mapped[float | None] = mapped_column(Float)
    dangerous_attacks: Mapped[float | None] = mapped_column(Float)
    goals: Mapped[float | None] = mapped_column(Float)
    xg: Mapped[float | None] = mapped_column(Float)
    yellow_cards: Mapped[float | None] = mapped_column(Float)
    red_cards: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)


class TeamForm(Base):
    __tablename__ = "team_form"
    __table_args__ = (UniqueConstraint("team_id", "competition_id", "reference_date", name="uq_team_form_ref"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    competition_id: Mapped[int] = mapped_column(ForeignKey("competitions.id"), index=True)
    reference_date: Mapped[datetime] = mapped_column(DateTime, index=True)
    matches_sample: Mapped[int] = mapped_column(Integer)
    goals_for_avg: Mapped[float | None] = mapped_column(Float)
    goals_against_avg: Mapped[float | None] = mapped_column(Float)
    first_half_goals_avg: Mapped[float | None] = mapped_column(Float)
    second_half_goals_avg: Mapped[float | None] = mapped_column(Float)
    corners_for_avg: Mapped[float | None] = mapped_column(Float)
    corners_against_avg: Mapped[float | None] = mapped_column(Float)
    shots_avg: Mapped[float | None] = mapped_column(Float)
    shots_on_target_avg: Mapped[float | None] = mapped_column(Float)
    xg_avg: Mapped[float | None] = mapped_column(Float)
    xga_avg: Mapped[float | None] = mapped_column(Float)
    big_chances_avg: Mapped[float | None] = mapped_column(Float)
    dangerous_attacks_avg: Mapped[float | None] = mapped_column(Float)
    possession_avg: Mapped[float | None] = mapped_column(Float)
    over_8_5_corners_rate: Mapped[float | None] = mapped_column(Float)
    over_9_5_corners_rate: Mapped[float | None] = mapped_column(Float)
    over_10_5_corners_rate: Mapped[float | None] = mapped_column(Float)
    btts_rate: Mapped[float | None] = mapped_column(Float)
    over_1_5_goals_rate: Mapped[float | None] = mapped_column(Float)
    over_2_5_goals_rate: Mapped[float | None] = mapped_column(Float)
    over_3_5_goals_rate: Mapped[float | None] = mapped_column(Float)
    home_away_sample: Mapped[int | None] = mapped_column(Integer)
    h2h_goals_avg: Mapped[float | None] = mapped_column(Float)
    h2h_btts_rate: Mapped[float | None] = mapped_column(Float)
    clean_sheet_rate: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)


class Odds(Base):
    __tablename__ = "odds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), index=True)
    bookmaker: Mapped[str] = mapped_column(String(120), index=True)
    market: Mapped[str] = mapped_column(String(120), index=True)
    selection: Mapped[str] = mapped_column(String(120), index=True)
    line: Mapped[float | None] = mapped_column(Float)
    odds: Mapped[float] = mapped_column(Float)
    provider: Mapped[str | None] = mapped_column(String(80), index=True)
    event_id: Mapped[str | None] = mapped_column(String(120), index=True)
    fixture_id: Mapped[str | None] = mapped_column(String(120), index=True)
    provider_competition_id: Mapped[str | None] = mapped_column(String(120), index=True)
    market_family: Mapped[str | None] = mapped_column(String(80), index=True)
    market_name_raw: Mapped[str | None] = mapped_column(String(180))
    period: Mapped[str | None] = mapped_column(String(40), index=True)
    team_scope: Mapped[str | None] = mapped_column(String(40), index=True)
    raw_payload: Mapped[str | None] = mapped_column(Text)
    validation_status: Mapped[str | None] = mapped_column(String(60), default="mapped")
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, index=True)
    is_closing_odds: Mapped[bool] = mapped_column(Boolean, default=False)


class MarketDefinition(TimestampMixin, Base):
    __tablename__ = "market_definitions"
    __table_args__ = (
        UniqueConstraint(
            "family",
            "period",
            "team_scope",
            "selection",
            "line",
            "settlement_type",
            name="uq_market_definition_logic",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    family: Mapped[str] = mapped_column(String(80), index=True)
    period: Mapped[str] = mapped_column(String(40), index=True)
    team_scope: Mapped[str] = mapped_column(String(40), index=True)
    selection: Mapped[str] = mapped_column(String(80), index=True)
    line: Mapped[float | None] = mapped_column(Float)
    settlement_type: Mapped[str] = mapped_column(String(80), index=True)
    is_supported: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_publishable: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


class ModelProbability(Base):
    __tablename__ = "model_probabilities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), index=True)
    market_definition_id: Mapped[int] = mapped_column(ForeignKey("market_definitions.id"), index=True)
    probability_full_win: Mapped[float | None] = mapped_column(Float)
    probability_half_win: Mapped[float | None] = mapped_column(Float)
    probability_push: Mapped[float | None] = mapped_column(Float)
    probability_half_loss: Mapped[float | None] = mapped_column(Float)
    probability_full_loss: Mapped[float | None] = mapped_column(Float)
    model_probability: Mapped[float | None] = mapped_column(Float)
    fair_odds: Mapped[float | None] = mapped_column(Float)
    confidence: Mapped[float | None] = mapped_column(Float)
    model_name: Mapped[str] = mapped_column(String(120), default="poisson_goal_matrix_v1")
    feature_snapshot: Mapped[str | None] = mapped_column(Text)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, index=True)


class MarketEvaluation(Base):
    __tablename__ = "market_evaluations"
    __table_args__ = (UniqueConstraint("match_id", "market_definition_id", "bookmaker", name="uq_market_eval_bookmaker"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), index=True)
    fixture_id: Mapped[str | None] = mapped_column(String(120), index=True)
    market_definition_id: Mapped[int] = mapped_column(ForeignKey("market_definitions.id"), index=True)
    probability_full_win: Mapped[float | None] = mapped_column(Float)
    probability_half_win: Mapped[float | None] = mapped_column(Float)
    probability_push: Mapped[float | None] = mapped_column(Float)
    probability_half_loss: Mapped[float | None] = mapped_column(Float)
    probability_full_loss: Mapped[float | None] = mapped_column(Float)
    fair_odds: Mapped[float | None] = mapped_column(Float)
    market_odds: Mapped[float | None] = mapped_column(Float)
    expected_value: Mapped[float | None] = mapped_column(Float)
    bookmaker: Mapped[str | None] = mapped_column(String(120), index=True)
    merlin_score: Mapped[float | None] = mapped_column(Float)
    data_quality: Mapped[float | None] = mapped_column(Float)
    risk_level: Mapped[str | None] = mapped_column(String(40), index=True)
    validation_status: Mapped[str] = mapped_column(String(60), default="pending_validation", index=True)
    decision: Mapped[str] = mapped_column(String(60), default="pending_validation", index=True)
    reasons: Mapped[str | None] = mapped_column(Text)
    alerts: Mapped[str | None] = mapped_column(Text)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, index=True)


class PredictionFeature(Base):
    __tablename__ = "prediction_features"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prediction_id: Mapped[int | None] = mapped_column(ForeignKey("predictions.id"), index=True)
    market_evaluation_id: Mapped[int | None] = mapped_column(ForeignKey("market_evaluations.id"), index=True)
    features_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)


class PredictionResult(Base):
    __tablename__ = "prediction_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prediction_id: Mapped[int] = mapped_column(ForeignKey("predictions.id"), index=True)
    settlement_status: Mapped[str] = mapped_column(String(40), index=True)
    profit_units: Mapped[float | None] = mapped_column(Float)
    settled_score_home: Mapped[int | None] = mapped_column(Integer)
    settled_score_away: Mapped[int | None] = mapped_column(Integer)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime)


class SettlementRule(Base):
    __tablename__ = "settlement_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    settlement_type: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class ModelCalibration(Base):
    __tablename__ = "model_calibrations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_name: Mapped[str] = mapped_column(String(120), index=True)
    market_family: Mapped[str] = mapped_column(String(80), index=True)
    period: Mapped[str] = mapped_column(String(40), index=True)
    sample_size: Mapped[int] = mapped_column(Integer, default=0)
    brier_score: Mapped[float | None] = mapped_column(Float)
    calibration_error: Mapped[float | None] = mapped_column(Float)
    is_production_validated: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, onupdate=now_utc)


class PredictionSystem(TimestampMixin, Base):
    __tablename__ = "prediction_systems"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text)
    market: Mapped[str] = mapped_column(String(120), index=True)
    version: Mapped[str] = mapped_column(String(40), default="1.0.0")
    minimum_probability: Mapped[float] = mapped_column(Float)
    minimum_value: Mapped[float] = mapped_column(Float)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Prediction(Base):
    __tablename__ = "predictions"
    __table_args__ = (
        UniqueConstraint("match_id", "system_id", "market", "selection", "line", name="uq_prediction_market"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), index=True)
    system_id: Mapped[int] = mapped_column(ForeignKey("prediction_systems.id"), index=True)
    market: Mapped[str] = mapped_column(String(120), index=True)
    selection: Mapped[str] = mapped_column(String(120), index=True)
    line: Mapped[float | None] = mapped_column(Float)
    predicted_probability: Mapped[float | None] = mapped_column(Float)
    fair_odds: Mapped[float | None] = mapped_column(Float)
    available_odds: Mapped[float | None] = mapped_column(Float)
    expected_value: Mapped[float | None] = mapped_column(Float)
    confidence: Mapped[float | None] = mapped_column(Float)
    recommended_stake: Mapped[float] = mapped_column(Float, default=0)
    explanation: Mapped[str] = mapped_column(Text)
    feature_snapshot: Mapped[str | None] = mapped_column(Text)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    status: Mapped[str] = mapped_column(String(40), default="not_published", index=True)
    result: Mapped[str | None] = mapped_column(String(40))
    profit: Mapped[float | None] = mapped_column(Float)
    closing_odds: Mapped[float | None] = mapped_column(Float)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime)

    match: Mapped[Match] = relationship(back_populates="predictions")
    system: Mapped[PredictionSystem] = relationship()


class SystemPerformance(Base):
    __tablename__ = "system_performance"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    system_id: Mapped[int] = mapped_column(ForeignKey("prediction_systems.id"), index=True)
    competition_id: Mapped[int | None] = mapped_column(ForeignKey("competitions.id"), index=True)
    market: Mapped[str] = mapped_column(String(120), index=True)
    sample_size: Mapped[int] = mapped_column(Integer, default=0)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    losses: Mapped[int] = mapped_column(Integer, default=0)
    voids: Mapped[int] = mapped_column(Integer, default=0)
    total_stake: Mapped[float] = mapped_column(Float, default=0)
    total_profit: Mapped[float] = mapped_column(Float, default=0)
    yield_percentage: Mapped[float] = mapped_column(Float, default=0)
    hit_rate: Mapped[float] = mapped_column(Float, default=0)
    average_odds: Mapped[float] = mapped_column(Float, default=0)
    maximum_drawdown: Mapped[float] = mapped_column(Float, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, onupdate=now_utc)


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(40), default="admin")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
