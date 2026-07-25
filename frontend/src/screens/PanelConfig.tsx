import { useEffect, useState } from 'react'
import {
  getSinonimos,
  getUmbrales,
  putUmbrales,
  umbralesValidos,
  type Sinonimo,
  type Umbrales,
} from '../lib/config'

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
