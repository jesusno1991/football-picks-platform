import { useState } from 'react'
import { useCompetitions, useStandings } from '../hooks/queries'

export function StandingsPage() {
  const { data: competitions = [] } = useCompetitions()
  const [competitionId, setCompetitionId] = useState<number | undefined>()
  const { data: rows = [] } = useStandings(competitionId)
  return (
    <div className="space-y-4">
      <div className="card p-5">
        <h2 className="text-2xl font-black">Clasificaciones</h2>
        <select className="mt-4 w-full rounded-lg border border-line bg-white px-3 py-2 font-bold" value={competitionId ?? ''} onChange={(event) => setCompetitionId(event.target.value ? Number(event.target.value) : undefined)}>
          <option value="">Todas las competiciones</option>
          {competitions.map((competition) => <option key={competition.id} value={competition.id}>{competition.country} · {competition.name}</option>)}
        </select>
      </div>
      <div className="card overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500"><tr><th className="px-3 py-3">#</th><th className="px-3 py-3">Equipo</th><th className="px-3 py-3">PJ</th><th className="px-3 py-3">V</th><th className="px-3 py-3">E</th><th className="px-3 py-3">D</th><th className="px-3 py-3">GF</th><th className="px-3 py-3">GC</th><th className="px-3 py-3">DG</th><th className="px-3 py-3">Pts</th></tr></thead>
          <tbody>{rows.map((row, index) => <tr key={index} className="border-t border-slate-100"><td className="px-3 py-3">{row.rank ?? '-'}</td><td className="px-3 py-3 font-black">{row.team_name}</td><td className="px-3 py-3">{row.played ?? '-'}</td><td className="px-3 py-3">{row.wins ?? '-'}</td><td className="px-3 py-3">{row.draws ?? '-'}</td><td className="px-3 py-3">{row.losses ?? '-'}</td><td className="px-3 py-3">{row.goals_for ?? '-'}</td><td className="px-3 py-3">{row.goals_against ?? '-'}</td><td className="px-3 py-3">{row.goal_difference ?? '-'}</td><td className="px-3 py-3 font-black">{row.points ?? '-'}</td></tr>)}</tbody>
        </table>
        {!rows.length ? <div className="p-5 text-sm font-semibold text-slate-600">No disponible: clasificaciones no sincronizadas todavia.</div> : null}
      </div>
    </div>
  )
}
