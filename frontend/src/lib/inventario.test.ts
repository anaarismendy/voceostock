import { describe, expect, it } from 'vitest'
import type { ArticuloResumen } from './articulos'
import { filtrarArticulos } from './inventario'

const CATALOGO: ArticuloResumen[] = [
  { articulo_id: 1, articulo_nombre: 'ACEITE DE OLIVA', unidad: 'Liter' },
  { articulo_id: 2, articulo_nombre: 'CAZUELA 16 ONZ', unidad: 'Unidad' },
  { articulo_id: 3, articulo_nombre: 'PORCIÓN DE PAPA', unidad: 'Portion' },
]

describe('filtrarArticulos', () => {
  it('sin búsqueda ni filtro devuelve todo', () => {
    expect(filtrarArticulos(CATALOGO, '', null)).toHaveLength(3)
  })

  it('busca sin importar mayúsculas ni tildes', () => {
    expect(filtrarArticulos(CATALOGO, 'porcion', null).map((a) => a.articulo_id)).toEqual([3])
    expect(filtrarArticulos(CATALOGO, 'OLIVA', null).map((a) => a.articulo_id)).toEqual([1])
  })

  it('deja fuera los ya contados cuando se filtra por pendientes', () => {
    const contados = new Set([1, 3])
    expect(filtrarArticulos(CATALOGO, '', contados).map((a) => a.articulo_id)).toEqual([2])
  })

  it('combina búsqueda y pendientes', () => {
    expect(filtrarArticulos(CATALOGO, 'a', new Set([1]))).toHaveLength(2)
  })
})
