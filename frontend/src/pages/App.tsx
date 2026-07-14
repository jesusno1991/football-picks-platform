import { useState } from 'react'
import type React from 'react'
import { Activity, BarChart3, CalendarDays, Database, FileClock, Home, ListChecks, Search, Shield, Star, Table2, Trophy, Users } from 'lucide-react'
import { AdminPage } from './AdminPage'
import { ArchivePage } from './ArchivePage'
import { CalendarPage } from './CalendarPage'
import { CompetitionsPage } from './CompetitionsPage'
import { DashboardPage } from './DashboardPage'
import { HomePage } from './HomePage'
import { ModelHealthPage } from './ModelHealthPage'
import { PicksPage } from './PicksPage'
import { PlayersPage } from './PlayersPage'
import { StandingsPage } from './StandingsPage'
import { StatsPage } from './StatsPage'
import { TeamsPage } from './TeamsPage'
import { TipstrrMarketsPage } from './TipstrrMarketsPage'

type Page =
  | 'inicio'
  | 'partidos'
  | 'calendario'
  | 'competiciones'
  | 'equipos'
  | 'jugadores'
  | 'clasificaciones'
  | 'mercados'
  | 'picks'
  | 'predicciones'
  | 'estadisticas'
  | 'archivo'
  | 'modelo'
  | 'administracion'

const nav: { page: Page; label: string; icon: React.ReactNode }[] = [
  { page: 'inicio', label: 'Inicio', icon: <Home size={17} /> },
  { page: 'partidos', label: 'Partidos', icon: <Trophy size={17} /> },
  { page: 'calendario', label: 'Calendario', icon: <CalendarDays size={17} /> },
  { page: 'competiciones', label: 'Competiciones', icon: <Database size={17} /> },
  { page: 'equipos', label: 'Equipos', icon: <Users size={17} /> },
  { page: 'jugadores', label: 'Jugadores', icon: <Search size={17} /> },
  { page: 'clasificaciones', label: 'Clasificaciones', icon: <Table2 size={17} /> },
  { page: 'mercados', label: 'Mercados', icon: <ListChecks size={17} /> },
  { page: 'picks', label: 'Picks', icon: <Star size={17} /> },
  { page: 'predicciones', label: 'Predicciones', icon: <ListChecks size={17} /> },
  { page: 'estadisticas', label: 'Estadisticas', icon: <BarChart3 size={17} /> },
  { page: 'archivo', label: 'Archivo', icon: <FileClock size={17} /> },
  { page: 'modelo', label: 'Modelo', icon: <Activity size={17} /> },
  { page: 'administracion', label: 'Admin', icon: <Shield size={17} /> },
]

export function App() {
  const [page, setPage] = useState<Page>('inicio')
  return (
    <main className="mx-auto max-w-7xl px-4 py-5">
      <header className="mb-5 rounded-lg border border-line bg-white p-5 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h1 className="text-3xl font-black text-slate-950">The Merlin Football Hub</h1>
            <p className="text-sm font-semibold text-slate-500">Centro de informacion futbolistica, predicciones y picks de valor.</p>
          </div>
          <div className="rounded-full bg-cyan-50 px-4 py-2 text-xs font-black text-cyan-800">Datos reales de proveedores · Sin demos inventadas</div>
        </div>
        <nav className="mt-5 flex gap-2 overflow-x-auto pb-1">
          {nav.map((item) => <NavButton key={item.page} active={page === item.page} onClick={() => setPage(item.page)} icon={item.icon} label={item.label} />)}
        </nav>
      </header>

      {page === 'inicio' ? <DashboardPage /> : null}
      {page === 'partidos' ? <HomePage /> : null}
      {page === 'calendario' ? <CalendarPage /> : null}
      {page === 'competiciones' ? <CompetitionsPage /> : null}
      {page === 'equipos' ? <TeamsPage /> : null}
      {page === 'jugadores' ? <PlayersPage /> : null}
      {page === 'clasificaciones' ? <StandingsPage /> : null}
      {page === 'mercados' ? <TipstrrMarketsPage /> : null}
      {page === 'picks' ? <PicksPage onlyPublishable /> : null}
      {page === 'predicciones' ? <PicksPage /> : null}
      {page === 'estadisticas' ? <StatsPage /> : null}
      {page === 'archivo' ? <ArchivePage /> : null}
      {page === 'modelo' ? <ModelHealthPage /> : null}
      {page === 'administracion' ? <AdminPage /> : null}
    </main>
  )
}

function NavButton({ active, onClick, icon, label }: { active: boolean; onClick: () => void; icon: React.ReactNode; label: string }) {
  return (
    <button
      onClick={onClick}
      className={`inline-flex shrink-0 items-center gap-2 rounded-full px-4 py-2 text-sm font-black ${
        active ? 'bg-cyan-500 text-white' : 'border border-line bg-white text-slate-800'
      }`}
    >
      {icon}
      {label}
    </button>
  )
}
