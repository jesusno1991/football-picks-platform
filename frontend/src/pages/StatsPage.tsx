import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { MetricCard } from '../components/MetricCard'
import { useOverview, useProfitCurve } from '../hooks/queries'

export function StatsPage() {
  const { data } = useOverview()
  const { data: curve = [] } = useProfitCurve()
  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-black">Estadísticas</h1>
      <div className="grid gap-3 md:grid-cols-4">
        <MetricCard label="Picks" value={data?.total_picks ?? 0} />
        <MetricCard label="Acierto" value={`${data?.hit_rate ?? 0}%`} />
        <MetricCard label="Profit" value={`${data?.profit ?? 0}u`} />
        <MetricCard label="Yield" value={`${data?.yield_percentage ?? 0}%`} />
      </div>
      <div className="card h-80 p-4">
        <h2 className="mb-3 text-lg font-black">Evolución acumulada</h2>
        <ResponsiveContainer width="100%" height="85%">
          <LineChart data={curve}>
            <XAxis dataKey="date" hide />
            <YAxis />
            <Tooltip />
            <Line type="monotone" dataKey="cumulative_profit" stroke="#0891b2" strokeWidth={3} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
