import { expect, test } from 'vitest'
import { calcularCierre } from './cierre.ts'
import type { ArticuloCatalogo } from './catalogo.ts'
import type { ConteoRegistrado } from './store.ts'

const CATALOGO: ArticuloCatalogo[] = [
  { bodega: 'X', nr_articulo: '100', articulo: 'ACEITE', unidad: 'Liter', sd: 10 },
  { bodega: 'X', nr_articulo: '200', articulo: 'POLLO', unidad: 'Kilogram', sd: 5 },
  { bodega: 'X', nr_articulo: '300', articulo: 'CAZUELA', unidad: 'Unidad', sd: 8 },
]

test('une contado + SD y calcula la diferencia', () => {
  const conteos: ConteoRegistrado[] = [
    { articulo_id: 100, articulo_nombre: 'ACEITE', cantidad: 12, unidad: 'Liter' },
  ]
  const filas = calcularCierre(CATALOGO, conteos, [100])
  expect(filas).toHaveLength(1)
  expect(filas[0]).toMatchObject({ articulo_id: 100, sd: 10, contado: 12, diferencia: 2 })
})

test('suma varios conteos del mismo artículo (append-only)', () => {
  const conteos: ConteoRegistrado[] = [
    { articulo_id: 200, articulo_nombre: 'POLLO', cantidad: 2, unidad: 'Kilogram' },
    { articulo_id: 200, articulo_nombre: 'POLLO', cantidad: 3, unidad: 'Kilogram' },
  ]
  const [fila] = calcularCierre(CATALOGO, conteos, [200])
  expect(fila.contado).toBe(5)
  expect(fila.diferencia).toBe(0) // 5 contado vs 5 SD
})

test('un esperado sin contar aparece con contado 0 y diferencia negativa', () => {
  const filas = calcularCierre(CATALOGO, [], [300])
  expect(filas[0]).toMatchObject({ articulo_id: 300, contado: 0, sd: 8, diferencia: -8 })
})

test('incluye artículos contados aunque no estén en la lista esperada', () => {
  const conteos: ConteoRegistrado[] = [
    { articulo_id: 200, articulo_nombre: 'POLLO', cantidad: 1, unidad: 'Kilogram' },
  ]
  const filas = calcularCierre(CATALOGO, conteos, [100])
  const ids = filas.map((f) => f.articulo_id).sort()
  expect(ids).toEqual([100, 200])
})

test('ordena por desvío absoluto descendente', () => {
  const conteos: ConteoRegistrado[] = [
    { articulo_id: 100, articulo_nombre: 'ACEITE', cantidad: 11, unidad: 'Liter' }, // dif 1
    { articulo_id: 200, articulo_nombre: 'POLLO', cantidad: 15, unidad: 'Kilogram' }, // dif 10
  ]
  const filas = calcularCierre(CATALOGO, conteos, [])
  expect(filas[0].articulo_id).toBe(200) // mayor desvío primero
})
