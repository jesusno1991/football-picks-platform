from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TeamRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_id: str
    name: str
    short_name: str | None = None
    country: str | None = None
    logo_url: str | None = None


class CompetitionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_id: str
    name: str
    country: str
    logo_url: str | None = None
    season: str
    is_active: bool


class MatchListRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_id: str
    kickoff_at: datetime
    status: str
    venue: str | None = None
    round: str | None = None
    season: str
    competition: CompetitionRead
    home_team: TeamRead
    away_team: TeamRead
    pick_count: int = 0
    main_probability: float | None = None
    best_odds: float | None = None
    confidence: float | None = None


class CalendarDayRead(BaseModel):
    date: str
    match_count: int
    pick_count: int
    published_pick_count: int
    competition_count: int


class TeamFormRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    team_id: int
    matches_sample: int
    goals_for_avg: float | None = None
    goals_against_avg: float | None = None
    corners_for_avg: float | None = None
    corners_against_avg: float | None = None
    shots_avg: float | None = None
    shots_on_target_avg: float | None = None
    possession_avg: float | None = None
    over_9_5_corners_rate: float | None = None


class PredictionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    match_id: int
    market: str
    selection: str
    line: float | None = None
    predicted_probability: float | None = None
    fair_odds: float | None = None
    available_odds: float | None = None
    expected_value: float | None = None
    confidence: float | None = None
    recommended_stake: float
    explanation: str
    feature_snapshot: str | None = None
    generated_at: datetime
    published_at: datetime | None = None
    status: str
    result: str | None = None
    profit: float | None = None
    match: MatchListRead | None = None


class MarketEvaluationRead(BaseModel):
    code: str
    family: str
    period: str
    team_scope: str
    selection: str
    line: float | None = None
    settlement_type: str
    probability_full_win: float
    probability_half_win: float
    probability_push: float
    probability_half_loss: float
    probability_full_loss: float
    model_probability: float | None = None
    fair_odds: float | None = None
    market_odds: float | None = None
    bookmaker: str | None = None
    expected_value: float | None = None
    merlin_score: float
    data_quality: float
    risk_level: str
    validation_status: str
    decision: str
    reasons: list[str]
    alerts: list[str]


class TipstrrMarketPickRead(BaseModel):
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
    line: float | None = None
    label: str
    model_probability: float | None = None
    fair_odds: float | None = None
    market_odds: float | None = None
    bookmaker: str | None = None
    expected_value: float | None = None
    merlin_score: float
    data_quality: float
    risk_level: str
    decision: str
    reason: str


class MatchDetailRead(MatchListRead):
    home_form: TeamFormRead | None = None
    away_form: TeamFormRead | None = None
    predictions: list[PredictionRead] = []


class StatisticsOverview(BaseModel):
    total_picks: int
    wins: int
    losses: int
    voids: int
    hit_rate: float
    profit: float
    yield_percentage: float
    average_odds: float
    total_stake: float
    maximum_drawdown: float


class PerformanceRow(BaseModel):
    name: str
    market: str | None = None
    sample_size: int
    wins: int
    losses: int
    voids: int
    profit: float
    yield_percentage: float
    hit_rate: float
    sample_label: str


class ProfitPoint(BaseModel):
    date: datetime
    profit: float
    cumulative_profit: float
