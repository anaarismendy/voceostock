import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const __dirname = dirname(fileURLToPath(import.meta.url))
const EJEMPLOS_DIR = resolve(__dirname, '../../docs/contrato/ejemplos')

function cargarJson(nombre: string): Record<string, unknown> {
  const raw = readFileSync(resolve(EJEMPLOS_DIR, nombre), 'utf-8')
  return JSON.parse(raw) as Record<string, unknown>
}

// Se recargan del disco en cada llamada (no cache) para poder ajustar el
// texto de las preguntas de demo sin reiniciar el servidor de dev.
export const ejemploConfirmado = () => cargarJson('confirmado.json')
export const ejemploAmbiguedad = () => cargarJson('requiere_confirmacion_ambiguedad.json')
export const ejemploAnomalia = () => cargarJson('requiere_confirmacion_anomalia.json')
export const ejemploNoCatalogado = () => cargarJson('no_catalogado.json')
