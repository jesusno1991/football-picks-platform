import { useState } from 'react'
import { PredictionTable } from '../components/PredictionTable'
import { useMatch, useMatchInfo, useMatchMarkets, useMatchOdds } from '../hooks/queries'
import type { GenericInfo, MarketEvaluation, OddsRow } from '../types/api'
import { formatDecimal, formatPercent } from '../utils/format'

type Tab = 'resumen' | 'estadisticas' | 'eventos' | 'alineaciones' | 'cuotas' | 'mercados' | 'predicciones' | 'h2h'

export function MatchDetailPage({ matchId }: { matchId: number }) {
  const [tab, setTab] = useState<Tab>('resumen')
  const { data: match, isLoading } = useMatch(matchId)
  const { data: markets = [], isLoading: marketsLoading } = useMatchMarkets(matchId)
  const { data: stats } = useMatchInfo(matchId, 'statistics')
  const { data: events } = useMatchInfo(matchId, 'events')
  const { data: lineups } = useMatchInfo(matchId, 'lineups')
  const { data: h2h } = useMatchInfo(matchId, 'h2h')
  const { data: odds = [] } = useMatchOdds(matchId)

  if (isLoading || !match) return <div className="card p-6">Cargando detalle...</div>

  const tabs: { id: Tab; label: string }[] = [
    { id: 'resumen', label: 'Resumen' },
    { id: 'estadisticas', label: 'Estadísticas' },
    { id: 'eventos', label: 'Eventos' },
    { id: 'alineaciones', label: 'Alineaciones' },
    { id: 'cuotas', label: 'Cuotas' },
    { id: 'mercados', label: 'Mercados' },
    { id: 'predicciones', label: 'Predicciones' },
    { id: 'h2h', label: 'H2H' },
  ]

  return (
    <div className="space-y-4">
      <div className="card p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="text-sm font-bold text-slate-500">{match.competition.country} · {match.competition.name}</div>
            <div className="mt-1 text-sm font-semibold text-slate-500">
              {match.season} · {match.round ?? 'No disponible'} · {match.venue ?? 'Sede no disponible'}
            </div>
          </div>
          <span className="rounded-full bg-slate-100 px-4 py-2 text-sm font-black text-slate-800">{match.status}</span>
        </div>
        <div className="mt-5 grid grid-cols-[1fr_auto_1fr] items-center gap-4">
          <TeamHeader name={match.home_team.name} logo={match.home_team.logo_url} />
          <div className="text-center">
            <div className="text-3xl font-black">{scoreLabel(match)}</div>
            <div className="mt-1 text-xs font-bold text-slate-500">
              {new Date(match.kickoff_at).toLocaleString('es-ES', { dateStyle: 'short', timeStyle: 'short' })}
            </div>
          </div>
          <TeamHeader name={match.away_team.name} logo={match.away_team.logo_url} align="right" />
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          {Object.entries(match.availability ?? {}).map(([key, value]) => (
            <span key={key} className={`rounded-full px-3 py-1 text-xs font-black ${value === 'Disponible' ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-600'}`}>
              {key}: {value}
            </span>
          ))}
        </div>
      </div>

      <div className="card overflow-x-auto p-2">
        <div className="flex min-w-max gap-2">
          {tabs.map((item) => (
            <button key={item.id} onClick={() => setTab(item.id)} className={`rounded-full px-4 py-2 text-sm font-black ${tab === item.id ? 'bg-cyan-500 text-white' : 'bg-slate-100 text-slate-800'}`}>
              {item.label}
            </button>
          ))}
        </div>
      </div>

      {tab === 'resumen' ? <SummaryPanel match={match} stats={stats} /> : null}
      {tab === 'estadisticas' ? <GenericInfoTable title="Estadísticas del partido" info={stats} /> : null}
      {tab === 'eventos' ? <GenericInfoTable title="Eventos" info={events} /> : null}
      {tab === 'alineaciones' ? <GenericInfoTable title="Alineaciones" info={lineups} /> : null}
      {tab === 'cuotas' ? <OddsTable odds={odds} /> : null}
      {tab === 'mercados' ? (marketsLoading ? <div className="card p-4 font-bold text-slate-600">Calculando mercados disponibles...</div> : <MarketGroups markets={markets} />) : null}
      {tab === 'predicciones' ? <PredictionTable predictions={match.predictions ?? []} /> : null}
      {tab === 'h2h' ? <GenericInfoTable title="Enfrentamientos directos" info={h2h} /> : null}
    </div>
  )
}

