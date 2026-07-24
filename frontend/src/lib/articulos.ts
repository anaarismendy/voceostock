export interface ArticuloResumen {
  articulo_id: number
  articulo_nombre: string
  unidad: string
}

export async function getArticulos(): Promise<ArticuloResumen[]> {
  const r = await fetch('/api/v1/articulos')
  if (!r.ok) throw new Error(`Error ${r.status} al listar artículos`)
  return r.json()
}
