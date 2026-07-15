import { CalendarDays, Search, Star, TrendingUp } from 'lucide-react'
import type React from 'react'
import { useMemo, useState } from 'react'
import { MatchCard } from '../components/MatchCard'
import { MatchDetailPage } from './MatchDetailPage'
import { useMatches, useOverview, useSearch, useTipstrrMarketPicks } from '../hooks/queries'
import { formatDateInput, formatDecimal } from '../utils/format'

export function DashboardPage() {
  const today = formatDateInput(new Date())
  const tomorrowDate = new Date()
  tomorrowDate.setDate(tomorrowDate.getDate() + 1)
  const tomorrow = formatDateInput(tomorrowDate)
  const { data: todayMatches = [] } = useMatches(today)
  const { data: tomorrowMatches = [] } = useMatches(tomorrow)
  const { data: picks = [] } = useTipstrrMarketPicks(today, 'PUBLICABLE')
  const { data: overview } = useOverview()
  const [selectedId, setSelectedId] = useState<number | undefined>()
  const [q, setQ] = useState('')
  const { data: results = [] } = useSearch(q)
  const live = todayMatches.filter((match) => ['live', '1H', '2H', 'HT'].includes(match.status))
  const selected = selectedId ?? todayMatches[0]?.id
  const grouped = useMemo(() => todayMatches.slice(0, 12), [todayMatches])

  return (
    <div className="space-y-5">
      <section className="grid gap-4 md:grid-cols-4">
        <Kpi icon={<CalendarDays size={18} />} label="Partidos hoy" value={todayMatches.length} />
        <Kpi icon={<TrendingUp size={18} />} label="Partidos manana" value={tomorrowMatches.length} />
        <Kpi icon={<Star size={18} />} label="Picks para revisar" value={picks.length} />
        <Kpi icon={<TrendingUp size={18} />} label="Yield" value={`${formatDecimal(overview?.yield_percentage ?? null, 1)}%`} />
      </section>

      <section className="card p-4">
        <div className="flex items-center gap-2">
          <Search size={18} />
          <input value={q} onChange={(event) => setQ(event.target.value)} className="w-full rounded-lg border border-line px-3 py-2" placeholder="Buscar equipo, competicion, jugador o partido..." />
        </div>
        {q.trim().length >= 2 ? (
          <div className="mt-3 grid gap-2 md:grid-cols-2">
            {results.length ? results.map((result) => (
              <div key={`${result.type}-${result.id}`} className="rounded-lg border border-line p-3">
                <div className="text-xs font-black uppercase text-cyan-700">{result.type}</div>
                <div className="font-black">{result.title}</div>
                <div className="text-sm font-semibold text-slate-500">{result.subtitle ?? 'No disponible'}</div>
              </div>
            )) : <div className="text-sm font-semibold text-slate-500">Sin resultados.</div>}
          </div>
        ) : null}
      </section>

      <section className="grid gap-5 lg:grid-cols-[420px_1fr]">
        <div className="space-y-4">
          <div className="card overflow-hidden">
            <div className="border-b border-line bg-slate-50 px-4 py-3 text-sm font-black">Partidos destacados de hoy</div>
            {grouped.length ? grouped.map((match) => <MatchCard key={match.id} match={match} selected={match.id === selected} onSelect={setSelectedId} />) : <div className="p-4 text-sm font-semibold text-slate-500">No disponible</div>}
          </div>
          <div className="card p-4">
            <h2 className="text-lg font-black">En directo</h2>
            <div className="mt-2 text-sm font-semibold text-slate-600">{live.length ? `${live.length} partidos en juego` : 'No disponible'}</div>
          </div>
        </div>
        <div>{selected ? <MatchDetailPage matchId={selected} /> : <div className="card p-6">Selecciona un partido.</div>}</div>
      </section>
    </div>
  )
}

function Kpi({ icon, label, value }: { icon: React.ReactNode; label: string; value: string | number }) {
  return (
    <div className="card p-4">
      <div className="flex items-center gap-2 text-sm font-black text-slate-500">{icon}{label}</div>
      <div className="mt-2 text-3xl font-black">{value}</div>
    </div>
  )
}
