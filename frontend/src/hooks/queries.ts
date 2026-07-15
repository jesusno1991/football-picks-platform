import { useQuery } from '@tanstack/react-query'
import {
  fetchAdminStatus,
  fetchCalendarMonth,
  fetchCompetition,
  fetchCompetitions,
  fetchCompetitionStandings,
  fetchLivePicks,
  fetchMatch,
  fetchMatchInfo,
  fetchMatchMarkets,
  fetchMatchOdds,
  fetchMarketRankings,
  fetchModelHealth,
  fetchMatches,
  fetchPickSafetyMode,
  fetchPredictionExport,
  fetchOverview,
  fetchPlayers,
  fetchPredictions,
  fetchProfitCurve,
  fetchReadiness,
  fetchSearch,
  fetchStandings,
  fetchSystemAlerts,
  fetchTeamDetail,
  fetchTeams,
  fetchTipstrrMarketPicks,
  fetchUltimateReport,
} from '../services/api'

export function useMatches(date: string) {
  return useQuery({ queryKey: ['matches', date], queryFn: () => fetchMatches(date) })
}

export function useCalendarMonth(year: number, month: number) {
  return useQuery({ queryKey: ['calendar-month', year, month], queryFn: () => fetchCalendarMonth(year, month) })
}

export function useMatch(id?: number) {
  return useQuery({ queryKey: ['match', id], queryFn: () => fetchMatch(id!), enabled: Boolean(id) })
}

export function useMatchMarkets(id?: number) {
  return useQuery({ queryKey: ['match-markets', id], queryFn: () => fetchMatchMarkets(id!), enabled: Boolean(id) })
}

export function useMatchInfo(id: number | undefined, section: 'statistics' | 'events' | 'lineups' | 'player-statistics' | 'h2h') {
  return useQuery({ queryKey: ['match-info', id, section], queryFn: () => fetchMatchInfo(id!, section), enabled: Boolean(id) })
}

export function useMatchOdds(id?: number) {
  return useQuery({ queryKey: ['match-odds', id], queryFn: () => fetchMatchOdds(id!), enabled: Boolean(id) })
}

export function usePredictions(status?: string, date?: string) {
  return useQuery({ queryKey: ['predictions', status ?? 'all', date ?? 'all'], queryFn: () => fetchPredictions(status, date) })
}

export function usePredictionExport(date: string, enabled: boolean) {
  return useQuery({ queryKey: ['prediction-export', date], queryFn: () => fetchPredictionExport(date), enabled })
}

export function useTipstrrMarketPicks(date: string, decision?: string, limit = 1000) {
  return useQuery({
    queryKey: ['tipstrr-market-picks', date, decision ?? 'all', limit],
    queryFn: () => fetchTipstrrMarketPicks(date, decision, limit),
  })
}

export function useLivePicks(limit = 500) {
  return useQuery({ queryKey: ['live-picks', limit], queryFn: () => fetchLivePicks(limit), refetchInterval: 60_000 })
}

export function useMarketRankings() {
  return useQuery({ queryKey: ['market-rankings'], queryFn: fetchMarketRankings })
}

export function useModelHealth() {
  return useQuery({ queryKey: ['model-health'], queryFn: fetchModelHealth })
}

export function useReadiness() {
  return useQuery({ queryKey: ['readiness'], queryFn: fetchReadiness })
}

export function usePickSafetyMode() {
  return useQuery({ queryKey: ['pick-safety-mode'], queryFn: fetchPickSafetyMode })
}

export function useSystemAlerts() {
  return useQuery({ queryKey: ['system-alerts'], queryFn: fetchSystemAlerts })
}

export function useOverview() {
  return useQuery({ queryKey: ['overview'], queryFn: fetchOverview })
}

export function useProfitCurve() {
  return useQuery({ queryKey: ['profit-curve'], queryFn: fetchProfitCurve })
}

export function useCompetitions() {
  return useQuery({ queryKey: ['competitions'], queryFn: fetchCompetitions })
}

export function useCompetition(id?: number) {
  return useQuery({ queryKey: ['competition', id], queryFn: () => fetchCompetition(id!), enabled: Boolean(id) })
}

export function useCompetitionStandings(id?: number) {
  return useQuery({ queryKey: ['competition-standings', id], queryFn: () => fetchCompetitionStandings(id!), enabled: Boolean(id) })
}

export function useTeams(q?: string) {
  return useQuery({ queryKey: ['teams', q ?? 'all'], queryFn: () => fetchTeams(q) })
}

export function useTeamDetail(id?: number) {
  return useQuery({ queryKey: ['team-detail', id], queryFn: () => fetchTeamDetail(id!), enabled: Boolean(id) })
}

export function usePlayers(q?: string) {
  return useQuery({ queryKey: ['players', q ?? 'all'], queryFn: () => fetchPlayers(q) })
}

export function useStandings(competitionId?: number) {
  return useQuery({ queryKey: ['standings', competitionId ?? 'all'], queryFn: () => fetchStandings(competitionId) })
}

export function useSearch(q: string) {
  return useQuery({ queryKey: ['search', q], queryFn: () => fetchSearch(q), enabled: q.trim().length >= 2 })
}

export function useAdminStatus() {
  return useQuery({ queryKey: ['admin-status'], queryFn: fetchAdminStatus })
}

export function useUltimateReport() {
  return useQuery({ queryKey: ['ultimate-report'], queryFn: fetchUltimateReport })
}
