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
 * El "momento estelar de la demo" (C4): la pregunta se lee en voz alta al
 * aparecer; candidatos se responden tocando (ambigüedad) o Sí/No + campo
 * numérico (anomalía/baja_confianza) — la voz es un camino adicional.
 *
 * Pantalla D del design doc: la anomalía toma TODO el lienzo en amarillo
 * Colsubsidio con texto grafito — el sistema TOMÓ una decisión, no es un
 * error. Pantalla E: tarjetas de igual peso con botón azul "Es este".
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

  if (candidatos) {
    // --- Pantalla E: ambigüedad ---
    return (
      <div className="animar-entrada flex w-full flex-1 flex-col gap-7 self-stretch">
        <div className="flex flex-col gap-2.5">
          <div className="text-sm tracking-widest text-texto-tenue">NECESITO QUE ME AYUDES A DESEMPATAR</div>
          <div className="text-xl font-semibold">¿A cuál te refieres?</div>
        </div>
        <div className="flex flex-1 flex-col gap-5">
          {candidatos.map((c) => (
            <button
              key={c.articulo_id}
              type="button"
              disabled={enviando}
              aria-label={c.articulo_nombre.toLowerCase()}
              onClick={() => onResponder(`articulo_id:${c.articulo_id}`)}
              className="clay transicion-estado flex flex-1 items-center justify-between gap-6 rounded-tarjeta bg-superficie1 px-8 py-7 text-left active:bg-superficie2 disabled:opacity-50"
            >
              <span className="text-xl font-semibold leading-tight">{c.articulo_nombre}</span>
              <span className="clay-azul flex h-[72px] shrink-0 items-center rounded-control bg-accion px-8 text-lg font-semibold text-white">
                Es este
              </span>
            </button>
          ))}
        </div>
        <button
          type="button"
          disabled={enviando}
          onClick={() => onResponder('no')}
          className="transicion-estado h-16 w-full rounded-control bg-superficie1 text-base text-texto-sec active:bg-superficie2 disabled:opacity-50"
        >
          Ninguno · vuelvo a decirlo
        </button>
        <BotonVoz enviando={enviando} escuchando={estadoVoz === 'escuchando'} onEscuchar={escuchar} oscuro />
      </div>
    )
  }

  // --- Pantalla D: anomalía / baja confianza en amarillo total ---
  const [preguntaPrincipal, ...restoMotivo] = pregunta.split('?')
  const motivo = restoMotivo.join('?').trim()

  return (
    <div className="animar-entrada flex min-h-full w-full flex-1 flex-col gap-6 self-stretch rounded-pantalla bg-marca p-10 text-sobre-marca">
      <div className="flex items-center gap-3.5">
        <span className="flex h-[52px] w-[52px] items-center justify-center rounded-full bg-sobre-marca text-xl font-semibold text-marca">
          !
        </span>
        <span className="text-lg font-semibold tracking-widest">ESPERA UN MOMENTO</span>
      </div>

      <div className="flex flex-1 flex-col justify-center gap-6">
        <div className="text-2xl font-semibold leading-tight">
          {preguntaPrincipal.trim()}
          {pregunta.includes('?') ? '?' : ''}
        </div>
        {motivo && <div className="max-w-3xl text-xl leading-snug">{motivo}</div>}
      </div>

      <div className="flex gap-5">
        <button
          type="button"
          disabled={enviando}
          aria-label="Sí"
          onClick={() => onResponder('si')}
          className="transicion-estado flex h-[120px] flex-1 flex-col items-center justify-center gap-1 rounded-control bg-sobre-marca active:opacity-85 disabled:opacity-50"
        >
          <span className="text-xl font-semibold text-white">Sí, confirmo</span>
          <span className="text-base text-texto-sec">Ya lo verifiqué</span>
        </button>
        <button
          type="button"
          disabled={enviando}
          aria-label="No"
          onClick={() => onResponder('no')}
          className="transicion-estado flex h-[120px] flex-1 flex-col items-center justify-center gap-1 rounded-control bg-white shadow-[inset_0_0_0_3px_#1C1C1B] active:opacity-85 disabled:opacity-50"
        >
          <span className="text-xl font-semibold text-sobre-marca">No, corrijo</span>
          <span className="text-base text-grafito">Vuelvo a contar</span>
        </button>
      </div>

      <form
        className="flex justify-center gap-3"
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
          className="h-16 w-48 rounded-control bg-sobre-marca-suave px-5 text-lg text-sobre-marca placeholder:text-sobre-marca placeholder:opacity-60 focus:outline-none"
        />
        <button
          type="submit"
          disabled={enviando || !cantidadManual.trim()}
          className="transicion-estado h-16 rounded-control bg-sobre-marca-suave px-7 text-base font-semibold text-sobre-marca active:opacity-75 disabled:opacity-40"
        >
          Enviar
        </button>
        <BotonVoz enviando={enviando} escuchando={estadoVoz === 'escuchando'} onEscuchar={escuchar} />
      </form>
    </div>
  )
}

function BotonVoz({
  enviando,
  escuchando,
  onEscuchar,
  oscuro = false,
}: {
  enviando: boolean
  escuchando: boolean
  onEscuchar: () => void
  oscuro?: boolean
}) {
  return (
    <button
      type="button"
      onClick={onEscuchar}
      disabled={enviando || escuchando}
      aria-label="Responder por voz"
      className={`transicion-estado flex h-16 w-16 shrink-0 items-center justify-center self-center rounded-full text-lg ${
        escuchando
          ? 'animar-respira bg-accion text-white'
          : oscuro
            ? 'clay-tecla bg-superficie2'
            : 'bg-sobre-marca text-marca'
      }`}
    >
      🎤
    </button>
  )
}
