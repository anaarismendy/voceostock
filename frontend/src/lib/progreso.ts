import type { ArticuloResumen } from './articulos'

// Lógica pura del progreso y del recorrido guiado (C8). Sin React ni DOM para
// poder probarla con vitest. No conoce el stock teórico (SD): el progreso es
// "cuántos artículos del checklist ya se contaron", nunca cuánto había.

export interface ResumenProgreso {
  hechos: number
  total: number
  porcentaje: number // entero 0..100
  completo: boolean
}

/** Resumen del progreso: cuántos items del checklist están en `contados`. */
export function resumenProgreso(
  lista: readonly ArticuloResumen[],
  contados: ReadonlySet<number>,
): ResumenProgreso {
  const total = lista.length
  const hechos = lista.filter((a) => contados.has(a.articulo_id)).length
  const porcentaje = total === 0 ? 0 : Math.round((hechos / total) * 100)
  return { hechos, total, porcentaje, completo: total > 0 && hechos === total }
}

/**
 * Primer artículo del checklist que aún no hay que omitir. `omitir` reúne los
 * ya contados y los saltados: así el recorrido avanza sin repetir. Devuelve
 * null cuando no queda ninguno pendiente.
 */
export function siguientePendiente(
  lista: readonly ArticuloResumen[],
  omitir: ReadonlySet<number>,
): ArticuloResumen | null {
  return lista.find((a) => !omitir.has(a.articulo_id)) ?? null
}

/**
 * Arma el texto que se manda al contrato para un artículo objetivo del modo
 * guiado: "<cantidad> <nombre exacto>". El operario solo dice/teclea la
 * cantidad; el nombre lo pone el checklist, de modo que el match del backend
 * (o del mock) sea exacto y determinista.
 */
export function textoCantidadArticulo(cantidadTexto: string, articulo: ArticuloResumen): string {
  return `${cantidadTexto.trim()} ${articulo.articulo_nombre}`.trim()
}
