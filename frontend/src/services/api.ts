import axios from 'axios'
import type { Match, Overview, Prediction } from '../types/api'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '',
})

export async function fetchMatches(date?: string) {
  const response = await api.get<Match[]>('/api/matches', { params: { date } })
  return response.data
}

export async function fetchMatch(id: number) {
  const response = await api.get<Match>(`/api/matches/${id}`)
  return response.data
}

export async function fetchPredictions(status?: string, date?: string) {
  const response = await api.get<Prediction[]>('/api/predictions', { params: { status, date } })
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
