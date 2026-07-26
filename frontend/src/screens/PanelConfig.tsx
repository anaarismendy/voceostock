import { useEffect, useState } from 'react'
import {
  getSinonimos,
  getUmbrales,
  putUmbrales,
  umbralesValidos,
  type Sinonimo,
  type Umbrales,
} from '../lib/config'
import {
  crearOperario,
  editarOperario,
  efectoConfianza,
  getOperarios,
  pinValido,
  recalcularOperarios,
  type OperarioForm,
  type OperarioStats,
} from '../lib/operarios'

// F3: panel de ajustes del líder (consume E2). Edita los umbrales de confianza
// y revisa los sinónimos aprendidos. Al guardar, el backend recarga el pipeline
// vivo → el cambio se refleja en la siguiente captura sin reiniciar. Sin SD.
export default function PanelConfig() {
  const [umbrales, setUmbrales] = useState<Umbrales | null>(null)
  const [sinonimos, setSinonimos] = useState<Sinonimo[]>([])
  const [guardando, setGuardando] = useState(false)
  const [mensaje, setMensaje] = useState<string | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    getUmbrales().then(setUmbrales).catch(() => setError(true))
    getSinonimos().then(setSinonimos).catch(() => setSinonimos([]))
  }, [])

  function set(campo: keyof Umbrales, valor: number) {
    setUmbrales((u) => (u ? { ...u, [campo]: valor } : u))
    setMensaje(null)
  }

  async function guardar() {
    if (!umbrales || !umbralesValidos(umbrales)) return
    setGuardando(true)
    setMensaje(null)
    try {
      const guardado = await putUmbrales(umbrales)
      setUmbrales(guardado)
      setMensaje('Guardado. Se aplica desde la próxima captura.')
    } catch {
      setMensaje('No se pudo guardar. Revisa la conexión.')
    } finally {
      setGuardando(false)
    }
  }

  if (error) return <p className="text-base text-critico-claro">No se pudo cargar la configuración.</p>
  if (!umbrales) return <p className="text-base text-texto-sec">Cargando configuración…</p>

  const valido = umbralesValidos(umbrales)

  return (
    <div className="flex flex-col gap-6">
      <div className="clay flex flex-col gap-4 rounded-tarjeta bg-superficie1 p-6">
        <div>
          <p className="text-xl font-semibold">Sensibilidad de confirmación</p>
          <p className="mt-1 text-sm text-texto-tenue">
            Confianza mínima para cada acción (0 a 1). Arriba de <b>auto</b> se confirma solo;
            debajo de <b>aclaración</b> se ofrecen candidatos.
          </p>
        </div>
        <CampoUmbral etiqueta="Auto (confirmar solo)" valor={umbrales.auto} onChange={(v) => set('auto', v)} />
        <CampoUmbral etiqueta="Rápida (confirmación ágil)" valor={umbrales.rapida} onChange={(v) => set('rapida', v)} />
        <CampoUmbral etiqueta="Aclaración (preguntar)" valor={umbrales.aclaracion} onChange={(v) => set('aclaracion', v)} />
        {!valido && (
          <p className="text-sm text-critico-claro">
            Debe cumplirse: aclaración ≤ rápida ≤ auto, todo entre 0 y 1.
          </p>
        )}
        <div className="flex items-center gap-4">
          <button
            type="button"
            onClick={guardar}
            disabled={!valido || guardando}
            className="clay-azul transicion-estado h-16 rounded-control bg-accion px-8 text-base font-semibold text-white active:bg-accion-claro disabled:opacity-40"
          >
            {guardando ? 'Guardando…' : 'Guardar'}
          </button>
          {mensaje && <span className="text-sm text-texto-sec" role="status">{mensaje}</span>}
        </div>
      </div>

      <div className="clay flex flex-col gap-3 rounded-tarjeta bg-superficie1 p-6">
        <p className="text-xl font-semibold">Sinónimos aprendidos</p>
        {sinonimos.length === 0 ? (
          <p className="text-sm text-texto-tenue">Todavía no hay sinónimos registrados.</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {sinonimos.map((sino) => (
              <li key={sino.id} className="flex items-center justify-between rounded-chip bg-superficie2 px-4 py-3">
                <span className="capitalize">{sino.texto_sinonimo}</span>
                <span className="text-sm text-texto-tenue">
                  #{sino.articulo_id} · {sino.origen}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <SeccionOperarios />
    </div>
  )
}

// Módulo por operario (D5): quién se equivoca más y qué está haciendo el sistema
// al respecto. Las estadísticas se refrescan solas al cerrar cada sesión; el
// botón es para verlas al día sin esperar al cierre.
function SeccionOperarios() {
  const [operarios, setOperarios] = useState<OperarioStats[] | null>(null)
  const [recalculando, setRecalculando] = useState(false)
  const [creando, setCreando] = useState(false)
  const [editando, setEditando] = useState<string | null>(null)

  useEffect(() => {
    getOperarios().then(setOperarios).catch(() => setOperarios([]))
  }, [])

  async function recalcular() {
    setRecalculando(true)
    try {
      setOperarios(await recalcularOperarios())
    } catch {
      /* se queda con lo último bueno; el cierre de sesión lo reintenta */
    } finally {
      setRecalculando(false)
    }
  }

  return (
    <div className="clay flex flex-col gap-3 rounded-tarjeta bg-superficie1 p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xl font-semibold">Operarios</p>
          <p className="mt-1 text-sm text-texto-tenue">
            Precisión histórica de cada uno. A quien más se equivoca, el sistema le baja la
            confianza y le pide confirmar más seguido.
          </p>
        </div>
        <button
          type="button"
          onClick={recalcular}
          disabled={recalculando}
          className="clay transicion-estado h-12 shrink-0 rounded-control bg-superficie2 px-5 text-sm font-semibold disabled:opacity-40"
        >
          {recalculando ? 'Recalculando…' : 'Recalcular'}
        </button>
      </div>

      {operarios === null ? (
        <p className="text-sm text-texto-tenue">Cargando operarios…</p>
      ) : operarios.length === 0 ? (
        <p className="text-sm text-texto-tenue">
          Todavía no hay operarios. Da de alta al menos uno: sin PIN registrado nadie puede
          entrar.
        </p>
      ) : (
        <ul className="flex flex-col gap-2">
          {operarios.map((o) =>
            editando === o.id ? (
              <li key={o.id}>
                <FormOperario
                  inicial={{ nombre: o.nombre, pin: '', rol: o.rol ?? 'operario' }}
                  pinOpcional
                  onCancelar={() => setEditando(null)}
                  onGuardar={async (datos) => {
                    // PIN vacío = "no lo cambies": no se manda al backend.
                    const cambios = datos.pin ? datos : { nombre: datos.nombre, rol: datos.rol }
                    const act = await editarOperario(o.id, cambios)
                    setOperarios((xs) => (xs ?? []).map((x) => (x.id === o.id ? act : x)))
                    setEditando(null)
                  }}
                />
              </li>
            ) : (
              <li
                key={o.id}
                className="flex items-center justify-between gap-4 rounded-chip bg-superficie2 px-4 py-3"
              >
                <div className="min-w-0">
                  <p className="truncate text-base font-semibold">
                    {o.nombre}
                    {o.rol !== 'operario' && (
                      <span className="ml-2 text-sm font-normal text-texto-tenue capitalize">
                        {o.rol}
                      </span>
                    )}
                  </p>
                  <p className="text-sm text-texto-tenue">{efectoConfianza(o)}</p>
                </div>
                <div className="flex shrink-0 items-center gap-4">
                  <div className="text-right tabular-nums">
                    <p className="text-base">
                      {o.precision === null ? '—' : `${Math.round(o.precision * 100)}%`}
                    </p>
                    <p className="text-sm text-texto-tenue">
                      {o.capturas_totales} capturas
                      {o.perfil_activo && ` · ${o.ajuste > 0 ? '+' : ''}${o.ajuste.toFixed(2)}`}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setEditando(o.id)
                      setCreando(false)
                    }}
                    className="transicion-estado h-11 rounded-chip px-4 text-sm font-semibold text-texto-tenue active:bg-superficie1"
                  >
                    Editar
                  </button>
                </div>
              </li>
            ),
          )}
        </ul>
      )}

      {creando ? (
        <FormOperario
          inicial={{ nombre: '', pin: '', rol: 'operario' }}
          onCancelar={() => setCreando(false)}
          onGuardar={async (datos) => {
            const nuevo = await crearOperario(datos)
            setOperarios((xs) => [...(xs ?? []), nuevo])
            setCreando(false)
          }}
        />
      ) : (
        <button
          type="button"
          onClick={() => {
            setCreando(true)
            setEditando(null)
          }}
          className="clay transicion-estado h-14 rounded-control bg-superficie2 text-base font-semibold"
        >
          + Agregar operario
        </button>
      )}
    </div>
  )
}

// Alta y edición comparten formulario. En edición el PIN va vacío y opcional:
// se deja en blanco para no cambiarlo.
function FormOperario({
  inicial,
  pinOpcional = false,
  onGuardar,
  onCancelar,
}: {
  inicial: OperarioForm
  pinOpcional?: boolean
  onGuardar: (datos: OperarioForm) => Promise<void>
  onCancelar: () => void
}) {
  const [datos, setDatos] = useState<OperarioForm>(inicial)
  const [error, setError] = useState<string | null>(null)
  const [guardando, setGuardando] = useState(false)

  const pinOk = pinOpcional && datos.pin === '' ? true : pinValido(datos.pin)
  const valido = datos.nombre.trim().length > 0 && pinOk

  async function guardar() {
    if (!valido) return
    setGuardando(true)
    setError(null)
    try {
      await onGuardar({ ...datos, nombre: datos.nombre.trim() })
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setGuardando(false)
    }
  }

  return (
    <div className="clay-hundido flex flex-col gap-3 rounded-control bg-superficie2 p-4">
      <div className="flex flex-wrap gap-3">
        <label className="flex min-w-[180px] flex-1 flex-col gap-1">
          <span className="text-sm text-texto-tenue">Nombre</span>
          <input
            type="text"
            value={datos.nombre}
            onChange={(e) => setDatos({ ...datos, nombre: e.target.value })}
            className="h-14 rounded-control bg-superficie1 px-4 text-base text-texto focus:outline-none"
          />
        </label>
        <label className="flex w-32 flex-col gap-1">
          <span className="text-sm text-texto-tenue">
            PIN {pinOpcional && <span className="text-texto-tenue">(opcional)</span>}
          </span>
          <input
            type="text"
            inputMode="numeric"
            maxLength={4}
            placeholder={pinOpcional ? 'sin cambio' : '4 dígitos'}
            value={datos.pin}
            onChange={(e) =>
              setDatos({ ...datos, pin: e.target.value.replace(/\D/g, '').slice(0, 4) })
            }
            className="h-14 rounded-control bg-superficie1 px-4 text-base tabular-nums text-texto focus:outline-none"
          />
        </label>
        <label className="flex w-36 flex-col gap-1">
          <span className="text-sm text-texto-tenue">Rol</span>
          <select
            value={datos.rol}
            onChange={(e) => setDatos({ ...datos, rol: e.target.value })}
            className="h-14 rounded-control bg-superficie1 px-3 text-base text-texto focus:outline-none"
          >
            <option value="operario">Operario</option>
            <option value="auditor">Auditor</option>
            <option value="lider">Líder</option>
          </select>
        </label>
      </div>

      {error && <p className="text-sm text-critico-claro">{error}</p>}

      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={guardar}
          disabled={!valido || guardando}
          className="clay-azul transicion-estado h-14 rounded-control bg-accion px-6 text-base font-semibold text-white disabled:opacity-40"
        >
          {guardando ? 'Guardando…' : 'Guardar'}
        </button>
        <button
          type="button"
          onClick={onCancelar}
          className="transicion-estado h-14 rounded-control px-4 text-base text-texto-tenue"
        >
          Cancelar
        </button>
      </div>
    </div>
  )
}

function CampoUmbral({
  etiqueta,
  valor,
  onChange,
}: {
  etiqueta: string
  valor: number
  onChange: (v: number) => void
}) {
  return (
    <label className="flex items-center justify-between gap-4">
      <span className="text-base">{etiqueta}</span>
      <input
        type="number"
        min={0}
        max={1}
        step={0.01}
        value={valor}
        onChange={(e) => onChange(Number(e.target.value))}
        className="clay-hundido h-14 w-28 rounded-control bg-superficie2 px-4 text-right text-lg tabular-nums text-texto focus:outline-none"
      />
    </label>
  )
}
