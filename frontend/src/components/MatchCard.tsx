import { Activity, BadgeCheck, BarChart3, ClipboardList, LineChart, ShieldCheck } from 'lucide-react'
import type React from 'react'
import type { Match } from '../types/api'
import { formatPercent } from '../utils/format'

type Props = {
  match: Match
  selected: boolean
  onSelect: (id: number) => void
}

export function MatchCard({ match, selected, onSelect }: Props) {
  const kickoff = new Date(match.kickoff_at)
  const score = match.merlin_score ?? 0
  const scoreClass = score >= 75 ? 'bg-emerald-100 text-emerald-800' : score >= 55 ? 'bg-amber-100 text-amber-800' : 'bg-slate-100 text-slate-700'
  return (
    <button
      onClick={() => onSelect(match.id)}
      className={`w-full border-b border-slate-200 px-4 py-3 text-left transition hover:bg-cyan-50 ${
        selected ? 'bg-cyan-50 shadow-[inset_4px_0_0_#0891b2]' : 'bg-white'
      }`}
    >
      <div className="flex items-center justify-between gap-3 text-xs font-black text-slate-500">
        <span>{kickoff.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}</span>
        <span className="rounded-full bg-slate-100 px-2 py-1">{match.status}</span>
      </div>
      <div className="mt-2 grid grid-cols-[1fr_auto] gap-2 text-base font-extrabold text-slate-950">
        <TeamName logo={match.home_team.logo_url} name={match.home_team.name} />
        <span>{scorePart(match.home_score)}</span>
        <TeamName logo={match.away_team.logo_url} name={match.away_team.name} />
        <span>{scorePart(match.away_score)}</span>
      </div>
      <div className="mt-2 text-xs font-semibold text-slate-500">{match.competition.country} · {match.competition.name}{match.round ? ` · ${match.round}` : ''}</div>
      <div className="mt-3 grid gap-2 rounded-lg bg-slate-50 p-3">
        <div className="flex items-center justify-between gap-3">
          <div>
            <div className="text-xs font-black uppercase text-slate-500">Mejor mercado</div>
            <div className="text-sm font-black text-slate-900">{match.best_market ?? 'Sin mercado validado'}</div>
          </div>
          <span className={`rounded-full px-3 py-1 text-xs font-black ${scoreClass}`}>Merlin {match.merlin_score ?? '-'}</span>
        </div>
        <div className="grid grid-cols-3 gap-2 text-xs font-black">
          <span>Prob. {formatPercent(match.main_probability)}</span>
          <span>Cuota {match.best_odds ?? '-'}</span>
          <span>Calidad {match.data_quality_score ?? 0}%</span>
        </div>
      </div>
      <div className="mt-3 flex flex-wrap gap-2 text-xs font-bold">
        <Signal icon={<BarChart3 size={13} />} active={match.has_statistics} label="Stats" />
        <Signal icon={<ClipboardList size={13} />} active={match.has_lineups} label="XI" />
        <Signal icon={<LineChart size={13} />} active={match.has_odds} label="Cuotas" />
        <Signal icon={<Activity size={13} />} active={match.has_prediction} label={`${match.pick_count} pred.`} />
        <Signal icon={<BadgeCheck size={13} />} active={match.has_pick} label={`${match.publishable_pick_count} public.`} />
      </div>
    </button>
  )
}

function TeamName({ logo, name }: { logo?: string | null; name: string }) {
  return (
    <span className="flex min-w-0 items-center gap-2">
      {logo ? <img src={logo} alt="" className="h-5 w-5 shrink-0 rounded-full object-contain" /> : <ShieldCheck size={18} className="shrink-0 text-slate-400" />}
      <span className="truncate">{name}</span>
    </span>
  )
}

function Signal({ icon, active, label }: { icon: React.ReactNode; active: boolean; label: string }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-1 ${active ? 'bg-cyan-100 text-cyan-800' : 'bg-slate-100 text-slate-500'}`}>
      {icon}
      {label}
    </span>
  )
}

function scorePart(value?: number | null) {
  return value === null || value === undefined ? '-' : value
}
