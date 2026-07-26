import { Check, Search, X } from 'lucide-react'
import { useMemo, useState } from 'react'
import type { ArticuloResumen } from '../lib/articulos'
import { filtrarArticulos } from '../lib/inventario'

interface Props {
  articulos: readonly ArticuloResumen[]
  contados: ReadonlySet<number>
  onCerrar: () => void
}

/**
 * Inventario de la bodega: qué artículos pertenecen a esta bodega y cuáles
 * faltan por contar. Antes de esto el operario tenía que adivinar qué dictar.
 *
 * Conteo ciego: muestra nombre y unidad, NUNCA el SD — /articulos no lo trae.
 */
export default function ListaInventario({ articulos, contados, onCerrar }: Props) {
  const [busqueda, setBusqueda] = useState('')
  const [soloPendientes, setSoloPendientes] = useState(false)

  const visibles = useMemo(
    () => filtrarArticulos(articulos, busqueda, soloPendientes ? contados : null),
    [articulos, busqueda, soloPendientes, contados],
  )
  const hechos = useMemo(
    () => articulos.filter((a) => contados.has(a.articulo_id)).length,
    [articulos, contados],
  )

  return (
    <div className="clay animar-entrada flex w-full max-w-lg flex-col gap-3 rounded-tarjeta bg-superficie1 p-4 sm:p-5">
      <div className="flex items-center justify-between gap-3">
        <p className="text-base font-semibold sm:text-lg">Inventario de la bodega</p>
        <button
          type="button"
          onClick={onCerrar}
          aria-label="Cerrar inventario"
          className="transicion-estado flex h-11 w-11 shrink-0 items-center justify-center rounded-control bg-superficie2 active:bg-grafito"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      <div className="clay-hundido flex h-14 items-center gap-3 rounded-control bg-superficie2 px-4">
        <Search className="h-5 w-5 shrink-0 text-texto-tenue" />
        <input
          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
          placeholder="Buscar artículo…"
          aria-label="Buscar artículo"
          className="w-full bg-transparent text-base text-texto placeholder:text-texto-tenue focus:outline-none"
        />
      </div>

      <button
        type="button"
        role="switch"
        aria-checked={soloPendientes}
        onClick={() => setSoloPendientes((v) => !v)}
        className={`transicion-estado h-12 shrink-0 self-start rounded-chip px-4 text-sm font-semibold ${
          soloPendientes ? 'clay-tecla bg-superficie2 text-texto' : 'bg-superficie2/50 text-texto-sec'
        }`}
      >
        Solo pendientes
      </button>

      <ul className="flex max-h-[45vh] flex-col overflow-y-auto">
        {visibles.length === 0 && (
          <li className="py-4 text-center text-base text-texto-sec">Ningún artículo coincide.</li>
        )}
        {visibles.map((a) => {
          const contado = contados.has(a.articulo_id)
          return (
            <li
              key={a.articulo_id}
              className="flex items-center gap-3 border-b border-borde py-3 last:border-b-0"
            >
              <span className="flex h-6 w-6 shrink-0 items-center justify-center">
                {contado && <Check className="h-5 w-5 text-exito-claro" aria-label="Ya contado" />}
              </span>
              <span
                className={`min-w-0 flex-1 truncate text-sm capitalize sm:text-base ${
                  contado ? 'text-texto-tenue line-through' : 'text-texto'
                }`}
              >
                {a.articulo_nombre.toLowerCase()}
              </span>
              <span className="shrink-0 text-xs text-texto-tenue sm:text-sm">{a.unidad}</span>
            </li>
          )
        })}
      </ul>

      <p className="text-sm text-texto-sec" aria-live="polite">
        {hechos} contados · {articulos.length - hechos} pendientes de {articulos.length}
      </p>
    </div>
  )
}
