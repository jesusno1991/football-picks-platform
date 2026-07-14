import { useState } from 'react'
import { MatchCard } from '../components/MatchCard'
import { useTeamDetail, useTeams } from '../hooks/queries'

export function TeamsPage() {
  const [q, setQ] = useState('')
  const { data: teams = [] } = useTeams(q)
  const [selectedId, setSelectedId] = useState<number | undefined>()
  const selected = selectedId ?? teams[0]?.id
  const { data: detail } = useTeamDetail(selected)

  return (
    <div className="grid gap-5 lg:grid-cols-[360px_1fr]">
      <section className="card overflow-hidden">
        <div className="border-b border-line bg-slate-50 p-4">
          <div className="text-sm font-black">Equipos</div>
          <input value={q} onChange={(event) => setQ(event.target.value)} className="mt-3 w-full rounded-lg border border-line px-3 py-2" placeholder="Buscar equipo..." />
        </div>
        {teams.map((team) => (
          <button key={team.id} onClick={() => setSelectedId(team.id)} className={`w-full border-b border-slate-100 px-4 py-3 text-left hover:bg-cyan-50 ${selected === team.id ? 'bg-cyan-50' : ''}`}>
            <div className="font-black">{team.name}</div>
            <div className="text-sm font-semibold text-slate-500">{team.country ?? 'No disponible'}</div>
          </button>
        ))}
        {!teams.length ? <div className="p-4 text-sm font-semibold text-slate-500">No disponible</div> : null}
      </section>
      <section className="space-y-4">
        {detail ? (
          <>
            <div className="card p-5">
              <div className="text-sm font-bold text-slate-500">{detail.country ?? 'No disponible'}</div>
              <h2 className="text-3xl font-black">{detail.name}</h2>
              <div className="mt-3 grid gap-3 md:grid-cols-4">
                {Object.entries(detail.statistics).map(([key, value]) => <Metric key={key} label={key.replace(/_/g, ' ')} value={String(value ?? 'No disponible')} />)}
              </div>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <MatchList title="Proximos partidos" matches={detail.upcoming_matches} />
              <MatchList title="Resultados recientes" matches={detail.recent_matches} />
            </div>
            <InfoBox title="Plantilla" message={detail.squad.message} />
            <InfoBox title="Lesiones y sanciones" message={detail.injuries.message} />
          </>
        ) : <div className="card p-6">Selecciona un equipo.</div>}
      </section>
    </div>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="rounded-lg bg-slate-50 p-3"><div className="text-xs font-bold capitalize text-slate-500">{label}</div><div className="text-lg font-black">{value}</div></div>
}

function MatchList({ title, matches }: { title: string; matches: import('../types/api').Match[] }) {
  return (
    <div className="card overflow-hidden">
      <div className="border-b border-line bg-slate-50 px-4 py-3 text-sm font-black">{title}</div>
      {matches.length ? matches.map((match) => <MatchCard key={match.id} match={match} selected={false} onSelect={() => undefined} />) : <div className="p-4 text-sm font-semibold text-slate-500">No disponible</div>}
    </div>
  )
}

function InfoBox({ title, message }: { title: string; message: string }) {
  return <div className="card p-4"><h3 className="text-lg font-black">{title}</h3><p className="mt-2 text-sm font-semibold text-slate-600">{message}</p></div>
}
