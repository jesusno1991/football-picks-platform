import { PredictionTable } from '../components/PredictionTable'
import { usePredictions } from '../hooks/queries'

export function PicksPage() {
  const { data = [] } = usePredictions()
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-black">Picks prepartido</h1>
        <p className="text-sm font-semibold text-slate-500">Solo se muestran señales generadas antes del inicio.</p>
      </div>
      <PredictionTable predictions={data} />
    </div>
  )
}
