import { ArrowLeft, LogOut, Mic, Square } from 'lucide-react'
import { useCallback, useMemo, useState } from 'react'
import ConfirmacionPendiente from '../components/ConfirmacionPendiente'
import ModoGuiado from '../components/ModoGuiado'
import PanelProgreso from '../components/PanelProgreso'
import TecladoManual from '../components/TecladoManual'
import type { ArticuloResumen } from '../lib/articulos'
import {
  ApiError,
  mensajeConfirmacion,
  nuevoConteoRequest,
  postConteo,
  resolverConteo,
  type Candidato,
  type Conteo,
  type ConteoResponse,
  type Fuente,
  type MotivoConfirmacion,
} from '../lib/conteos'
import { CHECKLIST_DEMO } from '../lib/listaGuiada'
import { resumenProgreso, siguientePendiente, textoCantidadArticulo } from '../lib/progreso'
import { conReintento } from '../lib/reintento'
import { useProgreso } from '../lib/useProgreso'
import { useVoz } from '../lib/useVoz'
import { useOperario } from '../state/OperarioContext'

type Modo = 'libre' | 'guiado'

type EstadoPantalla =
  | { tipo: 'lista' }
  | { tipo: 'procesando'; transcripcion?: string }
  | { tipo: 'confirmando'; conteo: Conteo }
  | {
      tipo: 'requiere_confirmacion'
      tokenPendiente: string
      motivo: MotivoConfirmacion
      pregunta: string
      candidatos: Candidato[] | null
    }
  | { tipo: 'no_catalogado'; textoCapturado: string }
  | { tipo: 'error'; mensaje: string }

