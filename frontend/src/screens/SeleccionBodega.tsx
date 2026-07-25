import { useEffect, useMemo, useState } from 'react'
import { getBodegas, type Bodega } from '../lib/bodegas'
import { useOperario } from '../state/OperarioContext'

const POR_PAGINA = 9

export default function SeleccionBodega() {
  const { operario, seleccionarBodega } = useOperario()
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
    <main className="mx-auto flex min-h-screen w-full max-w-4xl flex-col gap-6 bg-pantalla p-8 text-texto">
      <div className="flex items-end justify-between">
        <h1 className="text-xl font-semibold">¿En qué bodega estás?</h1>
        <div className="text-sm text-texto-tenue">
          Hola, {operario?.nombre ?? 'operario'} · {bodegas?.length ?? '…'} bodegas
        </div>
      </div>

      <div className="clay-hundido flex h-[72px] items-center gap-4 rounded-control bg-superficie2 px-6">
        <span className="text-lg text-texto-tenue">⌕</span>
        <input
          type="text"
          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
          placeholder="Busca por nombre o código…"
          className="h-full flex-1 bg-transparent text-lg text-texto placeholder:text-texto-tenue focus:outline-none"
        />
      </div>

      {error && <p className="text-base text-critico">No se pudo cargar la lista de bodegas.</p>}
      {errorSesion && (
        <p className="text-base text-critico">No se pudo abrir la sesión de conteo. Toca la bodega de nuevo.</p>
      )}
      {!error && bodegas === null && <p className="text-base text-texto-sec">Cargando bodegas…</p>}
      {!error && bodegas !== null && filtradas.length === 0 && (
        <p className="text-base text-texto-sec">Sin resultados para "{busqueda}".</p>
      )}

      <div className="grid flex-1 grid-cols-3 content-start gap-5">
        {visibles.map((bodega) => (
          <button
            key={bodega.id}
            type="button"
            onClick={() => {
              setErrorSesion(false)
              // I2: al elegir bodega se abre la sesión REAL en BD.
              seleccionarBodega(bodega).catch(() => setErrorSesion(true))
            }}
            className="clay transicion-estado flex min-h-[158px] flex-col justify-between rounded-tarjeta bg-superficie1 p-6 text-left active:bg-superficie2"
          >
            <div className="flex flex-col gap-1.5">
              <div className="text-lg font-semibold capitalize leading-tight">{bodega.nombre}</div>
              <div className="text-sm text-texto-tenue">
                {bodega.total_articulos != null ? `${bodega.total_articulos} artículos` : ''}
              </div>
            </div>
            <div
              className={`flex items-center gap-2.5 self-start rounded-full px-3.5 py-2 text-sm ${
                bodega.en_conteo ? 'bg-tinte-azul text-azul-suave' : 'bg-superficie2 text-texto-sec'
              }`}
            >
              <span
                className={`h-2.5 w-2.5 rounded-full ${bodega.en_conteo ? 'bg-azul-texto' : 'bg-texto-tenue'}`}
              />
              {bodega.en_conteo ? 'En conteo' : 'Sin empezar'}
            </div>
          </button>
        ))}
      </div>

      {totalPaginas > 1 && (
        <div className="flex items-center gap-4">
          <button
            type="button"
            disabled={paginaActual === 0}
            onClick={() => setPagina((p) => p - 1)}
            className="clay-tecla transicion-estado h-16 flex-1 rounded-control bg-superficie2 text-base font-semibold active:bg-grafito disabled:opacity-40"
          >
            ← Anterior
          </button>
          <span className="text-sm text-texto-tenue">
            Página {paginaActual + 1} de {totalPaginas}
          </span>
          <button
            type="button"
            disabled={paginaActual >= totalPaginas - 1}
            onClick={() => setPagina((p) => p + 1)}
            className="clay-tecla transicion-estado h-16 flex-1 rounded-control bg-superficie2 text-base font-semibold active:bg-grafito disabled:opacity-40"
          >
            Siguiente →
          </button>
        </div>
      )}
    </main>
  )
}
