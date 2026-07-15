export function formatPercent(value?: number | null) {
  if (value === null || value === undefined) return '-'
  return `${Math.round(value * 100)}%`
}

export function formatDecimal(value?: number | null, digits = 2) {
  if (value === null || value === undefined) return '-'
  return value.toFixed(digits)
}

export function formatDateInput(date: Date) {
  return date.toISOString().slice(0, 10)
}

export function marketLabel(market: string, selection?: string, line?: number | null) {
  if (market === 'corners' && selection === 'over') return `Más de ${line} córners`
  if (market === 'goals' && selection === 'over') return `Más de ${line} goles`
  if (market === 'btts' && selection === 'yes') return 'Ambos equipos marcan'
  return market
}
