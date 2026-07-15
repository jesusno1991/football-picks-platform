import { useState } from 'react'
import { usePlayers } from '../hooks/queries'

export function PlayersPage() {
  const [q, setQ] = useState('')
  const { data: players = [], isLoading } = usePlayers(q)
  return (
    <div className="space-y-4">
      <div className="card p-5">
        <h2 className="text-2xl font-black">Jugadores</h2>
        <p className="text-sm font-semibold text-slate-500">Ficha preparada para jugadores, estadísticas y lesiones cuando el proveedor lo entregue.</p>
        <input value={q} onChange={(event) => setQ(event.target.value)} className="mt-4 w-full rounded-lg border border-line px-3 py-2" placeholder="Buscar jugador..." />
      </div>
      <div className="card overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500"><tr><th className="px-3 py-3">Jugador</th><th className="px-3 py-3">Nacionalidad</th><th className="px-3 py-3">Posición</th><th className="px-3 py-3">Equipo</th></tr></thead>
          <tbody>
            {players.map((player, index) => (
              <tr key={String(player.id ?? index)} className="border-t border-slate-100">
                <td className="px-3 py-3 font-black">{String(player.nombre ?? 'No disponible')}</td>
                <td className="px-3 py-3">{String(player.nacionalidad ?? 'No disponible')}</td>
                <td className="px-3 py-3">{String(player.posicion ?? 'No disponible')}</td>
                <td className="px-3 py-3">{String(player.equipo_actual_id ?? 'No disponible')}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!isLoading && !players.length ? <div className="p-5 text-sm font-semibold text-slate-600">No disponible: jugadores no sincronizados todavía.</div> : null}
      </div>
    </div>
  )
}
