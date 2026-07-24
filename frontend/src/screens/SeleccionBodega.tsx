import { useEffect, useMemo, useState } from 'react'
import { getBodegas, type Bodega } from '../lib/bodegas'
import { useOperario } from '../state/OperarioContext'

const POR_PAGINA = 10

export default function SeleccionBodega() {
  const { seleccionarBodega } = useOperario()
  const [bodegas, setBodegas] = useState<Bodega[] | null>(null)
  const [error, setError] = useState(false)
  const [busqueda, setBusqueda] = useState('')
  const [pagina, setPagina] = useState(0)

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

  // Al cambiar el filtro, el resultado puede tener menos páginas que antes.
  useEffect(() => {
    setPagina(0)
  }, [busqueda])

  const totalPaginas = Math.max(1, Math.ceil(filtradas.length / POR_PAGINA))
  const paginaActual = Math.min(pagina, totalPaginas - 1)
  const visibles = filtradas.slice(paginaActual * POR_PAGINA, (paginaActual + 1) * POR_PAGINA)

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

      {totalPaginas > 1 && (
        <p className="mt-3 text-center text-sm text-slate-400">
          Página {paginaActual + 1} de {totalPaginas} ({filtradas.length} bodegas)
        </p>
      )}

      <div className="mt-4 flex-1 space-y-3 overflow-y-auto pb-6">
        {error && <p className="text-lg text-red-400">No se pudo cargar la lista de bodegas.</p>}
        {!error && bodegas === null && <p className="text-lg text-slate-300">Cargando bodegas…</p>}
        {!error && bodegas !== null && filtradas.length === 0 && (
          <p className="text-lg text-slate-300">Sin resultados para "{busqueda}".</p>
        )}
        {visibles.map((bodega) => (
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

      {totalPaginas > 1 && (
        <div className="flex gap-3 pt-2">
          <button
            type="button"
            disabled={paginaActual === 0}
            onClick={() => setPagina((p) => p - 1)}
            className="h-16 flex-1 rounded-2xl bg-slate-800 text-lg font-semibold active:bg-slate-700 disabled:opacity-40"
          >
            ← Anterior
          </button>
          <button
            type="button"
            disabled={paginaActual >= totalPaginas - 1}
            onClick={() => setPagina((p) => p + 1)}
            className="h-16 flex-1 rounded-2xl bg-slate-800 text-lg font-semibold active:bg-slate-700 disabled:opacity-40"
          >
            Siguiente →
          </button>
        </div>
      )}
    </main>
  )
}
