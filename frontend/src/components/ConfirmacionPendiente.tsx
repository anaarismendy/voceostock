import { useEffect, useState } from 'react'
import type { Candidato } from '../lib/conteos'
import { interpretarRespuestaVoz } from '../lib/resolverVoz'
import { useVoz } from '../lib/useVoz'

interface Props {
  tokenPendiente: string
  pregunta: string
  candidatos: Candidato[] | null
  enviando: boolean
  onResponder: (respuesta: string) => void
}

/**
 * El "momento estelar de la demo" (plan_por_persona.md, C4): la pregunta se
 * lee en voz alta al aparecer; candidatos se responden tocando (ambigüedad)
 * o los botones Sí/No + un campo numérico (anomalía/baja_confianza) — la
 * respuesta hablada es un camino adicional, no el único, para no depender
 * del reconocimiento en el instante que más importa.
 */
export default function ConfirmacionPendiente({ tokenPendiente, pregunta, candidatos, enviando, onResponder }: Props) {
  const [cantidadManual, setCantidadManual] = useState('')

  const { estado: estadoVoz, escuchar, hablar } = useVoz((texto) => {
    const respuesta = interpretarRespuestaVoz(texto, candidatos)
    if (respuesta) onResponder(respuesta)
  })

  // Solo debe releer la pregunta cuando cambia el token (una pregunta nueva),
  // no en cada render de `hablar`/`pregunta`.
  useEffect(() => {
    hablar(pregunta)
  }, [tokenPendiente])

  return (
    <div className="w-full max-w-lg rounded-3xl bg-slate-800 p-8 text-center">
      <p className="text-4xl font-semibold">{pregunta}</p>

      {candidatos && (
        <div className="mt-8 flex flex-col gap-4">
          {candidatos.map((c) => (
            <button
              key={c.articulo_id}
              type="button"
              disabled={enviando}
              onClick={() => onResponder(`articulo_id:${c.articulo_id}`)}
              className="min-h-16 rounded-2xl bg-white px-6 py-4 text-xl font-medium text-slate-900 active:bg-slate-200 disabled:opacity-50"
            >
              {c.articulo_nombre}
            </button>
          ))}
        </div>
      )}

      {!candidatos && (
        <>
          <div className="mt-8 flex justify-center gap-6">
            <button
              type="button"
              disabled={enviando}
              onClick={() => onResponder('si')}
              className="h-20 w-32 rounded-2xl bg-emerald-600 text-2xl font-semibold active:bg-emerald-500 disabled:opacity-50"
            >
              Sí
            </button>
            <button
              type="button"
              disabled={enviando}
              onClick={() => onResponder('no')}
              className="h-20 w-32 rounded-2xl bg-red-600 text-2xl font-semibold active:bg-red-500 disabled:opacity-50"
            >
              No
            </button>
          </div>

          <form
            className="mt-6 flex justify-center gap-3"
            onSubmit={(e) => {
              e.preventDefault()
              if (cantidadManual.trim()) onResponder(`cantidad:${cantidadManual.trim()}`)
            }}
          >
            <input
              type="number"
              inputMode="decimal"
              value={cantidadManual}
              onChange={(e) => setCantidadManual(e.target.value)}
              placeholder="Otra cantidad"
              className="h-16 w-40 rounded-2xl bg-slate-700 px-4 text-xl text-white placeholder:text-slate-400"
            />
            <button
              type="submit"
              disabled={enviando || !cantidadManual.trim()}
              className="h-16 rounded-2xl bg-white px-6 text-lg font-semibold text-slate-900 disabled:opacity-50"
            >
              Enviar
            </button>
          </form>
        </>
      )}

      <button
        type="button"
        onClick={escuchar}
        disabled={enviando || estadoVoz === 'escuchando'}
        aria-label="Responder por voz"
        className={`mx-auto mt-8 flex h-16 w-16 items-center justify-center rounded-full text-2xl ${
          estadoVoz === 'escuchando' ? 'bg-red-600' : 'bg-slate-600 active:bg-slate-500'
        }`}
      >
        🎤
      </button>
      {estadoVoz === 'escuchando' && <p className="mt-2 text-sm text-slate-400">Escuchando…</p>}
    </div>
  )
}
