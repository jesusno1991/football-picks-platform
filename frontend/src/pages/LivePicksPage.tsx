import { useMemo, useState } from 'react'
import { Activity, RefreshCcw } from 'lucide-react'
import { useLivePicks } from '../hooks/queries'
import type { TipstrrMarketPick } from '../types/api'
import { formatDecimal, formatPercent } from '../utils/format'

export function LivePicksPage() {
  const [decision, setDecision] = useState('Todos')
  const [search, setSearch] = useState('')
  const { data = [], isLoading, error, refetch, isFetching } = useLivePicks(500)

  const rows = useMemo(() => {
    const normalized = search.trim().toLowerCase()
    return data.filter((row) => {
      const matchesDecision = decision === 'Todos' || row.decision === decision
      const matchesSearch =
        !normalized ||
        row.match_name.toLowerCase().includes(normalized) ||
        row.competition_name.toLowerCase().includes(normalized) ||
        row.label.toLowerCase().includes(normalized)
      return matchesDecision && matchesSearch
    })
  }, [data, decision, search])

  const liveValueCount = data.filter((row) => row.decision === 'LIVE_VALUE').length
  const withOddsCount = data.filter((row) => row.market_odds != null).length

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-2xl font-black">Picks Live</h1>
          <p className="text-sm font-semibold text-slate-500">
            Candidatos para partidos en vivo. Separado de prepartido y sin publicación automática.
          </p>
        </div>
        <button
          className="inline-flex items-center gap-2 rounded-full bg-cyan-500 px-4 py-2 text-sm font-black text-white disabled:opacity-60"
          disabled={isFetching}
          onClick={() => refetch()}
        >
          <RefreshCcw size={16} />
          Actualizar live
        </button>
      </div>

      <section className="grid gap-3 md:grid-cols-4">
        <Metric label="Candidatos live" value={data.length} />
        <Metric label="LIVE_VALUE" value={liveValueCount} />
        <Metric label="Con cuota" value={withOddsCount} />
        <Metric label="Refresco" value="60s" />
      </section>

      <div className="card p-4">
        <div className="flex items-start gap-3 rounded-2xl bg-amber-50 p-3 text-sm font-semibold text-amber-900">
          <Activity className="mt-0.5 shrink-0" size={18} />
          <div>
            <div className="font-black">Modo live separado</div>
            <div>Estos candidatos dependen de datos y cuotas disponibles durante el partido. Revisa siempre marcador, minuto y liquidez antes de usar cualquier señal.</div>
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
            placeholder="Buscar partido, liga o mercado live..."
          />
        </div>
      </div>

      {isLoading ? <div className="card p-5 text-sm font-bold text-slate-600">Cargando partidos live...</div> : null}
      {!isLoading && error ? (
        <div className="card p-5 text-sm font-bold text-rose-700">No se puede conectar con la API live.</div>
      ) : null}
      {!isLoading && !error && rows.length === 0 ? (
        <div className="card p-5 text-sm font-semibold text-slate-600">No hay candidatos live con los filtros actuales.</div>
      ) : rows.length ? (
        <LiveTable rows={rows} />
      ) : null}
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

function LiveTable({ rows }: { rows: TipstrrMarketPick[] }) {
  return (
    <div className="card overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
          <tr>
            <th className="px-3 py-3">Partido</th>
            <th className="px-3 py-3">Estado</th>
            <th className="px-3 py-3">Mercado</th>
            <th className="px-3 py-3">Prob.</th>
            <th className="px-3 py-3">Cuota</th>
            <th className="px-3 py-3">EV</th>
            <th className="px-3 py-3">Merlin</th>
            <th className="px-3 py-3">Riesgo</th>
            <th className="px-3 py-3">Decisión</th>
            <th className="px-3 py-3">Motivo</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={`${row.match_id}-${row.family}-${row.period}-${row.team_scope}-${row.selection}-${row.line ?? 'nl'}-${index}`} className="border-t border-slate-100">
              <td className="min-w-[260px] px-3 py-3">
                <div className="font-black">{row.match_name}</div>
                <div className="text-xs font-semibold text-slate-500">{row.country} · {row.competition_name}</div>
              </td>
              <td className="px-3 py-3 font-black text-cyan-800">{row.match_status}</td>
              <td className="min-w-[220px] px-3 py-3">
                <div className="font-black">{row.label}</div>
                <div className="text-xs font-semibold text-slate-500">{row.period} · {row.team_scope}</div>
              </td>
              <td className="px-3 py-3 font-black">{formatPercent(row.model_probability)}</td>
              <td className="px-3 py-3 font-black">{formatDecimal(row.market_odds, 2)}</td>
              <td className="px-3 py-3 font-black text-emerald-700">{formatDecimal(row.expected_value, 3)}</td>
              <td className="px-3 py-3 font-black">{formatDecimal(row.merlin_score, 1)}</td>
              <td className="px-3 py-3">{riskLabel(row.risk_level)}</td>
              <td className="px-3 py-3"><DecisionBadge decision={row.decision} /></td>
              <td className="min-w-[240px] px-3 py-3 text-xs font-semibold text-slate-600">{row.reason}</td>
            </tr>
          ))}
        </tbody>
      </table>
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

function riskLabel(value: string) {
  if (value === 'low') return 'Bajo'
  if (value === 'medium') return 'Medio'
  if (value === 'high') return 'Alto'
  return value
}
