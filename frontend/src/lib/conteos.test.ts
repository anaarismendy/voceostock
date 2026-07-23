import { expect, test } from 'vitest'
import { nuevoConteoRequest } from './conteos'

test('nuevoConteoRequest arma el payload del contrato', () => {
  const r = nuevoConteoRequest('noventa cajas', 13)
  expect(r.bodega_id).toBe(13)
  expect(r.fuente).toBe('manual')
  expect(r.payload_texto).toBe('noventa cajas')
  expect(r.payload_audio_b64).toBeNull()
  expect(r.sesion_id).not.toBe(r.operario_id)
})
