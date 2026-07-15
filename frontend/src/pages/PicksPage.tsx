import { useState } from 'react'
import { usePredictionExport, useTipstrrMarketPicks } from '../hooks/queries'
import type { PredictionExportResponse, TipstrrMarketPick } from '../types/api'
import { formatDateInput, formatDecimal, formatPercent } from '../utils/format'

function dateFromUrl() {
  const params = new URLSearchParams(window.location.search)
  const value = params.get('date')
  return value && /^\d{4}-\d{2}-\d{2}$/.test(value) ? value : formatDateInput(new Date())
}

export function PicksPage({ onlyPublishable = false }: { onlyPublishable?: boolean }) {
  const [date, setDateState] = useState(dateFromUrl)
  const [viewMode, setViewMode] = useState<'table' | 'export'>('table')
  const { data: publicablePicks = [], isLoading: picksLoading, error: picksError } = useTipstrrMarketPicks(date, 'PUBLICABLE', 1000)
  const { data: allMarketRows = [], isLoading: marketRowsLoading, error: marketRowsError } = useTipstrrMarketPicks(date, undefined, 1000)
  const tableRows = onlyPublishable ? publicablePicks : allMarketRows
  const isLoading = onlyPublishable ? picksLoading : marketRowsLoading
  const loadError = onlyPublishable ? picksError || marketRowsError : marketRowsError

  const setDate = (nextDate: string) => {
    setDateState(nextDate)
    window.history.pushState({}, '', `${onlyPublishable ? '/picks' : '/predictions'}?date=${nextDate}`)
  }

  const shiftDate = (days: number) => {
    const next = new Date(`${date}T12:00:00`)
    next.setDate(next.getDate() + days)
    setDate(formatDateInput(next))
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-2xl font-black">{onlyPublishable ? 'Picks para publicar' : 'Predicciones'}</h1>
          <p className="text-sm font-semibold text-slate-500">
            {onlyPublishable
              ? 'Solo aparecen las señales válidas para publicar. Over 1.5 y Over 2.5 vuelven a estar permitidos si pasan los filtros.'
              : 'Predicciones generadas antes del inicio, incluyendo candidatos y descartes.'}
          </p>
        </div>
        <div className="card flex flex-wrap items-center gap-2 p-2">
          <button className="rounded-lg border border-line px-3 py-2 text-sm font-bold" onClick={() => shiftDate(-1)}>Ayer</button>
          <button className="rounded-lg bg-brand px-3 py-2 text-sm font-bold text-white" onClick={() => setDate(formatDateInput(new Date()))}>Hoy</button>
          <button className="rounded-lg border border-line px-3 py-2 text-sm font-bold" onClick={() => shiftDate(1)}>Mañana</button>
          <input className="rounded-lg border border-line px-3 py-2 text-sm font-bold" type="date" value={date} onChange={(event) => setDate(event.target.value)} />
        </div>
      </div>
      <div className="card flex flex-col gap-3 p-3 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="text-sm font-black text-slate-900">{onlyPublishable ? 'Herramientas de picks' : 'Vista de predicciones'}</div>
          <div className="text-xs font-semibold text-slate-500">
            {onlyPublishable
              ? 'Descarga los picks publicables y el diagnóstico de candidatos para revisarlo en ChatGPT.'
              : 'Puedes ver la tabla normal o descargar todos los picks de la fecha para analizarlos en ChatGPT.'}
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            className={`rounded-full px-4 py-2 text-sm font-black ${viewMode === 'table' ? 'bg-cyan-500 text-white' : 'border border-line bg-white text-slate-700'}`}
            onClick={() => setViewMode('table')}
          >
            Tabla
          </button>
          <button
            className={`rounded-full px-4 py-2 text-sm font-black ${viewMode === 'export' ? 'bg-cyan-500 text-white' : 'border border-line bg-white text-slate-700'}`}
            onClick={() => setViewMode('export')}
          >
            Exportar para ChatGPT
          </button>
        </div>
      </div>
      {isLoading ? <div className="card p-4 font-bold text-slate-600">Cargando datos reales de la fecha...</div> : null}
      {viewMode === 'export' ? (
        <ChatGptExportPanel date={date} enabled={viewMode === 'export'} onlyPublicable={onlyPublishable} />
      ) : !isLoading && loadError ? (
        <div className="card p-5 text-sm font-semibold text-rose-700">
          No se puede conectar con la API. En local abre tambien el backend en el puerto 8000 o usa la web de Railway.
        </div>
      ) : !isLoading && tableRows.length === 0 ? (
        <div className="card p-5 text-sm font-semibold text-slate-600">
          {onlyPublishable
            ? `No hay picks publicables en esta fecha. Candidatos analizados visibles: ${allMarketRows.length}.`
            : 'No hay predicciones generadas para esta fecha.'}
        </div>
      ) : (
        <MarketPickTable picks={tableRows} />
      )}
    </div>
  )
}

