import { expect, test } from 'vitest'
import { extraerBase64DeDataUrl } from './audioBase64'

test('extrae la parte base64 de un data URL', () => {
  expect(extraerBase64DeDataUrl('data:audio/webm;base64,AAAA')).toBe('AAAA')
})

test('devuelve el string tal cual si no hay coma', () => {
  expect(extraerBase64DeDataUrl('AAAA')).toBe('AAAA')
})
