import type { ArticuloResumen } from './articulos'

/**
 * Checklist corto que recorre el MODO GUIADO (C8).
 *
 * Placeholder de demo a propósito: son nombres REALES de data/fixtures/
 * catalogo.csv (con su nr_articulo y unidad), para que al armar el texto
 * "<cantidad> <nombre>" el mock los reconozca por match exacto y confirme.
 * Cuando C11 traiga la seed por bodega (o el backend real un endpoint de
 * checklist por bodega), esta constante se reemplaza por esa lista.
 *
 * Se mantiene corto (8 items) porque el criterio de C8 es que el operario
 * complete un recorrido guiado en la demo sin fatiga, no cubrir las ~796
 * referencias del catálogo.
 */
export const CHECKLIST_DEMO: ArticuloResumen[] = [
  { articulo_id: 7293, articulo_nombre: 'ACEITE DE OLIVA', unidad: 'Liter' },
  { articulo_id: 3022, articulo_nombre: 'POLLO ENTERO', unidad: 'Kilogram' },
  { articulo_id: 95026919, articulo_nombre: 'CAZUELA 16 ONZ', unidad: 'Unidad' },
  { articulo_id: 2027, articulo_nombre: 'COSTILLA DE RES', unidad: 'Kilogram' },
  { articulo_id: 5004, articulo_nombre: 'AGUACATE', unidad: 'Kilogram' },
  { articulo_id: 97503241, articulo_nombre: 'ABRELATAS MARIPOSA', unidad: 'Unidad' },
  { articulo_id: 4003, articulo_nombre: 'CHORIZO', unidad: 'Kilogram' },
  { articulo_id: 7292, articulo_nombre: 'ACEITE DE AJONJOLI', unidad: 'Liter' },
]
