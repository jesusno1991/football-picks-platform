export type Team = {
  id: number
  external_id: string
  name: string
  short_name?: string | null
  country?: string | null
  logo_url?: string | null
}

export type Competition = {
  id: number
  external_id: string
  name: string
  country: string
  season: string
  logo_url?: string | null
}

export type Prediction = {
  id: number
  match_id: number
  market: string
  selection: string
  line?: number | null
  predicted_probability?: number | null
  fair_odds?: number | null
  available_odds?: number | null
  expected_value?: number | null
  confidence?: number | null
  recommended_stake: number
  explanation: string
  feature_snapshot?: string | null
  status: string
  result?: string | null
  profit?: number | null
  match?: Match | null
}

export type MarketEvaluation = {
  code: string
  family: string
  period: string
  team_scope: string
  selection: string
  line?: number | null
  settlement_type: string
  probability_full_win: number
  probability_half_win: number
  probability_push: number
  probability_half_loss: number
  probability_full_loss: number
  model_probability?: number | null
  fair_odds?: number | null
  market_odds?: number | null
  bookmaker?: string | null
  expected_value?: number | null
  merlin_score: number
  data_quality: number
  risk_level: string
  validation_status: string
  decision: string
  reasons: string[]
  alerts: string[]
}

export type TipstrrMarketPick = {
  match_id: number
  external_id: string
  match_name: string
  competition_name: string
  country: string
  kickoff_at: string
  kickoff_local_date: string
  match_status: string
  group: string
  family: string
  period: string
  team_scope: string
  selection: string
  line?: number | null
  label: string
  model_probability?: number | null
  fair_odds?: number | null
  market_odds?: number | null
  bookmaker?: string | null
  odds_collected_at?: string | null
  odds_validation_status?: string | null
  expected_value?: number | null
  merlin_score: number
  data_quality: number
  risk_level: string
  decision: string
  reason: string
  passed_rules: string[]
  failed_rules: string[]
  filter_reasons: string[]
  odds_quality_score: number
  price_age_minutes?: number | null
  publish_blocked_by_config: boolean
  publish_blocked_by_risk: boolean
  publish_blocked_by_data_quality: boolean
  publish_blocked_by_ev: boolean
  publish_blocked_by_odds: boolean
  safety_mode: string
}

export type PredictionExportDiagnostics = {
  matches_found: number
  future_matches: number
  matches_with_recent_odds: number
  matches_evaluated: number
  discard_reasons: Record<string, number>
  max_odds_age_hours: number
  refresh_status?: string
  refresh_error?: string | null
}

export type PredictionExportResponse = {
  export_type: string
  date: string
  generated_at: string
  timezone: string
  diagnostics: PredictionExportDiagnostics
  publicable_picks: TipstrrMarketPick[]
  market_evaluations: TipstrrMarketPick[]
}

export type Match = {
  id: number
  external_id: string
  kickoff_at: string
  status: string
  home_score?: number | null
  away_score?: number | null
  venue?: string | null
  round?: string | null
  season: string
  competition: Competition
  home_team: Team
  away_team: Team
  pick_count: number
  publishable_pick_count: number
  main_probability?: number | null
  best_odds?: number | null
  confidence?: number | null
  best_market?: string | null
  merlin_score?: number | null
  data_quality_score?: number | null
  has_statistics: boolean
  has_lineups: boolean
  has_odds: boolean
  has_prediction: boolean
  has_pick: boolean
  predictions?: Prediction[]
  home_form?: Record<string, number | string | null>
  away_form?: Record<string, number | string | null>
  availability?: Record<string, string>
}

export type CalendarDay = {
  date: string
  match_count: number
  pick_count: number
  publishable_pick_count: number
  published_pick_count: number
  competition_count: number
}

export type Overview = {
  total_picks: number
  wins: number
  losses: number
  voids: number
  hit_rate: number
  profit: number
  yield_percentage: number
  average_odds: number
  total_stake: number
  maximum_drawdown: number
}

export type GenericInfo = {
  available: boolean
  message: string
  rows: Record<string, unknown>[]
}

