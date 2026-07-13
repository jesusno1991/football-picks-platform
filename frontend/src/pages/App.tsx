import { useState } from 'react'
import type React from 'react'
import { BarChart3, CheckCircle2, ListChecks, Trophy } from 'lucide-react'
import { HomePage } from './HomePage'
import { PicksPage } from './PicksPage'
import { StatsPage } from './StatsPage'

type Page = 'matches' | 'picks' | 'publishable' | 'stats'

export function App() {
  const [page, setPage] = useState<Page>('matches')
  return (
    <main className="mx-auto max-w-7xl px-4 py-5">
      <header className="mb-5 flex flex-col gap-4 rounded-lg border border-line bg-white p-5 shadow-sm md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-black text-slate-950">Football Picks Platform</h1>
          <p className="text-sm font-semibold text-slate-500">Inteligencia prepartido especializada en mercados de goles y picks de valor.</p>
        </div>
        <nav className="flex flex-wrap gap-2">
          <NavButton active={page === 'matches'} onClick={() => setPage('matches')} icon={<Trophy size={17} />} label="Partidos" />
          <NavButton active={page === 'picks'} onClick={() => setPage('picks')} icon={<ListChecks size={17} />} label="Picks" />
          <NavButton active={page === 'publishable'} onClick={() => setPage('publishable')} icon={<CheckCircle2 size={17} />} label="Para publicar" />
          <NavButton active={page === 'stats'} onClick={() => setPage('stats')} icon={<BarChart3 size={17} />} label="Estadísticas" />
        </nav>
      </header>
      {page === 'matches' ? <HomePage /> : null}
      {page === 'picks' ? <PicksPage /> : null}
      {page === 'publishable' ? <PicksPage onlyPublishable /> : null}
      {page === 'stats' ? <StatsPage /> : null}
    </main>
  )
}

function NavButton({ active, onClick, icon, label }: { active: boolean; onClick: () => void; icon: React.ReactNode; label: string }) {
  return (
    <button
      onClick={onClick}
      className={`inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-black ${
        active ? 'bg-cyan-500 text-white' : 'border border-line bg-white text-slate-800'
      }`}
    >
      {icon}
      {label}
    </button>
  )
}
