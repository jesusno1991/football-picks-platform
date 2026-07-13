import { PredictionTable } from '../components/PredictionTable'
import { useMatch } from '../hooks/queries'

export function MatchDetailPage({ matchId }: { matchId: number }) {
  const { data: match, isLoading } = useMatch(matchId)
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
