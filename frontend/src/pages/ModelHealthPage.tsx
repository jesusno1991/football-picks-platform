import { Activity, AlertTriangle, CheckCircle2, Database, ShieldAlert } from 'lucide-react'
import type React from 'react'
import { useModelHealth } from '../hooks/queries'

export function ModelHealthPage() {
  const { data, isLoading } = useModelHealth()
  if (isLoading || !data) return <div className="card p-6">Cargando estado del modelo...</div>
  const statusClass = data.status === 'operativo' ? 'bg-emerald-100 text-emerald-800' : data.status === 'degradado' ? 'bg-amber-100 text-amber-800' : 'bg-red-100 text-red-800'
  const kpis = [
    ['Partidos descargados', data.matches_downloaded],
    ['Partidos analizados', data.matches_analyzed],
    ['Mercados evaluados', data.markets_evaluated],
    ['Candidatos', data.candidate_picks],
    ['Publicables', data.publishable_picks],
    ['Rechazados', data.rejected_picks],
    ['Sin cuotas', data.matches_without_odds],
    ['Sin estadisticas', data.matches_without_statistics],
    ['Entidades sin mapear', data.unmapped_entities],
    ['Competiciones incompletas', data.incomplete_competitions],
  ]
  return (
    <div className="space-y-4">
      <div className="card p-5">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 className="text-2xl font-black">Salud del modelo</h2>
            <p className="text-sm font-semibold text-slate-500">Control operativo de datos, proveedores, picks y calidad.</p>
          </div>
          <span className={`inline-flex w-fit items-center gap-2 rounded-full px-4 py-2 text-sm font-black ${statusClass}`}>
            {data.status === 'operativo' ? <CheckCircle2 size={18} /> : <AlertTriangle size={18} />}
            {data.status.toUpperCase()}
          </span>
        </div>
      </div>

      <section className="grid gap-3 md:grid-cols-4">
        <ProviderCard icon={<Database size={18} />} label="Proveedor activo" value={data.active_provider} />
        <ProviderCard icon={<Activity size={18} />} label="Estado de datos" value={data.data_status} />
        <ProviderCard icon={<CheckCircle2 size={18} />} label="API-Football" value={data.api_football_configured ? 'Conectada' : 'No configurada'} />
        <ProviderCard icon={<CheckCircle2 size={18} />} label="FlashScore" value={data.flashscore_configured ? 'Conectada' : 'No configurada'} />
      </section>

      <section className="grid gap-3 md:grid-cols-5">
        {kpis.map(([label, value]) => (
          <div key={String(label)} className="card p-4">
            <div className="text-xs font-black uppercase text-slate-500">{label}</div>
            <div className="mt-2 text-2xl font-black">{String(value)}</div>
          </div>
        ))}
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <RawTable title="Errores recientes" rows={data.recent_errors} empty="No hay errores recientes registrados." />
        <RawTable title="Uso de APIs" rows={data.api_usage} empty="No hay consumo de API registrado." />
      </section>

      <div className="card p-4 text-sm font-bold text-slate-600">
        <div className="flex items-center gap-2 font-black text-slate-900"><ShieldAlert size={18} /> Proxima sincronizacion</div>
        <div className="mt-1">{data.next_sync_hint}</div>
        <div className="mt-1">Ultima sincronizacion: {data.last_sync_at ?? 'No disponible'}</div>
      </div>
    </div>
  )
}

function ProviderCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="card p-4">
      <div className="flex items-center gap-2 text-xs font-black uppercase text-slate-500">{icon}{label}</div>
      <div className="mt-2 text-lg font-black">{value}</div>
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
