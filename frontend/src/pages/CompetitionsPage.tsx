import { useState } from 'react'
import { MatchCard } from '../components/MatchCard'
import { useCompetition, useCompetitionStandings, useCompetitions } from '../hooks/queries'

export function CompetitionsPage() {
  const { data: competitions = [] } = useCompetitions()
  const [selectedId, setSelectedId] = useState<number | undefined>(competitions[0]?.id)
  const selected = selectedId ?? competitions[0]?.id
  const { data: detail } = useCompetition(selected)
  const { data: standings = [] } = useCompetitionStandings(selected)

  return (
    <div className="grid gap-5 lg:grid-cols-[360px_1fr]">
      <section className="card overflow-hidden">
        <div className="border-b border-line bg-slate-50 px-4 py-3 text-sm font-black">Competiciones</div>
        {competitions.map((competition) => (
          <button key={competition.id} onClick={() => setSelectedId(competition.id)} className={`w-full border-b border-slate-100 px-4 py-3 text-left hover:bg-cyan-50 ${selected === competition.id ? 'bg-cyan-50' : ''}`}>
            <div className="font-black">{competition.name}</div>
            <div className="text-sm font-semibold text-slate-500">{competition.country} · {competition.season}</div>
          </button>
        ))}
        {!competitions.length ? <div className="p-4 text-sm font-semibold text-slate-500">No disponible</div> : null}
      </section>

      <section className="space-y-4">
        {detail ? (
          <>
            <div className="card p-5">
              <div className="text-sm font-bold text-slate-500">{detail.country}</div>
              <h2 className="text-3xl font-black">{detail.name}</h2>
              <div className="mt-3 grid gap-3 md:grid-cols-4">
                <Metric label="Partidos" value={detail.match_count} />
                <Metric label="Equipos" value={detail.teams_count} />
                <Metric label="Picks" value={detail.picks_count} />
                <Metric label="Clasificacion" value={detail.standings_available ? 'Disponible' : 'No disponible'} />
              </div>
            </div>
            <div className="card overflow-hidden">
              <div className="border-b border-line bg-slate-50 px-4 py-3 text-sm font-black">Próximos partidos</div>
              {detail.next_matches.length ? detail.next_matches.map((match) => <MatchCard key={match.id} match={match} selected={false} onSelect={() => undefined} />) : <Empty />}
            </div>
            <StandingsTable rows={standings} />
          </>
        ) : <div className="card p-6">Selecciona una competición.</div>}
      </section>
    </div>
  )
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return <div className="rounded-lg bg-slate-50 p-3"><div className="text-xs font-bold text-slate-500">{label}</div><div className="text-xl font-black">{value}</div></div>
}

function Empty() {
  return <div className="p-4 text-sm font-semibold text-slate-500">No disponible</div>
}

function StandingsTable({ rows }: { rows: { rank?: number | null; team_name: string; played?: number | null; points?: number | null; goal_difference?: number | null; form?: string | null }[] }) {
  if (!rows.length) return <div className="card p-5 text-sm font-semibold text-slate-600">No disponible: clasificación no sincronizada.</div>
  return (
    <div className="card overflow-x-auto">
      <div className="border-b border-line bg-slate-50 px-4 py-3 text-sm font-black">Clasificación</div>
      <table className="min-w-full text-sm">
        <thead className="text-left text-xs uppercase text-slate-500"><tr><th className="px-3 py-3">#</th><th className="px-3 py-3">Equipo</th><th className="px-3 py-3">PJ</th><th className="px-3 py-3">DG</th><th className="px-3 py-3">Pts</th><th className="px-3 py-3">Forma</th></tr></thead>
        <tbody>{rows.map((row, index) => <tr key={index} className="border-t border-slate-100"><td className="px-3 py-3">{row.rank ?? '-'}</td><td className="px-3 py-3 font-black">{row.team_name}</td><td className="px-3 py-3">{row.played ?? '-'}</td><td className="px-3 py-3">{row.goal_difference ?? '-'}</td><td className="px-3 py-3 font-black">{row.points ?? '-'}</td><td className="px-3 py-3">{row.form ?? '-'}</td></tr>)}</tbody>
      </table>
    </div>
  )
}
