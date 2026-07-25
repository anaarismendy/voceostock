import { useEffect, useRef, useState } from 'react'
import { getDashboard, tiempoRelativo, type ResumenDashboard } from '../lib/dashboard'
import { useOperario } from '../state/OperarioContext'

const INTERVALO_MS = 2500

/**
 * Dashboard en vivo (C10). Polea el resumen cada 2.5 s — polling en vez de
 * websockets a propósito: si el wifi del auditorio parpadea, la próxima vuelta
 * se recupera sola, sin conexión que reconectar. Ante un error mantiene el
 * último dato bueno y muestra "reconectando", nunca una pantalla en blanco.
 */
export default function Dashboard() {
  const { bodega } = useOperario()
  const [datos, setDatos] = useState<ResumenDashboard | null>(null)
  const [desconectado, setDesconectado] = useState(false)
  const [ahora, setAhora] = useState(() => Date.now())
  const montado = useRef(true)

  useEffect(() => {
    montado.current = true
    const tick = async () => {
      try {
        const d = await getDashboard(bodega!.id)
        if (!montado.current) return
        setDatos(d)
        setDesconectado(false)
        setAhora(Date.now())
      } catch {
        if (montado.current) setDesconectado(true)
      }
    }
    tick()
    const id = setInterval(tick, INTERVALO_MS)
    return () => {
      montado.current = false
      clearInterval(id)
    }
  }, [])

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-2 text-sm font-semibold">
        {desconectado ? (
          <span className="text-alerta">◌ Reconectando…</span>
        ) : (
          <span className="flex items-center gap-2 text-exito">
            <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-exito" />
            EN VIVO
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-tarjeta border border-borde-sutil bg-superficie1 p-5 text-center">
          <p className="text-2xl font-semibold tabular-nums">{datos?.total_conteos ?? '—'}</p>
          <p className="mt-1 text-sm text-texto-sec">conteos registrados</p>
        </div>
        <div className="rounded-tarjeta border border-borde-sutil bg-superficie1 p-5 text-center">
          <p className="text-2xl font-semibold tabular-nums">{datos?.articulos_unicos ?? '—'}</p>
          <p className="mt-1 text-sm text-texto-sec">artículos distintos</p>
        </div>
      </div>

      <div>
        <p className="mb-2 text-sm font-semibold text-texto-sec">Últimas capturas</p>
        {datos === null && <p className="text-texto-sec">Cargando…</p>}
        {datos && datos.recientes.length === 0 && (
          <p className="text-texto-sec">Aún no hay conteos en esta sesión.</p>
        )}
        <ul className="flex flex-col gap-2">
          {datos?.recientes.map((c, i) => (
            <li
              key={`${c.articulo_id}-${c.creado_en ?? i}`}
              className="flex items-center justify-between rounded-control border border-borde-sutil bg-superficie1 px-4 py-3"
            >
              <span className="min-w-0">
                <span className="text-lg font-semibold tabular-nums">{c.cantidad}</span>{' '}
                <span className="text-texto-sec">{c.unidad}</span>{' '}
                <span className="capitalize">{c.articulo_nombre.toLowerCase()}</span>
              </span>
              <span className="shrink-0 pl-3 text-sm text-texto-tenue">{tiempoRelativo(c.creado_en, ahora)}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
