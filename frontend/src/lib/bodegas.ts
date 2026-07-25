export interface Bodega {
  id: number
  nombre: string
  /** Rediseño (pantalla B): tamaño y estado para la tarjeta. */
  total_articulos?: number
  en_conteo?: boolean
}

export async function getBodegas(): Promise<Bodega[]> {
  const r = await fetch('/api/v1/bodegas')
  if (!r.ok) throw new Error(`Error ${r.status} al listar bodegas`)
  return r.json()
}