export default function PantallaConteo() {
  const { operario, bodega, sesionId, cerrarSesion, volverASeleccionarBodega } = useOperario()
  const [pantalla, setPantalla] = useState<EstadoPantalla>({ tipo: 'lista' })
  const [enviandoRespuesta, setEnviandoRespuesta] = useState(false)
  const [pendientes, setPendientes] = useState(0)
  const [intentoActual, setIntentoActual] = useState<number | null>(null)
  const [toast, setToast] = useState<string | null>(null)
  // C8: modo guiado/libre. `contados` = artículos del checklist ya confirmados
  // (guía de P3); `saltados` = omitidos en el recorrido guiado. El progreso de
  // la BODEGA completa llega del WebSocket real (PanelProgreso).
  const [modo, setModo] = useState<Modo>('libre')
  const [contados, setContados] = useState<Set<number>>(new Set())
  const [saltados, setSaltados] = useState<Set<number>>(new Set())
  const { progreso: progresoBodega, enVivo } = useProgreso(bodega!.id, sesionId!)

  const progresoGuia = useMemo(() => resumenProgreso(CHECKLIST_DEMO, contados), [contados])
  const objetivoGuiado = useMemo(
    () => siguientePendiente(CHECKLIST_DEMO, new Set([...contados, ...saltados])),
    [contados, saltados],
  )

  function mostrarToast(mensaje: string) {
    setToast(mensaje)
    setTimeout(() => setToast(null), 2500)
  }

  const enviarCaptura = useCallback(
    async (payload: { texto?: string; audioBase64?: string }, fuente: Fuente) => {
      // Latencia percibida: la transcripción cruda aparece al instante,
      // aunque la respuesta del backend tarde ~2,5 s en modo live.
      setPantalla({ tipo: 'procesando', transcripcion: payload.texto ?? '🎙️ audio grabado' })
      setPendientes((p) => p + 1)
      setIntentoActual(null)
      try {
        const request = nuevoConteoRequest({
          sesionId: sesionId!,
          bodegaId: bodega!.id,
          operarioId: operario!.id,
          fuente,
          ...payload,
        })
        const respuesta = await conReintento(() => postConteo(request), {
          onReintento: (intento) => setIntentoActual(intento),
        })
        aplicarRespuesta(respuesta)
      } catch (error) {
        setPantalla({ tipo: 'error', mensaje: mensajeErrorConteo(error) })
      } finally {
        setPendientes((p) => Math.max(0, p - 1))
        setIntentoActual(null)
      }
    },
    [bodega, operario, sesionId],
  )

  const manejarTranscripcion = useCallback((texto: string) => enviarCaptura({ texto }, 'voz-tablet'), [enviarCaptura])
  const manejarAudioListo = useCallback(
    (audioBase64: string) => enviarCaptura({ audioBase64 }, 'voz-tablet'),
    [enviarCaptura],
  )

  const { estado: estadoVoz, usarAudio, escuchar, hablar, grabarAudio, detenerGrabacion } = useVoz(
    manejarTranscripcion,
    manejarAudioListo,
  )

  function alTocarMicrofono() {
    if (!usarAudio) {
      escuchar()
      return
    }
    if (estadoVoz === 'grabando') {
      detenerGrabacion()
    } else {
      grabarAudio()
    }
  }

  function aplicarRespuesta(respuesta: ConteoResponse) {
    if (respuesta.status === 'confirmado') {
      // Progreso de la guía: se marca por NOMBRE porque el checklist habla en
      // nr_articulo (mock) y el backend real responde con ids de BD.
      const item = CHECKLIST_DEMO.find((a) => a.articulo_nombre === respuesta.conteo.articulo_nombre)
      const id = item?.articulo_id ?? respuesta.conteo.articulo_id
      setContados((prev) => (prev.has(id) ? prev : new Set(prev).add(id)))
      setPantalla({ tipo: 'confirmando', conteo: respuesta.conteo })
      hablar(mensajeConfirmacion(respuesta.conteo))
      return
    }

    if (respuesta.status === 'descartado') {
      // Cuarto estado del contrato (/resolver con "no"): nada se persistió.
      setPantalla({ tipo: 'lista' })
      mostrarToast('Conteo descartado')
      hablar('Descartado. Puedes dictar el siguiente conteo.')
      return
    }

    if (respuesta.status === 'no_catalogado' && !respuesta.texto_capturado.trim()) {
      // Degradación con gracia: el NLU no entendió (o falló) → caer al
      // teclado con mensaje claro, nunca pantalla de error genérica.
      setPantalla({ tipo: 'lista' })
      mostrarToast('No pude entender el audio, usa el teclado')
      hablar('No pude entender. Usa el teclado o repite el conteo.')
      return
    }

    if (respuesta.status === 'requiere_confirmacion') {
      setPantalla({
        tipo: 'requiere_confirmacion',
        tokenPendiente: respuesta.token_pendiente,
        motivo: respuesta.motivo,
        pregunta: respuesta.pregunta,
        candidatos: respuesta.candidatos,
      })
      return
    }

    setPantalla({ tipo: 'no_catalogado', textoCapturado: respuesta.texto_capturado })
    hablar(`No encontré "${respuesta.texto_capturado}" en el catálogo de esta bodega.`)
  }

  async function responderConfirmacion(tokenPendiente: string, respuesta: string) {
    setEnviandoRespuesta(true)
    setPendientes((p) => p + 1)
    try {
      const resultado = await conReintento(() => resolverConteo(tokenPendiente, respuesta), {
        onReintento: (intento) => setIntentoActual(intento),
      })
      aplicarRespuesta(resultado)
    } catch (error) {
      // 410/404/409 del token: mensajes honestos y volver a escuchar —
      // reintentar el mismo token nunca va a funcionar.
      if (error instanceof ApiError && [404, 409, 410].includes(error.status)) {
        setPantalla({ tipo: 'lista' })
        mostrarToast(
          error.status === 410
            ? 'La pregunta expiró, vuelve a dictar el conteo'
            : error.status === 409
              ? 'Esa pregunta ya fue respondida'
              : 'La pregunta ya no existe, vuelve a dictar el conteo',
        )
      } else {
        setPantalla({ tipo: 'error', mensaje: 'No se pudo enviar la respuesta. Revisa tu conexión e intenta de nuevo.' })
      }
    } finally {
      setEnviandoRespuesta(false)
      setPendientes((p) => Math.max(0, p - 1))
      setIntentoActual(null)
    }
  }

  function volverAEscuchar() {
    setPantalla({ tipo: 'lista' })
  }

  // --- Modo guiado (C8) ---
  function registrarGuiado(cantidadTexto: string, articulo: ArticuloResumen) {
    // Fuente 'manual': el artículo lo fija la guía, así el match es exacto y no
    // dispara los casos de demo por palabra clave (noventa/cazuela/xyz).
    enviarCaptura({ texto: textoCantidadArticulo(cantidadTexto, articulo) }, 'manual')
  }

  function saltarGuiado(articulo: ArticuloResumen) {
    setSaltados((prev) => new Set(prev).add(articulo.articulo_id))
  }

  function reiniciarGuiado() {
    setSaltados(new Set())
  }

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-3xl flex-col bg-fondo p-4 text-texto">
      <header className="flex items-center justify-between gap-3 rounded-tarjeta border border-borde-sutil bg-superficie1 px-3 py-2">
        <div className="flex min-w-0 items-center gap-3">
          <button
            type="button"
            onClick={volverASeleccionarBodega}
            aria-label="Volver a selección de bodega"
            className="transicion-estado flex h-16 w-16 shrink-0 items-center justify-center rounded-control bg-superficie2 active:bg-tinte"
          >
            <ArrowLeft className="h-6 w-6 text-texto-sec" />
          </button>
          <span className="line-clamp-2 text-lg font-semibold capitalize leading-tight">{bodega!.nombre}</span>
        </div>
        <div className="flex shrink-0 items-center gap-3">
          {pendientes > 0 && (
            <span className="rounded-full bg-tinte-alerta px-3 py-1 text-xs font-semibold text-alerta" aria-live="polite">
              {pendientes} pendiente{pendientes > 1 ? 's' : ''}
            </span>
          )}
          <button
            type="button"
            onClick={cerrarSesion}
            aria-label="Cerrar sesión"
            className="transicion-estado flex h-16 items-center gap-2 rounded-control px-3 text-sm font-medium text-texto-sec active:bg-superficie2"
          >
            <LogOut className="h-5 w-5" />
            <span className="hidden sm:inline">Cerrar sesión</span>
          </button>
        </div>
      </header>

      {/* C8: barra de progreso de la guía (subordinada) + selector de modo. */}
      <section className="mt-3 rounded-tarjeta border border-borde-sutil bg-superficie1 px-4 py-3">
        <div className="flex items-center justify-between text-sm font-medium text-texto-sec">
          <span>Progreso de la guía</span>
          <span className="tabular-nums">
            {progresoGuia.hechos} / {progresoGuia.total}
          </span>
        </div>
        <div
          className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-superficie2"
          role="progressbar"
          aria-valuenow={progresoGuia.porcentaje}
          aria-valuemin={0}
          aria-valuemax={100}
        >
          <div
            className="h-full rounded-full bg-primario transition-all"
            style={{ width: `${progresoGuia.porcentaje}%` }}
          />
        </div>

        {pantalla.tipo === 'lista' && (
          <div className="mt-3 grid grid-cols-2 gap-2" role="tablist" aria-label="Modo de conteo">
            {(['libre', 'guiado'] as const).map((m) => (
              <button
                key={m}
                type="button"
                role="tab"
                aria-selected={modo === m}
                onClick={() => setModo(m)}
                className={`transicion-estado h-16 rounded-control text-base font-semibold capitalize ${
                  modo === m
                    ? 'bg-tinte text-acento'
                    : 'bg-superficie2 text-texto-sec active:bg-tinte'
                }`}
              >
                {m === 'libre' ? 'Modo libre' : 'Modo guiado'}
              </button>
            ))}
          </div>
        )}
      </section>

      <div className="flex flex-1 flex-col items-center justify-center gap-8">
        {pantalla.tipo === 'lista' && modo === 'libre' && (
          <>
            <BotonMicrofono estadoVoz={estadoVoz} onTocar={alTocarMicrofono} />
            <DictadoPorTexto onEnviar={(texto) => enviarCaptura({ texto }, 'voz-tablet')} />
            <TecladoManual bodegaId={bodega!.id} onEnviar={(texto) => enviarCaptura({ texto }, 'manual')} />
            <PanelProgreso progreso={progresoBodega} enVivo={enVivo} />
          </>
        )}

        {pantalla.tipo === 'lista' && modo === 'guiado' && (
          <ModoGuiado
            objetivo={objetivoGuiado}
            progreso={progresoGuia}
            enviando={pendientes > 0}
            onRegistrar={registrarGuiado}
            onSaltar={saltarGuiado}
            onReiniciar={reiniciarGuiado}
          />
        )}

        {toast && (
          <div
            className="fixed bottom-6 left-1/2 -translate-x-1/2 rounded-control border border-borde-fuerte bg-superficie2 px-6 py-3 text-base"
            role="status"
            aria-live="polite"
          >
            {toast}
          </div>
        )}

        {estadoVoz === 'escuchando' && pantalla.tipo === 'lista' && modo === 'libre' && (
          <p className="text-lg text-acento">Escuchando…</p>
        )}

        {estadoVoz === 'grabando' && pantalla.tipo === 'lista' && modo === 'libre' && (
          <p className="text-lg font-semibold text-alerta">● Grabando… toca de nuevo para enviar</p>
        )}

        {pantalla.tipo === 'procesando' && (
          <div className="animar-entrada max-w-lg text-center">
            {pantalla.transcripcion && (
              <p className="text-xl font-semibold text-texto">"{pantalla.transcripcion}"</p>
            )}
            <p className="mt-3 animate-pulse text-lg text-texto-sec">
              {intentoActual
                ? `Sin conexión, reintentando… (intento ${intentoActual})`
                : 'Procesando…'}
            </p>
          </div>
        )}

        {pantalla.tipo === 'confirmando' && (
          <TarjetaConfirmacion conteo={pantalla.conteo} onCerrar={volverAEscuchar} />
        )}

        {pantalla.tipo === 'requiere_confirmacion' && (
          <ConfirmacionPendiente
            tokenPendiente={pantalla.tokenPendiente}
            pregunta={pantalla.pregunta}
            candidatos={pantalla.candidatos}
            enviando={enviandoRespuesta}
            onResponder={(respuesta) => responderConfirmacion(pantalla.tokenPendiente, respuesta)}
          />
        )}

        {pantalla.tipo === 'no_catalogado' && (
          <div className="animar-entrada w-full max-w-lg rounded-tarjeta border border-borde-sutil bg-superficie1 p-6 text-center">
            <p className="text-lg font-semibold">No encontré "{pantalla.textoCapturado}" en el catálogo.</p>
            <button
              type="button"
              onClick={volverAEscuchar}
              className="transicion-estado mt-6 h-[72px] w-full rounded-control bg-primario px-8 text-lg font-semibold text-texto active:bg-primario-hover"
            >
              Volver a intentar
            </button>
          </div>
        )}

        {pantalla.tipo === 'error' && (
          <div className="animar-entrada w-full max-w-lg rounded-tarjeta border border-critico bg-superficie1 p-6 text-center">
            <p className="text-lg font-semibold text-critico">{pantalla.mensaje}</p>
            <button
              type="button"
              onClick={volverAEscuchar}
              className="transicion-estado mt-6 h-[72px] w-full rounded-control bg-primario px-8 text-lg font-semibold text-texto active:bg-primario-hover"
            >
              Reintentar
            </button>
          </div>
        )}

        {usarAudio && estadoVoz !== 'grabando' && pantalla.tipo === 'lista' && modo === 'libre' && (
          <p className="max-w-sm text-center text-sm text-alerta">
            {estadoVoz === 'no_soportado'
              ? 'Este navegador no transcribe voz en vivo: el micrófono ahora graba audio.'
              : 'El reconocimiento de voz está fallando: el micrófono ahora graba audio.'}
          </p>
        )}
      </div>
    </main>
  )
}

