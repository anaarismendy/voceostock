import { ArrowLeft, LogOut, Mic, Square } from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import ConfirmacionPendiente from '../components/ConfirmacionPendiente'
import ListaInventario from '../components/ListaInventario'
import ModoGuiado from '../components/ModoGuiado'
import TecladoManual from '../components/TecladoManual'
import { getArticulos, type ArticuloResumen } from '../lib/articulos'
import { AVISO_RIESGO_TEXTO, debeAvisar, type NivelRiesgo } from '../lib/avisoRiesgo'
import { indicadorConfianza, type NivelConfianza } from '../lib/confianza'
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
  | { tipo: 'confirmando'; conteo: Conteo; viaAclaracion: boolean }
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
  // la BODEGA completa llega del WebSocket real (barra superior).
  const [modo, setModo] = useState<Modo>('libre')
  // Pantalla G: el teclado manual vive detrás de "Escribir a mano".
  const [tecladoVisible, setTecladoVisible] = useState(false)
  const [contados, setContados] = useState<Set<number>>(new Set())
  const [saltados, setSaltados] = useState<Set<number>>(new Set())
  // Inventario real de la bodega: sin él el operario no sabe qué se cuenta aquí.
  const [articulos, setArticulos] = useState<ArticuloResumen[]>([])
  const [inventarioVisible, setInventarioVisible] = useState(false)
  const { progreso: progresoBodega, enVivo } = useProgreso(bodega!.id, sesionId!)
  // F4: nivel de riesgo por artículo (del catálogo, sin request extra en captura)
  // y los ya avisados en esta sesión. Refs: no necesitan re-render.
  const riesgosRef = useRef<Map<number, NivelRiesgo>>(new Map())
  const avisadosRiesgoRef = useRef<Set<number>>(new Set())

  useEffect(() => {
    let vivo = true
    getArticulos(bodega!.id)
      .then((arts) => {
        if (!vivo) return
        setArticulos(arts)
        riesgosRef.current = new Map(
          arts.filter((a) => a.riesgo).map((a) => [a.articulo_id, a.riesgo as NivelRiesgo]),
        )
      })
      .catch(() => {
        /* sin catálogo: no se avisa riesgo y la guía cae al checklist de demo */
      })
    return () => {
      vivo = false
    }
  }, [bodega])

  // La guía recorre el inventario REAL de la bodega. Fallback al checklist de
  // demo solo si el catálogo no cargó (mock sin backend, red caída).
  const guia = articulos.length > 0 ? articulos : CHECKLIST_DEMO
  const progresoGuia = useMemo(() => resumenProgreso(guia, contados), [guia, contados])
  const objetivoGuiado = useMemo(
    () => siguientePendiente(guia, new Set([...contados, ...saltados])),
    [guia, contados, saltados],
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

  function aplicarRespuesta(respuesta: ConteoResponse, viaAclaracion = false) {
    if (respuesta.status === 'confirmado') {
      // `articulo_id` es la MISMA clave que devuelve /articulos (id de BD en el
      // backend real, nr_articulo en el mock), así que marca directo. No buscar
      // por nombre: `enviarCaptura` está memoizada sin `articulos` en sus deps,
      // y ese lookup quedaba congelado sobre el checklist de demo, traduciendo
      // el id bueno a uno que el inventario no conoce (nada se marcaba).
      const id = respuesta.conteo.articulo_id
      setContados((prev) => (prev.has(id) ? prev : new Set(prev).add(id)))
      // F1: `viaAclaracion` distingue el auto-confirmado del que pasó por una
      // pregunta, para el indicador de confianza (sin revelar nunca el SD).
      setPantalla({ tipo: 'confirmando', conteo: respuesta.conteo, viaAclaracion })
      hablar(mensajeConfirmacion(respuesta.conteo))
      // F4: aviso preventivo si el artículo es de riesgo alto. Una sola vez por
      // sesión por artículo; genérico, sin revelar el SD ni el histórico exacto.
      const riesgo = riesgosRef.current.get(respuesta.conteo.articulo_id)
      if (debeAvisar(respuesta.conteo.articulo_id, riesgo, avisadosRiesgoRef.current)) {
        avisadosRiesgoRef.current.add(respuesta.conteo.articulo_id)
        hablar(AVISO_RIESGO_TEXTO)
      }
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
      aplicarRespuesta(resultado, true) // F1: vino tras una aclaración del operario
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

  // Pantalla D: la anomalía toma TODO el lienzo (sin chrome de conteo).
  const anomaliaTotal = pantalla.tipo === 'requiere_confirmacion' && !pantalla.candidatos

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-4xl flex-col gap-4 bg-pantalla p-4 text-texto sm:gap-5 sm:p-7">
      {!anomaliaTotal && (
        <>
          <header className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <button
                type="button"
                onClick={volverASeleccionarBodega}
                aria-label="Volver a selección de bodega"
                className="transicion-estado flex h-16 w-16 shrink-0 items-center justify-center rounded-control bg-superficie1 active:bg-superficie2"
              >
                <ArrowLeft className="h-6 w-6 text-texto-sec" />
              </button>
              <div className="h-[26px] w-2 shrink-0 rounded-full bg-marca" />
              <span className="line-clamp-1 text-base capitalize text-texto-sec">{bodega!.nombre}</span>
            </div>
            <div className="flex shrink-0 items-center gap-3">
              {pendientes > 0 && (
                <span
                  className="flex h-10 items-center gap-2 rounded-full bg-superficie2 px-4 text-sm text-texto-sec"
                  aria-live="polite"
                >
                  <span className="h-2 w-2 rounded-full bg-texto-tenue" />
                  {pendientes} sin sincronizar
                </span>
              )}
              {estadoVoz === 'escuchando' && (
                <span className="flex h-10 items-center gap-2 rounded-full bg-tinte-azul px-4 text-sm text-azul-suave">
                  <span className="h-2 w-2 rounded-full bg-azul-texto" />
                  Te escucho
                </span>
              )}
              <button
                type="button"
                onClick={cerrarSesion}
                aria-label="Cerrar sesión"
                className="transicion-estado flex h-16 items-center gap-2 rounded-control px-3 text-sm text-texto-sec active:bg-superficie1"
              >
                <LogOut className="h-5 w-5" />
                <span className="hidden sm:inline">Cerrar sesión</span>
              </button>
            </div>
          </header>

          <div className="flex flex-col gap-2.5">
            <div className="flex justify-between text-sm text-texto-sec">
              <span>
                {progresoBodega
                  ? `Artículo ${progresoBodega.contados} de ${progresoBodega.total}`
                  : 'Cargando progreso…'}
              </span>
              <span className="flex items-center gap-2">
                Guía {progresoGuia.hechos}/{progresoGuia.total}
                <span
                  className={`h-2 w-2 rounded-full ${enVivo ? 'bg-exito' : 'bg-texto-tenue'}`}
                  title={enVivo ? 'En vivo' : 'Actualización periódica'}
                />
              </span>
            </div>
            <div
              className="clay-hundido h-3 overflow-hidden rounded-full bg-superficie1"
              role="progressbar"
              aria-valuenow={progresoBodega ? Math.round((progresoBodega.contados / Math.max(1, progresoBodega.total)) * 100) : 0}
              aria-valuemin={0}
              aria-valuemax={100}
            >
              <div
                className="h-full rounded-full bg-accion transition-all"
                style={{
                  width: `${progresoBodega ? (progresoBodega.contados / Math.max(1, progresoBodega.total)) * 100 : 0}%`,
                }}
              />
            </div>
          </div>
        </>
      )}

      <div className={`flex flex-1 flex-col items-center gap-6 ${anomaliaTotal ? 'justify-stretch' : 'justify-center'}`}>
        {pantalla.tipo === 'lista' && modo === 'libre' && (
          <>
            <div className="flex flex-1 flex-col items-center justify-center gap-3.5">
              <div className="text-center text-xl font-semibold">Toca y dime qué cuentas</div>
              <div className="max-w-xl text-center text-lg text-texto-tenue">
                Ejemplo: “treinta y tres litros de aceite de oliva”
              </div>
            </div>
            <div className="flex flex-col items-center gap-4">
              <BotonMicrofono estadoVoz={estadoVoz} onTocar={alTocarMicrofono} />
              <div className="text-base text-texto-tenue">
                {estadoVoz === 'escuchando'
                  ? 'Suelta cuando termines'
                  : estadoVoz === 'grabando'
                    ? 'Toca de nuevo para enviar'
                    : 'Mantén pulsado o toca una vez'}
              </div>
            </div>
            <DictadoPorTexto onEnviar={(texto) => enviarCaptura({ texto }, 'voz-tablet')} />
            <BarraModo modo={modo} onCambiarModo={setModo}>
              <BotonInventario abierto={inventarioVisible} onClick={() => setInventarioVisible((v) => !v)} />
              <button
                type="button"
                onClick={() => setTecladoVisible((v) => !v)}
                aria-expanded={tecladoVisible}
                className="clay-tecla transicion-estado flex h-16 items-center gap-2 rounded-control bg-superficie2 px-5 text-sm font-semibold active:bg-grafito sm:px-7 sm:text-base"
              >
                ⌨ Escribir a mano
              </button>
            </BarraModo>
            {tecladoVisible && (
              <TecladoManual bodegaId={bodega!.id} onEnviar={(texto) => enviarCaptura({ texto }, 'manual')} />
            )}
          </>
        )}

        {pantalla.tipo === 'lista' && modo === 'guiado' && (
          <>
            <BarraModo modo={modo} onCambiarModo={setModo}>
              <BotonInventario abierto={inventarioVisible} onClick={() => setInventarioVisible((v) => !v)} />
            </BarraModo>
            <ModoGuiado
              objetivo={objetivoGuiado}
              progreso={progresoGuia}
              enviando={pendientes > 0}
              onRegistrar={registrarGuiado}
              onSaltar={saltarGuiado}
              onReiniciar={reiniciarGuiado}
            />
          </>
        )}

        {/* El inventario acompaña TODA la captura: en modo libre para saber qué
            dictar, y en guiado para ver qué falta sin salirse del recorrido. */}
        {pantalla.tipo === 'lista' && inventarioVisible && (
          <ListaInventario
            articulos={articulos}
            contados={contados}
            onCerrar={() => setInventarioVisible(false)}
          />
        )}

        {toast && (
          <div
            className="clay-tecla fixed bottom-6 left-1/2 -translate-x-1/2 rounded-control bg-superficie2 px-6 py-3 text-base"
            role="status"
            aria-live="polite"
          >
            {toast}
          </div>
        )}

        {pantalla.tipo === 'procesando' && (
          <div className="animar-entrada flex w-full max-w-2xl flex-col items-center gap-7">
            {intentoActual ? (
              // J1: sin conexión — informar sin alarmar, nunca rojo.
              <>
                <div className="clay-hundido flex h-[72px] w-full items-center gap-3.5 rounded-control bg-superficie2 px-6">
                  <span className="h-3 w-3 rounded-full bg-texto-tenue" />
                  <span className="text-lg">Sin señal · sigue contando, yo guardo todo aquí</span>
                </div>
                <div className="clay flex h-40 w-40 flex-col items-center justify-center rounded-full bg-superficie1 sm:h-[200px] sm:w-[200px]">
                  <div className="text-2xl font-semibold">{pendientes}</div>
                  <div className="text-sm text-texto-tenue">pendiente{pendientes === 1 ? '' : 's'}</div>
                </div>
                <div className="text-center text-xl font-semibold">Reintentando… (intento {intentoActual})</div>
                <div className="max-w-xl text-center text-lg text-texto-sec">
                  No se pierde nada. Cuando vuelva la señal se sube solo.
                </div>
              </>
            ) : (
              <>
                <div className="clay flex w-full flex-col gap-3 rounded-tarjeta bg-superficie1 p-5 sm:p-8">
                  <div className="text-sm tracking-widest text-texto-tenue">TE ESCUCHÉ</div>
                  <div className="text-xl font-normal leading-snug">“{pantalla.transcripcion}”</div>
                </div>
                <div className="flex items-center gap-3.5">
                  <div className="flex gap-2">
                    <span className="animar-bob h-3.5 w-3.5 rounded-full bg-azul-texto" />
                    <span className="animar-bob h-3.5 w-3.5 rounded-full bg-azul-texto [animation-delay:150ms]" />
                    <span className="animar-bob h-3.5 w-3.5 rounded-full bg-azul-texto [animation-delay:300ms]" />
                  </div>
                  <span className="text-lg text-texto-sec">Buscando el producto…</span>
                </div>
              </>
            )}
          </div>
        )}

        {pantalla.tipo === 'confirmando' && (
          <TarjetaConfirmacion
            conteo={pantalla.conteo}
            viaAclaracion={pantalla.viaAclaracion}
            onCerrar={volverAEscuchar}
          />
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
          // Pantalla F: no es un error del operario — nada de rojo.
          <div className="animar-entrada flex w-full max-w-2xl flex-col gap-6">
            <div className="clay-hundido flex h-[72px] w-[72px] items-center justify-center rounded-full bg-superficie2 text-xl text-texto-sec">
              ?
            </div>
            <div className="text-xl font-semibold">No tengo ese producto en esta bodega</div>
            <div className="clay flex flex-col gap-2.5 rounded-tarjeta bg-superficie1 p-5 sm:p-7">
              <div className="text-sm tracking-widest text-texto-tenue">TE ESCUCHÉ</div>
              <div className="text-xl leading-snug">“{pantalla.textoCapturado}”</div>
            </div>
            <div className="text-lg text-texto-sec">
              Quedó guardado para que el líder lo revise al cierre.
            </div>
            <button
              type="button"
              onClick={volverAEscuchar}
              aria-label="Volver a intentar"
              className="clay-azul transicion-estado h-20 sm:h-[104px] w-full rounded-control bg-accion text-xl font-semibold text-white active:bg-accion-claro"
            >
              Seguir contando
            </button>
          </div>
        )}

        {pantalla.tipo === 'error' && (
          // J2/J3: el rojo vive en la franja, nunca en un botón.
          <div className="animar-entrada flex w-full max-w-2xl flex-col gap-6">
            <div className="flex h-[72px] items-center gap-3.5 rounded-control bg-tinte-critico px-6">
              <span className="flex h-7 w-7 items-center justify-center rounded-full bg-critico text-base font-semibold text-white">
                !
              </span>
              <span className="text-lg">{pantalla.mensaje}</span>
            </div>
            <button
              type="button"
              onClick={volverAEscuchar}
              className="clay-azul transicion-estado h-20 sm:h-[104px] w-full rounded-control bg-accion text-xl font-semibold text-white active:bg-accion-claro"
            >
              Reintentar
            </button>
          </div>
        )}

        {usarAudio && estadoVoz !== 'grabando' && pantalla.tipo === 'lista' && modo === 'libre' && (
          <p className="max-w-md text-center text-sm text-texto-tenue">
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
      className="flex w-full max-w-xl gap-2"
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
        className="clay-hundido transicion-estado h-16 flex-1 rounded-control bg-superficie2 px-5 text-base text-texto placeholder:text-texto-tenue focus:outline-none"
      />
      <button
        type="submit"
        disabled={!texto.trim()}
        className="clay-tecla transicion-estado h-16 rounded-control bg-superficie2 px-6 text-base font-semibold text-texto-sec active:bg-grafito disabled:opacity-40"
      >
        Enviar
      </button>
    </form>
  )
}

/** Selector de modo + acciones de la derecha. Los tabs estaban duplicados en
 *  libre y guiado; ahora una sola barra sirve a los dos. */
function BarraModo({
  modo,
  onCambiarModo,
  children,
}: {
  modo: Modo
  onCambiarModo: (m: Modo) => void
  children: React.ReactNode
}) {
  return (
    <div className="flex w-full flex-wrap items-center justify-between gap-3">
      <div className="clay-hundido flex h-16 rounded-control bg-superficie1 p-1.5" role="tablist" aria-label="Modo de conteo">
        {(['libre', 'guiado'] as const).map((m) => (
          <button
            key={m}
            type="button"
            role="tab"
            aria-selected={modo === m}
            onClick={() => onCambiarModo(m)}
            className={`transicion-estado w-28 rounded-chip text-sm sm:w-32 sm:text-base ${
              modo === m ? 'clay-tecla bg-superficie2 font-semibold text-texto' : 'text-texto-tenue'
            }`}
          >
            {m === 'libre' ? 'Modo libre' : 'Modo guiado'}
          </button>
        ))}
      </div>
      <div className="flex flex-1 flex-wrap justify-end gap-3">{children}</div>
    </div>
  )
}

function BotonInventario({ abierto, onClick }: { abierto: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-expanded={abierto}
      className="clay-tecla transicion-estado flex h-16 items-center gap-2 rounded-control bg-superficie2 px-5 text-sm font-semibold active:bg-grafito sm:px-7 sm:text-base"
    >
      ☰ Inventario
    </button>
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
    <div className="relative flex h-44 w-44 items-center justify-center sm:h-56 sm:w-56">
      {activo && (
        <>
          <span className="animar-anillo absolute inset-0 rounded-full border-[3px] border-accion" />
          <span className="animar-anillo-tarde absolute inset-0 rounded-full border-[3px] border-accion" />
        </>
      )}
      <button
        type="button"
        onClick={onTocar}
        disabled={escuchando}
        aria-label={grabando ? 'Detener grabación y enviar' : 'Hablar para registrar un conteo'}
        className={`transicion-estado flex h-44 w-44 items-center justify-center rounded-full bg-accion sm:h-56 sm:w-56 ${
          activo ? 'animar-respira' : 'active:bg-accion-claro'
        }`}
        style={{
          boxShadow:
            '0 30px 56px -20px rgba(0,70,125,.95), inset 0 3px 0 rgba(255,255,255,.22), inset 0 -6px 14px rgba(0,0,0,.35)',
        }}
      >
        {grabando ? (
          <Square className="h-16 w-16 text-white sm:h-20 sm:w-20" fill="currentColor" strokeWidth={1.5} />
        ) : (
          <Mic className="h-20 w-20 text-white sm:h-24 sm:w-24" strokeWidth={1.75} />
        )}
      </button>
    </div>
  )
}

// F1: color del punto por nivel. Sutil y no invasivo; nunca rojo (no es error).
const PUNTO_CONFIANZA: Record<NivelConfianza, string> = {
  alta: 'bg-exito',
  media: 'bg-azul-texto',
  revisar: 'bg-texto-tenue',
}

function TarjetaConfirmacion({
  conteo,
  viaAclaracion,
  onCerrar,
}: {
  conteo: Conteo
  viaAclaracion: boolean
  onCerrar: () => void
}) {
  // F1: indicador de confianza — auto-confirmado vs. revisado. Usa solo la
  // confianza del pipeline; jamás el SD (conteo ciego intacto).
  const indicador = indicadorConfianza(conteo.confianza, viaAclaracion)
  return (
    <div className="animar-entrada flex w-full max-w-2xl flex-col gap-5">
      {/* C4: cantidad y unidad a 56/32px, lo primero que se lee a un brazo. */}
      <div className="clay flex w-full flex-col gap-4 rounded-tarjeta bg-superficie1 px-10 py-9">
        <div className="flex items-center justify-between gap-3">
          <div className="text-sm tracking-widest text-texto-tenue">ANOTÉ ESTO</div>
          <div
            className="flex items-center gap-2 text-sm text-texto-tenue"
            aria-label={`Confianza: ${indicador.etiqueta}`}
          >
            <span className={`h-2 w-2 rounded-full ${PUNTO_CONFIANZA[indicador.nivel]}`} />
            {indicador.etiqueta}
          </div>
        </div>
        <div className="flex items-baseline gap-4">
          <div className="text-2xl font-semibold leading-none tabular-nums">{conteo.cantidad}</div>
          <div className="text-xl font-semibold text-texto-sec">{conteo.unidad}</div>
        </div>
        <div className="text-xl font-semibold leading-tight">{conteo.articulo_nombre}</div>
      </div>
      <div className="flex gap-5">
        <button
          type="button"
          onClick={onCerrar}
          aria-label="Confirmar"
          className="clay-azul transicion-estado h-20 sm:h-[104px] flex-[1.4] rounded-control bg-accion text-xl font-semibold text-white active:bg-accion-claro"
        >
          ✓ Correcto
        </button>
        <button
          type="button"
          onClick={onCerrar}
          aria-label="Rechazar"
          className="clay-tecla transicion-estado h-20 sm:h-[104px] flex-1 rounded-control bg-superficie2 text-xl font-semibold active:bg-grafito"
        >
          ✗ Corregir
        </button>
      </div>
    </div>
  )
}
