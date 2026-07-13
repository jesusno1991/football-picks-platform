import type { Prediction } from '../types/api'
import { formatDecimal, formatPercent, marketLabel } from '../utils/format'

export function PredictionTable({ predictions }: { predictions: Prediction[] }) {
  return (
    <div className="card overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
          <tr>
            <th className="px-3 py-3">Mercado</th>
            <th className="px-3 py-3">Probabilidad</th>
            <th className="px-3 py-3">Cuota justa</th>
            <th className="px-3 py-3">Cuota</th>
            <th className="px-3 py-3">EV</th>
            <th className="px-3 py-3">Stake</th>
            <th className="px-3 py-3">Estado</th>
          </tr>
        </thead>
        <tbody>
          {predictions.map((prediction) => (
            <tr key={prediction.id} className="border-t border-slate-100">
              <td className="px-3 py-3 font-bold">{marketLabel(prediction.market, prediction.selection, prediction.line)}</td>
              <td className="px-3 py-3">{formatPercent(prediction.predicted_probability)}</td>
              <td className="px-3 py-3">{formatDecimal(prediction.fair_odds)}</td>
              <td className="px-3 py-3">{formatDecimal(prediction.available_odds)}</td>
              <td className="px-3 py-3">{formatDecimal(prediction.expected_value, 3)}</td>
              <td className="px-3 py-3">{prediction.recommended_stake}u</td>
              <td className="px-3 py-3">
                <span className="rounded-full bg-cyan-100 px-2 py-1 text-xs font-bold text-cyan-800">{prediction.status}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
