import { expect, test } from 'vitest'
import { resumenDashboard } from './dashboard.ts'
import type { ConteoRegistrado } from './store.ts'

function conteo(id: number, nombre = `A${id}`): ConteoRegistrado {
  return { articulo_id: id, articulo_nombre: nombre, cantidad: 1, unidad: 'Unidad' }
}

test('cuenta total y artículos únicos', () => {
  const r = resumenDashboard([conteo(1), conteo(1), conteo(2)])
  expect(r.total_conteos).toBe(3)
  expect(r.articulos_unicos).toBe(2)
})

test('recientes: los más nuevos primero, acotado al límite', () => {
  const conteos = [conteo(1), conteo(2), conteo(3), conteo(4)]
  const r = resumenDashboard(conteos, 2)
  expect(r.recientes.map((c) => c.articulo_id)).toEqual([4, 3])
})

test('lista vacía', () => {
  expect(resumenDashboard([])).toEqual({ total_conteos: 0, articulos_unicos: 0, recientes: [] })
})
