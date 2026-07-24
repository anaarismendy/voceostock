import { expect, test } from 'vitest'
import { interpretarRespuestaVoz } from './resolverVoz'

test('interpreta sí', () => {
  expect(interpretarRespuestaVoz('sí', null)).toBe('si')
  expect(interpretarRespuestaVoz('si claro', null)).toBe('si')
})

test('interpreta no', () => {
  expect(interpretarRespuestaVoz('no', null)).toBe('no')
})

test('interpreta una cantidad dicha en dígitos', () => {
  expect(interpretarRespuestaVoz('85', null)).toBe('cantidad:85')
})

test('no interpreta cantidades en palabras (fuera de alcance de C4)', () => {
  expect(interpretarRespuestaVoz('ochenta y cinco', null)).toBe(null)
})

test('interpreta un candidato por nombre', () => {
  const candidatos = [
    { articulo_id: 1, articulo_nombre: 'CAZUELA 16 ONZ' },
    { articulo_id: 2, articulo_nombre: 'CALDERO RECORT TAPA 50X60 CM' },
  ]
  expect(interpretarRespuestaVoz('la cazuela 16 onz', candidatos)).toBe('articulo_id:1')
  expect(interpretarRespuestaVoz('ninguna de esas', candidatos)).toBe(null)
})
