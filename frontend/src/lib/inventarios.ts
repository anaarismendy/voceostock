export interface Inventario {
  id: number
  bodega_id: number
  numero: number
  estado: 'abierto' | 'cerrado'
  corte_fecha: string | null
  abierto_en: string
  cerrado_en: string | null
  articulos_contados: number
  operarios: number
}

export async function getInventarios(bodegaId: number): Promise<Inventario[]> {
  const r = await fetch(`/api/v1/inventarios?bodega_id=${bodegaId}`)
  if (!r.ok) throw new Error(`Error ${r.status} al listar inventarios`)
  return r.json()
}

export async function abrirInventario(bodegaId: number): Promise<Inventario> {
  const r = await fetch('/api/v1/inventarios', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ bodega_id: bodegaId }),
  })
  if (!r.ok) throw new Error(`Error ${r.status} al abrir el inventario`)
  return r.json()
}

export async function cerrarInventario(id: number): Promise<Inventario> {
  const r = await fetch(`/api/v1/inventarios/${id}/cerrar`, { method: 'POST' })
  if (!r.ok) throw new Error(`Error ${r.status} al cerrar el inventario`)
  return r.json()
}

/** "25 jul — en curso" / "1 – 3 jul". Rango corto, legible de un vistazo. */
export function rangoFechas(inv: Inventario): string {
  const dia = (iso: string) =>
    new Date(iso).toLocaleDateString('es-CO', { day: 'numeric', month: 'short' })
  const desde = dia(inv.abierto_en)
  if (!inv.cerrado_en) return `${desde} — en curso`
  const hasta = dia(inv.cerrado_en)
  return desde === hasta ? desde : `${desde} – ${hasta}`
}

export function etiqueta(inv: Inventario): string {
  return `Inventario #${inv.numero}`
}
