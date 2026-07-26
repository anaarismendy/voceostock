import { describe, expect, it } from 'vitest'
import { etiqueta, rangoFechas, type Inventario } from './inventarios'

const base: Inventario = {
  id: 1,
  bodega_id: 3,
  numero: 2,
  estado: 'abierto',
  corte_fecha: null,
  abierto_en: '2026-07-25T14:30:00Z',
  cerrado_en: null,
  articulos_contados: 0,
  operarios: 0,
}

describe('rangoFechas', () => {
  it('un ciclo abierto se muestra en curso', () => {
    expect(rangoFechas(base)).toMatch(/en curso$/)
  })

  it('un ciclo de varios días muestra el rango', () => {
    const r = rangoFechas({ ...base, estado: 'cerrado', cerrado_en: '2026-07-27T10:00:00Z' })
    expect(r).toContain('–')
    expect(r).not.toContain('en curso')
  })

  it('abierto y cerrado el mismo día no repite la fecha', () => {
    const r = rangoFechas({ ...base, estado: 'cerrado', cerrado_en: '2026-07-25T20:00:00Z' })
    expect(r).not.toContain('–')
  })
})

it('etiqueta usa el número por bodega', () => {
  expect(etiqueta(base)).toBe('Inventario #2')
})
