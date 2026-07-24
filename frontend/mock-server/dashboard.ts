import type { ConteoRegistrado } from './store.ts'

// Resumen en vivo para el dashboard (C10). Conteo ciego: NO expone SD; solo
// actividad de captura (qué se contó y cuándo), nunca cuánto había teórico.

export interface ResumenDashboard {
  total_conteos: number
  articulos_unicos: number
  recientes: ConteoRegistrado[]
}

export function resumenDashboard(
  conteos: ConteoRegistrado[],
  limiteRecientes = 15,
): ResumenDashboard {
  const unicos = new Set(conteos.map((c) => c.articulo_id))
  // Los más nuevos primero, acotado al límite del feed.
  const recientes = conteos.slice(-limiteRecientes).reverse()
  return {
    total_conteos: conteos.length,
    articulos_unicos: unicos.size,
    recientes,
  }
}
