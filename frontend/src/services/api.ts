import axios from 'axios'
import type {
  AdminStatus,
  CalendarDay,
  Competition,
  CompetitionDetail,
  GenericInfo,
  LiveMatchCenterRow,
  MarketEvaluation,
  MarketRanking,
  ModelHealth,
  Match,
  OddsRow,
  Overview,
  PickSafetyMode,
  Prediction,
  PredictionExportResponse,
  Readiness,
  SearchResult,
  StandingRow,
  SystemAlert,
  Team,
  TeamDetail,
  TipstrrMarketPick,
} from '../types/api'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '',
})

export async function fetchMatches(date?: string) {
  const response = await api.get<Match[]>('/api/matches', { params: { date } })
  return response.data
}

export async function fetchMatchesRange(dateFrom: string, dateTo: string) {
  const response = await api.get<Match[]>('/api/matches/range', { params: { date_from: dateFrom, date_to: dateTo } })
  return response.data
}

export async function fetchCalendarMonth(year: number, month: number) {
  const response = await api.get<CalendarDay[]>('/api/calendar/month', { params: { year, month } })
  return response.data
}

export async function fetchMatch(id: number) {
  const response = await api.get<Match>(`/api/matches/${id}`)
  return response.data
}

export async function fetchMatchMarkets(id: number) {
  const response = await api.get<MarketEvaluation[]>(`/api/matches/${id}/markets`)
  return response.data
}

export async function fetchMatchInfo(id: number, section: 'statistics' | 'events' | 'lineups' | 'player-statistics' | 'h2h') {
  const response = await api.get<GenericInfo>(`/api/matches/${id}/${section}`)
  return response.data
}

export async function fetchMatchOdds(id: number) {
  const response = await api.get<OddsRow[]>(`/api/matches/${id}/odds`)
  return response.data
}

export async function fetchPredictions(status?: string, date?: string) {
  const response = await api.get<Prediction[]>('/api/predictions', { params: { status, date } })
  return response.data
}

export async function fetchPredictionExport(date: string) {
  const response = await api.get<PredictionExportResponse>('/api/predictions/export', { params: { date, refresh: true } })
  return response.data
}

export async function fetchTipstrrMarketPicks(date?: string, decision?: string, limit = 1000) {
  const response = await api.get<TipstrrMarketPick[]>('/api/tipstrr-market-picks', { params: { date, decision, limit } })
  return response.data
}

export async function fetchLivePicks(limit = 500) {
  const response = await api.get<TipstrrMarketPick[]>('/api/live-picks', { params: { limit } })
  return response.data
}

export async function fetchLiveMatchCenter(limit = 100) {
  const response = await api.get<LiveMatchCenterRow[]>('/api/live-match-center', { params: { limit } })
  return response.data
}

export async function fetchMarketRankings() {
  const response = await api.get<MarketRanking[]>('/api/market-rankings')
  return response.data
}

export async function fetchOverview() {
  const response = await api.get<Overview>('/api/statistics/overview')
  return response.data
}

export async function fetchCompetitions() {
  const response = await api.get<Competition[]>('/api/competitions')
  return response.data
}

export async function fetchCompetition(id: number) {
  const response = await api.get<CompetitionDetail>(`/api/competitions/${id}`)
  return response.data
}

export async function fetchCompetitionStandings(id: number) {
  const response = await api.get<StandingRow[]>(`/api/competitions/${id}/standings`)
  return response.data
}

export async function fetchTeams(q?: string) {
  const response = await api.get<Team[]>('/api/teams', { params: { q } })
  return response.data
}

export async function fetchTeamDetail(id: number) {
  const response = await api.get<TeamDetail>(`/api/teams/${id}/detail`)
  return response.data
}

export async function fetchPlayers(q?: string) {
  const response = await api.get<Record<string, unknown>[]>('/api/players', { params: { q } })
  return response.data
}

export async function fetchStandings(competitionId?: number) {
  const response = await api.get<StandingRow[]>('/api/standings', { params: { competition_id: competitionId } })
  return response.data
}

export async function fetchSearch(q: string) {
  const response = await api.get<SearchResult[]>('/api/search', { params: { q } })
  return response.data
}

export async function fetchAdminStatus() {
  const response = await api.get<AdminStatus>('/api/admin/status')
  return response.data
}

export async function fetchModelHealth() {
  const response = await api.get<ModelHealth>('/api/model-health')
  return response.data
}

export async function fetchReadiness() {
  const response = await api.get<Readiness>('/api/readiness')
  return response.data
}

export async function fetchPickSafetyMode() {
  const response = await api.get<PickSafetyMode>('/api/pick-safety-mode')
  return response.data
}

export async function fetchSystemAlerts() {
  const response = await api.get<SystemAlert[]>('/api/system-alerts')
  return response.data
}

export async function fetchUltimateReport() {
  const response = await api.get<Record<string, unknown>>('/api/admin/ultimate-report')
  return response.data
}

export async function fetchProfitCurve() {
  const response = await api.get<{ date: string; profit: number; cumulative_profit: number }[]>('/api/statistics/profit-curve')
  return response.data
}

export async function runAdminAction(path: string, token: string, params?: Record<string, string | number | undefined>) {
  const response = await api.post<Record<string, unknown>>(path, null, {
    params,
    headers: { 'X-Admin-Token': token },
  })
  return response.data
}
