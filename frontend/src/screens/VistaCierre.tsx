import { RefreshCw } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { estadoFila, getCierre, totalesCierre, type EstadoFila, type FilaCierre } from '../lib/cierre'
import { CHECKLIST_DEMO } from '../lib/listaGuiada'

const ESTILO_ESTADO: Record<EstadoFila, { etiqueta: string; clase: string }> = {
  cuadra: { etiqueta: 'Cuadra', clase: 'text-emerald-400' },
  sobrante: { etiqueta: 'Sobra', clase: 'text-sky-400' },
  faltante: { etiqueta: 'Falta', clase: 'text-amber-400' },
  sin_contar: { etiqueta: 'Sin contar', clase: 'text-slate-500' },
}

// Contenido del reporte de cierre (C9). El header (bodega/volver/salir) lo pone
// PanelLider; aquí solo la tabla de diferencias. Único lugar que muestra el SD.
export default function VistaCierre() {
  const [filas, setFilas] = useState<FilaCierre[] | null>(null)
  const [error, setError] = useState(false)

  const esperados = useMemo(() => CHECKLIST_DEMO.map((a) => a.articulo_id), [])

  const cargar = useCallback(() => {
    setError(false)
    setFilas(null)
    getCierre(esperados)
      .then(setFilas)
      .catch(() => setError(true))
  }, [esperados])

  useEffect(() => {
    cargar()
  }, [cargar])

  const totales = filas ? totalesCierre(filas) : null

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold text-slate-400">Contado vs. teórico</p>
        <button
          type="button"
          onClick={cargar}
          aria-label="Actualizar cierre"
          className="flex h-12 w-12 items-center justify-center rounded-xl bg-slate-800 active:bg-slate-700"
        >
          <RefreshCw className="h-5 w-5" />
        </button>
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

      {filas && filas.length > 0 && (
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
            {filas.map((fila) => {
              const estilo = ESTILO_ESTADO[estadoFila(fila)]
              return (
                <tr key={fila.articulo_id} className="border-t border-slate-800">
                  <td className="py-3 pr-2">
                    <span className="font-medium capitalize">{fila.articulo_nombre.toLowerCase()}</span>
                    <span className={`ml-2 text-xs font-semibold uppercase ${estilo.clase}`}>{estilo.etiqueta}</span>
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
