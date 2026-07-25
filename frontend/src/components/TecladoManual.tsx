import { useEffect, useMemo, useState } from 'react'
import { getArticulos, type ArticuloResumen } from '../lib/articulos'

interface Props {
  bodegaId?: number
  onEnviar: (texto: string) => void
}

const TECLAS = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '.', '0', '⌫'] as const

/**
 * Fallback permanente (C5): siempre visible junto al micrófono, para que si
 * falla el reconocimiento de voz en el auditorio la demo siga sin pausa.
 * Manda el mismo POST /conteos que la voz (payload_texto), solo que con
 * `fuente: manual` — el contrato congelado no tiene un campo estructurado
 * de articulo_id/cantidad, así que el teclado arma texto igual que dictarlo.
 */
export default function TecladoManual({ bodegaId, onEnviar }: Props) {
  const [articulos, setArticulos] = useState<ArticuloResumen[] | null>(null)
  const [busqueda, setBusqueda] = useState('')
  const [seleccionado, setSeleccionado] = useState<ArticuloResumen | null>(null)
  const [cantidad, setCantidad] = useState('')

  useEffect(() => {
    getArticulos(bodegaId)
      .then(setArticulos)
      .catch(() => setArticulos([]))
  }, [bodegaId])

  const sugerencias = useMemo(() => {
    if (!articulos || seleccionado) return []
    const q = busqueda.trim().toLowerCase()
    if (q.length < 2) return []
    return articulos.filter((a) => a.articulo_nombre.toLowerCase().includes(q)).slice(0, 6)
  }, [articulos, busqueda, seleccionado])

  function elegirArticulo(a: ArticuloResumen) {
    setSeleccionado(a)
    setBusqueda(a.articulo_nombre)
  }

  function cambiarBusqueda(valor: string) {
    setBusqueda(valor)
    setSeleccionado(null)
  }

  function agregarTecla(t: string) {
    if (t === '.' && cantidad.includes('.')) return
    setCantidad((c) => (c.length >= 6 ? c : c + t))
  }

  function borrar() {
    setCantidad((c) => c.slice(0, -1))
  }

  function registrar() {
    if (!seleccionado || !cantidad) return
    onEnviar(`${cantidad} ${seleccionado.articulo_nombre}`)
    setSeleccionado(null)
    setBusqueda('')
    setCantidad('')
  }

  return (
    <div className="w-full max-w-md rounded-tarjeta border border-borde-sutil bg-superficie1 p-4">
      <p className="text-sm font-medium text-texto-sec">⌨️ ¿Falla el micrófono? Usa el teclado.</p>

      <div className="relative mt-2">
        <input
          type="text"
          value={busqueda}
          onChange={(e) => cambiarBusqueda(e.target.value)}
          placeholder="Buscar artículo…"
          className="transicion-estado h-16 w-full rounded-control border border-borde-sutil bg-superficie2 px-4 text-base text-texto placeholder:text-texto-tenue focus:border-primario focus:outline-none"
        />
        {sugerencias.length > 0 && (
          <ul className="absolute z-10 mt-1 w-full overflow-hidden rounded-control border border-borde-fuerte bg-superficie2">
            {sugerencias.map((a) => (
              <li key={a.articulo_id}>
                <button
                  type="button"
                  onClick={() => elegirArticulo(a)}
                  className="transicion-estado block min-h-16 w-full px-4 py-3 text-left text-base active:bg-tinte"
                >
                  {a.articulo_nombre}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {seleccionado && (
        <div className="mt-4">
          <p className="text-lg font-semibold tabular-nums">
            {cantidad || '0'} <span className="text-base font-normal text-texto-sec">{seleccionado.unidad}</span>
          </p>

          <div className="mt-2 grid grid-cols-3 gap-2">
            {TECLAS.map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => (t === '⌫' ? borrar() : agregarTecla(t))}
                className="transicion-estado h-16 rounded-control bg-superficie2 text-lg font-semibold active:bg-tinte"
              >
                {t}
              </button>
            ))}
          </div>

          <button
            type="button"
            disabled={!cantidad}
            onClick={registrar}
            className="transicion-estado mt-3 h-[72px] w-full rounded-control bg-primario text-lg font-semibold text-texto active:bg-primario-hover disabled:opacity-50"
          >
            Registrar
          </button>
        </div>
      )}
    </div>
  )
}
