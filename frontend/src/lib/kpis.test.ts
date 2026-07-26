import { expect, test } from 'vitest'
import { capturasPorMinuto, tiempoPromedioCapturaS } from './kpis'
import type { ConteoReciente } from './dashboard'

function feed(tiempos: (number | undefined)[]): ConteoReciente[] {
  return tiempos.map((creado_en, i) => ({
    articulo_id: i,
    articulo_nombre: `A${i}`,
    cantidad: 1,
    unidad: 'Unidad',
    creado_en,
  }))
}

const MIN = 60_000

test('capturasPorMinuto: 5 capturas en 2 min ≈ 2/min', () => {
  // 5 marcas separadas 30 s → span 2 min, 4 intervalos → 2 por minuto.
  const f = feed([0, 30_000, 60_000, 90_000, 120_000])
  expect(capturasPorMinuto(f)).toBe(2)
})

test('capturasPorMinuto: null sin dos marcas', () => {
  expect(capturasPorMinuto(feed([]))).toBeNull()
  expect(capturasPorMinuto(feed([1000]))).toBeNull()
  expect(capturasPorMinuto(feed([undefined, undefined]))).toBeNull()
})

test('tiempoPromedioCapturaS: promedio de intervalos en segundos', () => {
  const f = feed([0, 10_000, 30_000]) // intervalos 10 s y 20 s → promedio 15 s
  expect(tiempoPromedioCapturaS(f)).toBe(15)
})

test('tiempoPromedioCapturaS: null sin dos marcas', () => {
  expect(tiempoPromedioCapturaS(feed([2 * MIN]))).toBeNull()
})

test('ignora capturas sin marca de tiempo', () => {
  const f = feed([0, undefined, 60_000]) // solo 2 válidas, span 1 min → 1/min
  expect(capturasPorMinuto(f)).toBe(1)
})
