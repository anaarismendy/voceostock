import { Download, RefreshCw } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { estadoFila, getCierre, totalesCierre, type EstadoFila, type FilaCierre } from '../lib/cierre'
import { CHECKLIST_DEMO } from '../lib/listaGuiada'
import { useOperario } from '../state/OperarioContext'

const ESTILO_ESTADO: Record<EstadoFila, { etiqueta: string; clase: string }> = {
  cuadra: { etiqueta: 'Cuadra', clase: 'text-emerald-400' },
  sobrante: { etiqueta: 'Sobra', clase: 'text-sky-400' },
  faltante: { etiqueta: 'Falta', clase: 'text-amber-400' },
  sin_contar: { etiqueta: 'Sin contar', clase: 'text-slate-500' },
}

// Contenido del reporte de cierre (C9). El header (bodega/volver/salir) lo pone
// PanelLider; aquí solo la tabla de diferencias. Único lugar que muestra el SD.
export default function VistaCierre() {
  const { bodega } = useOperario()
  const [filas, setFilas] = useState<FilaCierre[] | null>(null)
  const [error, setError] = useState(false)
  const [filtro, setFiltro] = useState<EstadoFila | 'todos'>('todos')

  const esperados = useMemo(() => CHECKLIST_DEMO.map((a) => a.articulo_id), [])

  const cargar = useCallback(() => {
    setError(false)
    setFilas(null)
    getCierre(bodega!.id, esperados)
      .then(setFilas)
      .catch(() => setError(true))
  }, [bodega, esperados])

  useEffect(() => {
    cargar()
  }, [cargar])

  const totales = filas ? totalesCierre(filas) : null
  const visibles = useMemo(
    () => (filas ?? []).filter((f) => filtro === 'todos' || estadoFila(f) === filtro),
    [filas, filtro],
  )

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold text-slate-400">Contado vs. teórico</p>
        <div className="flex gap-2">
          <a
            href={`/api/v1/reportes/bodegas/${bodega!.id}/export`}
            download
            aria-label="Descargar Excel de cierre"
            className="flex h-12 items-center gap-2 rounded-xl bg-slate-800 px-4 text-sm font-semibold active:bg-slate-700"
          >
            <Download className="h-5 w-5" /> Excel
          </a>
          <button
            type="button"
            onClick={cargar}
            aria-label="Actualizar cierre"
            className="flex h-12 w-12 items-center justify-center rounded-xl bg-slate-800 active:bg-slate-700"
          >
            <RefreshCw className="h-5 w-5" />
          </button>
        </div>
      </div>

      <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="Filtro de estado">
        {(['todos', 'cuadra', 'sobrante', 'faltante', 'sin_contar'] as const).map((f) => (
          <button
            key={f}
            type="button"
            role="radio"
            aria-checked={filtro === f}
            onClick={() => setFiltro(f)}
            className={`h-10 rounded-full px-4 text-sm font-semibold capitalize ${
              filtro === f ? 'bg-white text-slate-900' : 'bg-slate-800 text-slate-300 active:bg-slate-700'
            }`}
          >
            {f === 'todos' ? 'Todos' : ESTILO_ESTADO[f].etiqueta}
          </button>
        ))}
      </div>

      {totales && (
        <div className="grid grid-cols-4 gap-2 text-center">
          <Tarjeta valor={totales.cuadran} etiqueta="Cuadran" clase="text-emerald-400" />
          <Tarjeta valor={totales.sobrantes} etiqueta="Sobran" clase="text-sky-400" />
          <Tarjeta valor={totales.faltantes} etiqueta="Faltan" clase="text-amber-400" />
          <Tarjeta valor={totales.sinContar} etiqueta="Sin contar" clase="text-slate-400" />
        </div>
      )}

      {error && <p className="text-lg text-red-400">No se pudo cargar el reporte de cierre.</p>}
      {!error && filas === null && <p className="text-lg text-slate-300">Cargando cierre…</p>}
      {filas && filas.length === 0 && (
        <p className="text-lg text-slate-300">Todavía no hay conteos en esta sesión.</p>
      )}

      {filas && visibles.length > 0 && (
        <table className="w-full border-collapse text-left">
          <thead className="text-sm text-slate-400">
            <tr>
              <th className="py-2 pr-2">Artículo</th>
              <th className="px-2 text-right">Contado</th>
              <th className="px-2 text-right">Teórico</th>
              <th className="px-2 text-right">Dif.</th>
            </tr>
          </thead>
          <tbody>
            {visibles.map((fila) => {
              const estilo = ESTILO_ESTADO[estadoFila(fila)]
              return (
                <tr key={fila.articulo_id} className="border-t border-slate-800">
                  <td className="py-3 pr-2">
                    <span className="font-medium capitalize">{fila.articulo_nombre.toLowerCase()}</span>
                    <span className={`ml-2 text-xs font-semibold uppercase ${estilo.clase}`}>{estilo.etiqueta}</span>
                    {fila.evidencia_url && (
                      // Evidencia de voz (C9): reproducible directo en la fila.
                      <audio controls preload="none" src={fila.evidencia_url} className="mt-1 h-8 w-48" />
                    )}
                  </td>
                  <td className="px-2 text-right tabular-nums">{fila.contado}</td>
                  <td className="px-2 text-right tabular-nums text-slate-400">{fila.sd}</td>
                  <td className={`px-2 text-right font-semibold tabular-nums ${estilo.clase}`}>
                    {fila.diferencia > 0 ? `+${fila.diferencia}` : fila.diferencia}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      )}
    </div>
  )
}

function Tarjeta({ valor, etiqueta, clase }: { valor: number; etiqueta: string; clase: string }) {
  return (
    <div className="rounded-2xl bg-slate-800 py-3">
      <p className={`text-3xl font-bold tabular-nums ${clase}`}>{valor}</p>
      <p className="text-xs text-slate-400">{etiqueta}</p>
    </div>
  )
}
