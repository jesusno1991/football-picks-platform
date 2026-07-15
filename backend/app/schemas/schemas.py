from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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
    home_score: int | None = None
    away_score: int | None = None
    venue: str | None = None
    round: str | None = None
    season: str
    competition: CompetitionRead
    home_team: TeamRead
    away_team: TeamRead
    pick_count: int = 0
    publishable_pick_count: int = 0
    main_probability: float | None = None
    best_odds: float | None = None
    confidence: float | None = None
    best_market: str | None = None
    merlin_score: float | None = None
    data_quality_score: float | None = None
    has_statistics: bool = False
    has_lineups: bool = False
    has_odds: bool = False
    has_prediction: bool = False
    has_pick: bool = False


class CalendarDayRead(BaseModel):
    date: str
    match_count: int
    pick_count: int
    publishable_pick_count: int = 0
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
    kickoff_local_date: str
    match_status: str
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
    odds_collected_at: datetime | None = None
    odds_validation_status: str | None = None
    expected_value: float | None = None
    merlin_score: float
    data_quality: float
    risk_level: str
    decision: str
    reason: str


class MatchDetailRead(MatchListRead):
    home_form: TeamFormRead | None = None
    away_form: TeamFormRead | None = None
    predictions: list[PredictionRead] = Field(default_factory=list)
    availability: dict[str, str] = Field(default_factory=dict)


class DataAvailabilityRead(BaseModel):
    status: str
    message: str = "No disponible"


class GenericInfoRead(BaseModel):
    available: bool
    message: str = "No disponible"
    rows: list[dict] = Field(default_factory=list)


class OddsRead(BaseModel):
    bookmaker: str
    market: str
    selection: str
    line: float | None = None
    odds: float
    provider: str | None = None
    period: str | None = None
    team_scope: str | None = None
    collected_at: datetime | None = None


class TeamDetailRead(TeamRead):
    recent_matches: list[MatchListRead] = Field(default_factory=list)
    upcoming_matches: list[MatchListRead] = Field(default_factory=list)
    form: TeamFormRead | None = None
    injuries: GenericInfoRead
    squad: GenericInfoRead
    statistics: dict[str, float | int | str | None] = Field(default_factory=dict)


class CompetitionDetailRead(CompetitionRead):
    match_count: int
    teams_count: int
    next_matches: list[MatchListRead] = Field(default_factory=list)
    recent_results: list[MatchListRead] = Field(default_factory=list)
    standings_available: bool = False
    picks_count: int = 0


class StandingRowRead(BaseModel):
    rank: int | None = None
    team_id: int | None = None
    team_name: str
    played: int | None = None
    wins: int | None = None
    draws: int | None = None
    losses: int | None = None
    goals_for: int | None = None
    goals_against: int | None = None
    goal_difference: int | None = None
    points: int | None = None
    form: str | None = None
    group_name: str | None = None
    source_provider: str | None = None


class SearchResultRead(BaseModel):
    type: str
    id: int
    title: str
    subtitle: str | None = None
    url: str


class AdminStatusRead(BaseModel):
    active_provider: str
    api_football_configured: bool
    flashscore_configured: bool
    matches: int
    competitions: int
    teams: int
    players: int
    standings_rows: int
    raw_responses: int
    mappings_unmatched: int
    referees: int = 0
    squad_members: int = 0
    team_season_statistics: int = 0
    player_season_statistics: int = 0
    data_quality_snapshots: int = 0
    cache_entries: int = 0
    model_audit_logs: int = 0
    market_rankings: int = 0
    publication_queue: int = 0
    automation_runs: int = 0
    historical_sync_windows: int = 0
    calibration_runs: int = 0
    provider_data_coverage: int = 0
    latest_sync_jobs: list[dict] = Field(default_factory=list)
    api_usage: list[dict] = Field(default_factory=list)


class ModelHealthRead(BaseModel):
    status: str
    data_status: str
    active_provider: str
    api_football_configured: bool
    flashscore_configured: bool
    last_sync_at: datetime | None = None
    next_sync_hint: str
    matches_downloaded: int
    matches_analyzed: int
    markets_evaluated: int
    candidate_picks: int
    rejected_picks: int
    publishable_picks: int
    average_calculation_time_ms: float | None = None
    recent_errors: list[dict] = Field(default_factory=list)
    unmapped_entities: int
    matches_without_odds: int
    matches_without_statistics: int
    incomplete_competitions: int
    api_usage: list[dict] = Field(default_factory=list)
    rate_limits: list[dict] = Field(default_factory=list)


class MarketRankingRead(BaseModel):
    prediction_id: int
    match_id: int
    market: str
    selection: str
    line: float | None = None
    rank_score: float
    grade: str
    publish_decision: str
    expected_value: float | None = None
    confidence: float | None = None
    probability: float | None = None
    ranked_at: str


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
