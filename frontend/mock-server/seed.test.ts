import { expect, test } from 'vitest'
import { conteosSemilla } from './seed.ts'
import type { ArticuloCatalogo } from './catalogo.ts'

const AHORA = 1_000_000_000

const CATALOGO: ArticuloCatalogo[] = [
  { bodega: 'X', nr_articulo: '7293', articulo: 'ACEITE DE OLIVA', unidad: 'Liter', sd: 33 },
  { bodega: 'X', nr_articulo: '95026919', articulo: 'CAZUELA 16 ONZ', unidad: 'Unidad', sd: 10 },
  { bodega: 'X', nr_articulo: '2027', articulo: 'COSTILLA DE RES', unidad: 'Kilogram', sd: 66 },
]

test('siembra cuadra / sobra / falta según el delta sobre el SD', () => {
  const semilla = conteosSemilla(CATALOGO, AHORA)
  const porId = new Map(semilla.map((c) => [c.articulo_id, c]))
  expect(porId.get(7293)?.cantidad).toBe(33) // cuadra (sd + 0)
  expect(porId.get(95026919)?.cantidad).toBe(12) // sobra (sd + 2)
  expect(porId.get(2027)?.cantidad).toBe(63) // falta (sd - 3)
})

test('marca timestamps en el pasado y escalonados', () => {
  const semilla = conteosSemilla(CATALOGO, AHORA)
  for (const c of semilla) expect(c.creado_en!).toBeLessThan(AHORA)
  // Escalonados: cada uno más reciente que el anterior.
  const tiempos = semilla.map((c) => c.creado_en!)
  expect(tiempos[0]).toBeLessThan(tiempos[1])
  expect(tiempos[1]).toBeLessThan(tiempos[2])
})

test('omite artículos que no estén en el catálogo (no revienta)', () => {
  const semilla = conteosSemilla([CATALOGO[0]], AHORA)
  expect(semilla).toHaveLength(1)
  expect(semilla[0].articulo_id).toBe(7293)
})
