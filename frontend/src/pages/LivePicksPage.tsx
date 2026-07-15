import { useMemo, useState } from 'react'
import { Activity, Flame, RefreshCcw, Target } from 'lucide-react'
import { useLiveMatchCenter, useLivePicks } from '../hooks/queries'
import type { LiveMatchCenterRow, TipstrrMarketPick } from '../types/api'
import { formatDecimal, formatPercent } from '../utils/format'

export function LivePicksPage() {
  const [decision, setDecision] = useState('Todos')
  const [search, setSearch] = useState('')
  const { data: matches = [], isLoading, error, refetch, isFetching } = useLiveMatchCenter(100)
  const { data: marketRows = [] } = useLivePicks(500)

  const filteredMatches = useMemo(() => {
    const normalized = search.trim().toLowerCase()
    return matches.filter((row) => {
      const matchesSearch =
        !normalized ||
        row.match_name.toLowerCase().includes(normalized) ||
        row.competition.toLowerCase().includes(normalized) ||
        row.top_signal.label.toLowerCase().includes(normalized)
      const matchesDecision =
        decision === 'Todos' ||
        (decision === 'LIVE_VALUE' && row.picks.live_value > 0) ||
        (decision === 'WATCH' && row.picks.watch > 0) ||
        (decision === 'SIN_CUOTA' && row.picks.total > 0 && row.picks.live_value === 0)
      return matchesSearch && matchesDecision
    })
  }, [matches, decision, search])

  const hotCount = matches.filter((row) => row.momentum.temperature === 'Muy caliente').length
  const liveValueCount = matches.reduce((total, row) => total + row.picks.live_value, 0)
  const withStatsCount = matches.filter((row) => hasAnyStats(row)).length

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-2xl font-black">Picks Live</h1>
          <p className="text-sm font-semibold text-slate-500">
            Centro live por partido: marcador, presión, ritmo, estadísticas y señales. Separado de prepartido.
          </p>
        </div>
        <button
          className="inline-flex items-center gap-2 rounded-full bg-cyan-500 px-4 py-2 text-sm font-black text-white disabled:opacity-60"
          disabled={isFetching}
          onClick={() => refetch()}
        >
          <RefreshCcw size={16} />
          Actualizar directo
        </button>
      </div>

      <section className="grid gap-3 md:grid-cols-4">
        <Metric label="Partidos live" value={matches.length} />
        <Metric label="Muy calientes" value={hotCount} />
        <Metric label="Valor live" value={liveValueCount} />
        <Metric label="Con estadísticas" value={withStatsCount} />
      </section>

      <div className="card p-4">
        <div className="flex items-start gap-3 rounded-2xl bg-amber-50 p-3 text-sm font-semibold text-amber-900">
          <Flame className="mt-0.5 shrink-0" size={18} />
          <div>
            <div className="font-black">Lectura live, no adivinación</div>
            <div>La pantalla intenta parecerse a ver el partido: mide presión, tiros, corners y ritmo. Si faltan estadísticas o cuotas, la señal queda como espera/vigilar.</div>
          </div>
        </div>
        <div className="mt-4 grid gap-2 md:grid-cols-[220px_1fr]">
          <select className="rounded-lg border border-line bg-white px-3 py-2 text-sm font-bold" value={decision} onChange={(event) => setDecision(event.target.value)}>
            {['Todos', 'LIVE_VALUE', 'WATCH', 'SIN_CUOTA'].map((item) => <option key={item} value={item}>{labelDecision(item)}</option>)}
          </select>
          <input
            className="rounded-lg border border-line px-3 py-2 text-sm font-semibold"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Buscar partido, liga o señal live..."
          />
        </div>
      </div>

      {isLoading ? <div className="card p-5 text-sm font-bold text-slate-600">Cargando lectura live...</div> : null}
      {!isLoading && error ? <div className="card p-5 text-sm font-bold text-rose-700">No se puede conectar con la API live.</div> : null}
      {!isLoading && !error && filteredMatches.length === 0 ? (
        <div className="card p-5 text-sm font-semibold text-slate-600">No hay partidos live con lectura suficiente ahora mismo.</div>
      ) : null}

      <section className="grid gap-4 xl:grid-cols-2">
        {filteredMatches.map((match) => <LiveMatchCard key={match.match_id} match={match} />)}
      </section>

      {marketRows.length ? <MarketDetail rows={marketRows.slice(0, 80)} /> : null}
    </div>
  )
}

