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
      <div className="w-full max-w-lg rounded-3xl bg-slate-800 p-8 text-center">
        <p className="text-5xl font-bold">✓ Recorrido completo</p>
        <p className="mt-3 text-2xl text-slate-300">
          Contaste los {progreso.total} artículos de la guía.
        </p>
        <button
          type="button"
          onClick={onReiniciar}
          className="mt-8 h-16 rounded-2xl bg-white px-8 text-xl font-semibold text-slate-900 active:bg-slate-200"
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
    <div className="w-full max-w-lg rounded-3xl bg-slate-800 p-6 text-center">
      <p className="text-lg font-medium text-slate-400">Cuenta ahora:</p>
      <p className="mt-1 text-4xl font-bold leading-tight">{objetivo.articulo_nombre}</p>
      <p className="mt-1 text-2xl text-slate-300">en {objetivo.unidad}</p>

      <p className="mt-4 text-3xl font-semibold tabular-nums">
        {cantidad || '0'} <span className="text-lg font-normal text-slate-400">{objetivo.unidad}</span>
      </p>

      <div className="mt-3 grid grid-cols-3 gap-2">
        {TECLAS.map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => (t === '⌫' ? setCantidad((c) => c.slice(0, -1)) : agregarTecla(t))}
            className="h-16 rounded-xl bg-slate-700 text-2xl font-semibold active:bg-slate-600"
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
            estadoVoz === 'escuchando' ? 'animate-pulse bg-red-600' : 'bg-emerald-600 active:bg-emerald-500'
          }`}
        >
          <Mic className="h-7 w-7 text-white" />
        </button>
        <button
          type="button"
          disabled={!cantidad || enviando}
          onClick={registrar}
          className="h-16 flex-1 rounded-2xl bg-white text-xl font-semibold text-slate-900 active:bg-slate-200 disabled:opacity-50"
        >
          Registrar
        </button>
      </div>

      <button
        type="button"
        onClick={saltar}
        disabled={enviando}
        className="mt-4 h-14 w-full rounded-2xl text-lg font-medium text-slate-300 active:bg-slate-700 disabled:opacity-50"
      >
        Saltar este artículo →
      </button>

      {estadoVoz === 'escuchando' && <p className="mt-2 text-sm text-slate-400">Escuchando la cantidad…</p>}
    </div>
  )
}
