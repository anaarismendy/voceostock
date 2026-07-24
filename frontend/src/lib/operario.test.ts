import { expect, test } from 'vitest'
import { esPinValido } from './operario'

test('esPinValido acepta exactamente 4 digitos', () => {
  expect(esPinValido('1234')).toBe(true)
  expect(esPinValido('0000')).toBe(true)
  expect(esPinValido('123')).toBe(false)
  expect(esPinValido('12345')).toBe(false)
  expect(esPinValido('12a4')).toBe(false)
  expect(esPinValido('')).toBe(false)
})
