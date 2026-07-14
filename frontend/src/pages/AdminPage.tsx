import { useAdminStatus } from '../hooks/queries'

export function AdminPage() {
  const { data, isLoading } = useAdminStatus()
  if (isLoading || !data) return <div className="card p-6">Cargando administracion...</div>
  const metrics = [
    ['Proveedor activo', data.active_provider],
    ['API-Football', data.api_football_configured ? 'Conectada' : 'No configurada'],
    ['FlashScore', data.flashscore_configured ? 'Conectada' : 'No configurada'],
    ['Partidos', data.matches],
    ['Competiciones', data.competitions],
    ['Equipos', data.teams],
    ['Jugadores', data.players],
    ['Clasificaciones', data.standings_rows],
    ['Raw responses', data.raw_responses],
    ['Mappings pendientes', data.mappings_unmatched],
    ['Arbitros', data.referees],
    ['Plantillas', data.squad_members],
    ['Stats equipos temporada', data.team_season_statistics],
    ['Stats jugadores temporada', data.player_season_statistics],
    ['Calidad de datos', data.data_quality_snapshots],
    ['Cache', data.cache_entries],
    ['Auditoria IA', data.model_audit_logs],
  ]
  return (
    <div className="space-y-4">
      <div className="card p-5">
        <h2 className="text-2xl font-black">Administracion</h2>
        <p className="text-sm font-semibold text-slate-500">Estado de proveedores, datos sincronizados y control operativo.</p>
      </div>
      <div className="grid gap-3 md:grid-cols-5">
        {metrics.map(([label, value]) => <div key={String(label)} className="card p-4"><div className="text-xs font-black text-slate-500">{label}</div><div className="mt-2 text-xl font-black">{String(value)}</div></div>)}
      </div>
      <RawTable title="Ultimas sincronizaciones" rows={data.latest_sync_jobs} empty="No disponible: no hay jobs registrados." />
      <RawTable title="Uso de API" rows={data.api_usage} empty="No disponible: no hay consumo registrado." />
    </div>
  )
}

function RawTable({ title, rows, empty }: { title: string; rows: Record<string, unknown>[]; empty: string }) {
  if (!rows.length) return <div className="card p-5 text-sm font-semibold text-slate-600">{empty}</div>
  const columns = Array.from(new Set(rows.flatMap((row) => Object.keys(row))))
  return (
    <div className="card overflow-x-auto">
      <div className="border-b border-line bg-slate-50 px-4 py-3 text-sm font-black">{title}</div>
      <table className="min-w-full text-sm">
        <thead className="text-left text-xs uppercase text-slate-500"><tr>{columns.map((column) => <th key={column} className="px-3 py-3">{column}</th>)}</tr></thead>
        <tbody>{rows.map((row, index) => <tr key={index} className="border-t border-slate-100">{columns.map((column) => <td key={column} className="px-3 py-3">{String(row[column] ?? 'No disponible')}</td>)}</tr>)}</tbody>
      </table>
    </div>
  )
}
