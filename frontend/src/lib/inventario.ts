import type { ArticuloResumen } from './articulos'

/** Búsqueda sin tildes ni mayúsculas: el operario teclea "aceite" con prisa. */
function normalizar(s: string): string {
  return s
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .trim()
}

/**
 * Filtra el inventario de la bodega por texto y, opcionalmente, deja solo los
 * pendientes. `contados` null = no filtrar por estado.
 */
export function filtrarArticulos(
  articulos: readonly ArticuloResumen[],
  busqueda: string,
  contados: ReadonlySet<number> | null,
): ArticuloResumen[] {
  const q = normalizar(busqueda)
  return articulos.filter(
    (a) =>
      (q === '' || normalizar(a.articulo_nombre).includes(q)) &&
      (contados === null || !contados.has(a.articulo_id)),
  )
}
