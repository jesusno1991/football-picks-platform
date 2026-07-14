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
  expected_value?: number | null
  merlin_score: number
  data_quality: number
  risk_level: string
  decision: string
  reason: string
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
  main_probability?: number | null
  best_odds?: number | null
  confidence?: number | null
  predictions?: Prediction[]
  home_form?: Record<string, number | string | null>
  away_form?: Record<string, number | string | null>
  availability?: Record<string, string>
}

export type CalendarDay = {
  date: string
  match_count: number
  pick_count: number
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
