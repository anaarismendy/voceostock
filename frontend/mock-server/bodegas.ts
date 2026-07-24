import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const __dirname = dirname(fileURLToPath(import.meta.url))
const BODEGAS_PATH = resolve(__dirname, '../../data/fixtures/bodegas.csv')

export interface BodegaFixture {
  id: number
  nombre: string
}

/**
 * No hay endpoint real de listado de bodegas todavía (B4 solo expone
 * POST /sesiones, que ya recibe un bodega_id). Se sirve el fixture crudo
 * tal cual —con sus duplicados conocidos (CLAUDE.md)— porque fusionarlos
 * es trabajo de ingesta de P2, no del mock de C1.
 */
export function cargarBodegas(): BodegaFixture[] {
  const raw = readFileSync(BODEGAS_PATH, 'utf-8')
  const [, ...lineas] = raw.trim().split(/\r?\n/)

  return lineas
    .filter((linea) => linea.trim().length > 0)
    .map((linea) => {
      const [id, nombre] = linea.split(',')
      return { id: Number(id), nombre: nombre.trim() }
    })
}
