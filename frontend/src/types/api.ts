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
