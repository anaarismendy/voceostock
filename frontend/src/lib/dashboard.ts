// Cliente + helpers del dashboard en vivo (C10). No maneja SD (conteo ciego):
// solo actividad de captura de la sesión.

export interface ConteoReciente {
  articulo_id: number
  articulo_nombre: string
  cantidad: number
  unidad: string
  creado_en?: number
  /** Rediseño (pantalla I): el feed destaca anomalías en amarillo. */
  es_anomalia?: boolean
}

/** F2: KPIs que agrega el backend (E-stats). Opcionales: si no vienen (mock o
 * backend viejo), el widget muestra "—". No incluyen SD (conteo ciego). */
export interface KpisDashboard {
  dispositivos_offline?: number
  precision_reconocimiento?: number // 0..1
  pct_correcciones?: number // 0..1
}

export interface ResumenDashboard {
  total_conteos: number
  articulos_unicos: number
  anomalias?: number
  kpis?: KpisDashboard
  recientes: ConteoReciente[]
}

export async function getDashboard(
  bodegaId: number,
  inventarioId?: number | null,
): Promise<ResumenDashboard> {
  const params = new URLSearchParams({ bodega_id: String(bodegaId) })
  if (inventarioId != null) params.set('inventario_id', String(inventarioId))
  const r = await fetch(`/api/v1/dashboard?${params}`)
  if (!r.ok) throw new Error(`Error ${r.status} al cargar el dashboard`)
  return r.json()
}

/** "ahora" / "hace 12 s" / "hace 3 min" / "hace 2 h". `ahora` se inyecta para testear. */
export function tiempoRelativo(desde: number | undefined, ahora: number): string {
  if (!desde) return ''
  const seg = Math.max(0, Math.round((ahora - desde) / 1000))
  if (seg < 5) return 'ahora'
  if (seg < 60) return `hace ${seg} s`
  const min = Math.floor(seg / 60)
  if (min < 60) return `hace ${min} min`
  const horas = Math.floor(min / 60)
  return `hace ${horas} h`
}
