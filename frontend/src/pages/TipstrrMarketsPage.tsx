import { useMemo, useState } from 'react'
import { useTipstrrMarketPicks } from '../hooks/queries'
import type { TipstrrMarketPick } from '../types/api'
import { formatDateInput, formatDecimal, formatPercent } from '../utils/format'

const decisions = [
  { value: undefined, label: 'Todos' },
  { value: 'PUBLICABLE', label: 'Publicables' },
  { value: 'WATCH', label: 'En estudio' },
  { value: 'SIN_CUOTA', label: 'Sin cuota' },
]

const groups = [
  'Todos',
  '1X2',
  'Resultado al descanso',
  'Empate no apuesta',
  'Doble oportunidad',
  'Gana + ambos marcan',
  'Goles partido',
  'Goles al descanso',
  'Marcador correcto',
  'Goles local',
  'Goles visitante',
  '1ª parte local',
  '1ª parte visitante',
  'Hándicap asiático',
  'Hándicap asiático 1ª parte',
  'Primer gol',
  'Se clasificará',
]

export function TipstrrMarketsPage() {
  const [date, setDate] = useState(formatDateInput(new Date()))
  const [decision, setDecision] = useState<string | undefined>(undefined)
  const [group, setGroup] = useState('Todos')
  const [search, setSearch] = useState('')
  const { data = [], isLoading } = useTipstrrMarketPicks(date, decision)

  const rows = useMemo(() => {
    const normalized = search.trim().toLowerCase()
    return data.filter((row) => {
      const matchesGroup = group === 'Todos' || row.group === group
      const matchesSearch =
        !normalized ||
        row.match_name.toLowerCase().includes(normalized) ||
        row.competition_name.toLowerCase().includes(normalized) ||
        row.country.toLowerCase().includes(normalized) ||
        row.label.toLowerCase().includes(normalized)
      return matchesGroup && matchesSearch
    })
  }, [data, group, search])

  const publicableCount = data.filter((row) => row.decision === 'PUBLICABLE').length
  const withOddsCount = data.filter((row) => row.market_odds).length

  const shiftDate = (days: number) => {
    const next = new Date(date)
    next.setDate(next.getDate() + days)
    setDate(formatDateInput(next))
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-2xl font-black">Mercados principales</h1>
          <p className="text-sm font-semibold text-slate-500">
            Mercados tipo Tipstrr para todos los partidos: 1X2, DNB, goles, marcador correcto, equipos y hándicap asiático.
          </p>
        </div>
        <div className="card flex flex-wrap items-center gap-2 p-2">
          <button className="rounded-lg border border-line px-3 py-2 text-sm font-bold" onClick={() => shiftDate(-1)}>Ayer</button>
          <button className="rounded-lg bg-brand px-3 py-2 text-sm font-bold text-white" onClick={() => setDate(formatDateInput(new Date()))}>Hoy</button>
          <button className="rounded-lg border border-line px-3 py-2 text-sm font-bold" onClick={() => shiftDate(1)}>Mañana</button>
          <input className="rounded-lg border border-line px-3 py-2 text-sm font-bold" type="date" value={date} onChange={(event) => setDate(event.target.value)} />
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        <Metric label="Mercados generados" value={data.length.toString()} />
        <Metric label="Con cuota real" value={withOddsCount.toString()} />
        <Metric label="Publicables" value={publicableCount.toString()} />
      </div>

      <div className="card space-y-3 p-3">
        <div className="flex flex-wrap gap-2">
          {decisions.map((item) => (
            <button
              key={item.label}
              onClick={() => setDecision(item.value)}
              className={`rounded-full px-3 py-2 text-sm font-black ${
                decision === item.value ? 'bg-cyan-500 text-white' : 'border border-line bg-white text-slate-800'
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>
        <div className="flex flex-col gap-2 md:flex-row">
          <select className="rounded-lg border border-line bg-white px-3 py-2 text-sm font-bold" value={group} onChange={(event) => setGroup(event.target.value)}>
            {groups.map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
          <input
            className="min-w-0 flex-1 rounded-lg border border-line px-3 py-2 text-sm font-semibold"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Buscar partido, liga o mercado..."
          />
        </div>
      </div>

      {isLoading ? <div className="card p-4 font-bold text-slate-600">Cargando partidos y mercados reales...</div> : null}
      {!isLoading && rows.length === 0 ? (
        <div className="card p-5 text-sm font-semibold text-slate-600">No hay mercados para estos filtros.</div>
      ) : (
        <MarketTable rows={rows} />
      )}
    </div>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="card p-4">
      <div className="text-xs font-black uppercase text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-black text-slate-950">{value}</div>
    </div>
  )
}

function MarketTable({ rows }: { rows: TipstrrMarketPick[] }) {
  return (
    <div className="card overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
          <tr>
            <th className="px-3 py-3">Partido</th>
            <th className="px-3 py-3">Hora</th>
            <th className="px-3 py-3">Grupo</th>
            <th className="px-3 py-3">Mercado</th>
            <th className="px-3 py-3">Prob.</th>
            <th className="px-3 py-3">Cuota justa</th>
            <th className="px-3 py-3">Cuota</th>
            <th className="px-3 py-3">EV</th>
            <th className="px-3 py-3">Casa</th>
            <th className="px-3 py-3">Merlin</th>
            <th className="px-3 py-3">Riesgo</th>
            <th className="px-3 py-3">Calidad cuota</th>
            <th className="px-3 py-3">Reglas</th>
            <th className="px-3 py-3">Decisión</th>
            <th className="px-3 py-3">Motivo</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={`${row.match_id}-${row.family}-${row.period}-${row.team_scope}-${row.selection}-${row.line ?? 'none'}`} className="border-t border-slate-100">
              <td className="min-w-[260px] px-3 py-3">
                <div className="font-black text-slate-900">{row.match_name}</div>
                <div className="text-xs font-bold text-slate-500">{row.country} · {row.competition_name}</div>
              </td>
              <td className="px-3 py-3 font-semibold">
                {new Date(row.kickoff_at).toLocaleString('es-ES', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}
              </td>
              <td className="min-w-[150px] px-3 py-3 font-bold text-slate-700">{row.group}</td>
              <td className="min-w-[210px] px-3 py-3 font-black text-slate-900">{row.label}</td>
              <td className="px-3 py-3">{formatPercent(row.model_probability)}</td>
              <td className="px-3 py-3">{formatDecimal(row.fair_odds)}</td>
              <td className="px-3 py-3 font-black">{formatDecimal(row.market_odds)}</td>
              <td className={`px-3 py-3 font-black ${row.expected_value && row.expected_value > 0 ? 'text-emerald-700' : 'text-slate-600'}`}>{formatDecimal(row.expected_value, 3)}</td>
              <td className="px-3 py-3">{row.bookmaker ?? '-'}</td>
              <td className="px-3 py-3">{formatDecimal(row.merlin_score, 1)}</td>
              <td className="px-3 py-3">{riskLabel(row.risk_level)}</td>
              <td className="px-3 py-3">
                <div className="font-black">{formatDecimal(row.odds_quality_score, 0)}</div>
                <div className="text-xs font-semibold text-slate-500">{row.price_age_minutes != null ? `${formatDecimal(row.price_age_minutes, 0)} min` : '-'}</div>
              </td>
              <td className="min-w-[240px] px-3 py-3"><RuleSummary row={row} /></td>
              <td className="px-3 py-3"><DecisionBadge decision={row.decision} /></td>
              <td className="min-w-[220px] px-3 py-3 text-xs font-semibold text-slate-600">{row.reason}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function RuleSummary({ row }: { row: TipstrrMarketPick }) {
  const failed = row.failed_rules.slice(0, 2)
  const passed = row.passed_rules.slice(0, 2)
  return (
    <div className="flex flex-wrap gap-1">
      {failed.length ? failed.map((rule) => (
        <span key={rule} className="rounded-full bg-rose-50 px-2 py-1 text-[11px] font-black text-rose-700">{rule}</span>
      )) : passed.map((rule) => (
        <span key={rule} className="rounded-full bg-emerald-50 px-2 py-1 text-[11px] font-black text-emerald-700">{rule}</span>
      ))}
      <span className="rounded-full bg-slate-100 px-2 py-1 text-[11px] font-black text-slate-700">{row.safety_mode}</span>
    </div>
  )
}

function DecisionBadge({ decision }: { decision: string }) {
  const className =
    decision === 'PUBLICABLE'
      ? 'bg-emerald-100 text-emerald-800'
      : decision === 'SIN_CUOTA'
        ? 'bg-slate-100 text-slate-700'
        : 'bg-cyan-100 text-cyan-800'
  const label = decision === 'PUBLICABLE' ? 'Publicable' : decision === 'SIN_CUOTA' ? 'Sin cuota' : 'Estudio'
  return <span className={`rounded-full px-2 py-1 text-xs font-black ${className}`}>{label}</span>
}

function riskLabel(value: string) {
  if (value === 'low') return 'Bajo'
  if (value === 'medium') return 'Medio'
  if (value === 'high') return 'Alto'
  return value
}
