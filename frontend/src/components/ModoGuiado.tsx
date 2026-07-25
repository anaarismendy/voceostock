import { Mic } from 'lucide-react'
import { useState } from 'react'
import type { ArticuloResumen } from '../lib/articulos'
import type { ResumenProgreso } from '../lib/progreso'
import { useVoz } from '../lib/useVoz'

interface Props {
  objetivo: ArticuloResumen | null
  progreso: ResumenProgreso
  enviando: boolean
  /** Registra `cantidadTexto` (dicha o tecleada) para el artículo objetivo. */
  onRegistrar: (cantidadTexto: string, articulo: ArticuloResumen) => void
  onSaltar: (articulo: ArticuloResumen) => void
  onReiniciar: () => void
}

const TECLAS = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '.', '0', '⌫'] as const

/**
 * Modo guiado (C8): el sistema le dice al operario QUÉ contar ahora, en vez de
 * que él recuerde la lista. Garantiza cobertura del checklist sin fatiga. El
 * operario solo aporta la cantidad (voz o teclado); el artículo lo fija la
 * guía. Nunca muestra stock teórico (conteo ciego).
 */
export default function ModoGuiado({ objetivo, progreso, enviando, onRegistrar, onSaltar, onReiniciar }: Props) {
  const [cantidad, setCantidad] = useState('')

  const { estado: estadoVoz, escuchar } = useVoz((texto) => {
    if (objetivo) onRegistrar(texto, objetivo)
  })

  if (!objetivo) {
    return (
      <div className="clay animar-entrada w-full max-w-lg rounded-tarjeta bg-superficie1 p-8 text-center">
        <p className="text-xl font-semibold text-exito-claro">✓ Recorrido completo</p>
        <p className="mt-3 text-base text-texto-sec">
          Contaste los {progreso.total} artículos de la guía.
        </p>
        <button
          type="button"
          onClick={onReiniciar}
          className="clay-azul transicion-estado mt-8 h-[88px] rounded-control bg-accion px-8 text-lg font-semibold text-white active:bg-accion-claro"
        >
          Revisar de nuevo
        </button>
      </div>
    )
  }

  function agregarTecla(t: string) {
    if (t === '.' && cantidad.includes('.')) return
    setCantidad((c) => (c.length >= 6 ? c : c + t))
  }

  function registrar() {
    if (!cantidad || !objetivo) return
    onRegistrar(cantidad, objetivo)
    setCantidad('')
  }

  function saltar() {
    if (!objetivo) return
    setCantidad('')
    onSaltar(objetivo)
  }

  return (
    <div className="clay animar-entrada w-full max-w-lg rounded-tarjeta bg-superficie1 p-6 text-center">
      <p className="text-sm tracking-widest text-texto-tenue">CUENTA AHORA</p>
      <p className="mt-2 text-xl font-semibold leading-tight">{objetivo.articulo_nombre}</p>
      <p className="mt-1 text-base text-texto-sec">en {objetivo.unidad}</p>

      <p className="mt-4 text-xl font-semibold tabular-nums">
        {cantidad || '0'} <span className="text-base font-normal text-texto-sec">{objetivo.unidad}</span>
      </p>

      <div className="mt-3 grid grid-cols-3 gap-2">
        {TECLAS.map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => (t === '⌫' ? setCantidad((c) => c.slice(0, -1)) : agregarTecla(t))}
            className="clay-tecla transicion-estado h-16 rounded-control bg-superficie2 text-lg font-semibold active:bg-grafito"
          >
            {t}
          </button>
        ))}
      </div>

      <div className="mt-4 flex items-center gap-3">
        <button
          type="button"
          onClick={escuchar}
          disabled={enviando || estadoVoz === 'escuchando'}
          aria-label="Decir la cantidad por voz"
          className={`flex h-16 w-16 shrink-0 items-center justify-center rounded-full ${
            estadoVoz === 'escuchando' ? 'animar-respira bg-accion' : 'clay-azul bg-accion active:bg-accion-claro'
          }`}
        >
          <Mic className="h-7 w-7 text-white" />
        </button>
        <button
          type="button"
          disabled={!cantidad || enviando}
          onClick={registrar}
          className="clay-azul transicion-estado h-[72px] flex-1 rounded-control bg-accion text-lg font-semibold text-white active:bg-accion-claro disabled:opacity-50"
        >
          Registrar
        </button>
      </div>

      <button
        type="button"
        onClick={saltar}
        disabled={enviando}
        className="transicion-estado mt-4 h-16 w-full rounded-control text-base font-medium text-texto-sec active:bg-superficie2 disabled:opacity-50"
      >
        Saltar este artículo →
      </button>

      {estadoVoz === 'escuchando' && <p className="mt-2 text-sm text-texto-sec">Escuchando la cantidad…</p>}
    </div>
  )
}
