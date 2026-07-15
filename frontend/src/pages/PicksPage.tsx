import { useState } from 'react'
import { PredictionTable } from '../components/PredictionTable'
import { usePredictions, useTipstrrMarketPicks } from '../hooks/queries'
import type { TipstrrMarketPick } from '../types/api'
import { formatDateInput, formatDecimal, formatPercent } from '../utils/format'

function dateFromUrl() {
  const params = new URLSearchParams(window.location.search)
  const value = params.get('date')
  return value && /^\d{4}-\d{2}-\d{2}$/.test(value) ? value : formatDateInput(new Date())
}

export function PicksPage({ onlyPublishable = false }: { onlyPublishable?: boolean }) {
  const [date, setDateState] = useState(dateFromUrl)
  const { data: predictions = [], isLoading: predictionsLoading } = usePredictions(undefined, date)
  const { data: publicablePicks = [], isLoading: picksLoading } = useTipstrrMarketPicks(date, 'PUBLICABLE')
  const { data: allMarketRows = [] } = useTipstrrMarketPicks(date)
  const isLoading = onlyPublishable ? picksLoading : predictionsLoading
  const data = onlyPublishable ? publicablePicks : predictions

  const setDate = (nextDate: string) => {
    setDateState(nextDate)
    window.history.pushState({}, '', `${onlyPublishable ? '/picks' : '/predictions'}?date=${nextDate}`)
  }

  const shiftDate = (days: number) => {
    const next = new Date(`${date}T12:00:00`)
    next.setDate(next.getDate() + days)
    setDate(formatDateInput(next))
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-2xl font-black">{onlyPublishable ? 'Picks para publicar' : 'Predicciones'}</h1>
          <p className="text-sm font-semibold text-slate-500">
            {onlyPublishable
              ? 'Solo aparecen las señales validas para publicar. Over 1.5 y Over 2.5 estan bloqueados.'
              : 'Predicciones generadas antes del inicio, incluyendo candidatos y descartes.'}
          </p>
        </div>
        <div className="card flex flex-wrap items-center gap-2 p-2">
          <button className="rounded-lg border border-line px-3 py-2 text-sm font-bold" onClick={() => shiftDate(-1)}>Ayer</button>
          <button className="rounded-lg bg-brand px-3 py-2 text-sm font-bold text-white" onClick={() => setDate(formatDateInput(new Date()))}>Hoy</button>
          <button className="rounded-lg border border-line px-3 py-2 text-sm font-bold" onClick={() => shiftDate(1)}>Mañana</button>
          <input className="rounded-lg border border-line px-3 py-2 text-sm font-bold" type="date" value={date} onChange={(event) => setDate(event.target.value)} />
        </div>
      </div>
      {isLoading ? <div className="card p-4 font-bold text-slate-600">Cargando datos reales de la fecha...</div> : null}
      {!isLoading && data.length === 0 ? (
        <div className="card p-5 text-sm font-semibold text-slate-600">
          {onlyPublishable
            ? `No hay picks publicables en esta fecha. Candidatos analizados: ${allMarketRows.length}.`
            : 'No hay predicciones generadas para esta fecha.'}
        </div>
      ) : onlyPublishable ? <MarketPickTable picks={publicablePicks} /> : <PredictionTable predictions={predictions} />}
    </div>
  )
}

function MarketPickTable({ picks }: { picks: TipstrrMarketPick[] }) {
  const [sortKey, setSortKey] = useState<'probability' | 'ev' | 'merlin' | 'odds'>('probability')
  const sortedPicks = [...picks].sort((left, right) => {
    if (sortKey === 'probability') return value(right.model_probability) - value(left.model_probability)
    if (sortKey === 'ev') return value(right.expected_value) - value(left.expected_value)
    if (sortKey === 'merlin') return value(right.merlin_score) - value(left.merlin_score)
    return value(right.market_odds) - value(left.market_odds)
  })

  return (
    <div className="card overflow-hidden">
      <div className="flex flex-wrap items-center gap-2 border-b border-line bg-white p-3 text-xs font-black">
        <span className="text-slate-500">Ordenar por:</span>
        <SortButton active={sortKey === 'probability'} onClick={() => setSortKey('probability')} label="Mayor probabilidad" />
        <SortButton active={sortKey === 'ev'} onClick={() => setSortKey('ev')} label="Mejor EV" />
        <SortButton active={sortKey === 'merlin'} onClick={() => setSortKey('merlin')} label="Merlin Score" />
        <SortButton active={sortKey === 'odds'} onClick={() => setSortKey('odds')} label="Mayor cuota" />
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
            <tr>
              <th className="px-3 py-3">Partido</th>
              <th className="px-3 py-3">Mercado</th>
              <th className="px-3 py-3"><button className="font-black uppercase" onClick={() => setSortKey('probability')}>Prob. ↓</button></th>
              <th className="px-3 py-3">Cuota justa</th>
              <th className="px-3 py-3"><button className="font-black uppercase" onClick={() => setSortKey('odds')}>Cuota ↓</button></th>
              <th className="px-3 py-3"><button className="font-black uppercase" onClick={() => setSortKey('ev')}>EV ↓</button></th>
              <th className="px-3 py-3"><button className="font-black uppercase" onClick={() => setSortKey('merlin')}>Merlin ↓</button></th>
              <th className="px-3 py-3">Riesgo</th>
              <th className="px-3 py-3">Motivo</th>
            </tr>
          </thead>
          <tbody>
            {sortedPicks.map((pick, index) => (
              <tr key={`${pick.match_id}-${pick.family}-${pick.period}-${pick.team_scope}-${pick.selection}-${pick.line ?? 'nl'}-${index}`} className="border-t border-slate-100">
                <td className="px-3 py-3">
                  <div className="font-black">{pick.match_name}</div>
                  <div className="text-xs font-semibold text-slate-500">{pick.country} · {pick.competition_name}</div>
                </td>
                <td className="px-3 py-3">
                  <div className="font-black">{pick.label}</div>
                  <div className="text-xs font-semibold text-slate-500">{pick.period} · {pick.team_scope}</div>
                </td>
                <td className="px-3 py-3 font-black text-cyan-800">{formatPercent(pick.model_probability)}</td>
                <td className="px-3 py-3">{formatDecimal(pick.fair_odds, 2)}</td>
                <td className="px-3 py-3 font-black">{formatDecimal(pick.market_odds, 2)}</td>
                <td className="px-3 py-3 font-black text-emerald-700">{formatDecimal(pick.expected_value, 3)}</td>
                <td className="px-3 py-3 font-black">{formatDecimal(pick.merlin_score, 1)}</td>
                <td className="px-3 py-3">{pick.risk_level}</td>
                <td className="px-3 py-3">{pick.reason}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function SortButton({ active, onClick, label }: { active: boolean; onClick: () => void; label: string }) {
  return <button onClick={onClick} className={`rounded-full px-3 py-1.5 ${active ? 'bg-cyan-500 text-white' : 'border border-line bg-white text-slate-700'}`}>{label}</button>
}

function value(input?: number | null) {
  return input ?? -999
}
