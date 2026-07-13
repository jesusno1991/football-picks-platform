type Props = {
  label: string
  value: string | number
  helper?: string
}

export function MetricCard({ label, value, helper }: Props) {
  return (
    <div className="card p-4">
      <div className="text-sm font-semibold text-slate-500">{label}</div>
      <div className="mt-2 text-3xl font-black text-slate-950">{value}</div>
      {helper ? <div className="mt-1 text-xs font-semibold text-slate-500">{helper}</div> : null}
    </div>
  )
}
