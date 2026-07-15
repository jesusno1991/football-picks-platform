import { useState } from 'react'
import { PredictionTable } from '../components/PredictionTable'
import { useMatches, usePredictions } from '../hooks/queries'
import { formatDateInput } from '../utils/format'

export function ArchivePage() {
  const [date, setDate] = useState(formatDateInput(new Date()))
  const { data: matches = [] } = useMatches(date)
  const { data: predictions = [] } = usePredictions(undefined, date)
  return (
    <div className="space-y-4">
      <div className="card p-5">
        <h2 className="text-2xl font-black">Archivo</h2>
        <p className="text-sm font-semibold text-slate-500">Histórico de partidos, picks y predicciones por fecha.</p>
        <input type="date" className="mt-4 rounded-lg border border-line px-3 py-2" value={date} onChange={(event) => setDate(event.target.value)} />
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        <Metric label="Partidos" value={matches.length} />
        <Metric label="Predicciones" value={predictions.length} />
        <Metric label="Picks publicados" value={predictions.filter((item) => item.status === 'published').length} />
      </div>
      <PredictionTable predictions={predictions} />
    </div>
  )
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return <div className="card p-4"><div className="text-sm font-black text-slate-500">{label}</div><div className="mt-2 text-3xl font-black">{value}</div></div>
}
