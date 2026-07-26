import { Download, RefreshCw } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { getArticulos } from '../lib/articulos'
import { estadoFila, getCierre, totalesCierre, type EstadoFila, type FilaCierre } from '../lib/cierre'
import { useOperario } from '../state/OperarioContext'

// El cierre se refresca solo: el líder lo deja abierto mientras el operario
// sigue contando, y antes solo se actualizaba con el botón ↻.
const REFRESCO_MS = 5000

// Semáforo con icono + palabra: funciona en blanco y negro (design doc H).
const ESTILO_ESTADO: Record<EstadoFila, { etiqueta: string; icono: string; clase: string }> = {
  cuadra: { etiqueta: 'Cuadra', icono: '✓', clase: 'text-exito-claro' },
  sobrante: { etiqueta: 'Sobra', icono: '▲', clase: 'text-marca' },
  faltante: { etiqueta: 'Falta', icono: '▼', clase: 'text-critico-claro' },
  sin_contar: { etiqueta: 'Sin contar', icono: '—', clase: 'text-texto-tenue' },
}

// Contenido del reporte de cierre (C9 / pantalla H). Único lugar del frontend
// que muestra el SD (reporte del líder, sancionado por CLAUDE.md).
export default function VistaCierre() {
  const { bodega } = useOperario()
  const [filas, setFilas] = useState<FilaCierre[] | null>(null)
  const [error, setError] = useState(false)
  const [filtro, setFiltro] = useState<EstadoFila | 'todos'>('todos')

  // "Sin contar" = artículos de ESTA bodega que nadie contó todavía. Antes eran
  // 8 ids hardcodeados de demo, que ni siquiera pertenecían a la bodega abierta.
  const [esperados, setEsperados] = useState<number[]>([])

  useEffect(() => {
    let vivo = true
    getArticulos(bodega!.id)
      .then((arts) => vivo && setEsperados(arts.map((a) => a.articulo_id)))
      .catch(() => {
        /* sin catálogo: el cierre muestra solo lo contado */
      })
    return () => {
      vivo = false
    }
  }, [bodega])

  // `silencioso`: el refresco automático no vacía la tabla (sin parpadeo a
  // "Cargando cierre…" cada 5 s); el botón ↻ y el arranque sí muestran carga.
  const cargar = useCallback(
    (silencioso = false) => {
      if (!silencioso) {
        setError(false)
        setFilas(null)
      }
      getCierre(bodega!.id, esperados)
        .then((f) => {
          setFilas(f)
          setError(false)
        })
        .catch(() => !silencioso && setError(true))
    },
    [bodega, esperados],
  )

  useEffect(() => {
    cargar()
    const id = setInterval(() => cargar(true), REFRESCO_MS)
    return () => clearInterval(id)
  }, [cargar])

  const totales = filas ? totalesCierre(filas) : null
  const visibles = useMemo(
    () => (filas ?? []).filter((f) => filtro === 'todos' || estadoFila(f) === filtro),
    [filas, filtro],
  )

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex flex-col gap-1">
          <p className="text-sm text-texto-tenue">Contado vs. teórico</p>
          <p className="text-xl font-semibold">Diferencias del conteo</p>
        </div>
        <div className="flex gap-3">
          <a
            href={`/api/v1/reportes/bodegas/${bodega!.id}/export`}
            download
            aria-label="Descargar Excel de cierre"
            className="clay-azul transicion-estado flex h-16 items-center gap-2.5 rounded-control bg-accion px-6 text-base font-semibold text-white active:bg-accion-claro"
          >
            <Download className="h-5 w-5" /> Exportar Excel
          </a>
          <button
            type="button"
            onClick={() => cargar()}
            aria-label="Actualizar cierre"
            className="clay-tecla transicion-estado flex h-16 w-16 items-center justify-center rounded-control bg-superficie2 active:bg-grafito"
          >
            <RefreshCw className="h-5 w-5" />
          </button>
        </div>
      </div>

      {totales && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <TarjetaTotal valor={totales.cuadran} etiqueta="Cuadran" clase="text-exito-claro" />
          <TarjetaTotal valor={totales.sobrantes} etiqueta="Sobran" clase="text-marca" />
          <TarjetaTotal valor={totales.faltantes} etiqueta="Faltan" clase="text-critico-claro" />
          <TarjetaTotal valor={totales.sinContar} etiqueta="Sin contar" clase="text-texto-sec" />
        </div>
      )}

      <div className="flex flex-wrap gap-3" role="radiogroup" aria-label="Filtro de estado">
        {(['todos', 'cuadra', 'sobrante', 'faltante', 'sin_contar'] as const).map((f) => (
          <button
            key={f}
            type="button"
            role="radio"
            aria-checked={filtro === f}
            onClick={() => setFiltro(f)}
            className={`transicion-estado h-14 rounded-chip px-5 text-sm capitalize ${
              filtro === f
                ? 'clay-tecla bg-superficie2 font-semibold text-texto'
                : 'bg-superficie1 text-texto-sec active:bg-superficie2'
            }`}
          >
            {f === 'todos' ? `Todos${filas ? ` · ${filas.length}` : ''}` : ESTILO_ESTADO[f].etiqueta}
          </button>
        ))}
      </div>

      {error && <p className="text-base text-critico-claro">No se pudo cargar el reporte de cierre.</p>}
      {!error && filas === null && <p className="text-base text-texto-sec">Cargando cierre…</p>}
      {filas && filas.length === 0 && (
        <p className="text-base text-texto-sec">Todavía no hay conteos en esta sesión.</p>
      )}

      {filas && visibles.length > 0 && (
        // overflow-x-auto: la tabla scrollea dentro de su tarjeta, la página no.
        <div className="clay overflow-x-auto rounded-tarjeta bg-superficie1 px-4 pb-5 pt-2 sm:px-5">
          <table className="w-full min-w-[520px] border-collapse text-left">
            <thead className="text-xs tracking-widest text-texto-tenue">
              <tr>
                <th className="py-3.5 pr-2 font-normal">PRODUCTO</th>
                <th className="px-2 text-right font-normal">FÍSICO</th>
                <th className="px-2 text-right font-normal">SISTEMA</th>
                <th className="px-2 text-right font-normal">DIFERENCIA</th>
                <th className="px-2 text-right font-normal">%</th>
                <th className="pl-2 font-normal">ESTADO</th>
              </tr>
            </thead>
            <tbody>
              {visibles.map((fila) => {
                const estilo = ESTILO_ESTADO[estadoFila(fila)]
                const pct = fila.sd > 0 ? `${Math.round((Math.abs(fila.diferencia) / fila.sd) * 100)}%` : '—'
                return (
                  <tr key={fila.articulo_id} className="border-t border-borde">
                    <td className="py-3.5 pr-2">
                      <span className="text-sm font-semibold capitalize">{fila.articulo_nombre.toLowerCase()}</span>
                      {fila.evidencia_url && (
                        // Evidencia de voz (C9): reproducible directo en la fila.
                        <audio controls preload="none" src={fila.evidencia_url} className="mt-1.5 h-8 w-48" />
                      )}
                    </td>
                    <td className="px-2 text-right text-sm tabular-nums">{fila.contado}</td>
                    <td className="px-2 text-right text-sm tabular-nums text-texto-sec">{fila.sd}</td>
                    <td className={`px-2 text-right text-sm font-semibold tabular-nums ${estilo.clase}`}>
                      {fila.diferencia > 0 ? `+${fila.diferencia}` : fila.diferencia}
                    </td>
                    <td className="px-2 text-right text-sm tabular-nums text-texto-sec">{pct}</td>
                    <td className={`pl-2 text-xs font-semibold ${estilo.clase}`}>
                      <span className="mr-1.5">{estilo.icono}</span>
                      {estilo.etiqueta}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function TarjetaTotal({ valor, etiqueta, clase }: { valor: number; etiqueta: string; clase: string }) {
  return (
    <div className="clay rounded-tarjeta bg-superficie1 px-5 py-4">
      <p className={`text-xl font-semibold tabular-nums ${clase}`}>{valor}</p>
      <p className="text-xs text-texto-tenue">{etiqueta}</p>
    </div>
  )
}