function ChatGptExportPanel({ date, enabled, onlyPublicable = false }: { date: string; enabled: boolean; onlyPublicable?: boolean }) {
  const { data: exportData, isFetching, refetch } = usePredictionExport(date, enabled)
  const fileBase = `${onlyPublicable ? 'picks-publicables' : 'picks-predicciones'}-${date}`
  const prompt = [
    onlyPublicable ? 'Analiza estos picks prepartido publicables como auditor externo.' : 'Analiza estos picks prepartido como auditor externo.',
    'Prioriza mercados con EV positivo, probabilidad alta, cuota coherente, Merlin Score alto y buen control de riesgo.',
    'Separa picks publicables, picks a vigilar y descartes. No inventes datos que no vengan en el archivo.',
  ].join(' ')

  return (
    <div className="card p-5">
      <div className="grid gap-3 md:grid-cols-4">
        <ExportMetric label="Partidos encontrados" value={exportData?.diagnostics.matches_found ?? '-'} />
        <ExportMetric label="Partidos futuros" value={exportData?.diagnostics.future_matches ?? '-'} />
        <ExportMetric label="Mercados evaluados" value={exportData?.market_evaluations.length ?? '-'} />
        <ExportMetric label="Picks publicables" value={exportData?.publicable_picks.length ?? '-'} />
      </div>
      <div className="mt-3 grid gap-3 md:grid-cols-3">
        <ExportMetric label="Con cuotas recientes" value={exportData?.diagnostics.matches_with_recent_odds ?? '-'} />
        <ExportMetric label="Partidos evaluados" value={exportData?.diagnostics.matches_evaluated ?? '-'} />
        <ExportMetric label="Fecha" value={date} />
      </div>
      <div className="mt-5 rounded-2xl border border-line bg-slate-50 p-4">
        <div className="text-sm font-black text-slate-900">Archivo para enviar a ChatGPT</div>
        <p className="mt-1 text-sm font-semibold text-slate-600">
          El servidor vuelve a consultar fixtures y cuotas antes de preparar el archivo. Solo entran partidos futuros de la fecha local seleccionada con cuotas recientes.
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          <button
            className="rounded-full border border-line bg-white px-4 py-2 text-sm font-black text-slate-800"
            onClick={() => refetch()}
          >
            Actualizar exportación
          </button>
          <button
            disabled={!exportData || isFetching}
            className="rounded-full bg-cyan-500 px-4 py-2 text-sm font-black text-white disabled:cursor-not-allowed disabled:opacity-50"
            onClick={() => exportData && downloadFile(`${fileBase}.json`, JSON.stringify(exportData, null, 2), 'application/json;charset=utf-8')}
          >
            Descargar JSON completo
          </button>
          <button
            disabled={!exportData || isFetching}
            className="rounded-full border border-line bg-white px-4 py-2 text-sm font-black text-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
            onClick={() => exportData && downloadFile(`${fileBase}.txt`, buildChatGptText(prompt, exportData), 'text/plain;charset=utf-8')}
          >
            Descargar TXT para ChatGPT
          </button>
        </div>
        {isFetching ? <div className="mt-3 text-sm font-black text-cyan-700">Actualizando fixtures, cuotas y candidatos...</div> : null}
      </div>
      {exportData ? <ExportDiagnostics exportData={exportData} /> : null}
      <div className="mt-5">
        <label className="text-xs font-black uppercase text-slate-500">Prompt recomendado</label>
        <textarea
          className="mt-2 min-h-24 w-full rounded-2xl border border-line bg-white p-3 text-sm font-semibold text-slate-700"
          readOnly
          value={prompt}
        />
      </div>
    </div>
  )
}

