import { expect, test } from 'vitest'
import { elegirVozEspanol } from './vozEspanol'

test('prefiere una voz de Google en español sobre otras', () => {
  const voces = [
    { lang: 'es-ES', name: 'Microsoft Sabina' },
    { lang: 'es-US', name: 'Google español' },
    { lang: 'en-US', name: 'Google US English' },
  ]
  expect(elegirVozEspanol(voces)?.name).toBe('Google español')
})

test('descarta voces que no son en español', () => {
  const voces = [{ lang: 'en-US', name: 'Google US English' }]
  expect(elegirVozEspanol(voces)).toBeUndefined()
})

test('sin voces de Google, prioriza es-CO sobre otros dialectos', () => {
  const voces = [
    { lang: 'es-ES', name: 'Microsoft Sabina' },
    { lang: 'es-CO', name: 'Microsoft Something' },
  ]
  expect(elegirVozEspanol(voces)?.lang).toBe('es-CO')
})

test('devuelve undefined si no hay voces', () => {
  expect(elegirVozEspanol([])).toBeUndefined()
})
