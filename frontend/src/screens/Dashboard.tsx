import { useEffect, useRef, useState } from 'react'
import { getDashboard, tiempoRelativo, type ResumenDashboard } from '../lib/dashboard'
import { capturasPorMinuto, tiempoPromedioCapturaS } from '../lib/kpis'
import { useOperario } from '../state/OperarioContext'

const INTERVALO_MS = 2500

/**
 * Dashboard en vivo (C10 / pantalla I). Polea el resumen cada 2.5 s — polling
 * a propósito: si el wifi parpadea, la próxima vuelta se recupera sola. Ante
 * un error mantiene el último dato bueno y muestra "reconectando".
 *
 * Diseño: métricas a 56px legibles a 3 metros; el amarillo aparece solo en la
 * métrica de anomalías y en las filas del feed que fueron anomalía.
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
  }, [bodega])

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-center gap-2 text-sm font-semibold">
        {desconectado ? (
          <span className="text-texto-tenue">◌ Reconectando…</span>
        ) : (
          <span className="flex items-center gap-2 text-exito-claro">
            <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-exito" />
            EN VIVO
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3 sm:gap-4">
        <div className="clay rounded-tarjeta bg-superficie1 px-6 py-5">
          <p className="text-xs tracking-widest text-texto-tenue">CONTEOS REGISTRADOS</p>
          <p className="mt-1 text-2xl font-semibold leading-none tabular-nums">{datos?.total_conteos ?? '—'}</p>
        </div>
        <div className="clay rounded-tarjeta bg-superficie1 px-6 py-5">
          <p className="text-xs tracking-widest text-texto-tenue">ARTÍCULOS DISTINTOS</p>
          <p className="mt-1 text-2xl font-semibold leading-none tabular-nums">{datos?.articulos_unicos ?? '—'}</p>
        </div>
        <div className="clay-marca rounded-tarjeta bg-marca px-6 py-5 text-sobre-marca">
          <p className="text-xs tracking-widest">ANOMALÍAS ATRAPADAS</p>
          <p className="mt-1 text-2xl font-semibold leading-none tabular-nums">{datos?.anomalias ?? '—'}</p>
        </div>
      </div>

      {/* F2: KPIs operativos. Los dos primeros se calculan del feed (reales);
          los tres del backend (E-stats) llegan en `kpis` o muestran "—". */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        <Kpi rotulo="CAPTURAS / MIN" valor={fmtNum(datos && capturasPorMinuto(datos.recientes))} />
        <Kpi rotulo="SEG / CAPTURA" valor={fmtNum(datos && tiempoPromedioCapturaS(datos.recientes))} />
        <Kpi rotulo="DISPOSITIVOS OFFLINE" valor={fmtNum(datos?.kpis?.dispositivos_offline)} />
        <Kpi rotulo="PRECISIÓN VOZ" valor={fmtPct(datos?.kpis?.precision_reconocimiento)} />
        <Kpi rotulo="% CORRECCIONES" valor={fmtPct(datos?.kpis?.pct_correcciones)} />
      </div>

      <div>
        <p className="mb-3 text-lg font-semibold text-texto-sec">Lo que está pasando</p>
        {datos === null && <p className="text-texto-sec">Cargando…</p>}
        {datos && datos.recientes.length === 0 && (
          <p className="text-texto-sec">Aún no hay conteos en esta sesión.</p>
        )}
        <ul className="flex flex-col gap-2.5">
          {datos?.recientes.map((c, i) => (
            <li
              key={`${c.articulo_id}-${c.creado_en ?? i}`}
              className={`flex items-center justify-between rounded-chip ${
                c.es_anomalia ? 'clay-marca bg-marca text-sobre-marca' : 'bg-superficie1'
              }`}
              style={{ padding: '14px 18px' }}
            >
              <span className="min-w-0">
                <span className="text-lg font-semibold tabular-nums">{c.cantidad}</span>{' '}
                <span className={c.es_anomalia ? '' : 'text-texto-sec'}>{c.unidad}</span>{' '}
                <span className="capitalize">{c.articulo_nombre.toLowerCase()}</span>
                {c.es_anomalia && <span className="ml-2 text-sm font-semibold">· anomalía confirmada</span>}
              </span>
              <span className={`shrink-0 pl-3 text-sm ${c.es_anomalia ? '' : 'text-texto-tenue'}`}>
                {tiempoRelativo(c.creado_en, ahora)}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}

// F2: "—" cuando el dato no está (mock o backend viejo), nunca 0 engañoso.
function fmtNum(v: number | null | undefined): string {
  return v === null || v === undefined ? '—' : String(v)
}

function fmtPct(v: number | null | undefined): string {
  return v === null || v === undefined ? '—' : `${Math.round(v * 100)}%`
}

function Kpi({ rotulo, valor }: { rotulo: string; valor: string }) {
  return (
    <div className="clay rounded-tarjeta bg-superficie1 px-5 py-4">
      <p className="text-[11px] tracking-widest text-texto-tenue">{rotulo}</p>
      <p className="mt-1 text-xl font-semibold leading-none tabular-nums">{valor}</p>
    </div>
  )
}
