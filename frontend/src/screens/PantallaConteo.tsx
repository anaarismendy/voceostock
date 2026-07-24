import { ArrowLeft, LogOut, Mic, Square } from 'lucide-react'
import { useCallback, useState } from 'react'
import ConfirmacionPendiente from '../components/ConfirmacionPendiente'
import TecladoManual from '../components/TecladoManual'
import {
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
import { conReintento } from '../lib/reintento'
import { useVoz } from '../lib/useVoz'
import { useOperario } from '../state/OperarioContext'

type EstadoPantalla =
  | { tipo: 'lista' }
  | { tipo: 'procesando' }
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
  const { operario, bodega, cerrarSesion, volverASeleccionarBodega } = useOperario()
  const [pantalla, setPantalla] = useState<EstadoPantalla>({ tipo: 'lista' })
  const [enviandoRespuesta, setEnviandoRespuesta] = useState(false)
  const [pendientes, setPendientes] = useState(0)
  const [intentoActual, setIntentoActual] = useState<number | null>(null)

  const enviarCaptura = useCallback(
    async (payload: { texto?: string; audioBase64?: string }, fuente: Fuente) => {
      setPantalla({ tipo: 'procesando' })
      setPendientes((p) => p + 1)
      setIntentoActual(null)
      try {
        const request = nuevoConteoRequest({
          bodegaId: bodega!.id,
          operarioId: operario!.id,
          fuente,
          ...payload,
        })
        const respuesta = await conReintento(() => postConteo(request), {
          onReintento: (intento) => setIntentoActual(intento),
        })
        aplicarRespuesta(respuesta)
      } catch {
        setPantalla({ tipo: 'error', mensaje: 'No se pudo enviar el conteo. Revisa tu conexión e intenta de nuevo.' })
      } finally {
        setPendientes((p) => Math.max(0, p - 1))
        setIntentoActual(null)
      }
    },
    [bodega, operario],
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
      setPantalla({ tipo: 'confirmando', conteo: respuesta.conteo })
      hablar(mensajeConfirmacion(respuesta.conteo))
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
    } catch {
      setPantalla({ tipo: 'error', mensaje: 'No se pudo enviar la respuesta. Revisa tu conexión e intenta de nuevo.' })
    } finally {
      setEnviandoRespuesta(false)
      setPendientes((p) => Math.max(0, p - 1))
      setIntentoActual(null)
    }
  }

  function volverAEscuchar() {
    setPantalla({ tipo: 'lista' })
  }

  return (
    <main className="flex min-h-screen flex-col bg-slate-900 p-6 text-white">
      <header className="flex items-start justify-between gap-3 rounded-2xl bg-slate-800 px-4 py-3 shadow-md">
        <div className="flex min-w-0 items-center gap-3">
          <button
            type="button"
            onClick={volverASeleccionarBodega}
            aria-label="Volver a selección de bodega"
            className="flex h-16 w-16 shrink-0 items-center justify-center rounded-xl bg-slate-700 active:bg-slate-600"
          >
            <ArrowLeft className="h-7 w-7" />
          </button>
          <span className="line-clamp-2 text-2xl font-bold capitalize leading-tight">{bodega!.nombre}</span>
        </div>
        <div className="flex shrink-0 items-center gap-3">
          {pendientes > 0 && (
            <span className="rounded-full bg-amber-600 px-3 py-1 text-xs font-semibold" aria-live="polite">
              {pendientes} pendiente{pendientes > 1 ? 's' : ''}
            </span>
          )}
          <button
            type="button"
            onClick={cerrarSesion}
            aria-label="Cerrar sesión"
            className="flex items-center gap-2 rounded-xl px-3 py-3 text-sm font-medium text-slate-300 active:bg-slate-700"
          >
            <LogOut className="h-5 w-5" />
            <span className="hidden sm:inline">Cerrar sesión</span>
          </button>
        </div>
      </header>

      <div className="flex flex-1 flex-col items-center justify-center gap-8">
        {pantalla.tipo === 'lista' && (
          <>
            <BotonMicrofono estadoVoz={estadoVoz} onTocar={alTocarMicrofono} />
            <TecladoManual onEnviar={(texto) => enviarCaptura({ texto }, 'manual')} />
          </>
        )}

        {estadoVoz === 'escuchando' && pantalla.tipo === 'lista' && (
          <p className="text-2xl text-slate-300">Escuchando…</p>
        )}

        {estadoVoz === 'grabando' && pantalla.tipo === 'lista' && (
          <p className="text-2xl text-red-300">🔴 Grabando… toca de nuevo para enviar</p>
        )}

        {pantalla.tipo === 'procesando' && (
          <p className="text-2xl text-slate-300">
            {intentoActual
              ? `Sin conexión, reintentando… (intento ${intentoActual})`
              : 'Procesando…'}
          </p>
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
          <div className="max-w-lg rounded-2xl bg-slate-800 p-6 text-center">
            <p className="text-3xl font-semibold">No encontré "{pantalla.textoCapturado}" en el catálogo.</p>
            <button
              type="button"
              onClick={volverAEscuchar}
              className="mt-4 h-16 rounded-2xl bg-white px-8 text-xl font-semibold text-slate-900 active:bg-slate-200"
            >
              Volver a intentar
            </button>
          </div>
        )}

        {pantalla.tipo === 'error' && (
          <div className="max-w-lg rounded-2xl bg-red-950 p-6 text-center">
            <p className="text-2xl font-semibold text-red-200">{pantalla.mensaje}</p>
            <button
              type="button"
              onClick={volverAEscuchar}
              className="mt-4 h-16 rounded-2xl bg-white px-8 text-xl font-semibold text-slate-900 active:bg-slate-200"
            >
              Reintentar
            </button>
          </div>
        )}

        {usarAudio && estadoVoz !== 'grabando' && pantalla.tipo === 'lista' && (
          <p className="max-w-sm text-center text-lg text-amber-300">
            {estadoVoz === 'no_soportado'
              ? 'Este navegador no transcribe voz en vivo: el micrófono ahora graba audio.'
              : 'El reconocimiento de voz está fallando: el micrófono ahora graba audio.'}
          </p>
        )}
      </div>
    </main>
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
      className={`flex h-40 w-40 items-center justify-center rounded-full shadow-lg transition-all ${
        activo
          ? 'animate-pulse bg-red-600 ring-4 ring-red-400/60'
          : 'bg-emerald-600 active:bg-emerald-500'
      }`}
    >
      {grabando ? (
        <Square className="h-16 w-16 text-white" fill="white" strokeWidth={1.5} />
      ) : (
        <Mic className="h-16 w-16 text-white" strokeWidth={1.75} />
      )}
    </button>
  )
}

function TarjetaConfirmacion({ conteo, onCerrar }: { conteo: Conteo; onCerrar: () => void }) {
  return (
    <div className="w-full max-w-lg rounded-3xl bg-slate-800 p-8 text-center">
      <p className="text-5xl font-bold">{conteo.cantidad}</p>
      <p className="mt-1 text-3xl font-medium text-slate-200">{conteo.unidad}</p>
      <p className="mt-4 text-4xl font-semibold">{conteo.articulo_nombre}</p>

      <div className="mt-8 flex justify-center gap-6">
        <button
          type="button"
          onClick={onCerrar}
          aria-label="Confirmar"
          className="flex h-20 w-20 items-center justify-center rounded-full bg-emerald-600 text-4xl active:bg-emerald-500"
        >
          ✓
        </button>
        <button
          type="button"
          onClick={onCerrar}
          aria-label="Rechazar"
          className="flex h-20 w-20 items-center justify-center rounded-full bg-red-600 text-4xl active:bg-red-500"
        >
          ✗
        </button>
      </div>
    </div>
  )
}
