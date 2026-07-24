import type { ArticuloCatalogo } from './catalogo.ts'
import { buscarPorId } from './catalogo.ts'
import type { ConteoRegistrado } from './store.ts'

// Semilla de demo (C11): deja el dashboard y el cierre con datos al arrancar,
// contando una historia clara. `contado = sd + delta`, así el reporte muestra
// a propósito un artículo que cuadra, uno que sobra y uno que falta; el resto
// del checklist queda sin contar para contarlo EN VIVO durante la demo.

interface ItemSemilla {
  articulo_id: number
  delta: number
}

const SEMILLA: ItemSemilla[] = [
  { articulo_id: 7293, delta: 0 }, // ACEITE DE OLIVA -> cuadra
  { articulo_id: 95026919, delta: 2 }, // CAZUELA 16 ONZ -> sobra (+2)
  { articulo_id: 2027, delta: -3 }, // COSTILLA DE RES -> falta (-3)
]

const MINUTO = 60_000

/**
 * `ahora` se inyecta (Date.now en el arranque, o un valor fijo en pruebas).
 * Los conteos se marcan escalonados "hacia atrás" para que en el feed en vivo
 * aparezcan como capturas de hace unos minutos, no como recién hechas.
 */
export function conteosSemilla(catalogo: ArticuloCatalogo[], ahora: number): ConteoRegistrado[] {
  const salida: ConteoRegistrado[] = []
  SEMILLA.forEach((item, i) => {
    const art = buscarPorId(catalogo, String(item.articulo_id))
    if (!art) return
    salida.push({
      articulo_id: item.articulo_id,
      articulo_nombre: art.articulo,
      cantidad: Number((art.sd + item.delta).toFixed(3)),
      unidad: art.unidad,
      creado_en: ahora - (SEMILLA.length - i) * 3 * MINUTO,
    })
  })
  return salida
}