function ExportDiagnostics({ exportData }: { exportData: PredictionExportResponse }) {
  const reasons = Object.entries(exportData.diagnostics.discard_reasons)
  return (
    <div className="mt-5 rounded-2xl border border-line bg-white p-4">
      <div className="text-sm font-black text-slate-900">Diagnóstico de exportación</div>
      <div className="mt-2 grid gap-2 text-sm font-semibold text-slate-600 md:grid-cols-2">
        <div>Generado: {new Date(exportData.generated_at).toLocaleString('es-ES')}</div>
        <div>Zona horaria: {exportData.timezone}</div>
        <div>Cuota máxima antigua: {exportData.diagnostics.max_odds_age_hours}h</div>
        <div>Mercados exportados: {exportData.market_evaluations.length}</div>
        <div>Refresco de datos: {exportData.diagnostics.refresh_status ?? 'ok'}</div>
      </div>
      {exportData.diagnostics.refresh_error ? (
        <div className="mt-4 rounded-xl bg-rose-50 p-3 text-sm font-bold text-rose-800">
          Error al refrescar proveedor: {exportData.diagnostics.refresh_error}
        </div>
      ) : null}
      {exportData.market_evaluations.length === 0 ? (
        <div className="mt-4 rounded-xl bg-amber-50 p-3 text-sm font-bold text-amber-800">
          No hay picks exportables para esta fecha con las reglas actuales.
        </div>
      ) : null}
      <div className="mt-4">
        <div className="text-xs font-black uppercase text-slate-500">Motivos de descarte</div>
        {reasons.length ? (
          <div className="mt-2 flex flex-wrap gap-2">
            {reasons.map(([reason, count]) => (
              <span key={reason} className="rounded-full border border-line bg-slate-50 px-3 py-1 text-xs font-black text-slate-700">
                {reason}: {count}
              </span>
            ))}
          </div>
        ) : (
          <div className="mt-2 text-sm font-semibold text-slate-500">Sin descartes registrados.</div>
        )}
      </div>
    </div>
  )
}

function ExportMetric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-2xl border border-line bg-white p-4">
      <div className="text-xs font-black uppercase text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-black text-slate-950">{value}</div>
    </div>
  )
}

