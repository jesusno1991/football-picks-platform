import { useEffect, useMemo, useState } from 'react'
import { CalendarDays, ChevronLeft, ChevronRight } from 'lucide-react'
import { MatchCard } from '../components/MatchCard'
import { MatchDetailPage } from './MatchDetailPage'
import { useCalendarMonth, useMatches } from '../hooks/queries'
import { formatDateInput } from '../utils/format'

function dateFromUrl() {
  const params = new URLSearchParams(window.location.search)
  const value = params.get('date')
  return value && /^\d{4}-\d{2}-\d{2}$/.test(value) ? value : formatDateInput(new Date())
}

export function HomePage() {
  const [date, setDateState] = useState(dateFromUrl)
  const [selectedId, setSelectedId] = useState<number | undefined>()
  const visibleMonth = useMemo(() => new Date(`${date}T12:00:00`), [date])
  const year = visibleMonth.getFullYear()
  const month = visibleMonth.getMonth() + 1
  const { data: matches = [], isLoading } = useMatches(date)
  const { data: calendarDays = [] } = useCalendarMonth(year, month)
  const selected = selectedId && matches.some((match) => match.id === selectedId) ? selectedId : matches[0]?.id
  const grouped = useMemo(() => matches.reduce<Record<string, typeof matches>>((acc, match) => {
    const key = `${match.competition.country} · ${match.competition.name}`
    acc[key] = acc[key] ?? []
    acc[key].push(match)
    return acc
  }, {}), [matches])

  useEffect(() => {
    const onPop = () => setDateState(dateFromUrl())
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [])

  useEffect(() => {
    if (selectedId && !matches.some((match) => match.id === selectedId)) setSelectedId(undefined)
  }, [matches, selectedId])

  const setDate = (nextDate: string, replace = false) => {
    setDateState(nextDate)
    const url = `/matches?date=${nextDate}`
    if (replace) window.history.replaceState({}, '', url)
    else window.history.pushState({}, '', url)
  }

  const shiftDate = (days: number) => {
    const next = new Date(`${date}T12:00:00`)
    next.setDate(next.getDate() + days)
    setDate(formatDateInput(next))
  }

  const today = formatDateInput(new Date())
  const selectedDate = new Date(`${date}T12:00:00`)
  const setMonthYear = (nextYear: number, nextMonth: number) => {
    const day = Math.min(selectedDate.getDate(), new Date(nextYear, nextMonth, 0).getDate())
    setDate(formatDateInput(new Date(nextYear, nextMonth - 1, day)))
  }

  return (
    <div className="grid gap-5 lg:grid-cols-[440px_1fr]">
      <section>
        <div className="card mb-4 p-4">
          <div className="flex items-center gap-2 text-lg font-black"><CalendarDays size={20} /> Partidos por fecha</div>
          <div className="mt-4 grid grid-cols-3 gap-2">
            <button className="rounded-lg border border-line px-3 py-2 font-bold" onClick={() => shiftDate(-1)}>Ayer</button>
            <button className="rounded-lg bg-brand px-3 py-2 font-bold text-white" onClick={() => setDate(today)}>Hoy</button>
            <button className="rounded-lg border border-line px-3 py-2 font-bold" onClick={() => shiftDate(1)}>Manana</button>
          </div>
          <div className="mt-3 grid grid-cols-[auto_1fr_auto] gap-2">
            <button className="rounded-lg border border-line px-3 py-2 font-bold" onClick={() => shiftDate(-1)} aria-label="Dia anterior"><ChevronLeft size={18} /></button>
            <input className="w-full rounded-lg border border-line px-3 py-2" type="date" value={date} onChange={(event) => setDate(event.target.value)} />
            <button className="rounded-lg border border-line px-3 py-2 font-bold" onClick={() => shiftDate(1)} aria-label="Dia siguiente"><ChevronRight size={18} /></button>
          </div>
          <div className="mt-3 grid grid-cols-2 gap-2">
            <select className="rounded-lg border border-line px-3 py-2 font-bold" value={month} onChange={(event) => setMonthYear(year, Number(event.target.value))}>
              {Array.from({ length: 12 }, (_, index) => index + 1).map((value) => <option key={value} value={value}>{new Date(2026, value - 1, 1).toLocaleString('es-ES', { month: 'long' })}</option>)}
            </select>
            <select className="rounded-lg border border-line px-3 py-2 font-bold" value={year} onChange={(event) => setMonthYear(Number(event.target.value), month)}>
              {Array.from({ length: 9 }, (_, index) => new Date().getFullYear() - 4 + index).map((value) => <option key={value} value={value}>{value}</option>)}
            </select>
          </div>
          <MonthCalendar selectedDate={selectedDate} selected={date} days={calendarDays} onSelect={setDate} />
        </div>
        <div className="card overflow-hidden">
          {isLoading ? <div className="p-4">Cargando partidos...</div> : null}
          {!isLoading && matches.length === 0 ? <div className="p-5 text-sm font-semibold text-slate-600">No hay partidos disponibles para esta fecha.</div> : null}
          {Object.entries(grouped).map(([competition, rows]) => (
            <div key={competition}>
              <div className="bg-slate-100 px-4 py-2 text-sm font-black text-slate-700">{competition}</div>
              {rows.map((match) => <MatchCard key={match.id} match={match} selected={match.id === selected} onSelect={setSelectedId} />)}
            </div>
          ))}
        </div>
      </section>
      <section>{selected ? <MatchDetailPage matchId={selected} /> : <div className="card p-6">Selecciona un partido.</div>}</section>
    </div>
  )
}

type CalendarCellStats = { date: string; match_count: number; pick_count: number; publishable_pick_count: number; published_pick_count: number }

function MonthCalendar({ selectedDate, selected, days, onSelect }: { selectedDate: Date; selected: string; days: CalendarCellStats[]; onSelect: (date: string) => void }) {
  const first = new Date(selectedDate.getFullYear(), selectedDate.getMonth(), 1)
  const last = new Date(selectedDate.getFullYear(), selectedDate.getMonth() + 1, 0)
  const startOffset = (first.getDay() + 6) % 7
  const byDate = new Map(days.map((day) => [day.date, day]))
  const cells: { key: string; date: string; label: string; stats?: CalendarCellStats }[] = [
    ...Array.from({ length: startOffset }, (_, index) => ({ key: `empty-${index}`, date: '', label: '' })),
    ...Array.from({ length: last.getDate() }, (_, index) => {
      const day = new Date(selectedDate.getFullYear(), selectedDate.getMonth(), index + 1)
      const iso = formatDateInput(day)
      return { key: iso, date: iso, label: String(index + 1), stats: byDate.get(iso) }
    }),
  ]
  return (
    <div className="mt-4">
      <div className="mb-2 grid grid-cols-7 text-center text-xs font-black uppercase text-slate-500">
        {['L', 'M', 'X', 'J', 'V', 'S', 'D'].map((day) => <span key={day}>{day}</span>)}
      </div>
      <div className="grid grid-cols-7 gap-1">
        {cells.map((cell) => cell.date ? (
          <button key={cell.key} onClick={() => onSelect(cell.date)} className={`min-h-[66px] rounded-lg border p-1 text-left text-xs ${cell.date === selected ? 'border-cyan-500 bg-cyan-50' : 'border-line bg-white'}`}>
            <div className="font-black">{cell.label}</div>
            <div className="mt-1 font-bold text-slate-600">{cell.stats?.match_count ?? 0} partidos</div>
            <div className="font-bold text-cyan-700">{cell.stats?.publishable_pick_count ?? 0} publicables</div>
            <div className="font-bold text-slate-500">{cell.stats?.pick_count ?? 0} pred.</div>
          </button>
        ) : <div key={cell.key} />)}
      </div>
    </div>
  )
}
