export interface ArticuloResumen {
  articulo_id: number
  articulo_nombre: string
  unidad: string
}

export async function getArticulos(bodegaId?: number): Promise<ArticuloResumen[]> {
  const query = bodegaId != null ? `?bodega_id=${bodegaId}` : ''
  const r = await fetch(`/api/v1/articulos${query}`)
  if (!r.ok) throw new Error(`Error ${r.status} al listar artículos`)
  return r.json()
}
