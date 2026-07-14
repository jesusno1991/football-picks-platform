import { useQuery } from '@tanstack/react-query'
import { fetchCalendarMonth, fetchMatch, fetchMatches, fetchMatchMarkets, fetchOverview, fetchPredictions, fetchProfitCurve, fetchTipstrrMarketPicks } from '../services/api'

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

export function usePredictions(status?: string, date?: string) {
  return useQuery({ queryKey: ['predictions', status ?? 'all', date ?? 'all'], queryFn: () => fetchPredictions(status, date) })
}

export function useTipstrrMarketPicks(date: string, decision?: string) {
  return useQuery({
    queryKey: ['tipstrr-market-picks', date, decision ?? 'all'],
    queryFn: () => fetchTipstrrMarketPicks(date, decision),
  })
}

export function useOverview() {
  return useQuery({ queryKey: ['overview'], queryFn: fetchOverview })
}

export function useProfitCurve() {
  return useQuery({ queryKey: ['profit-curve'], queryFn: fetchProfitCurve })
}
