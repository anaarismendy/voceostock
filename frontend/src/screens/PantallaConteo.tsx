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
  const { operario, bodega, cerrarSesion } = useOperario()
  const [pantalla, setPantalla] = useState<EstadoPantalla>({ tipo: 'lista' })
  const [enviandoRespuesta, setEnviandoRespuesta] = useState(false)

  const enviarTexto = useCallback(
    async (texto: string, fuente: Fuente) => {
      setPantalla({ tipo: 'procesando' })
      try {
        const request = nuevoConteoRequest({
          texto,
          bodegaId: bodega!.id,
          operarioId: operario!.id,
          fuente,
        })
        const respuesta = await postConteo(request)
        aplicarRespuesta(respuesta)
      } catch {
        setPantalla({ tipo: 'error', mensaje: 'No se pudo enviar el conteo. Intenta de nuevo.' })
      }
    },
    [bodega, operario],
  )

  const manejarTranscripcion = useCallback((texto: string) => enviarTexto(texto, 'voz-tablet'), [enviarTexto])

  const { estado: estadoVoz, escuchar, hablar } = useVoz(manejarTranscripcion)

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
    try {
      const resultado = await resolverConteo(tokenPendiente, respuesta)
      aplicarRespuesta(resultado)
    } catch {
      setPantalla({ tipo: 'error', mensaje: 'No se pudo enviar la respuesta. Intenta de nuevo.' })
    } finally {
      setEnviandoRespuesta(false)
    }
  }

  function volverAEscuchar() {
    setPantalla({ tipo: 'lista' })
  }

  return (
    <main className="flex min-h-screen flex-col bg-slate-900 p-6 text-white">
      <header className="flex items-center justify-between">
        <span className="text-lg font-medium capitalize">{bodega!.nombre}</span>
        <button className="text-sm text-slate-400 underline" onClick={cerrarSesion}>
          Cerrar sesión
        </button>
      </header>

      <div className="flex flex-1 flex-col items-center justify-center gap-8">
        {pantalla.tipo === 'lista' && (
          <>
            <BotonMicrofono estadoVoz={estadoVoz} onTocar={escuchar} />
            <TecladoManual onEnviar={(texto) => enviarTexto(texto, 'manual')} />
          </>
        )}

        {estadoVoz === 'escuchando' && pantalla.tipo === 'lista' && (
          <p className="text-2xl text-slate-300">Escuchando…</p>
        )}

        {pantalla.tipo === 'procesando' && (
          <p className="text-2xl text-slate-300">Procesando…</p>
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

        {estadoVoz === 'no_soportado' && pantalla.tipo === 'lista' && (
          <p className="max-w-sm text-center text-lg text-amber-300">
            Este navegador no soporta reconocimiento de voz. Usa el teclado de abajo.
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
  return (
    <button
      type="button"
      onClick={onTocar}
      disabled={escuchando}
      aria-label="Hablar para registrar un conteo"
      className={`flex h-40 w-40 items-center justify-center rounded-full text-6xl shadow-lg transition-colors ${
        escuchando ? 'bg-red-600' : 'bg-emerald-600 active:bg-emerald-500'
      }`}
    >
      🎤
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
