import type { ArticuloCatalogo } from './catalogo.ts'
import { buscarPorId } from './catalogo.ts'
import type { ConteoRegistrado } from './store.ts'

// Lógica del reporte de cierre (C9). El SD (stock teórico) SOLO aparece aquí:
// es el único lugar donde el conteo ciego permite exponerlo (ver CLAUDE.md).

export interface FilaCierre {
  articulo_id: number
  articulo_nombre: string
  unidad: string
  sd: number
  contado: number
  diferencia: number // contado - sd
}

/**
 * Une lo contado en la sesión con el SD del catálogo. `esperados` son los ids
 * que el líder quiere ver aunque no se hayan contado (el checklist guiado):
 * así los faltantes aparecen con contado 0 y diferencia negativa. Se agregan
 * también los artículos contados que no estaban en la lista esperada.
 */
export function calcularCierre(
  catalogo: ArticuloCatalogo[],
  conteos: ConteoRegistrado[],
  esperados: number[],
): FilaCierre[] {
  const contadoPorId = new Map<number, { total: number; nombre: string; unidad: string }>()
  for (const c of conteos) {
    const previo = contadoPorId.get(c.articulo_id)
    if (previo) previo.total += c.cantidad
    else contadoPorId.set(c.articulo_id, { total: c.cantidad, nombre: c.articulo_nombre, unidad: c.unidad })
  }

  const ids = [...new Set([...esperados, ...contadoPorId.keys()])]

  const filas = ids.map((id) => {
    const enCatalogo = buscarPorId(catalogo, String(id))
    const contadoInfo = contadoPorId.get(id)
    const sd = enCatalogo ? enCatalogo.sd : 0
    const contado = contadoInfo?.total ?? 0
    return {
      articulo_id: id,
      articulo_nombre: enCatalogo?.articulo ?? contadoInfo?.nombre ?? `#${id}`,
      unidad: enCatalogo?.unidad ?? contadoInfo?.unidad ?? '',
      sd,
      contado,
      diferencia: Number((contado - sd).toFixed(3)),
    }
  })

  // Primero lo que no cuadra (mayor desvío absoluto arriba), luego por nombre.
  return filas.sort(
    (a, b) => Math.abs(b.diferencia) - Math.abs(a.diferencia) || a.articulo_nombre.localeCompare(b.articulo_nombre),
  )
}
