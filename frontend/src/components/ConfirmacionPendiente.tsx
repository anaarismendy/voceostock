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
 *
 * Visual: la anomalía rompe el lila y usa ámbar — el sistema TOMÓ una
 * decisión y pide confirmación; no es un error.
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

  const esAnomalia = !candidatos

  return (
    <div
      className={`animar-entrada w-full max-w-2xl rounded-tarjeta border p-8 text-center ${
        esAnomalia ? 'border-alerta bg-tinte-alerta' : 'border-borde-fuerte bg-superficie1'
      }`}
    >
      {esAnomalia && (
        <p className="text-sm font-semibold uppercase tracking-widest text-alerta">
          ⚠ Validación del sistema
        </p>
      )}
      <p className={`${esAnomalia ? 'mt-4' : ''} text-xl font-semibold`}>{pregunta}</p>

      {candidatos && (
        <div className="mt-8 flex flex-col gap-3">
          {candidatos.map((c) => (
            <button
              key={c.articulo_id}
              type="button"
              disabled={enviando}
              onClick={() => onResponder(`articulo_id:${c.articulo_id}`)}
              className="transicion-estado min-h-[72px] rounded-tarjeta border-2 border-borde-fuerte bg-superficie2 px-6 py-4 text-lg font-semibold capitalize active:border-primario active:bg-tinte disabled:opacity-50"
            >
              {c.articulo_nombre.toLowerCase()}
            </button>
          ))}
        </div>
      )}

      {!candidatos && (
        <>
          <div className="mt-8 flex justify-center gap-4">
            <button
              type="button"
              disabled={enviando}
              onClick={() => onResponder('si')}
              className="transicion-estado h-[72px] flex-1 rounded-control bg-alerta text-lg font-semibold text-fondo active:opacity-80 disabled:opacity-50"
            >
              Sí
            </button>
            <button
              type="button"
              disabled={enviando}
              onClick={() => onResponder('no')}
              className="transicion-estado h-[72px] w-40 rounded-control border-2 border-borde-fuerte bg-superficie2 text-lg font-semibold text-texto-sec active:border-critico active:text-critico disabled:opacity-50"
            >
              No
            </button>
          </div>

          <form
            className="mt-4 flex justify-center gap-3"
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
              className="transicion-estado h-16 w-44 rounded-control border border-borde-sutil bg-superficie2 px-4 text-base text-texto placeholder:text-texto-tenue focus:border-alerta focus:outline-none"
            />
            <button
              type="submit"
              disabled={enviando || !cantidadManual.trim()}
              className="transicion-estado h-16 rounded-control border border-borde-sutil bg-superficie2 px-6 text-base font-semibold text-texto-sec active:bg-tinte-alerta disabled:opacity-50"
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
        className={`transicion-estado mx-auto mt-8 flex h-16 w-16 items-center justify-center rounded-full text-lg ${
          estadoVoz === 'escuchando'
            ? 'animar-pulso-mic bg-primario'
            : 'border border-borde-fuerte bg-superficie2 active:bg-tinte'
        }`}
      >
        🎤
      </button>
      {estadoVoz === 'escuchando' && <p className="mt-2 text-sm text-texto-sec">Escuchando…</p>}
    </div>
  )
}
