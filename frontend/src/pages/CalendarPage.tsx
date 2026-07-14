import { HomePage } from './HomePage'

export function CalendarPage() {
  return (
    <div className="space-y-4">
      <div className="card p-5">
        <h2 className="text-2xl font-black">Calendario</h2>
        <p className="text-sm font-semibold text-slate-500">Consulta partidos por fecha, ayer, hoy, manana o cualquier dia del mes.</p>
      </div>
      <HomePage />
    </div>
  )
}
