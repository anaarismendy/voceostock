import { expect, test } from 'vitest'
import type { ArticuloResumen } from './articulos'
import { resumenProgreso, siguientePendiente, textoCantidadArticulo } from './progreso'

const LISTA: ArticuloResumen[] = [
  { articulo_id: 1, articulo_nombre: 'ACEITE DE OLIVA', unidad: 'Liter' },
  { articulo_id: 2, articulo_nombre: 'POLLO ENTERO', unidad: 'Kilogram' },
  { articulo_id: 3, articulo_nombre: 'CAZUELA 16 ONZ', unidad: 'Unidad' },
]

test('resumenProgreso cuenta solo los items del checklist ya contados', () => {
  expect(resumenProgreso(LISTA, new Set())).toEqual({
    hechos: 0,
    total: 3,
    porcentaje: 0,
    completo: false,
  })
  expect(resumenProgreso(LISTA, new Set([1, 2]))).toEqual({
    hechos: 2,
    total: 3,
    porcentaje: 67,
    completo: false,
  })
})

test('resumenProgreso marca completo cuando están todos', () => {
  const r = resumenProgreso(LISTA, new Set([1, 2, 3]))
  expect(r).toEqual({ hechos: 3, total: 3, porcentaje: 100, completo: true })
})

test('resumenProgreso ignora ids contados fuera del checklist (modo libre)', () => {
  // En modo libre se puede contar algo que no está en el checklist: no infla el progreso.
  const r = resumenProgreso(LISTA, new Set([1, 999]))
  expect(r.hechos).toBe(1)
  expect(r.total).toBe(3)
})

test('resumenProgreso con lista vacía no divide por cero', () => {
  expect(resumenProgreso([], new Set())).toEqual({
    hechos: 0,
    total: 0,
    porcentaje: 0,
    completo: false,
  })
})

test('siguientePendiente devuelve el primero no omitido y avanza', () => {
  expect(siguientePendiente(LISTA, new Set())?.articulo_id).toBe(1)
  expect(siguientePendiente(LISTA, new Set([1]))?.articulo_id).toBe(2)
  expect(siguientePendiente(LISTA, new Set([1, 2]))?.articulo_id).toBe(3)
})

test('siguientePendiente salta los omitidos (contados o saltados)', () => {
  // El 1 saltado, el 2 contado → el siguiente es el 3.
  expect(siguientePendiente(LISTA, new Set([1, 2]))?.articulo_id).toBe(3)
})

test('siguientePendiente devuelve null cuando no queda nada', () => {
  expect(siguientePendiente(LISTA, new Set([1, 2, 3]))).toBeNull()
})

test('textoCantidadArticulo arma "<cantidad> <nombre>" para el match exacto', () => {
  expect(textoCantidadArticulo('33', LISTA[0])).toBe('33 ACEITE DE OLIVA')
  expect(textoCantidadArticulo('  treinta y tres  ', LISTA[0])).toBe('treinta y tres ACEITE DE OLIVA')
})
