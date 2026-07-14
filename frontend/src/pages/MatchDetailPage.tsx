import { PredictionTable } from '../components/PredictionTable'
import { useMatch, useMatchMarkets } from '../hooks/queries'
import type { MarketEvaluation } from '../types/api'
import { formatDecimal, formatPercent } from '../utils/format'

export function MatchDetailPage({ matchId }: { matchId: number }) {
  const { data: match, isLoading } = useMatch(matchId)
  const { data: markets = [], isLoading: marketsLoading } = useMatchMarkets(matchId)
  if (isLoading || !match) return <div className="card p-6">Cargando detalle...</div>
  const homeForm = match.home_form ?? {}
  const awayForm = match.away_form ?? {}

  return (
    <div className="space-y-4">
      <div className="card p-5">
        <div className="text-sm font-bold text-slate-500">{match.competition.name}</div>
        <div className="mt-2 grid grid-cols-[1fr_auto_1fr] items-center gap-4">
          <div className="text-2xl font-black">{match.home_team.name}</div>
          <div className="rounded-full bg-slate-100 px-4 py-2 text-sm font-black">
            {new Date(match.kickoff_at).toLocaleString('es-ES', { dateStyle: 'short', timeStyle: 'short' })}
          </div>
          <div className="text-right text-2xl font-black">{match.away_team.name}</div>
        </div>
        <div className="mt-3 text-sm font-semibold text-slate-500">{match.venue ?? 'Sede pendiente'} · {match.round ?? '-'}</div>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <FormPanel title="Forma local" form={homeForm} />
        <FormPanel title="Forma visitante" form={awayForm} />
      </div>

      <div>
        <h2 className="mb-3 text-xl font-black">Picks recomendados</h2>
        <PredictionTable predictions={match.predictions ?? []} />
        {match.predictions?.[0]?.explanation ? (
          <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm font-semibold text-amber-900">
            {match.predictions[0].explanation}
          </div>
        ) : null}
      </div>

      <div>
        <h2 className="mb-3 text-xl font-black">Mercados del partido</h2>
        {marketsLoading ? <div className="card p-4 font-bold text-slate-600">Calculando mercados disponibles...</div> : <MarketGroups markets={markets} />}
      </div>
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
                <th className="px-3 py-3">Disponible</th>
                <th className="px-3 py-3">Prob.</th>
                <th className="px-3 py-3">Cuota justa</th>
                <th className="px-3 py-3">Mejor cuota</th>
                <th className="px-3 py-3">EV</th>
                <th className="px-3 py-3">Settlement</th>
                <th className="px-3 py-3">Merlin</th>
                <th className="px-3 py-3">Riesgo</th>
                <th className="px-3 py-3">Decisión</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((market) => (
                <tr key={`${market.code}-${market.bookmaker}`} className="border-t border-slate-100">
                  <td className="min-w-[240px] px-3 py-3 font-black text-slate-900">{marketLabel(market)}</td>
                  <td className="px-3 py-3 font-bold text-emerald-700">Sí</td>
                  <td className="px-3 py-3">{formatPercent(market.model_probability)}</td>
                  <td className="px-3 py-3">{formatDecimal(market.fair_odds)}</td>
                  <td className="px-3 py-3 font-bold">{formatDecimal(market.market_odds)}</td>
                  <td className="px-3 py-3">{formatDecimal(market.expected_value, 3)}</td>
                  <td className="px-3 py-3">{market.settlement_type}</td>
                  <td className="px-3 py-3">{formatDecimal(market.merlin_score, 1)}</td>
                  <td className="px-3 py-3">{market.risk_level}</td>
                  <td className="px-3 py-3">
                    <span className={`rounded-full px-2 py-1 text-xs font-bold ${
                      market.decision === 'ready_to_publish' ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-700'
                    }`}>
                      {decisionLabel(market.decision)}
                    </span>
                  </td>
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
    ['Córners a favor', form.corners_for_avg],
    ['Córners en contra', form.corners_against_avg],
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
            <div className="text-lg font-black">{value ?? '-'}</div>
          </div>
        ))}
      </div>
    </div>
  )
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
  if (market.family === 'asian_handicap') return `${period} Hándicap ${market.team_scope === 'home' ? 'local' : 'visitante'} ${market.line}`
  if (market.family === 'correct_score') return `Marcador correcto ${market.selection}`
  return market.code
}

function decisionLabel(value: string) {
  if (value === 'ready_to_publish') return 'Para publicar'
  if (value === 'pending_validation') return 'Validación'
  return value
}
