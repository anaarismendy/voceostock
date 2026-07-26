import { expect, test } from 'vitest'
import { indicadorConfianza, nivelConfianza } from './confianza'

test('nivelConfianza por bandas (alineado con D1)', () => {
  expect(nivelConfianza(0.98)).toBe('alta')
  expect(nivelConfianza(0.95)).toBe('alta') // frontera inclusiva
  expect(nivelConfianza(0.92)).toBe('media')
  expect(nivelConfianza(0.9)).toBe('media')
  expect(nivelConfianza(0.8)).toBe('revisar')
})

test('auto: etiqueta distingue alta de media', () => {
  expect(indicadorConfianza(0.98).etiqueta).toMatch(/instante/i)
  expect(indicadorConfianza(0.98).nivel).toBe('alta')
  expect(indicadorConfianza(0.92).etiqueta).toBe('Confirmado')
})

test('viaAclaracion manda: se marca como revisado, no como automático', () => {
  const i = indicadorConfianza(0.99, true) // confianza alta pero pasó por pregunta
  expect(i.nivel).toBe('revisar')
  expect(i.etiqueta).toMatch(/revisión/i)
})
