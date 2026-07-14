import { useQuery } from '@tanstack/react-query'
import { fetchMatch, fetchMatches, fetchMatchMarkets, fetchOverview, fetchPredictions, fetchProfitCurve } from '../services/api'

export function useMatches(date: string) {
  return useQuery({ queryKey: ['matches', date], queryFn: () => fetchMatches(date) })
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

export function useOverview() {
  return useQuery({ queryKey: ['overview'], queryFn: fetchOverview })
}

export function useProfitCurve() {
  return useQuery({ queryKey: ['profit-curve'], queryFn: fetchProfitCurve })
}
