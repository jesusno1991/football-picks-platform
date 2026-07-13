import { useState } from 'react'
import { PredictionTable } from '../components/PredictionTable'
import { usePredictions } from '../hooks/queries'
import { formatDateInput } from '../utils/format'

export function PicksPage({ onlyPublishable = false }: { onlyPublishable?: boolean }) {
  const [date, setDate] = useState(formatDateInput(new Date()))
  const { data = [], isLoading } = usePredictions(onlyPublishable ? 'published' : undefined, date)

  const shiftDate = (days: number) => {
    const next = new Date(date)
    next.setDate(next.getDate() + days)
    setDate(formatDateInput(next))
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-2xl font-black">{onlyPublishable ? 'Picks para publicar' : 'Picks prepartido'}</h1>
          <p className="text-sm font-semibold text-slate-500">
            {onlyPublishable
              ? 'Solo aparecen las señales que el sistema ha marcado como publicables.'
              : 'Señales generadas antes del inicio, incluyendo candidatos y descartes.'}
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
          {onlyPublishable ? 'No hay picks marcados para publicar en esta fecha.' : 'No hay picks generados para esta fecha.'}
        </div>
      ) : (
        <PredictionTable predictions={data} />
      )}
    </div>
  )
}