function TeamHeader({ name, logo, align = 'left' }: { name: string; logo?: string | null; align?: 'left' | 'right' }) {
  return (
    <div className={`flex items-center gap-3 ${align === 'right' ? 'justify-end text-right' : ''}`}>
      {align === 'left' && <Logo url={logo} name={name} />}
      <div className="text-xl font-black text-slate-950">{name}</div>
      {align === 'right' && <Logo url={logo} name={name} />}
    </div>
  )
}

function Logo({ url, name }: { url?: string | null; name: string }) {
  return url ? <img src={url} alt={name} className="h-10 w-10 rounded-full object-contain" /> : <div className="grid h-10 w-10 place-items-center rounded-full bg-slate-100 text-xs font-black text-slate-600">ND</div>
}

function SummaryPanel({ match, stats }: { match: { home_form?: Record<string, number | string | null>; away_form?: Record<string, number | string | null>; pick_count: number; main_probability?: number | null; confidence?: number | null }; stats?: GenericInfo }) {
  const rows = [
    ['Picks detectados', match.pick_count],
    ['Probabilidad principal', formatPercent(match.main_probability)],
    ['Confianza', formatPercent(match.confidence)],
    ['Estadísticas API', stats?.available ? 'Disponible' : 'No disponible'],
  ]
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <div className="card p-4">
        <h2 className="text-lg font-black">Resumen</h2>
        <div className="mt-3 grid grid-cols-2 gap-2">
          {rows.map(([label, value]) => (
            <div key={String(label)} className="rounded-lg bg-slate-50 p-3">
              <div className="text-xs font-bold text-slate-500">{label}</div>
              <div className="text-lg font-black">{String(value ?? 'No disponible')}</div>
            </div>
          ))}
        </div>
      </div>
      <FormPanel title="Forma local" form={match.home_form ?? {}} />
      <FormPanel title="Forma visitante" form={match.away_form ?? {}} />
    </div>
  )
}

