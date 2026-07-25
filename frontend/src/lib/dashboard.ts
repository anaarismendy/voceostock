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

export interface ResumenDashboard {
  total_conteos: number
  articulos_unicos: number
  anomalias?: number
  recientes: ConteoReciente[]
}

export async function getDashboard(bodegaId: number): Promise<ResumenDashboard> {
  const r = await fetch(`/api/v1/dashboard?bodega_id=${bodegaId}`)
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
