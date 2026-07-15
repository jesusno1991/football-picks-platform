import { useState } from 'react'
import { PredictionTable } from '../components/PredictionTable'
import { usePredictions, useTipstrrMarketPicks } from '../hooks/queries'
import type { Prediction, TipstrrMarketPick } from '../types/api'
import { formatDateInput, formatDecimal, formatPercent } from '../utils/format'

function dateFromUrl() {
  const params = new URLSearchParams(window.location.search)
  const value = params.get('date')
  return value && /^\d{4}-\d{2}-\d{2}$/.test(value) ? value : formatDateInput(new Date())
}

export function PicksPage({ onlyPublishable = false }: { onlyPublishable?: boolean }) {
  const [date, setDateState] = useState(dateFromUrl)
  const [viewMode, setViewMode] = useState<'table' | 'export'>('table')
  const { data: predictions = [], isLoading: predictionsLoading } = usePredictions(undefined, date)
  const { data: publicablePicks = [], isLoading: picksLoading } = useTipstrrMarketPicks(date, 'PUBLICABLE')
  const { data: allMarketRows = [] } = useTipstrrMarketPicks(date)
  const isLoading = onlyPublishable ? picksLoading : predictionsLoading
  const data = onlyPublishable ? publicablePicks : predictions

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
              ? 'Solo aparecen las señales validas para publicar. Over 1.5 y Over 2.5 estan bloqueados.'
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
      {!onlyPublishable ? (
        <div className="card flex flex-col gap-3 p-3 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="text-sm font-black text-slate-900">Vista de predicciones</div>
            <div className="text-xs font-semibold text-slate-500">
              Puedes ver la tabla normal o descargar todos los picks de la fecha para analizarlos en ChatGPT.
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
      ) : null}
      {isLoading ? <div className="card p-4 font-bold text-slate-600">Cargando datos reales de la fecha...</div> : null}
      {!isLoading && data.length === 0 ? (
        <div className="card p-5 text-sm font-semibold text-slate-600">
          {onlyPublishable
            ? `No hay picks publicables en esta fecha. Candidatos analizados: ${allMarketRows.length}.`
            : 'No hay predicciones generadas para esta fecha.'}
        </div>
      ) : onlyPublishable ? (
        <MarketPickTable picks={publicablePicks} />
      ) : viewMode === 'export' ? (
        <ChatGptExportPanel date={date} predictions={predictions} marketRows={allMarketRows} publicablePicks={publicablePicks} />
      ) : (
        <PredictionTable predictions={predictions} />
      )}
    </div>
  )
}

function ChatGptExportPanel({
  date,
  predictions,
  marketRows,
  publicablePicks,
}: {
  date: string
  predictions: Prediction[]
  marketRows: TipstrrMarketPick[]
  publicablePicks: TipstrrMarketPick[]
}) {
  const fileBase = `picks-predicciones-${date}`
  const prompt = [
    'Analiza estos picks prepartido como auditor externo.',
    'Prioriza mercados con EV positivo, probabilidad alta, cuota coherente, Merlin Score alto y buen control de riesgo.',
    'Separa picks publicables, picks a vigilar y descartes. No inventes datos que no vengan en el archivo.',
  ].join(' ')

  return (
    <div className="card p-5">
      <div className="grid gap-3 md:grid-cols-4">
        <ExportMetric label="Predicciones" value={predictions.length} />
        <ExportMetric label="Mercados evaluados" value={marketRows.length} />
        <ExportMetric label="Picks publicables" value={publicablePicks.length} />
        <ExportMetric label="Fecha" value={date} />
      </div>
      <div className="mt-5 rounded-2xl border border-line bg-slate-50 p-4">
        <div className="text-sm font-black text-slate-900">Archivo para enviar a ChatGPT</div>
        <p className="mt-1 text-sm font-semibold text-slate-600">
          Descarga el JSON completo si quieres pasarle todos los datos estructurados. El TXT incluye todos los picks en formato legible con un prompt inicial.
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          <button
            className="rounded-full bg-cyan-500 px-4 py-2 text-sm font-black text-white"
            onClick={() => downloadFile(`${fileBase}.json`, JSON.stringify(buildExportJson(date, predictions, marketRows, publicablePicks), null, 2), 'application/json;charset=utf-8')}
          >
            Descargar JSON completo
          </button>
          <button
            className="rounded-full border border-line bg-white px-4 py-2 text-sm font-black text-slate-800"
            onClick={() => downloadFile(`${fileBase}.txt`, buildChatGptText(date, prompt, predictions, marketRows, publicablePicks), 'text/plain;charset=utf-8')}
          >
            Descargar TXT para ChatGPT
          </button>
        </div>
      </div>
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

function ExportMetric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-2xl border border-line bg-white p-4">
      <div className="text-xs font-black uppercase text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-black text-slate-950">{value}</div>
    </div>
  )
}

