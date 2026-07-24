import { useEffect, useMemo, useState } from 'react'
import { getBodegas, type Bodega } from '../lib/bodegas'
import { useOperario } from '../state/OperarioContext'

export default function SeleccionBodega() {
  const { seleccionarBodega } = useOperario()
  const [bodegas, setBodegas] = useState<Bodega[] | null>(null)
  const [error, setError] = useState(false)
  const [busqueda, setBusqueda] = useState('')

  useEffect(() => {
    getBodegas()
      .then(setBodegas)
      .catch(() => setError(true))
  }, [])

  const filtradas = useMemo(() => {
    if (!bodegas) return []
    const q = busqueda.trim().toLowerCase()
    if (!q) return bodegas
    return bodegas.filter((b) => b.nombre.toLowerCase().includes(q))
  }, [bodegas, busqueda])

  return (
    <main className="flex min-h-screen flex-col bg-slate-900 p-6 text-white">
      <h1 className="text-center text-2xl font-bold">¿En qué bodega estás?</h1>

      <input
        type="text"
        value={busqueda}
        onChange={(e) => setBusqueda(e.target.value)}
        placeholder="Buscar bodega…"
        className="mt-6 h-16 rounded-2xl bg-slate-800 px-4 text-xl text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-white"
      />

      <div className="mt-4 flex-1 space-y-3 overflow-y-auto pb-6">
        {error && <p className="text-lg text-red-400">No se pudo cargar la lista de bodegas.</p>}
        {!error && bodegas === null && <p className="text-lg text-slate-300">Cargando bodegas…</p>}
        {!error && bodegas !== null && filtradas.length === 0 && (
          <p className="text-lg text-slate-300">Sin resultados para "{busqueda}".</p>
        )}
        {filtradas.map((bodega) => (
          <button
            key={bodega.id}
            type="button"
            onClick={() => seleccionarBodega(bodega)}
            className="block min-h-16 w-full rounded-2xl bg-slate-800 px-5 py-4 text-left text-xl font-medium capitalize active:bg-slate-700"
          >
            {bodega.nombre}
          </button>
        ))}
      </div>
    </main>
  )
}
