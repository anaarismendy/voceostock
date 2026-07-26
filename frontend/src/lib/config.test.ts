import { expect, test } from 'vitest'
import { umbralesValidos } from './config'

test('umbralesValidos acepta el orden correcto', () => {
  expect(umbralesValidos({ auto: 0.95, rapida: 0.9, aclaracion: 0.7 })).toBe(true)
  expect(umbralesValidos({ auto: 0.9, rapida: 0.9, aclaracion: 0.9 })).toBe(true) // iguales
})

test('umbralesValidos rechaza orden invertido o fuera de rango', () => {
  expect(umbralesValidos({ auto: 0.5, rapida: 0.9, aclaracion: 0.4 })).toBe(false) // rapida > auto
  expect(umbralesValidos({ auto: 0.9, rapida: 0.5, aclaracion: 0.7 })).toBe(false) // aclaracion > rapida
  expect(umbralesValidos({ auto: 1.5, rapida: 0.9, aclaracion: 0.7 })).toBe(false) // fuera de [0,1]
})
