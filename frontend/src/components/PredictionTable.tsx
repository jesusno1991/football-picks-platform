import { useMemo, useState } from 'react'
import type { Prediction } from '../types/api'
import { formatDecimal, formatPercent, marketLabel } from '../utils/format'

type SortKey = 'probability' | 'ev' | 'odds' | 'time'

export function PredictionTable({ predictions }: { predictions: Prediction[] }) {
  const [sortKey, setSortKey] = useState<SortKey>('probability')
  const sortedPredictions = useMemo(() => {
    return [...predictions].sort((left, right) => {
      if (sortKey === 'probability') return numberValue(right.predicted_probability) - numberValue(left.predicted_probability)
      if (sortKey === 'ev') return numberValue(right.expected_value) - numberValue(left.expected_value)
      if (sortKey === 'odds') return numberValue(right.available_odds) - numberValue(left.available_odds)
      return timeValue(left) - timeValue(right)
    })
  }, [predictions, sortKey])

  return (
    <div className="card overflow-hidden">
      <div className="flex flex-wrap items-center gap-2 border-b border-line bg-white p-3 text-xs font-black">
        <span className="text-slate-500">Ordenar por:</span>
        <SortButton active={sortKey === 'probability'} onClick={() => setSortKey('probability')} label="Mayor probabilidad" />
        <SortButton active={sortKey === 'ev'} onClick={() => setSortKey('ev')} label="Mejor EV" />
        <SortButton active={sortKey === 'odds'} onClick={() => setSortKey('odds')} label="Mayor cuota" />
        <SortButton active={sortKey === 'time'} onClick={() => setSortKey('time')} label="Hora" />
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
            <tr>
              <th className="px-3 py-3">Partido</th>
              <th className="px-3 py-3">Competición</th>
              <th className="px-3 py-3"><button className="font-black uppercase" onClick={() => setSortKey('time')}>Hora</button></th>
              <th className="px-3 py-3">Mercado</th>
              <th className="px-3 py-3"><button className="font-black uppercase" onClick={() => setSortKey('probability')}>Probabilidad ↓</button></th>
              <th className="px-3 py-3">Cuota justa</th>
              <th className="px-3 py-3"><button className="font-black uppercase" onClick={() => setSortKey('odds')}>Cuota ↓</button></th>
              <th className="px-3 py-3"><button className="font-black uppercase" onClick={() => setSortKey('ev')}>EV ↓</button></th>
              <th className="px-3 py-3">Stake</th>
              <th className="px-3 py-3">Estado</th>
            </tr>
          </thead>
          <tbody>
            {sortedPredictions.map((prediction) => {
              const kickoff = prediction.match ? new Date(prediction.match.kickoff_at) : null
              const matchName = prediction.match ? `${prediction.match.home_team.name} vs ${prediction.match.away_team.name}` : `Partido #${prediction.match_id}`
              return (
                <tr key={prediction.id} className="border-t border-slate-100">
                  <td className="min-w-[260px] px-3 py-3 font-black text-slate-900">{matchName}</td>
                  <td className="min-w-[220px] px-3 py-3 text-xs font-bold text-slate-600">
                    {prediction.match ? `${prediction.match.competition.country} · ${prediction.match.competition.name}` : '-'}
                  </td>
                  <td className="px-3 py-3 font-semibold">{kickoff ? kickoff.toLocaleString('es-ES', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : '-'}</td>
                  <td className="px-3 py-3 font-bold">{predictionLabel(prediction)}</td>
                  <td className="px-3 py-3 font-black text-cyan-800">{formatPercent(prediction.predicted_probability)}</td>
                  <td className="px-3 py-3">{formatDecimal(prediction.fair_odds)}</td>
                  <td className="px-3 py-3">{formatDecimal(prediction.available_odds)}</td>
                  <td className="px-3 py-3">{formatDecimal(prediction.expected_value, 3)}</td>
                  <td className="px-3 py-3">{prediction.recommended_stake}u</td>
                  <td className="px-3 py-3">
                    <span className={`rounded-full px-2 py-1 text-xs font-bold ${prediction.status === 'published' ? 'bg-emerald-100 text-emerald-800' : 'bg-cyan-100 text-cyan-800'}`}>
                      {prediction.status === 'published' ? 'Para publicar' : prediction.status}
                    </span>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function SortButton({ active, onClick, label }: { active: boolean; onClick: () => void; label: string }) {
  return <button onClick={onClick} className={`rounded-full px-3 py-1.5 ${active ? 'bg-cyan-500 text-white' : 'border border-line bg-white text-slate-700'}`}>{label}</button>
}

function numberValue(input?: number | null) {
  return input ?? -999
}

function timeValue(prediction: Prediction) {
  return prediction.match ? new Date(prediction.match.kickoff_at).getTime() : Number.MAX_SAFE_INTEGER
}

function predictionLabel(prediction: Prediction) {
  if (prediction.feature_snapshot) {
    try {
      const snapshot = JSON.parse(prediction.feature_snapshot) as { label?: string; group?: string }
      if (snapshot.label && snapshot.group) return `${snapshot.group} · ${snapshot.label}`
      if (snapshot.label) return snapshot.label
    } catch {
      // Older predictions keep the legacy label path.
    }
  }
  return marketLabel(prediction.market, prediction.selection, prediction.line)
}
