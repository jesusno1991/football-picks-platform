import { useMemo, useState } from 'react'
import { CalendarDays } from 'lucide-react'
import { MatchCard } from '../components/MatchCard'
import { MatchDetailPage } from './MatchDetailPage'
import { useMatches } from '../hooks/queries'
import { formatDateInput } from '../utils/format'

export function HomePage() {
  const [date, setDate] = useState(formatDateInput(new Date()))
  const { data: matches = [], isLoading } = useMatches(date)
  const [selectedId, setSelectedId] = useState<number | undefined>()
  const selected = selectedId ?? matches[0]?.id
  const grouped = useMemo(() => {
    return matches.reduce<Record<string, typeof matches>>((acc, match) => {
      const key = `${match.competition.country} · ${match.competition.name}`
      acc[key] = acc[key] ?? []
      acc[key].push(match)
      return acc
    }, {})
  }, [matches])

  const shiftDate = (days: number) => {
    const next = new Date(date)
    next.setDate(next.getDate() + days)
    setDate(formatDateInput(next))
  }

  return (
    <div className="grid gap-5 lg:grid-cols-[420px_1fr]">
      <section>
        <div className="card mb-4 p-4">
          <div className="flex items-center gap-2 text-lg font-black">
            <CalendarDays size={20} /> Partidos
          </div>
          <div className="mt-4 grid grid-cols-3 gap-2">
            <button className="rounded-lg border border-line px-3 py-2 font-bold" onClick={() => shiftDate(-1)}>Ayer</button>
            <button className="rounded-lg bg-brand px-3 py-2 font-bold text-white" onClick={() => setDate(formatDateInput(new Date()))}>Hoy</button>
            <button className="rounded-lg border border-line px-3 py-2 font-bold" onClick={() => shiftDate(1)}>Mañana</button>
          </div>
          <input className="mt-3 w-full rounded-lg border border-line px-3 py-2" type="date" value={date} onChange={(event) => setDate(event.target.value)} />
        </div>
        <div className="card overflow-hidden">
          {isLoading ? <div className="p-4">Cargando partidos...</div> : null}
          {Object.entries(grouped).map(([competition, rows]) => (
            <div key={competition}>
              <div className="bg-slate-100 px-4 py-2 text-sm font-black text-slate-700">{competition}</div>
              {rows.map((match) => (
                <MatchCard key={match.id} match={match} selected={match.id === selected} onSelect={setSelectedId} />
              ))}
            </div>
          ))}
        </div>
      </section>
      <section>{selected ? <MatchDetailPage matchId={selected} /> : <div className="card p-6">Selecciona un partido.</div>}</section>
    </div>
  )
}