export type OddsRow = {
  bookmaker: string
  market: string
  selection: string
  line?: number | null
  odds: number
  provider?: string | null
  period?: string | null
  team_scope?: string | null
  collected_at?: string | null
}

export type TeamDetail = Team & {
  recent_matches: Match[]
  upcoming_matches: Match[]
  form?: Record<string, number | string | null> | null
  injuries: GenericInfo
  squad: GenericInfo
  statistics: Record<string, number | string | null>
}

export type CompetitionDetail = Competition & {
  match_count: number
  teams_count: number
  next_matches: Match[]
  recent_results: Match[]
  standings_available: boolean
  picks_count: number
}

export type StandingRow = {
  rank?: number | null
  team_id?: number | null
  team_name: string
  played?: number | null
  wins?: number | null
  draws?: number | null
  losses?: number | null
  goals_for?: number | null
  goals_against?: number | null
  goal_difference?: number | null
  points?: number | null
  form?: string | null
  group_name?: string | null
  source_provider?: string | null
}

export type SearchResult = {
  type: string
  id: number
  title: string
  subtitle?: string | null
  url: string
}

export type AdminStatus = {
  active_provider: string
  api_football_configured: boolean
  flashscore_configured: boolean
  matches: number
  competitions: number
  teams: number
  players: number
  standings_rows: number
  raw_responses: number
  mappings_unmatched: number
  referees: number
  squad_members: number
  team_season_statistics: number
  player_season_statistics: number
  data_quality_snapshots: number
  cache_entries: number
  model_audit_logs: number
  market_rankings: number
  publication_queue: number
  automation_runs: number
  historical_sync_windows: number
  calibration_runs: number
  provider_data_coverage: number
  latest_sync_jobs: Record<string, unknown>[]
  api_usage: Record<string, unknown>[]
}

export type ModelHealth = {
  status: string
  data_status: string
  active_provider: string
  api_football_configured: boolean
  flashscore_configured: boolean
  last_sync_at?: string | null
  next_sync_hint: string
  matches_downloaded: number
  matches_analyzed: number
  markets_evaluated: number
  candidate_picks: number
  rejected_picks: number
  publishable_picks: number
  average_calculation_time_ms?: number | null
  recent_errors: Record<string, unknown>[]
  unmapped_entities: number
  matches_without_odds: number
  matches_without_statistics: number
  incomplete_competitions: number
  api_usage: Record<string, unknown>[]
  rate_limits: Record<string, unknown>[]
}

export type ReadinessCheck = {
  name: string
  ok: boolean
  detail: string
}

export type Readiness = {
  status: 'ready' | 'degraded' | 'blocked'
  provider: string
  generated_at: string
  checks: ReadinessCheck[]
  actions: string[]
  metrics: Record<string, number>
}

export type PickSafetyMode = {
  mode: 'conservative' | 'normal' | 'aggressive'
  available_modes: string[]
  description: Record<string, string>
}

export type SystemAlert = {
  level: 'ok' | 'info' | 'warning' | 'critical'
  title: string
  message: string
  action: string
}

export type LiveMatchCenterRow = {
  match_id: number
  external_id: string
  match_name: string
  competition: string
  country: string
  live_data_source: string
  status: string
  minute: number
  score: { home?: number | null; away?: number | null }
  teams: { home: string; away: string }
  stats: {
    home: Record<string, number | null>
    away: Record<string, number | null>
  }
  momentum: {
    home_pressure: number
    away_pressure: number
    total_pressure: number
    leader: string
    pressure_gap: number
    temperature: string
  }
  top_signal: {
    label: string
    market: string
    confidence: number
    priority: number
    reason: string
  }
  recent_events: { minute?: number | null; type: string; detail?: string | null; team?: string | null }[]
  picks: {
    live_value: number
    watch: number
    total: number
    best?: Record<string, unknown> | null
  }
}

export type MarketRanking = {
  prediction_id: number
  match_id: number
  market: string
  selection: string
  line?: number | null
  rank_score: number
  grade: string
  publish_decision: string
  expected_value?: number | null
  confidence?: number | null
  probability?: number | null
  ranked_at: string
}
