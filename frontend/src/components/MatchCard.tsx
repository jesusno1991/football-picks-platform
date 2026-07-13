import type { Match } from '../types/api'
import { formatPercent } from '../utils/format'

type Props = {
  match: Match
  selected: boolean
  onSelect: (id: number) => void
}

export function MatchCard({ match, selected, onSelect }: Props) {
  const kickoff = new Date(match.kickoff_at)
  return (
    <button
      onClick={() => onSelect(match.id)}
      className={`w-full border-b border-slate-200 px-4 py-3 text-left transition hover:bg-cyan-50 ${
        selected ? 'bg-cyan-50 shadow-[inset_4px_0_0_#0891b2]' : 'bg-white'
      }`}
    >
      <div className="flex items-center justify-between gap-3 text-xs font-bold text-slate-500">
        <span>{kickoff.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}</span>
        <span>{match.status}</span>
      </div>
      <div className="mt-2 grid grid-cols-[1fr_auto] gap-2 text-base font-extrabold">
        <span>{match.home_team.name}</span>
        <span>-</span>
        <span>{match.away_team.name}</span>
        <span>-</span>
      </div>
      <div className="mt-3 flex flex-wrap gap-2 text-xs font-bold">
        {match.pick_count ? <span className="rounded-full bg-cyan-100 px-2 py-1 text-cyan-800">Análisis</span> : null}
        <span className="rounded-full bg-slate-100 px-2 py-1 text-slate-700">Prob. {formatPercent(match.main_probability)}</span>
        <span className="rounded-full bg-slate-100 px-2 py-1 text-slate-700">Cuota {match.best_odds ?? '-'}</span>
      </div>
    </button>
  )
}