function MarketPickTable({ picks }: { picks: TipstrrMarketPick[] }) {
  const [sortKey, setSortKey] = useState<'opportunity' | 'probability' | 'ev' | 'merlin' | 'odds'>('opportunity')
  const [marketFilter, setMarketFilter] = useState('Todos')
  const [riskFilter, setRiskFilter] = useState('Todos')
  const [minProbability, setMinProbability] = useState('')
  const [minEv, setMinEv] = useState('')
  const [bestPerMatch, setBestPerMatch] = useState(true)
  const marketGroups = ['Todos', ...Array.from(new Set(picks.map((pick) => pick.group))).sort()]
  const filteredPicks = picks.filter((pick) => {
    const probabilityOk = !minProbability || value(pick.model_probability) >= Number(minProbability) / 100
    const evOk = !minEv || value(pick.expected_value) >= Number(minEv)
    const marketOk = marketFilter === 'Todos' || pick.group === marketFilter
    const riskOk = riskFilter === 'Todos' || pick.risk_level === riskFilter
    return probabilityOk && evOk && marketOk && riskOk
  })
  const visiblePicks = bestPerMatch ? bestCandidatePerMatch(filteredPicks) : filteredPicks
  const sortedPicks = [...visiblePicks].sort((left, right) => {
    if (sortKey === 'opportunity') return opportunityScore(right) - opportunityScore(left)
    if (sortKey === 'probability') return value(right.model_probability) - value(left.model_probability)
    if (sortKey === 'ev') return value(right.expected_value) - value(left.expected_value)
    if (sortKey === 'merlin') return value(right.merlin_score) - value(left.merlin_score)
    return value(right.market_odds) - value(left.market_odds)
  })

  return (
    <div className="card overflow-hidden">
      <div className="space-y-3 border-b border-line bg-white p-3 text-xs font-black">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-slate-500">Ordenar por:</span>
          <SortButton active={sortKey === 'opportunity'} onClick={() => setSortKey('opportunity')} label="Mejor oportunidad" />
          <SortButton active={sortKey === 'probability'} onClick={() => setSortKey('probability')} label="Mayor probabilidad" />
          <SortButton active={sortKey === 'ev'} onClick={() => setSortKey('ev')} label="Mejor EV" />
          <SortButton active={sortKey === 'merlin'} onClick={() => setSortKey('merlin')} label="Merlin Score" />
          <SortButton active={sortKey === 'odds'} onClick={() => setSortKey('odds')} label="Mayor cuota" />
          <button
            onClick={() => setBestPerMatch((current) => !current)}
            className={`rounded-full px-3 py-1.5 ${bestPerMatch ? 'bg-slate-900 text-white' : 'border border-line bg-white text-slate-700'}`}
          >
            {bestPerMatch ? '1 mercado por partido' : 'Ver todos los mercados'}
          </button>
          <span className="ml-auto text-slate-500">{sortedPicks.length} visibles de {picks.length}</span>
        </div>
        <div className="grid gap-2 md:grid-cols-4">
          <select className="rounded-lg border border-line bg-white px-3 py-2 text-sm font-bold" value={marketFilter} onChange={(event) => setMarketFilter(event.target.value)}>
            {marketGroups.map((group) => <option key={group} value={group}>{group}</option>)}
          </select>
          <select className="rounded-lg border border-line bg-white px-3 py-2 text-sm font-bold" value={riskFilter} onChange={(event) => setRiskFilter(event.target.value)}>
            {['Todos', 'low', 'medium', 'high'].map((risk) => <option key={risk} value={risk}>{risk === 'Todos' ? 'Todos los riesgos' : riskLabel(risk)}</option>)}
          </select>
          <input className="rounded-lg border border-line px-3 py-2 text-sm font-bold" inputMode="decimal" value={minProbability} onChange={(event) => setMinProbability(event.target.value)} placeholder="Probabilidad minima %" />
          <input className="rounded-lg border border-line px-3 py-2 text-sm font-bold" inputMode="decimal" value={minEv} onChange={(event) => setMinEv(event.target.value)} placeholder="EV minimo, ej. 0.03" />
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
            <tr>
              <th className="px-3 py-3">Partido</th>
              <th className="px-3 py-3">Mercado</th>
              <th className="px-3 py-3"><button className="font-black uppercase" onClick={() => setSortKey('probability')}>Prob. ↓</button></th>
              <th className="px-3 py-3">Cuota justa</th>
              <th className="px-3 py-3"><button className="font-black uppercase" onClick={() => setSortKey('odds')}>Cuota ↓</button></th>
              <th className="px-3 py-3"><button className="font-black uppercase" onClick={() => setSortKey('ev')}>EV ↓</button></th>
              <th className="px-3 py-3"><button className="font-black uppercase" onClick={() => setSortKey('merlin')}>Merlin ↓</button></th>
              <th className="px-3 py-3">Riesgo</th>
              <th className="px-3 py-3">Calidad cuota</th>
              <th className="px-3 py-3">Auditoría</th>
              <th className="px-3 py-3">Motivo</th>
            </tr>
          </thead>
          <tbody>
            {sortedPicks.map((pick, index) => (
              <tr key={`${pick.match_id}-${pick.family}-${pick.period}-${pick.team_scope}-${pick.selection}-${pick.line ?? 'nl'}-${index}`} className="border-t border-slate-100">
                <td className="px-3 py-3">
                  <div className="font-black">{pick.match_name}</div>
                  <div className="text-xs font-semibold text-slate-500">{pick.country} · {pick.competition_name}</div>
                </td>
                <td className="px-3 py-3">
                  <div className="font-black">{pick.label}</div>
                  <div className="text-xs font-semibold text-slate-500">{pick.period} · {pick.team_scope}</div>
                </td>
                <td className="px-3 py-3 font-black text-cyan-800">{formatPercent(pick.model_probability)}</td>
                <td className="px-3 py-3">{formatDecimal(pick.fair_odds, 2)}</td>
                <td className="px-3 py-3 font-black">{formatDecimal(pick.market_odds, 2)}</td>
                <td className="px-3 py-3 font-black text-emerald-700">{formatDecimal(pick.expected_value, 3)}</td>
                <td className="px-3 py-3 font-black">{formatDecimal(pick.merlin_score, 1)}</td>
                <td className="px-3 py-3">{pick.risk_level}</td>
                <td className="px-3 py-3">
                  <div className="font-black">{formatDecimal(pick.odds_quality_score, 0)}</div>
                  <div className="text-xs font-semibold text-slate-500">{pick.price_age_minutes != null ? `${formatDecimal(pick.price_age_minutes, 0)} min` : '-'}</div>
                </td>
                <td className="min-w-[260px] px-3 py-3">
                  <AuditChips pick={pick} />
                </td>
                <td className="px-3 py-3">{pick.reason}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function SortButton({ active, onClick, label }: { active: boolean; onClick: () => void; label: string }) {
  return <button onClick={onClick} className={`rounded-full px-3 py-1.5 ${active ? 'bg-cyan-500 text-white' : 'border border-line bg-white text-slate-700'}`}>{label}</button>
}

function bestCandidatePerMatch(picks: TipstrrMarketPick[]) {
  const byMatch = new Map<number, TipstrrMarketPick>()
  picks.forEach((pick) => {
    const current = byMatch.get(pick.match_id)
    if (!current || opportunityScore(pick) > opportunityScore(current)) {
      byMatch.set(pick.match_id, pick)
    }
  })
  return Array.from(byMatch.values())
}

function opportunityScore(pick: TipstrrMarketPick) {
  const decisionBoost = pick.decision === 'PUBLICABLE' ? 100 : pick.expected_value != null ? 35 : 0
  const riskPenalty = pick.risk_level === 'high' ? 25 : pick.risk_level === 'medium' ? 8 : 0
  const marketPenalty = protectedHandicapPenalty(pick)
  return (
    decisionBoost
    + value(pick.merlin_score)
    + Math.max(0, value(pick.expected_value)) * 22
    + Math.max(0, value(pick.model_probability)) * 8
    + Math.max(0, value(pick.odds_quality_score)) * 0.08
    - riskPenalty
    - marketPenalty
  )
}

function protectedHandicapPenalty(pick: TipstrrMarketPick) {
  if (pick.family !== 'asian_handicap' || pick.line == null) return 0
  if (pick.line > 1.25) return 45
  if (pick.period === 'first_half' && pick.line > 0.75) return 45
  return 12
}

function value(input?: number | null) {
  return input ?? -999
}

function riskLabel(value: string) {
  if (value === 'low') return 'Bajo'
  if (value === 'medium') return 'Medio'
  if (value === 'high') return 'Alto'
  return value
}

function buildChatGptText(prompt: string, exportData: PredictionExportResponse) {
  const reasons = Object.entries(exportData.diagnostics.discard_reasons).map(([reason, count]) => `${reason}: ${count}`)
  const lines = [
    'EXPORTACION FOOTBALL PICKS PLATFORM',
    `Fecha local analizada: ${exportData.date}`,
    `Exportado: ${exportData.generated_at}`,
    `Zona horaria: ${exportData.timezone}`,
    '',
    'PROMPT RECOMENDADO',
    prompt,
    '',
    'DIAGNOSTICO',
    `Partidos encontrados: ${exportData.diagnostics.matches_found}`,
    `Partidos futuros: ${exportData.diagnostics.future_matches}`,
    `Partidos con cuotas recientes: ${exportData.diagnostics.matches_with_recent_odds}`,
    `Partidos evaluados: ${exportData.diagnostics.matches_evaluated}`,
    `Máxima antigüedad de cuota: ${exportData.diagnostics.max_odds_age_hours}h`,
    `Refresco de datos: ${exportData.diagnostics.refresh_status ?? 'ok'}`,
    `Error de refresco: ${exportData.diagnostics.refresh_error ?? 'ninguno'}`,
    `Motivos de descarte: ${reasons.length ? reasons.join(', ') : 'ninguno'}`,
    '',
    'PICKS PUBLICABLES',
    ...exportData.publicable_picks.map((pick, index) => formatMarketPickLine(index + 1, pick)),
    '',
    'TODOS LOS CANDIDATOS FUTUROS CON CUOTA RECIENTE',
    ...exportData.market_evaluations.map((pick, index) => formatMarketPickLine(index + 1, pick)),
  ]

  return lines.join('\n')
}

function formatMarketPickLine(index: number, pick: TipstrrMarketPick) {
  return [
    `${index}. ${pick.match_name}`,
    `kickoff_at=${pick.kickoff_at}`,
    `fecha_local=${pick.kickoff_local_date}`,
    `estado=${pick.match_status}`,
    `${pick.country} / ${pick.competition_name}`,
    `mercado="${pick.label}"`,
    `familia=${pick.family}`,
    `periodo=${pick.period}`,
    `equipo=${pick.team_scope}`,
    `seleccion=${pick.selection}`,
    `linea=${pick.line ?? '-'}`,
    `prob=${formatPercent(pick.model_probability)}`,
    `cuota_justa=${formatDecimal(pick.fair_odds, 2)}`,
    `cuota=${formatDecimal(pick.market_odds, 2)}`,
    `bookmaker=${pick.bookmaker ?? '-'}`,
    `odds_timestamp=${pick.odds_collected_at ?? '-'}`,
    `EV=${formatDecimal(pick.expected_value, 3)}`,
    `Merlin=${formatDecimal(pick.merlin_score, 1)}`,
    `calidad=${formatDecimal(pick.data_quality, 0)}`,
    `riesgo=${pick.risk_level}`,
    `decision=${pick.decision}`,
    `motivo="${pick.reason}"`,
    `reglas_ok="${pick.passed_rules.join('; ')}"`,
    `reglas_fallidas="${pick.failed_rules.join('; ')}"`,
    `calidad_cuota=${formatDecimal(pick.odds_quality_score, 0)}`,
    `edad_cuota_min=${pick.price_age_minutes ?? '-'}`,
    `modo=${pick.safety_mode}`,
  ].join(' | ')
}

function AuditChips({ pick }: { pick: TipstrrMarketPick }) {
  const failed = pick.failed_rules.slice(0, 2)
  const passed = pick.passed_rules.slice(0, 2)
  return (
    <div className="flex flex-wrap gap-1">
      {failed.length ? failed.map((rule) => (
        <span key={rule} className="rounded-full bg-rose-50 px-2 py-1 text-[11px] font-black text-rose-700">{rule}</span>
      )) : passed.map((rule) => (
        <span key={rule} className="rounded-full bg-emerald-50 px-2 py-1 text-[11px] font-black text-emerald-700">{rule}</span>
      ))}
      <span className="rounded-full bg-slate-100 px-2 py-1 text-[11px] font-black text-slate-700">{pick.safety_mode}</span>
    </div>
  )
}

function downloadFile(filename: string, content: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}