function LiveMatchCard({ match }: { match: LiveMatchCenterRow }) {
  const homePressure = Math.max(0, Math.min(100, match.momentum.home_pressure))
  const awayPressure = Math.max(0, Math.min(100, match.momentum.away_pressure))
  return (
    <article className="card overflow-hidden">
      <div className="border-b border-line bg-slate-50 p-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="text-xs font-black uppercase text-slate-500">{match.country} · {match.competition}</div>
            <h2 className="mt-1 text-lg font-black text-slate-950">{match.match_name}</h2>
          </div>
          <div className="rounded-full bg-cyan-100 px-3 py-1 text-sm font-black text-cyan-800">{match.status} · {match.minute}'</div>
        </div>
        <div className="mt-4 grid grid-cols-[1fr_auto_1fr] items-center gap-3">
          <TeamName name={match.teams.home} />
          <div className="rounded-2xl bg-white px-5 py-3 text-center shadow-sm">
            <div className="text-3xl font-black text-slate-950">{score(match.score.home)} - {score(match.score.away)}</div>
            <div className="mt-1 text-xs font-black uppercase text-slate-500">Live</div>
          </div>
          <TeamName name={match.teams.away} align="right" />
        </div>
      </div>

      <div className="space-y-4 p-4">
        <div className={`rounded-2xl border p-4 ${signalClass(match.top_signal.priority)}`}>
          <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <div>
              <div className="flex items-center gap-2 text-sm font-black"><Target size={17} /> {match.top_signal.label}</div>
              <div className="mt-1 text-sm font-semibold">{match.top_signal.market}</div>
            </div>
            <div className="rounded-full bg-white px-3 py-1 text-sm font-black">{match.top_signal.confidence}% confianza</div>
          </div>
          <div className="mt-2 text-sm font-semibold">{match.top_signal.reason}</div>
        </div>

        <div>
          <div className="mb-2 flex items-center justify-between text-xs font-black uppercase text-slate-500">
            <span>Presión live</span>
            <span>{match.momentum.temperature}</span>
          </div>
          <PressureBar home={homePressure} away={awayPressure} />
          <div className="mt-2 text-sm font-bold text-slate-700">Dominio: {match.momentum.leader}</div>
        </div>

        <div className="grid grid-cols-4 gap-2 text-center">
          <Stat label="Tiros" home={match.stats.home.shots} away={match.stats.away.shots} />
          <Stat label="A puerta" home={match.stats.home.shots_on_target} away={match.stats.away.shots_on_target} />
          <Stat label="Corners" home={match.stats.home.corners} away={match.stats.away.corners} />
          <Stat label="Ataques P." home={match.stats.home.dangerous_attacks} away={match.stats.away.dangerous_attacks} />
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          <div className="rounded-2xl border border-line bg-white p-3">
            <div className="text-xs font-black uppercase text-slate-500">Eventos recientes</div>
            <div className="mt-2 space-y-1">
              {match.recent_events.length ? match.recent_events.map((event, index) => (
                <div key={`${event.minute}-${event.type}-${index}`} className="text-sm font-semibold text-slate-700">
                  {event.minute ?? '-'}' · {event.type} {event.detail ? `· ${event.detail}` : ''} {event.team ? `· ${event.team}` : ''}
                </div>
              )) : <div className="text-sm font-semibold text-slate-500">Sin eventos sincronizados.</div>}
            </div>
          </div>
          <div className="rounded-2xl border border-line bg-white p-3">
            <div className="text-xs font-black uppercase text-slate-500">Mercado live</div>
            <div className="mt-2 grid grid-cols-3 gap-2 text-center">
              <Mini label="Valor" value={match.picks.live_value} />
              <Mini label="Vigilar" value={match.picks.watch} />
              <Mini label="Total" value={match.picks.total} />
            </div>
            {match.picks.best ? <div className="mt-2 text-sm font-bold text-slate-700">{String(match.picks.best.label ?? 'Sin pick principal')}</div> : null}
          </div>
        </div>
      </div>
    </article>
  )
}

