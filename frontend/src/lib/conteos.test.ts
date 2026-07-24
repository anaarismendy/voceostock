import { expect, test } from 'vitest'
import { mensajeConfirmacion, nuevoConteoRequest } from './conteos'

test('nuevoConteoRequest arma el payload del contrato', () => {
  const r = nuevoConteoRequest({ sesionId: 'ses-1', texto: 'noventa cajas', bodegaId: 13, operarioId: 'op-1' })
  expect(r.bodega_id).toBe(13)
  expect(r.operario_id).toBe('op-1')
  expect(r.fuente).toBe('manual')
  expect(r.payload_texto).toBe('noventa cajas')
  expect(r.payload_audio_b64).toBeNull()
  expect(r.sesion_id).toBe('ses-1')
})

test('nuevoConteoRequest respeta la fuente explícita', () => {
  const r = nuevoConteoRequest({ sesionId: 'ses-1', texto: 'aceite', bodegaId: 1, operarioId: 'op-1', fuente: 'voz-tablet' })
  expect(r.fuente).toBe('voz-tablet')
})

test('nuevoConteoRequest arma el payload de audio (ruta B, C6)', () => {
  const r = nuevoConteoRequest({ sesionId: 'ses-1', audioBase64: 'QUJD', bodegaId: 1, operarioId: 'op-1', fuente: 'voz-tablet' })
  expect(r.payload_texto).toBeNull()
  expect(r.payload_audio_b64).toBe('QUJD')
})

test('mensajeConfirmacion lee cantidad, unidad y artículo', () => {
  const texto = mensajeConfirmacion({
    id: 'x',
    articulo_id: 7290,
    articulo_nombre: 'ACEITE DE OLIVA',
    cantidad: 33.5,
    unidad: 'Liter',
    confianza: 0.95,
    fuente: 'voz-tablet',
    evidencia_url: null,
  })
  expect(texto).toBe('33.5 Liter de ACEITE DE OLIVA')
})
