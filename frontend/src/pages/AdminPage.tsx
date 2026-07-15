import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useAdminStatus, useMarketRankings, usePickSafetyMode, useSystemAlerts, useUltimateReport } from '../hooks/queries'
import { runAdminAction } from '../services/api'
import { formatDateInput } from '../utils/format'

export function AdminPage() {
  const queryClient = useQueryClient()
  const today = formatDateInput(new Date())
  const [token, setToken] = useState(localStorage.getItem('admin-token') ?? '')
  const [date, setDate] = useState(today)
  const [dateFrom, setDateFrom] = useState(today)
  const [dateTo, setDateTo] = useState(today)
  const [matchId, setMatchId] = useState('')
  const [lastResult, setLastResult] = useState<Record<string, unknown> | null>(null)
  const { data, isLoading } = useAdminStatus()
  const { data: rankings = [] } = useMarketRankings()
  const { data: safetyMode } = usePickSafetyMode()
  const { data: alerts = [] } = useSystemAlerts()
  const { data: report } = useUltimateReport()
  const action = useMutation({
    mutationFn: ({ path, params }: { path: string; params?: Record<string, string | number | undefined> }) => runAdminAction(path, token, params),
    onSuccess: (result) => {
      setLastResult(result)
      localStorage.setItem('admin-token', token)
      queryClient.invalidateQueries()
    },
  })
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
    ['Rankings mercado', data.market_rankings],
    ['Cola publicacion', data.publication_queue],
    ['Automatizaciones', data.automation_runs],
    ['Ventanas historicas', data.historical_sync_windows],
    ['Calibraciones', data.calibration_runs],
    ['Cobertura proveedor', data.provider_data_coverage],
  ]
  return (
    <div className="space-y-4">
      <div className="card p-5">
        <h2 className="text-2xl font-black">Administracion</h2>
        <p className="text-sm font-semibold text-slate-500">Estado de proveedores, datos sincronizados y control operativo.</p>
      </div>
      <div className="grid gap-4 lg:grid-cols-[1.1fr_1fr]">
        <div className="card p-5">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
              <h3 className="text-lg font-black">Modo de seguridad de picks</h3>
              <p className="text-sm font-semibold text-slate-500">Controla el volumen y la dureza del filtro antes de publicar candidatos.</p>
            </div>
            <span className="rounded-full bg-cyan-100 px-4 py-2 text-sm font-black text-cyan-800">{safetyMode?.mode ?? 'normal'}</span>
          </div>
          <div className="mt-4 grid gap-2 md:grid-cols-3">
            {[
              ['conservative', 'Conservador'],
              ['normal', 'Normal'],
              ['aggressive', 'Agresivo'],
            ].map(([mode, label]) => (
              <button
                key={mode}
                className={`rounded-xl border px-3 py-3 text-sm font-black ${safetyMode?.mode === mode ? 'border-cyan-500 bg-cyan-50 text-cyan-800' : 'border-line bg-white text-slate-800'}`}
                disabled={!token || action.isPending}
                onClick={() => action.mutate({ path: '/api/admin/pick-safety-mode', params: { mode } })}
              >
                {label}
              </button>
            ))}
          </div>
          <div className="mt-3 text-xs font-semibold text-slate-500">
            {safetyMode ? safetyMode.description[safetyMode.mode] : 'Modo normal activo por defecto.'}
          </div>
        </div>
        <div className="card p-5">
          <h3 className="text-lg font-black">Alertas operativas</h3>
          <div className="mt-3 space-y-2">
            {alerts.map((alert) => (
              <div key={`${alert.level}-${alert.title}`} className={`rounded-2xl border p-3 ${alert.level === 'critical' ? 'border-rose-200 bg-rose-50' : alert.level === 'warning' ? 'border-amber-200 bg-amber-50' : alert.level === 'ok' ? 'border-emerald-200 bg-emerald-50' : 'border-cyan-200 bg-cyan-50'}`}>
                <div className="text-sm font-black text-slate-950">{alert.title}</div>
                <div className="mt-1 text-xs font-semibold text-slate-600">{alert.message}</div>
                <div className="mt-1 text-xs font-black text-slate-800">{alert.action}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
      <div className="card p-5">
        <h3 className="text-lg font-black">Acciones operativas</h3>
        <p className="mt-1 text-sm font-semibold text-slate-500">Estas acciones requieren el token admin. La web no guarda credenciales externas ni claves de API.</p>
        <div className="mt-4 grid gap-3 md:grid-cols-[1fr_auto_auto]">
          <input className="rounded-lg border border-line px-3 py-2" type="password" value={token} onChange={(event) => setToken(event.target.value)} placeholder="Token admin" />
          <input className="rounded-lg border border-line px-3 py-2" type="date" value={date} onChange={(event) => setDate(event.target.value)} />
          <button className="rounded-lg bg-cyan-500 px-4 py-2 font-black text-white" disabled={!token || action.isPending} onClick={() => action.mutate({ path: '/api/admin/sync-day', params: { date } })}>Sincronizar fecha</button>
        </div>
        <div className="mt-3 grid gap-3 md:grid-cols-[1fr_1fr_auto_auto_auto]">
          <input className="rounded-lg border border-line px-3 py-2" type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} />
          <input className="rounded-lg border border-line px-3 py-2" type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} />
          <button className="rounded-lg border border-line px-4 py-2 font-black" disabled={!token || action.isPending} onClick={() => action.mutate({ path: '/api/admin/import-range', params: { date_from: dateFrom, date_to: dateTo } })}>Importar rango</button>
          <button className="rounded-lg border border-line px-4 py-2 font-black" disabled={!token || action.isPending} onClick={() => action.mutate({ path: '/api/admin/generate-predictions' })}>Recalcular picks</button>
          <button className="rounded-lg border border-line px-4 py-2 font-black" disabled={!token || action.isPending} onClick={() => action.mutate({ path: '/api/admin/rank-markets' })}>Rankear mercados</button>
        </div>
        <div className="mt-3 grid gap-3 md:grid-cols-[1fr_auto_1fr_auto]">
          <button className="rounded-lg border border-line px-4 py-2 font-black" disabled={!token || action.isPending} onClick={() => action.mutate({ path: '/api/admin/sync-day-deep', params: { date } })}>Enriquecer fecha</button>
          <input className="rounded-lg border border-line px-3 py-2" value={matchId} onChange={(event) => setMatchId(event.target.value)} placeholder="ID interno partido" />
          <button className="rounded-lg border border-line px-4 py-2 font-black" disabled={!token || !matchId || action.isPending} onClick={() => action.mutate({ path: '/api/admin/sync-match-deep', params: { match_id: Number(matchId) } })}>Enriquecer partido</button>
          <button className="rounded-lg border border-line px-4 py-2 font-black" disabled={!token || action.isPending} onClick={() => action.mutate({ path: '/api/admin/verify-results' })}>Verificar resultados</button>
        </div>
        <div className="mt-3">
          <button className="rounded-lg bg-slate-950 px-4 py-2 font-black text-white" disabled={!token || action.isPending} onClick={() => window.confirm('Ejecutar mantenimiento completo ahora?') && action.mutate({ path: '/api/admin/run-maintenance', params: { days_back: 1, days_forward: 7, deep_today: 'true' } })}>Ejecutar mantenimiento completo</button>
        </div>
        {action.error ? <div className="mt-3 rounded-lg bg-red-50 p-3 text-sm font-bold text-red-700">Error ejecutando accion.</div> : null}
        {lastResult ? <pre className="mt-3 max-h-52 overflow-auto rounded-lg bg-slate-950 p-3 text-xs font-semibold text-white">{JSON.stringify(lastResult, null, 2)}</pre> : null}
      </div>
      <div className="grid gap-3 md:grid-cols-5">
        {metrics.map(([label, value]) => <div key={String(label)} className="card p-4"><div className="text-xs font-black text-slate-500">{label}</div><div className="mt-2 text-xl font-black">{String(value)}</div></div>)}
      </div>
      <RawTable title="Ranking profesional de mercados" rows={rankings as unknown as Record<string, unknown>[]} empty="No disponible: ejecuta el ranking de mercados desde admin." />
      <RawTable title="Últimas sincronizaciones" rows={data.latest_sync_jobs} empty="No disponible: no hay jobs registrados." />
      <RawTable title="Uso de API" rows={data.api_usage} empty="No disponible: no hay consumo registrado." />
      <ReportBox report={report} />
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

function ReportBox({ report }: { report?: Record<string, unknown> }) {
  if (!report) return null
  return (
    <div className="card p-5">
      <h3 className="text-lg font-black">Informe de arquitectura</h3>
      <pre className="mt-3 max-h-[360px] overflow-auto rounded-lg bg-slate-950 p-4 text-xs font-semibold text-slate-50">
        {JSON.stringify(report, null, 2)}
      </pre>
    </div>
  )
}