function MarketDetail({ rows }: { rows: TipstrrMarketPick[] }) {
  return (
    <div className="card overflow-x-auto">
      <div className="border-b border-line bg-slate-50 px-4 py-3 text-sm font-black">Detalle técnico de mercados live</div>
      <table className="min-w-full text-sm">
        <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
          <tr>
            <th className="px-3 py-3">Partido</th>
            <th className="px-3 py-3">Mercado</th>
            <th className="px-3 py-3">Prob.</th>
            <th className="px-3 py-3">Cuota</th>
            <th className="px-3 py-3">EV</th>
            <th className="px-3 py-3">Decisión</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={`${row.match_id}-${row.family}-${row.period}-${row.team_scope}-${row.selection}-${row.line ?? 'nl'}-${index}`} className="border-t border-slate-100">
              <td className="px-3 py-3 font-black">{row.match_name}</td>
              <td className="px-3 py-3">{row.label}</td>
              <td className="px-3 py-3">{formatPercent(row.model_probability)}</td>
              <td className="px-3 py-3">{formatDecimal(row.market_odds, 2)}</td>
              <td className="px-3 py-3">{formatDecimal(row.expected_value, 3)}</td>
              <td className="px-3 py-3"><DecisionBadge decision={row.decision} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="card p-4">
      <div className="text-xs font-black uppercase text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-black text-slate-950">{value}</div>
    </div>
  )
}

function TeamName({ name, align = 'left' }: { name: string; align?: 'left' | 'right' }) {
  return <div className={`text-sm font-black text-slate-950 md:text-base ${align === 'right' ? 'text-right' : ''}`}>{name}</div>
}

function PressureBar({ home, away }: { home: number; away: number }) {
  const total = Math.max(home + away, 1)
  const homeWidth = `${Math.round((home / total) * 100)}%`
  const awayWidth = `${Math.round((away / total) * 100)}%`
  return (
    <div className="flex h-4 overflow-hidden rounded-full bg-slate-100">
      <div className="bg-cyan-500" style={{ width: homeWidth }} />
      <div className="bg-rose-400" style={{ width: awayWidth }} />
    </div>
  )
}

function Stat({ label, home, away }: { label: string; home?: number | null; away?: number | null }) {
  return (
    <div className="rounded-2xl border border-line bg-white p-3">
      <div className="text-xs font-black uppercase text-slate-500">{label}</div>
      <div className="mt-1 text-lg font-black">{value(home)} - {value(away)}</div>
    </div>
  )
}

function Mini({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl bg-slate-50 p-2">
      <div className="text-xs font-black text-slate-500">{label}</div>
      <div className="text-lg font-black">{value}</div>
    </div>
  )
}

function DecisionBadge({ decision }: { decision: string }) {
  const className =
    decision === 'LIVE_VALUE'
      ? 'bg-emerald-100 text-emerald-800'
      : decision === 'SIN_CUOTA'
        ? 'bg-slate-100 text-slate-700'
        : 'bg-cyan-100 text-cyan-800'
  return <span className={`rounded-full px-2 py-1 text-xs font-black ${className}`}>{labelDecision(decision)}</span>
}

function labelDecision(decision: string) {
  if (decision === 'LIVE_VALUE') return 'Valor live'
  if (decision === 'WATCH') return 'Vigilar'
  if (decision === 'SIN_CUOTA') return 'Sin cuota'
  return decision
}

function signalClass(priority: number) {
  if (priority >= 4) return 'border-emerald-200 bg-emerald-50 text-emerald-900'
  if (priority >= 3) return 'border-cyan-200 bg-cyan-50 text-cyan-900'
  if (priority >= 2) return 'border-amber-200 bg-amber-50 text-amber-900'
  return 'border-slate-200 bg-slate-50 text-slate-700'
}

function hasAnyStats(row: LiveMatchCenterRow) {
  return Object.values(row.stats.home).some((item) => item != null) || Object.values(row.stats.away).some((item) => item != null)
}

function score(value?: number | null) {
  return value == null ? '-' : value
}

function value(input?: number | null) {
  return input == null ? '-' : formatDecimal(input, 0)
}