function MarketPickTable({ picks }: { picks: TipstrrMarketPick[] }) {
  const [sortKey, setSortKey] = useState<'probability' | 'ev' | 'merlin' | 'odds'>('probability')
  const sortedPicks = [...picks].sort((left, right) => {
    if (sortKey === 'probability') return value(right.model_probability) - value(left.model_probability)
    if (sortKey === 'ev') return value(right.expected_value) - value(left.expected_value)
    if (sortKey === 'merlin') return value(right.merlin_score) - value(left.merlin_score)
    return value(right.market_odds) - value(left.market_odds)
  })

  return (
    <div className="card overflow-hidden">
      <div className="flex flex-wrap items-center gap-2 border-b border-line bg-white p-3 text-xs font-black">
        <span className="text-slate-500">Ordenar por:</span>
        <SortButton active={sortKey === 'probability'} onClick={() => setSortKey('probability')} label="Mayor probabilidad" />
        <SortButton active={sortKey === 'ev'} onClick={() => setSortKey('ev')} label="Mejor EV" />
        <SortButton active={sortKey === 'merlin'} onClick={() => setSortKey('merlin')} label="Merlin Score" />
        <SortButton active={sortKey === 'odds'} onClick={() => setSortKey('odds')} label="Mayor cuota" />
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

function value(input?: number | null) {
  return input ?? -999
}

function buildExportJson(date: string, predictions: Prediction[], marketRows: TipstrrMarketPick[], publicablePicks: TipstrrMarketPick[]) {
  return {
    export_type: 'football_pre_match_picks_for_chatgpt',
    exported_at: new Date().toISOString(),
    date,
    summary: {
      predictions: predictions.length,
      market_evaluations: marketRows.length,
      publishable_picks: publicablePicks.length,
    },
    publicable_picks: publicablePicks.map(normalizeMarketPickForExport),
    market_evaluations: marketRows.map(normalizeMarketPickForExport),
    predictions: predictions.map(normalizePredictionForExport),
  }
}

function buildChatGptText(
  date: string,
  prompt: string,
  predictions: Prediction[],
  marketRows: TipstrrMarketPick[],
  publicablePicks: TipstrrMarketPick[],
) {
  const lines = [
    'EXPORTACION FOOTBALL PICKS PLATFORM',
    `Fecha analizada: ${date}`,
    `Exportado: ${new Date().toISOString()}`,
    '',
    'PROMPT RECOMENDADO',
    prompt,
    '',
    'RESUMEN',
    `Predicciones historicas: ${predictions.length}`,
    `Mercados evaluados: ${marketRows.length}`,
    `Picks publicables: ${publicablePicks.length}`,
    '',
    'PICKS PUBLICABLES',
    ...publicablePicks.map((pick, index) => formatMarketPickLine(index + 1, pick)),
    '',
    'TODOS LOS MERCADOS EVALUADOS',
    ...marketRows.map((pick, index) => formatMarketPickLine(index + 1, pick)),
    '',
    'PREDICCIONES GUARDADAS',
    ...predictions.map((prediction, index) => formatPredictionLine(index + 1, prediction)),
  ]

  return lines.join('\n')
}

function normalizeMarketPickForExport(pick: TipstrrMarketPick) {
  return {
    match_id: pick.match_id,
    external_id: pick.external_id,
    match_name: pick.match_name,
    kickoff_at: pick.kickoff_at,
    country: pick.country,
    competition: pick.competition_name,
    group: pick.group,
    market_family: pick.family,
    market_label: pick.label,
    period: pick.period,
    team_scope: pick.team_scope,
    selection: pick.selection,
    line: pick.line ?? null,
    model_probability: pick.model_probability ?? null,
    fair_odds: pick.fair_odds ?? null,
    market_odds: pick.market_odds ?? null,
    bookmaker: pick.bookmaker ?? null,
    expected_value: pick.expected_value ?? null,
    merlin_score: pick.merlin_score,
    data_quality: pick.data_quality,
    risk_level: pick.risk_level,
    decision: pick.decision,
    reason: pick.reason,
  }
}

function normalizePredictionForExport(prediction: Prediction) {
  return {
    id: prediction.id,
    match_id: prediction.match_id,
    match_name: prediction.match ? `${prediction.match.home_team.name} vs ${prediction.match.away_team.name}` : null,
    kickoff_at: prediction.match?.kickoff_at ?? null,
    competition: prediction.match?.competition.name ?? null,
    country: prediction.match?.competition.country ?? null,
    market: prediction.market,
    selection: prediction.selection,
    line: prediction.line ?? null,
    predicted_probability: prediction.predicted_probability ?? null,
    fair_odds: prediction.fair_odds ?? null,
    available_odds: prediction.available_odds ?? null,
    expected_value: prediction.expected_value ?? null,
    confidence: prediction.confidence ?? null,
    recommended_stake: prediction.recommended_stake,
    status: prediction.status,
    explanation: prediction.explanation,
    result: prediction.result ?? null,
    profit: prediction.profit ?? null,
  }
}

function formatMarketPickLine(index: number, pick: TipstrrMarketPick) {
  return [
    `${index}. ${pick.match_name}`,
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
    `EV=${formatDecimal(pick.expected_value, 3)}`,
    `Merlin=${formatDecimal(pick.merlin_score, 1)}`,
    `calidad=${formatDecimal(pick.data_quality, 0)}`,
    `riesgo=${pick.risk_level}`,
    `decision=${pick.decision}`,
    `motivo="${pick.reason}"`,
  ].join(' | ')
}

function formatPredictionLine(index: number, prediction: Prediction) {
  const matchName = prediction.match ? `${prediction.match.home_team.name} vs ${prediction.match.away_team.name}` : `match_id=${prediction.match_id}`
  return [
    `${index}. ${matchName}`,
    prediction.match ? `${prediction.match.competition.country} / ${prediction.match.competition.name}` : 'competicion=-',
    `mercado=${prediction.market}`,
    `seleccion=${prediction.selection}`,
    `linea=${prediction.line ?? '-'}`,
    `prob=${formatPercent(prediction.predicted_probability)}`,
    `cuota_justa=${formatDecimal(prediction.fair_odds, 2)}`,
    `cuota=${formatDecimal(prediction.available_odds, 2)}`,
    `EV=${formatDecimal(prediction.expected_value, 3)}`,
    `confianza=${formatPercent(prediction.confidence)}`,
    `stake=${formatDecimal(prediction.recommended_stake, 1)}`,
    `estado=${prediction.status}`,
    `explicacion="${prediction.explanation}"`,
  ].join(' | ')
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
