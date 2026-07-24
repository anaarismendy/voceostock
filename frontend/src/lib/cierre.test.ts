import { expect, test } from 'vitest'
import { estadoFila, totalesCierre, type FilaCierre } from './cierre'

function fila(parcial: Partial<FilaCierre>): FilaCierre {
  return {
    articulo_id: 1,
    articulo_nombre: 'X',
    unidad: 'Unidad',
    sd: 0,
    contado: 0,
    diferencia: 0,
    ...parcial,
  }
}

test('estadoFila clasifica cuadra / sobrante / faltante / sin_contar', () => {
  expect(estadoFila(fila({ contado: 10, sd: 10, diferencia: 0 }))).toBe('cuadra')
  expect(estadoFila(fila({ contado: 12, sd: 10, diferencia: 2 }))).toBe('sobrante')
  expect(estadoFila(fila({ contado: 8, sd: 10, diferencia: -2 }))).toBe('faltante')
  // sin contar gana sobre la diferencia negativa: no se contó, no es "faltante real".
  expect(estadoFila(fila({ contado: 0, sd: 10, diferencia: -10 }))).toBe('sin_contar')
})

test('totalesCierre resume por estado', () => {
  const filas = [
    fila({ contado: 10, sd: 10, diferencia: 0 }),
    fila({ contado: 12, sd: 10, diferencia: 2 }),
    fila({ contado: 8, sd: 10, diferencia: -2 }),
    fila({ contado: 0, sd: 5, diferencia: -5 }),
  ]
  expect(totalesCierre(filas)).toEqual({
    articulos: 4,
    cuadran: 1,
    sobrantes: 1,
    faltantes: 1,
    sinContar: 1,
  })
})

test('totalesCierre con lista vacía', () => {
  expect(totalesCierre([])).toEqual({
    articulos: 0,
    cuadran: 0,
    sobrantes: 0,
    faltantes: 0,
    sinContar: 0,
  })
})