function GenericInfoTable({ title, info }: { title: string; info?: GenericInfo }) {
  if (!info || !info.available || info.rows.length === 0) {
    return <div className="card p-5 text-sm font-semibold text-slate-600">{info?.message ?? 'No disponible'}</div>
  }
  const columns = Array.from(new Set(info.rows.flatMap((row) => Object.keys(row))))
  return (
    <div className="card overflow-x-auto">
      <div className="border-b border-line bg-slate-50 px-4 py-3 text-sm font-black text-slate-800">{title}</div>
      <table className="min-w-full text-sm">
        <thead className="text-left text-xs uppercase text-slate-500">
          <tr>{columns.map((column) => <th key={column} className="px-3 py-3">{column}</th>)}</tr>
        </thead>
        <tbody>
          {info.rows.map((row, index) => (
            <tr key={index} className="border-t border-slate-100">
              {columns.map((column) => <td key={column} className="px-3 py-3 font-semibold">{String(row[column] ?? 'No disponible')}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function OddsTable({ odds }: { odds: OddsRow[] }) {
  if (!odds.length) return <div className="card p-5 text-sm font-semibold text-slate-600">No disponible: cuotas no sincronizadas para este partido.</div>
  return (
    <div className="card overflow-x-auto">
      <div className="border-b border-line bg-slate-50 px-4 py-3 text-sm font-black text-slate-800">Cuotas</div>
      <table className="min-w-full text-sm">
        <thead className="text-left text-xs uppercase text-slate-500">
          <tr>
            <th className="px-3 py-3">Casa</th>
            <th className="px-3 py-3">Mercado</th>
            <th className="px-3 py-3">Selección</th>
            <th className="px-3 py-3">Linea</th>
            <th className="px-3 py-3">Cuota</th>
            <th className="px-3 py-3">Proveedor</th>
          </tr>
        </thead>
        <tbody>
          {odds.map((odd, index) => (
            <tr key={`${odd.bookmaker}-${odd.market}-${odd.selection}-${index}`} className="border-t border-slate-100">
              <td className="px-3 py-3 font-black">{odd.bookmaker}</td>
              <td className="px-3 py-3">{odd.market}</td>
              <td className="px-3 py-3">{odd.selection}</td>
              <td className="px-3 py-3">{odd.line ?? '-'}</td>
              <td className="px-3 py-3 font-black">{formatDecimal(odd.odds)}</td>
              <td className="px-3 py-3">{odd.provider ?? 'No disponible'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function MarketGroups({ markets }: { markets: MarketEvaluation[] }) {
  if (markets.length === 0) {
    return <div className="card p-5 text-sm font-semibold text-slate-600">No hay mercados con cuota disponible para este partido.</div>
  }
  const groups = markets.reduce<Record<string, MarketEvaluation[]>>((acc, market) => {
    const key = groupLabel(market)
    acc[key] = acc[key] ?? []
    acc[key].push(market)
    return acc
  }, {})
  return (
    <div className="space-y-4">
      {Object.entries(groups).map(([group, rows]) => (
        <div key={group} className="card overflow-x-auto">
          <div className="border-b border-line bg-slate-50 px-4 py-3 text-sm font-black text-slate-800">{group}</div>
          <table className="min-w-full text-sm">
            <thead className="text-left text-xs uppercase text-slate-500">
              <tr>
                <th className="px-3 py-3">Mercado</th>
                <th className="px-3 py-3">Prob.</th>
                <th className="px-3 py-3">Cuota justa</th>
                <th className="px-3 py-3">Mejor cuota</th>
                <th className="px-3 py-3">EV</th>
                <th className="px-3 py-3">Merlin</th>
                <th className="px-3 py-3">Riesgo</th>
                <th className="px-3 py-3">Decisión</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((market) => (
                <tr key={`${market.code}-${market.bookmaker}`} className="border-t border-slate-100">
                  <td className="min-w-[240px] px-3 py-3 font-black text-slate-900">{marketLabel(market)}</td>
                  <td className="px-3 py-3">{formatPercent(market.model_probability)}</td>
                  <td className="px-3 py-3">{formatDecimal(market.fair_odds)}</td>
                  <td className="px-3 py-3 font-bold">{formatDecimal(market.market_odds)}</td>
                  <td className="px-3 py-3">{formatDecimal(market.expected_value, 3)}</td>
                  <td className="px-3 py-3">{formatDecimal(market.merlin_score, 1)}</td>
                  <td className="px-3 py-3">{market.risk_level}</td>
                  <td className="px-3 py-3">{decisionLabel(market.decision)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  )
}

function FormPanel({ title, form }: { title: string; form: Record<string, number | string | null> }) {
  const rows = [
    ['Muestra', form.matches_sample],
    ['Goles a favor', form.goals_for_avg],
    ['Goles en contra', form.goals_against_avg],
    ['Corners a favor', form.corners_for_avg],
    ['Corners en contra', form.corners_against_avg],
    ['Tiros', form.shots_avg],
    ['Tiros a puerta', form.shots_on_target_avg],
    ['Posesión', form.possession_avg],
  ]
  return (
    <div className="card p-4">
      <h3 className="text-lg font-black">{title}</h3>
      <div className="mt-3 grid grid-cols-2 gap-2">
        {rows.map(([label, value]) => (
          <div key={label as string} className="rounded-lg bg-slate-50 p-3">
            <div className="text-xs font-bold text-slate-500">{label}</div>
            <div className="text-lg font-black">{value ?? 'No disponible'}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

function scoreLabel(match: { home_score?: number | null; away_score?: number | null }) {
  if (match.home_score === null || match.home_score === undefined || match.away_score === null || match.away_score === undefined) return '-'
  return `${match.home_score} - ${match.away_score}`
}

function groupLabel(market: MarketEvaluation) {
  if (market.family === 'double_chance' || market.family === 'draw_no_bet' || market.family === 'match_result') return 'Partido completo'
  if (market.family === 'asian_handicap') return market.period === 'first_half' ? 'Hándicap asiático 1H' : 'Hándicap asiático'
  if (market.family === 'correct_score') return 'Marcador correcto'
  if (market.period === 'first_half' && market.team_scope === 'all') return 'Primera mitad'
  if (market.period === 'second_half' && market.team_scope === 'all') return 'Segunda mitad'
  if (market.team_scope === 'home') return 'Equipo local'
  if (market.team_scope === 'away') return 'Equipo visitante'
  return 'Partido completo'
}

function marketLabel(market: MarketEvaluation) {
  const period = market.period === 'first_half' ? '1H' : market.period === 'second_half' ? '2H' : 'FT'
  const team = market.team_scope === 'home' ? 'Local ' : market.team_scope === 'away' ? 'Visitante ' : ''
  if (market.family === 'total_goals') return `${team}${period} ${market.selection === 'over' ? 'Más' : 'Menos'} de ${market.line}`
  if (market.family === 'btts') return `${period} Ambos marcan ${market.selection === 'yes' ? 'Sí' : 'No'}`
  if (market.family === 'match_result') return `Resultado ${market.selection}`
  if (market.family === 'double_chance') return `Doble oportunidad ${market.selection.toUpperCase()}`
  if (market.family === 'draw_no_bet') return `Empate no apuesta ${market.selection}`
  if (market.family === 'asian_handicap') return `${period} Handicap ${market.team_scope === 'home' ? 'local' : 'visitante'} ${market.line}`
  if (market.family === 'correct_score') return `Marcador correcto ${market.selection}`
  return market.code
}

function decisionLabel(value: string) {
  if (value === 'ready_to_publish') return 'Para publicar'
  if (value === 'pending_validation') return 'Validación'
  return value
}
