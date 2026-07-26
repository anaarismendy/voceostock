import type { ConteoRegistrado } from './store.ts'

// Resumen en vivo para el dashboard (C10). Conteo ciego: NO expone SD; solo
// actividad de captura (qué se contó y cuándo), nunca cuánto había teórico.

export interface KpisDashboard {
  dispositivos_offline: number
  precision_reconocimiento: number // 0..1
  pct_correcciones: number // 0..1
}

export interface ResumenDashboard {
  total_conteos: number
  articulos_unicos: number
  kpis: KpisDashboard
  recientes: ConteoRegistrado[]
}

// F2: KPIs sintéticos de demo (el backend real los calcula de E-stats/J4). Son
// DETERMINISTAS: no usan Math.random para que la demo no titile entre polls.
function kpisDemo(conteos: ConteoRegistrado[]): KpisDashboard {
  return {
    dispositivos_offline: 0, // demo: todos en línea
    precision_reconocimiento: 0.94,
    // sube levemente con la actividad, sin pasar de ~8% (plausible en demo)
    pct_correcciones: Math.min(0.08, 0.02 + conteos.length * 0.005),
  }
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
    kpis: kpisDemo(conteos),
    recientes,
  }
}
