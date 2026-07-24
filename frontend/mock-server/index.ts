import { randomUUID } from 'node:crypto'
import type { IncomingMessage, ServerResponse } from 'node:http'
import type { Plugin } from 'vite'
import { cargarCatalogo, buscarPorNombre, buscarMejorMatch } from './catalogo.ts'
import { cargarBodegas } from './bodegas.ts'
import {
  ejemploAmbiguedad,
  ejemploAnomalia,
  ejemploConfirmado,
  ejemploNoCatalogado,
} from './examples.ts'
import { extraerCantidad } from './texto.ts'
import { crearTokenAmbiguedad, crearTokenAnomalia, resolverToken } from './store.ts'

function leerCuerpoJson(req: IncomingMessage): Promise<Record<string, unknown>> {
  return new Promise((resolvePromise, reject) => {
    let data = ''
    req.on('data', (chunk) => (data += chunk))
    req.on('end', () => {
      try {
        resolvePromise(data ? JSON.parse(data) : {})
      } catch (error) {
        reject(error)
      }
    })
    req.on('error', reject)
  })
}

function enviarJson(res: ServerResponse, status: number, body: unknown) {
  res.statusCode = status
  res.setHeader('Content-Type', 'application/json; charset=utf-8')
  res.end(JSON.stringify(body))
}

/**
 * Vite plugin que sirve el contrato de la API sobre el propio dev server
 * cuando VITE_API=mock. Ningún componente de React sabe que esto existe:
 * hablan con rutas relativas /api/v1/... igual que hablarían con el backend
 * real (ver src/lib/conteos.ts).
 */
export function mockApiPlugin(): Plugin {
  return {
    name: 'voceostock-mock-api',
    configureServer(server) {
      server.middlewares.use(async (req, res, next) => {
        if (req.url === '/health') {
          enviarJson(res, 200, { status: 'ok' })
          return
        }

        if (!req.url?.startsWith('/api/v1/')) {
          next()
          return
        }

        try {
          const url = new URL(req.url, 'http://localhost')
          const catalogo = cargarCatalogo()

          if (req.method === 'POST' && url.pathname === '/api/v1/conteos') {
            const body = await leerCuerpoJson(req)
            const texto = String(body.payload_texto ?? '').toLowerCase()
            const fuente = String(body.fuente ?? 'manual')

            // Las palabras clave de demo (noventa/cazuela/xyz) simulan texto
            // dictado sin precisión. El teclado manual (C5) manda el nombre
            // EXACTO que el operario eligió de /api/v1/articulos, así que
            // debe ir directo al match real y no disparar esos casos — de lo
            // contrario elegir "CAZUELA 16 ONZ" de la lista dispararía la
            // ambigüedad de demo en vez de confirmar lo que el operario tocó.
            if (fuente !== 'manual') {
              if (texto.includes('noventa')) {
                const cazuela = buscarPorNombre(catalogo, 'cazuela 16 onz')!
                const cantidad = extraerCantidad(texto, 90)
                const token_pendiente = crearTokenAnomalia(cazuela, cantidad, fuente)
                enviarJson(res, 200, { ...ejemploAnomalia(), token_pendiente })
                return
              }

              if (texto.includes('cazuela')) {
                const cantidad = extraerCantidad(texto, 1)
                const token_pendiente = crearTokenAmbiguedad(cantidad, 'Unidad', fuente)
                enviarJson(res, 200, { ...ejemploAmbiguedad(), token_pendiente })
                return
              }

              if (texto.includes('xyz')) {
                enviarJson(res, 200, ejemploNoCatalogado())
                return
              }
            }

            // Resto de textos: intenta un match real contra el catálogo (así
            // el teclado manual de C5, que manda "<cantidad> <nombre exacto>",
            // confirma el artículo que el operario realmente eligió).
            const encontrado = buscarMejorMatch(catalogo, texto)
            if (encontrado) {
              const cantidad = extraerCantidad(texto, 1)
              enviarJson(res, 200, {
                status: 'confirmado',
                conteo: {
                  id: randomUUID(),
                  articulo_id: Number(encontrado.nr_articulo),
                  articulo_nombre: encontrado.articulo,
                  cantidad,
                  unidad: encontrado.unidad,
                  confianza: 0.95,
                  fuente,
                  evidencia_url: null,
                },
              })
              return
            }

            enviarJson(res, 200, ejemploConfirmado())
            return
          }

          const resolverMatch = url.pathname.match(/^\/api\/v1\/conteos\/([^/]+)\/resolver$/)
          if (req.method === 'POST' && resolverMatch) {
            const token = resolverMatch[1]
            const body = await leerCuerpoJson(req)
            const resultado = resolverToken(token, String(body.respuesta ?? ''), catalogo)

            if (!resultado) {
              enviarJson(res, 404, { status: 'error', mensaje: 'Token no encontrado o ya resuelto' })
              return
            }

            enviarJson(res, 200, resultado)
            return
          }

          if (req.method === 'GET' && url.pathname === '/api/v1/bodegas') {
            enviarJson(res, 200, cargarBodegas())
            return
          }

          if (req.method === 'GET' && url.pathname === '/api/v1/articulos') {
            // Conteo ciego: nunca se expone `sd` en este endpoint.
            const vistos = new Set<string>()
            const articulos = catalogo
              .filter((a) => {
                if (!a.nr_articulo || vistos.has(a.nr_articulo)) return false
                vistos.add(a.nr_articulo)
                return true
              })
              .map((a) => ({
                articulo_id: Number(a.nr_articulo),
                articulo_nombre: a.articulo,
                unidad: a.unidad,
              }))
            enviarJson(res, 200, articulos)
            return
          }

          next()
        } catch (error) {
          enviarJson(res, 500, { status: 'error', mensaje: String(error) })
        }
      })
    },
  }
}
