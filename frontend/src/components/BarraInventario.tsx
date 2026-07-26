import { useEffect, useState } from 'react'
import {
  abrirInventario,
  cerrarInventario,
  etiqueta,
  getInventarios,
  rangoFechas,
  type Inventario,
} from '../lib/inventarios'

interface Props {
  bodegaId: number
  /** El inventario que el líder está viendo; null hasta que carga. */
  seleccionado: Inventario | null
  onSeleccionar: (inv: Inventario) => void
  /** Avisa que la lista cambió (abrir/cerrar) para refrescar cierre y dashboard. */
  onCambio: () => void
}

/**
 * Cabecera del panel del líder: qué ciclo se está viendo, de cuándo a cuándo,
 * y los controles para abrirlo/cerrarlo. Sin esto no había forma de saber si
 * el cierre en pantalla era el inventario de esta semana o el de la pasada.
 *
 * Conteo ciego: aquí solo van número, fechas y avance; nunca SD.
 */
export default function BarraInventario({ bodegaId, seleccionado, onSeleccionar, onCambio }: Props) {
  const [lista, setLista] = useState<Inventario[]>([])
  const [abiertoDesplegable, setAbiertoDesplegable] = useState(false)
  const [ocupado, setOcupado] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const recargar = () => {
    getInventarios(bodegaId)
      .then((filas) => {
        setLista(filas)
        // Al entrar, se mira el vigente: el abierto, o el último cerrado.
        if (!seleccionado && filas.length > 0) {
          onSeleccionar(filas.find((f) => f.estado === 'abierto') ?? filas[0])
        }
      })
      .catch(() => setError('No se pudo cargar la lista de inventarios.'))
  }

  useEffect(recargar, [bodegaId])

  async function accion(fn: () => Promise<Inventario>, mensajeError: string) {
    setOcupado(true)
    setError(null)
    try {
      const inv = await fn()
      onSeleccionar(inv)
      const filas = await getInventarios(bodegaId)
      setLista(filas)
      onCambio()
    } catch {
      setError(mensajeError)
    } finally {
      setOcupado(false)
      setAbiertoDesplegable(false)
    }
  }

  const hayAbierto = lista.some((f) => f.estado === 'abierto')

  return (
    <div className="clay flex flex-col gap-3 rounded-tarjeta bg-superficie1 p-4 sm:p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex min-w-0 flex-col gap-1">
          <div className="flex flex-wrap items-center gap-2.5">
            <span className="text-lg font-semibold">
              {seleccionado ? etiqueta(seleccionado) : 'Sin inventarios'}
            </span>
            {seleccionado && (
              <span
                className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ${
                  seleccionado.estado === 'abierto'
                    ? 'bg-tinte-azul text-azul-suave'
                    : 'bg-superficie2 text-texto-tenue'
                }`}
              >
                <span
                  className={`h-1.5 w-1.5 rounded-full ${
                    seleccionado.estado === 'abierto' ? 'bg-exito' : 'bg-texto-tenue'
                  }`}
                />
                {seleccionado.estado === 'abierto' ? 'Abierto' : 'Cerrado'}
              </span>
            )}
          </div>
          <span className="text-sm text-texto-sec">
            {seleccionado
              ? `${rangoFechas(seleccionado)} · ${seleccionado.operarios} operario${
                  seleccionado.operarios === 1 ? '' : 's'
                } · ${seleccionado.articulos_contados} artículos contados`
              : 'Abre uno para que los operarios puedan contar en esta bodega.'}
          </span>
        </div>

        <div className="flex flex-wrap gap-2.5">
          {lista.length > 1 && (
            <button
              type="button"
              onClick={() => setAbiertoDesplegable((v) => !v)}
              aria-expanded={abiertoDesplegable}
              className="clay-tecla transicion-estado h-12 rounded-control bg-superficie2 px-4 text-sm font-semibold active:bg-grafito"
            >
              Ver anteriores ▾
            </button>
          )}
          {hayAbierto && seleccionado?.estado === 'abierto' ? (
            <button
              type="button"
              disabled={ocupado}
              onClick={() =>
                accion(() => cerrarInventario(seleccionado.id), 'No se pudo cerrar el inventario.')
              }
              className="clay-tecla transicion-estado h-12 rounded-control bg-superficie2 px-4 text-sm font-semibold active:bg-grafito disabled:opacity-50"
            >
              Cerrar inventario
            </button>
          ) : (
            !hayAbierto && (
              <button
                type="button"
                disabled={ocupado}
                onClick={() =>
                  accion(() => abrirInventario(bodegaId), 'No se pudo abrir el inventario.')
                }
                className="clay-azul transicion-estado h-12 rounded-control bg-accion px-4 text-sm font-semibold text-white active:bg-accion-claro disabled:opacity-50"
              >
                Abrir inventario
              </button>
            )
          )}
        </div>
      </div>

      {abiertoDesplegable && (
        <ul className="flex flex-col gap-1.5 border-t border-borde pt-3">
          {lista.map((inv) => (
            <li key={inv.id}>
              <button
                type="button"
                onClick={() => {
                  onSeleccionar(inv)
                  setAbiertoDesplegable(false)
                  onCambio()
                }}
                className={`transicion-estado flex w-full flex-wrap items-center justify-between gap-2 rounded-chip px-4 py-3 text-left text-sm active:bg-superficie2 ${
                  seleccionado?.id === inv.id ? 'bg-superficie2 font-semibold' : 'text-texto-sec'
                }`}
              >
                <span>{etiqueta(inv)}</span>
                <span className="text-texto-tenue">
                  {inv.estado === 'abierto' ? 'abierto' : 'cerrado'} · {rangoFechas(inv)}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}

      {error && <p className="text-sm text-critico-claro">{error}</p>}
    </div>
  )
}