function mensajeErrorConteo(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 404) return 'La sesión ya no existe. Vuelve a elegir la bodega.'
    if (error.status === 409) return 'La sesión está cerrada. Vuelve a elegir la bodega.'
  }
  return 'No se pudo enviar el conteo. Revisa tu conexión e intenta de nuevo.'
}

/** Dictado escrito: mismo pipeline NLU que la voz (fuente voz-tablet), para
 * ensayar la demo sin micrófono o salvarla si el auditorio es muy ruidoso. */
function DictadoPorTexto({ onEnviar }: { onEnviar: (texto: string) => void }) {
  const [texto, setTexto] = useState('')
  return (
    <form
      className="flex w-full max-w-md gap-2"
      onSubmit={(e) => {
        e.preventDefault()
        const limpio = texto.trim()
        if (!limpio) return
        onEnviar(limpio)
        setTexto('')
      }}
    >
      <input
        type="text"
        value={texto}
        onChange={(e) => setTexto(e.target.value)}
        placeholder='Escribe el dictado: "noventa cajas de cazuelas"…'
        aria-label="Dictado por texto"
        className="transicion-estado h-16 flex-1 rounded-control border border-borde-sutil bg-superficie2 px-4 text-base text-texto placeholder:text-texto-tenue focus:border-primario focus:outline-none"
      />
      <button
        type="submit"
        disabled={!texto.trim()}
        className="transicion-estado h-16 rounded-control border border-borde-sutil bg-superficie2 px-5 text-base font-semibold text-texto-sec active:bg-tinte disabled:opacity-40"
      >
        Enviar
      </button>
    </form>
  )
}

