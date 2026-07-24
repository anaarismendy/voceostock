import { expect, test } from 'vitest'
import { tiempoRelativo } from './dashboard'

const AHORA = 1_000_000_000

test('tiempoRelativo: recién / segundos / minutos / horas', () => {
  expect(tiempoRelativo(AHORA, AHORA)).toBe('ahora')
  expect(tiempoRelativo(AHORA - 3_000, AHORA)).toBe('ahora') // < 5 s
  expect(tiempoRelativo(AHORA - 12_000, AHORA)).toBe('hace 12 s')
  expect(tiempoRelativo(AHORA - 90_000, AHORA)).toBe('hace 1 min')
  expect(tiempoRelativo(AHORA - 2 * 3_600_000, AHORA)).toBe('hace 2 h')
})

test('tiempoRelativo sin timestamp devuelve vacío', () => {
  expect(tiempoRelativo(undefined, AHORA)).toBe('')
})

test('tiempoRelativo nunca es negativo (reloj adelantado)', () => {
  expect(tiempoRelativo(AHORA + 5_000, AHORA)).toBe('ahora')
})
