import { Download, RefreshCw } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { estadoFila, getCierre, totalesCierre, type EstadoFila, type FilaCierre } from '../lib/cierre'
import { CHECKLIST_DEMO } from '../lib/listaGuiada'
import { useOperario } from '../state/OperarioContext'

const ESTILO_ESTADO: Record<EstadoFila, { etiqueta: string; clase: string }> = {
  cuadra: { etiqueta: 'OK Cuadra', clase: 'text-exito' },
  sobrante: { etiqueta: '+ Sobra', clase: 'text-alerta' },
  faltante: { etiqueta: '- Falta', clase: 'text-critico' },
  sin_contar: { etiqueta: 'Sin contar', clase: 'text-texto-tenue' },
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
        <p className="text-sm font-semibold text-texto-sec">Contado vs. teórico</p>
        <div className="flex gap-2">
          <a
            href={`/api/v1/reportes/bodegas/${bodega!.id}/export`}
            download
            aria-label="Descargar Excel de cierre"
            className="transicion-estado flex h-16 items-center gap-2 rounded-control border border-borde-sutil bg-superficie1 px-4 text-sm font-semibold active:bg-superficie2"
          >
            <Download className="h-5 w-5" /> Excel
          </a>
          <button
            type="button"
            onClick={cargar}
            aria-label="Actualizar cierre"
            className="transicion-estado flex h-16 w-16 items-center justify-center rounded-control border border-borde-sutil bg-superficie1 active:bg-superficie2"
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
            className={`transicion-estado h-16 rounded-control px-4 text-sm font-semibold capitalize ${
              filtro === f ? 'bg-tinte text-acento' : 'border border-borde-sutil bg-superficie1 text-texto-sec active:bg-superficie2'
            }`}
          >
            {f === 'todos' ? 'Todos' : ESTILO_ESTADO[f].etiqueta}
          </button>
        ))}
      </div>

      {totales && (
        <div className="grid grid-cols-4 gap-2 text-center">
          <Tarjeta valor={totales.cuadran} etiqueta="Cuadran" clase="text-exito" />
          <Tarjeta valor={totales.sobrantes} etiqueta="Sobran" clase="text-alerta" />
          <Tarjeta valor={totales.faltantes} etiqueta="Faltan" clase="text-critico" />
          <Tarjeta valor={totales.sinContar} etiqueta="Sin contar" clase="text-texto-sec" />
        </div>
      )}

      {error && <p className="text-base text-critico">No se pudo cargar el reporte de cierre.</p>}
      {!error && filas === null && <p className="text-base text-texto-sec">Cargando cierre…</p>}
      {filas && filas.length === 0 && (
        <p className="text-base text-texto-sec">Todavía no hay conteos en esta sesión.</p>
      )}

      {filas && visibles.length > 0 && (
        <table className="w-full border-collapse text-left text-base">
          <thead className="text-sm text-texto-sec">
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
                <tr key={fila.articulo_id} className="border-t border-borde-sutil">
                  <td className="py-3 pr-2">
                    <span className="font-medium capitalize">{fila.articulo_nombre.toLowerCase()}</span>
                    <span className={`ml-2 text-xs font-semibold uppercase ${estilo.clase}`}>{estilo.etiqueta}</span>
                    {fila.evidencia_url && (
                      // Evidencia de voz (C9): reproducible directo en la fila.
                      <audio controls preload="none" src={fila.evidencia_url} className="mt-1 h-8 w-48" />
                    )}
                  </td>
                  <td className="px-2 text-right tabular-nums">{fila.contado}</td>
                  <td className="px-2 text-right tabular-nums text-texto-sec">{fila.sd}</td>
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
    <div className="rounded-tarjeta border border-borde-sutil bg-superficie1 py-3">
      <p className={`text-xl font-semibold tabular-nums ${clase}`}>{valor}</p>
      <p className="text-xs text-texto-sec">{etiqueta}</p>
    </div>
  )
}
