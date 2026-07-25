import type { NivelRiesgo } from './avisoRiesgo'

export interface ArticuloResumen {
  articulo_id: number
  articulo_nombre: string
  unidad: string
  /** F4/E5: nivel de riesgo histórico; viaja en el mismo payload del catálogo
   * (disponible offline, sin request extra). Ausente = sin dato → sin aviso. */
  riesgo?: NivelRiesgo
}

export async function getArticulos(bodegaId?: number): Promise<ArticuloResumen[]> {
  const query = bodegaId != null ? `?bodega_id=${bodegaId}` : ''
  const r = await fetch(`/api/v1/articulos${query}`)
  if (!r.ok) throw new Error(`Error ${r.status} al listar artículos`)
  return r.json()
}
