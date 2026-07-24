import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const __dirname = dirname(fileURLToPath(import.meta.url))
const CATALOGO_PATH = resolve(__dirname, '../../data/fixtures/catalogo.csv')

export interface ArticuloCatalogo {
  bodega: string
  nr_articulo: string
  articulo: string
  unidad: string
  sd: number
}

/**
 * Parser CSV mínimo con soporte de campos entre comillas (nombres de
 * artículo con comas o comillas dobles escapadas, ej. `CUCHILLO 10""`):
 * el split(',') ingenuo rompe con el Excel real, ver CLAUDE.md.
 */
function parseLineaCsv(linea: string): string[] {
  const columnas: string[] = []
  let actual = ''
  let entreComillas = false

  for (let i = 0; i < linea.length; i++) {
    const char = linea[i]

    if (entreComillas) {
      if (char === '"') {
        if (linea[i + 1] === '"') {
          actual += '"'
          i++
        } else {
          entreComillas = false
        }
      } else {
        actual += char
      }
      continue
    }

    if (char === '"') {
      entreComillas = true
    } else if (char === ',') {
      columnas.push(actual)
      actual = ''
    } else {
      actual += char
    }
  }
  columnas.push(actual)
  return columnas
}

/**
 * Regla de conteo ciego: `sd` se carga porque el motor de anomalías (P1) lo
 * necesita, pero ningún endpoint orientado al operario debe reenviarlo.
 */
export function cargarCatalogo(): ArticuloCatalogo[] {
  const raw = readFileSync(CATALOGO_PATH, 'utf-8')
  const [, ...lineas] = raw.trim().split(/\r?\n/)

  return lineas
    .filter((linea) => linea.trim().length > 0)
    .map((linea) => {
      const [bodega, nr_articulo, articulo, unidad, sd] = parseLineaCsv(linea)
      return {
        bodega: bodega.trim(),
        nr_articulo: nr_articulo.trim(),
        articulo: articulo.trim(),
        unidad: unidad.trim(),
        sd: Number(sd),
      }
    })
}

export function buscarPorNombre(
  catalogo: ArticuloCatalogo[],
  subcadena: string,
): ArticuloCatalogo | undefined {
  const objetivo = subcadena.toLowerCase()
  return catalogo.find((a) => a.articulo.toLowerCase().includes(objetivo))
}

export function buscarPorId(
  catalogo: ArticuloCatalogo[],
  nrArticulo: string,
): ArticuloCatalogo | undefined {
  return catalogo.find((a) => a.nr_articulo === nrArticulo)
}

/**
 * El teclado manual (C5) manda como texto "<cantidad> <nombre exacto>"
 * (el operario lo eligió de la lista de /api/v1/articulos), así que el
 * match debe ser por substring dentro del texto, no al revés. Se toma el
 * nombre más largo que calce para no confundir "ACEITE" con "ACEITE DE
 * OLIVA" cuando ambos son substring del texto dictado.
 */
export function buscarMejorMatch(
  catalogo: ArticuloCatalogo[],
  texto: string,
): ArticuloCatalogo | undefined {
  const normalizado = texto.toLowerCase()
  let mejor: ArticuloCatalogo | undefined
  for (const a of catalogo) {
    const nombre = a.articulo.toLowerCase()
    if (nombre.length >= 4 && normalizado.includes(nombre)) {
      if (!mejor || nombre.length > mejor.articulo.length) mejor = a
    }
  }
  return mejor
}
