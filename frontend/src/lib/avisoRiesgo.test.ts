import { expect, test } from 'vitest'
import { debeAvisar } from './avisoRiesgo'

test('DoD: riesgo alto avisa la primera vez y no la segunda en la misma sesión', () => {
  const avisados = new Set<number>()
  // Primera captura del artículo 500 (riesgo alto) → avisa.
  expect(debeAvisar(500, 'alto', avisados)).toBe(true)
  avisados.add(500)
  // Segunda captura del MISMO artículo en la sesión → ya no avisa.
  expect(debeAvisar(500, 'alto', avisados)).toBe(false)
})

test('no avisa para riesgo medio/bajo/indefinido', () => {
  const avisados = new Set<number>()
  expect(debeAvisar(1, 'medio', avisados)).toBe(false)
  expect(debeAvisar(1, 'bajo', avisados)).toBe(false)
  expect(debeAvisar(1, undefined, avisados)).toBe(false)
})

test('cada artículo de riesgo alto avisa una vez, independiente de los demás', () => {
  const avisados = new Set<number>([500])
  expect(debeAvisar(500, 'alto', avisados)).toBe(false) // ya avisado
  expect(debeAvisar(600, 'alto', avisados)).toBe(true) // otro artículo, primera vez
})
