import { expect, test, vi } from 'vitest'
import { calcularEsperaMs, conReintento, esErrorDeRed } from './reintento'

test('esErrorDeRed distingue TypeError (red) de otros errores', () => {
  expect(esErrorDeRed(new TypeError('Failed to fetch'))).toBe(true)
  expect(esErrorDeRed(new Error('Error 404 al enviar conteo'))).toBe(false)
})

test('calcularEsperaMs crece exponencial y tiene techo', () => {
  expect(calcularEsperaMs(1)).toBe(1000)
  expect(calcularEsperaMs(2)).toBe(2000)
  expect(calcularEsperaMs(3)).toBe(4000)
  expect(calcularEsperaMs(10)).toBe(16000)
})

test('conReintento reintenta errores de red hasta lograrlo', async () => {
  vi.useFakeTimers()
  let llamadas = 0
  const fn = vi.fn(async () => {
    llamadas++
    if (llamadas < 3) throw new TypeError('Failed to fetch')
    return 'ok'
  })
  const onReintento = vi.fn()

  const promesa = conReintento(fn, { onReintento })
  await vi.runAllTimersAsync()
  const resultado = await promesa

  expect(resultado).toBe('ok')
  expect(llamadas).toBe(3)
  expect(onReintento).toHaveBeenCalledTimes(2)
  vi.useRealTimers()
})

test('conReintento no reintenta errores que no son de red', async () => {
  const fn = vi.fn(async () => {
    throw new Error('400 bad request')
  })
  await expect(conReintento(fn)).rejects.toThrow('400 bad request')
  expect(fn).toHaveBeenCalledTimes(1)
})

test('conReintento se rinde tras agotar los intentos', async () => {
  vi.useFakeTimers()
  const fn = vi.fn(async () => {
    throw new TypeError('Failed to fetch')
  })
  const promesa = conReintento(fn, { intentos: 3 })
  const expectacion = expect(promesa).rejects.toThrow('Failed to fetch')
  await vi.runAllTimersAsync()
  await expectacion
  expect(fn).toHaveBeenCalledTimes(3)
  vi.useRealTimers()
})
