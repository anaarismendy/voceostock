import { useEffect, useMemo, useState } from 'react'
import { getBodegas, type Bodega } from '../lib/bodegas'
import { useOperario } from '../state/OperarioContext'

const POR_PAGINA = 10

export default function SeleccionBodega() {
  const { seleccionarBodega } = useOperario()
  const [bodegas, setBodegas] = useState<Bodega[] | null>(null)
  const [error, setError] = useState(false)
  const [errorSesion, setErrorSesion] = useState(false)
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
    <main className="mx-auto flex min-h-screen w-full max-w-2xl flex-col bg-fondo p-6 text-texto">
      <h1 className="text-center text-lg font-semibold">¿En qué bodega estás?</h1>

      <input
        type="text"
        value={busqueda}
        onChange={(e) => setBusqueda(e.target.value)}
        placeholder="Buscar bodega…"
        className="transicion-estado mt-6 h-16 rounded-control border border-borde-sutil bg-superficie2 px-4 text-base text-texto placeholder:text-texto-tenue focus:border-primario focus:outline-none"
      />

      {totalPaginas > 1 && (
        <p className="mt-3 text-center text-sm text-texto-sec">
          Página {paginaActual + 1} de {totalPaginas} ({filtradas.length} bodegas)
        </p>
      )}

      <div className="mt-4 flex-1 space-y-2 overflow-y-auto pb-6">
        {error && <p className="text-base text-critico">No se pudo cargar la lista de bodegas.</p>}
        {errorSesion && <p className="text-base text-critico">No se pudo abrir la sesión de conteo. Toca la bodega de nuevo.</p>}
        {!error && bodegas === null && <p className="text-base text-texto-sec">Cargando bodegas…</p>}
        {!error && bodegas !== null && filtradas.length === 0 && (
          <p className="text-base text-texto-sec">Sin resultados para "{busqueda}".</p>
        )}
        {visibles.map((bodega) => (
          <button
            key={bodega.id}
            type="button"
            onClick={() => {
              setErrorSesion(false)
              // I2: al elegir bodega se abre la sesión REAL en BD.
              seleccionarBodega(bodega).catch(() => setErrorSesion(true))
            }}
            className="transicion-estado block min-h-16 w-full rounded-control border border-borde-sutil bg-superficie1 px-5 py-4 text-left text-base font-medium capitalize active:border-primario active:bg-superficie2"
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
            className="transicion-estado h-16 flex-1 rounded-control border border-borde-sutil bg-superficie1 text-base font-semibold active:bg-superficie2 disabled:opacity-40"
          >
            ← Anterior
          </button>
          <button
            type="button"
            disabled={paginaActual >= totalPaginas - 1}
            onClick={() => setPagina((p) => p + 1)}
            className="transicion-estado h-16 flex-1 rounded-control border border-borde-sutil bg-superficie1 text-base font-semibold active:bg-superficie2 disabled:opacity-40"
          >
            Siguiente →
          </button>
        </div>
      )}
    </main>
  )
}
