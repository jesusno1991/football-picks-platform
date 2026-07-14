import axios from 'axios'
import type { CalendarDay, MarketEvaluation, Match, Overview, Prediction, TipstrrMarketPick } from '../types/api'

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

export async function fetchPredictions(status?: string, date?: string) {
  const response = await api.get<Prediction[]>('/api/predictions', { params: { status, date } })
  return response.data
}

export async function fetchTipstrrMarketPicks(date?: string, decision?: string) {
  const response = await api.get<TipstrrMarketPick[]>('/api/tipstrr-market-picks', { params: { date, decision } })
  return response.data
}

export async function fetchOverview() {
  const response = await api.get<Overview>('/api/statistics/overview')
  return response.data
}

export async function fetchProfitCurve() {
  const response = await api.get<{ date: string; profit: number; cumulative_profit: number }[]>('/api/statistics/profit-curve')
  return response.data
}
