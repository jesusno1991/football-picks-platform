import { useQuery } from '@tanstack/react-query'
import { fetchMatch, fetchMatches, fetchOverview, fetchPredictions, fetchProfitCurve } from '../services/api'

export function useMatches(date: string) {
  return useQuery({ queryKey: ['matches', date], queryFn: () => fetchMatches(date) })
}

export function useMatch(id?: number) {
  return useQuery({ queryKey: ['match', id], queryFn: () => fetchMatch(id!), enabled: Boolean(id) })
}

export function usePredictions() {
  return useQuery({ queryKey: ['predictions'], queryFn: fetchPredictions })
}

export function useOverview() {
  return useQuery({ queryKey: ['overview'], queryFn: fetchOverview })
}

export function useProfitCurve() {
  return useQuery({ queryKey: ['profit-curve'], queryFn: fetchProfitCurve })
}
