import { expect, test } from 'vitest'
import { esPinValido, nuevoOperario } from './operario'

test('esPinValido acepta exactamente 4 dígitos', () => {
  expect(esPinValido('1234')).toBe(true)
  expect(esPinValido('0000')).toBe(true)
  expect(esPinValido('123')).toBe(false)
  expect(esPinValido('12345')).toBe(false)
  expect(esPinValido('12a4')).toBe(false)
  expect(esPinValido('')).toBe(false)
})

test('nuevoOperario arma un operario con id distinto por sesión', () => {
  const a = nuevoOperario('1234')
  const b = nuevoOperario('1234')
  expect(a.pin).toBe('1234')
  expect(a.id).not.toBe(b.id)
})

test('nuevoOperario usa rol operario por defecto y respeta el rol dado', () => {
  expect(nuevoOperario('1234').rol).toBe('operario')
  expect(nuevoOperario('1234', 'lider').rol).toBe('lider')
})
