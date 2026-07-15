import { lazy, Suspense, useEffect, useState } from 'react'
import type React from 'react'
import { Activity, BarChart3, CalendarDays, Database, FileClock, Home, ListChecks, Search, Shield, Star, Table2, Trophy, Users } from 'lucide-react'

const AdminPage = lazy(() => import('./AdminPage').then((module) => ({ default: module.AdminPage })))
const ArchivePage = lazy(() => import('./ArchivePage').then((module) => ({ default: module.ArchivePage })))
const CalendarPage = lazy(() => import('./CalendarPage').then((module) => ({ default: module.CalendarPage })))
const CompetitionsPage = lazy(() => import('./CompetitionsPage').then((module) => ({ default: module.CompetitionsPage })))
const DashboardPage = lazy(() => import('./DashboardPage').then((module) => ({ default: module.DashboardPage })))
const HomePage = lazy(() => import('./HomePage').then((module) => ({ default: module.HomePage })))
const MatchDetailPage = lazy(() => import('./MatchDetailPage').then((module) => ({ default: module.MatchDetailPage })))
const ModelHealthPage = lazy(() => import('./ModelHealthPage').then((module) => ({ default: module.ModelHealthPage })))
const PicksPage = lazy(() => import('./PicksPage').then((module) => ({ default: module.PicksPage })))
const PlayersPage = lazy(() => import('./PlayersPage').then((module) => ({ default: module.PlayersPage })))
const StandingsPage = lazy(() => import('./StandingsPage').then((module) => ({ default: module.StandingsPage })))
const StatsPage = lazy(() => import('./StatsPage').then((module) => ({ default: module.StatsPage })))
const TeamsPage = lazy(() => import('./TeamsPage').then((module) => ({ default: module.TeamsPage })))
const TipstrrMarketsPage = lazy(() => import('./TipstrrMarketsPage').then((module) => ({ default: module.TipstrrMarketsPage })))

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

function pageFromPath(pathname: string): { page: Page; matchId?: number } {
  const match = pathname.match(/^\/matches\/(\d+)/)
  if (match) return { page: 'partidos', matchId: Number(match[1]) }
  if (pathname.startsWith('/matches')) return { page: 'partidos' }
  if (pathname.startsWith('/calendar')) return { page: 'calendario' }
  if (pathname.startsWith('/competitions')) return { page: 'competiciones' }
  if (pathname.startsWith('/teams')) return { page: 'equipos' }
  if (pathname.startsWith('/players')) return { page: 'jugadores' }
  if (pathname.startsWith('/standings')) return { page: 'clasificaciones' }
  if (pathname.startsWith('/markets')) return { page: 'mercados' }
  if (pathname.startsWith('/picks')) return { page: 'picks' }
  if (pathname.startsWith('/predictions')) return { page: 'predicciones' }
  if (pathname.startsWith('/statistics')) return { page: 'estadisticas' }
  if (pathname.startsWith('/archive')) return { page: 'archivo' }
  if (pathname.startsWith('/model-health')) return { page: 'modelo' }
  if (pathname.startsWith('/admin')) return { page: 'administracion' }
  return { page: 'inicio' }
}

const pagePaths: Record<Page, string> = {
  inicio: '/',
  partidos: '/matches',
  calendario: '/calendar',
  competiciones: '/competitions',
  equipos: '/teams',
  jugadores: '/players',
  clasificaciones: '/standings',
  mercados: '/markets',
  picks: '/picks',
  predicciones: '/predictions',
  estadisticas: '/statistics',
  archivo: '/archive',
  modelo: '/model-health',
  administracion: '/admin',
}

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
  { page: 'estadisticas', label: 'Estadísticas', icon: <BarChart3 size={17} /> },
  { page: 'archivo', label: 'Archivo', icon: <FileClock size={17} /> },
  { page: 'modelo', label: 'Modelo', icon: <Activity size={17} /> },
  { page: 'administracion', label: 'Admin', icon: <Shield size={17} /> },
]

export function App() {
  const [route, setRoute] = useState(() => pageFromPath(window.location.pathname))
  const page = route.page

  useEffect(() => {
    const onPop = () => setRoute(pageFromPath(window.location.pathname))
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [])

  const navigate = (nextPage: Page) => {
    window.history.pushState({}, '', pagePaths[nextPage])
    setRoute({ page: nextPage })
  }

  return (
    <main className="mx-auto max-w-[1500px] px-3 py-4 sm:px-4 sm:py-5">
      <header className="mb-5 rounded-lg border border-line bg-white p-4 shadow-sm sm:p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h1 className="text-2xl font-black text-slate-950 sm:text-3xl">The Merlin Football Hub</h1>
            <p className="text-sm font-semibold text-slate-500">Centro de información futbolística, predicciones y picks de valor.</p>
          </div>
          <div className="w-fit rounded-full bg-cyan-50 px-4 py-2 text-xs font-black text-cyan-800">Datos reales de proveedores · Sin demos inventadas</div>
        </div>
        <nav className="mt-5 flex gap-2 overflow-x-auto pb-1">
          {nav.map((item) => <NavButton key={item.page} active={page === item.page} onClick={() => navigate(item.page)} icon={item.icon} label={item.label} />)}
        </nav>
      </header>

      <Suspense fallback={<div className="card p-6 font-bold text-slate-600">Cargando módulo...</div>}>
        {page === 'inicio' ? <DashboardPage /> : null}
        {page === 'partidos' ? route.matchId ? <MatchDetailPage matchId={route.matchId} /> : <HomePage /> : null}
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
      </Suspense>
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
