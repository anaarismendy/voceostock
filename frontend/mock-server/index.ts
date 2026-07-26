import { createHash, randomUUID } from 'node:crypto'
import { existsSync, readFileSync as leerArchivo } from 'node:fs'
import { resolve as resolverRuta, dirname as dirnameRuta } from 'node:path'
import { fileURLToPath as aRuta } from 'node:url'
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
import {
  crearTokenAmbiguedad,
  crearTokenAnomalia,
  listarConteos,
  registrarConteo,
  reiniciarConteos,
  resolverToken,
  sembrarConteos,
} from './store.ts'
import { calcularCierre } from './cierre.ts'
import { resumenDashboard } from './dashboard.ts'
import { conteosSemilla } from './seed.ts'

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
// F3/E2: config editable en memoria (el backend real la persiste en BD).
const umbralesMock = { auto: 0.95, rapida: 0.9, aclaracion: 0.7 }
const sinonimosMock = [
  { id: 1, sede_id: null, articulo_id: 95026919, texto_sinonimo: 'olla honda', origen: 'aprendido' },
  { id: 2, sede_id: null, articulo_id: 3022, texto_sinonimo: 'pollo entero grande', origen: 'manual' },
]

export function mockApiPlugin(): Plugin {
  return {
    name: 'voceostock-mock-api',
    configureServer(server) {
      // Semilla de demo al arrancar el dev server (C11): dashboard y cierre no
      // arrancan vacíos. Reiniciar el server = demo limpia.
      sembrarConteos(conteosSemilla(cargarCatalogo(), Date.now()))

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
              const articulo_id = Number(encontrado.nr_articulo)
              registrarConteo({ articulo_id, articulo_nombre: encontrado.articulo, cantidad, unidad: encontrado.unidad })
              enviarJson(res, 200, {
                status: 'confirmado',
                conteo: {
                  id: randomUUID(),
                  articulo_id,
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

            if (resultado.status === 'confirmado') {
              const { articulo_id, articulo_nombre, cantidad, unidad } = resultado.conteo
              registrarConteo({ articulo_id, articulo_nombre, cantidad, unidad })
            }
            enviarJson(res, 200, resultado)
            return
          }

          if (req.method === 'GET' && url.pathname === '/api/v1/bodegas') {
            enviarJson(res, 200, cargarBodegas())
            return
          }

          // Voz del agente (p2/tts): sirve la caché commiteada de ElevenLabs.
          // Mismo hash que backend/app/services/tts.py (modelo:voz:texto);
          // si la voz se cambia por .env en el backend, aquí hay miss → 503 →
          // el frontend cae a speechSynthesis (la cascada absorbe todo).
          if (req.method === 'POST' && url.pathname === '/api/v1/tts') {
            const body = await leerCuerpoJson(req)
            const texto = String(body.texto ?? '')
            const hash = createHash('sha1')
              .update(`eleven_flash_v2_5:cgSgspJ2msm6clMCkdW9:${texto}`)
              .digest('hex')
            const ruta = resolverRuta(
              dirnameRuta(aRuta(import.meta.url)), '../../data/tts_cache', `${hash}.mp3`,
            )
            if (!existsSync(ruta)) {
              enviarJson(res, 503, { detail: 'sin audio cacheado para esa frase' })
              return
            }
            res.statusCode = 200
            res.setHeader('Content-Type', 'audio/mpeg')
            res.setHeader('X-TTS-Cache', 'hit')
            res.end(leerArchivo(ruta))
            return
          }

          // I2: rutas que el frontend real necesita (login, sesión, progreso).
          if (req.method === 'POST' && url.pathname === '/api/v1/operarios/login') {
            const body = await leerCuerpoJson(req)
            const pin = String(body.pin ?? '')
            if (!/^\d{4}$/.test(pin)) {
              enviarJson(res, 422, { detail: 'PIN inválido' })
              return
            }
            // El rol lo manda el backend (el líder lo configura). En el mock,
            // 1111 entra como líder; cualquier otro PIN, como operario.
            enviarJson(res, 200, {
              id: randomUUID(),
              nombre: pin === '1111' ? 'Líder Demo' : `Operario ${pin}`,
              rol: pin === '1111' ? 'lider' : 'operario',
            })
            return
          }

          if (req.method === 'POST' && url.pathname === '/api/v1/sesiones') {
            const body = await leerCuerpoJson(req)
            const bodegas = cargarBodegas()
            const bodega = bodegas.find((b) => b.id === Number(body.bodega_id)) ?? bodegas[0]
            enviarJson(res, 200, {
              sesion_id: randomUUID(),
              bodega: { id: bodega.id, nombre: bodega.nombre },
              total_articulos: catalogo.length,
            })
            return
          }

          const progresoMatch = url.pathname.match(/^\/api\/v1\/sesiones\/([^/]+)\/progreso$/)
          if (req.method === 'GET' && progresoMatch) {
            enviarJson(res, 200, {
              contados: 3,
              total: catalogo.length,
              por_familia: [{ familia: 'General', contados: 3, total: catalogo.length }],
              colisiones: 0,
            })
            return
          }

          // Reporte de cierre del líder (C9). Único endpoint que expone el SD.
          // `ids` = artículos esperados (el checklist guiado), para que los no
          // contados salgan como faltantes.
          if (req.method === 'GET' && url.pathname === '/api/v1/cierre') {
            const idsParam = url.searchParams.get('ids')
            const esperados = idsParam
              ? idsParam.split(',').map(Number).filter((n) => !Number.isNaN(n))
              : []
            enviarJson(res, 200, calcularCierre(catalogo, listarConteos(), esperados))
            return
          }

          // Dashboard en vivo (C10): actividad de captura, sin SD.
          if (req.method === 'GET' && url.pathname === '/api/v1/dashboard') {
            enviarJson(res, 200, resumenDashboard(listarConteos()))
            return
          }

          // Config del líder (E2/F3): umbrales editables + sinónimos.
          if (url.pathname === '/api/v1/config/umbrales') {
            if (req.method === 'GET') {
              enviarJson(res, 200, umbralesMock)
              return
            }
            if (req.method === 'PUT') {
              const body = await leerCuerpoJson(req)
              for (const k of ['auto', 'rapida', 'aclaracion'] as const) {
                if (typeof body[k] === 'number') umbralesMock[k] = body[k] as number
              }
              enviarJson(res, 200, umbralesMock)
              return
            }
          }
          if (req.method === 'GET' && url.pathname === '/api/v1/config/sinonimos') {
            enviarJson(res, 200, sinonimosMock)
            return
          }

          // Control de demo (C11): re-correr la demo sin reiniciar el server.
          if (req.method === 'POST' && url.pathname === '/api/v1/demo/reset') {
            reiniciarConteos()
            enviarJson(res, 200, { ok: true, total: 0 })
            return
          }
          if (req.method === 'POST' && url.pathname === '/api/v1/demo/seed') {
            reiniciarConteos()
            const semilla = conteosSemilla(catalogo, Date.now())
            sembrarConteos(semilla)
            enviarJson(res, 200, { ok: true, total: semilla.length })
            return
          }

          if (req.method === 'GET' && url.pathname === '/api/v1/articulos') {
            // Conteo ciego: nunca se expone `sd` en este endpoint. F4/E5: sí el
            // nivel de riesgo (no revela el histórico exacto). Demo: un par de
            // artículos del checklist quedan en riesgo alto para disparar el aviso.
            const RIESGO_ALTO_DEMO = new Set(['95026919', '3022']) // CAZUELA 16 ONZ, POLLO ENTERO
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
                riesgo: RIESGO_ALTO_DEMO.has(a.nr_articulo) ? 'alto' : 'bajo',
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