function BotonMicrofono({
  estadoVoz,
  onTocar,
}: {
  estadoVoz: string
  onTocar: () => void
}) {
  const escuchando = estadoVoz === 'escuchando'
  const grabando = estadoVoz === 'grabando'
  const activo = escuchando || grabando

  return (
    <button
      type="button"
      onClick={onTocar}
      disabled={escuchando}
      aria-label={grabando ? 'Detener grabación y enviar' : 'Hablar para registrar un conteo'}
      className={`transicion-estado flex h-44 w-44 items-center justify-center rounded-full ${
        activo
          ? 'animar-pulso-mic border-2 border-acento bg-primario'
          : 'bg-primario active:bg-primario-hover'
      }`}
    >
      {grabando ? (
        <Square className="h-16 w-16 text-texto" fill="currentColor" strokeWidth={1.5} />
      ) : (
        <Mic className="h-16 w-16 text-texto" strokeWidth={1.75} />
      )}
    </button>
  )
}

function TarjetaConfirmacion({ conteo, onCerrar }: { conteo: Conteo; onCerrar: () => void }) {
  return (
    <div className="animar-entrada w-full max-w-lg rounded-tarjeta border border-borde-sutil bg-superficie1 p-8 text-center">
      {/* Jerarquía: cantidad+unidad 56px, artículo 32px — legible a 3 metros. */}
      <p className="text-2xl font-semibold tabular-nums text-texto">
        {conteo.cantidad} <span className="text-xl font-normal text-texto-sec">{conteo.unidad}</span>
      </p>
      <p className="mt-4 text-xl font-semibold capitalize text-acento">
        {conteo.articulo_nombre.toLowerCase()}
      </p>

      <div className="mt-8 flex justify-center gap-4">
        <button
          type="button"
          onClick={onCerrar}
          aria-label="Confirmar"
          className="transicion-estado h-[72px] flex-1 rounded-control bg-exito text-lg font-semibold text-fondo active:opacity-80"
        >
          ✓ Correcto
        </button>
        <button
          type="button"
          onClick={onCerrar}
          aria-label="Rechazar"
          className="transicion-estado h-[72px] w-32 rounded-control border border-borde-fuerte bg-superficie2 text-lg font-semibold text-texto-sec active:border-critico active:text-critico"
        >
          ✗
        </button>
      </div>
    </div>
  )
}
