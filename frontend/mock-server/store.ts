import { randomUUID } from 'node:crypto'
import type { ArticuloCatalogo } from './catalogo.ts'
import { buscarPorId } from './catalogo.ts'

interface PendienteAmbiguedad {
  motivo: 'ambiguedad'
  cantidad: number
  unidad: string
  fuente: string
}

interface PendienteAnomalia {
  motivo: 'anomalia' | 'baja_confianza'
  articulo_id: number
  articulo_nombre: string
  cantidad: number
  unidad: string
  fuente: string
}

type Pendiente = PendienteAmbiguedad | PendienteAnomalia

// Estado en memoria del proceso de dev — se pierde al reiniciar, que es
// exactamente lo que se quiere de un mock (nada que migrar a BD real).
const pendientes = new Map<string, Pendiente>()

function crearToken(pendiente: Pendiente): string {
  const token = randomUUID()
  pendientes.set(token, pendiente)
  return token
}

export function crearTokenAmbiguedad(cantidad: number, unidad: string, fuente: string): string {
  return crearToken({ motivo: 'ambiguedad', cantidad, unidad, fuente })
}

export function crearTokenAnomalia(articulo: ArticuloCatalogo, cantidad: number, fuente: string): string {
  return crearToken({
    motivo: 'anomalia',
    articulo_id: Number(articulo.nr_articulo),
    articulo_nombre: articulo.articulo,
    cantidad,
    unidad: articulo.unidad,
    fuente,
  })
}

interface Conteo {
  id: string
  articulo_id: number
  articulo_nombre: string
  cantidad: number
  unidad: string
  confianza: number
  fuente: string
  evidencia_url: null
}

export type ResultadoResolver =
  | { status: 'confirmado'; conteo: Conteo }
  | {
      status: 'requiere_confirmacion'
      token_pendiente: string
      motivo: 'anomalia' | 'baja_confianza'
      pregunta: string
      candidatos: null
    }
  | { status: 'no_catalogado'; texto_capturado: string; cantidad: number; unidad: string }
  | { status: 'descartado' }

function confirmar(articulo_id: number, articulo_nombre: string, cantidad: number, unidad: string, fuente: string): ResultadoResolver {
  return {
    status: 'confirmado',
    conteo: {
      id: randomUUID(),
      articulo_id,
      articulo_nombre,
      cantidad,
      unidad,
      confianza: 0.95,
      fuente,
      evidencia_url: null,
    },
  }
}

/**
 * `catalogo` se pasa por parámetro (en vez de importar cargarCatalogo aquí)
 * para no releer el CSV en cada resolución de ambigüedad.
 *
 * El protocolo de `respuesta` es el del contrato: "si" | "no" |
 * "articulo_id:<int>" | "cantidad:<float>". Qué produce exactamente cada
 * combinación motivo+respuesta no está definido en el contrato (es decisión
 * de negocio de P1/P2) — este mock elige el comportamiento más plausible
 * para no bloquear el desarrollo de las pantallas C4 en adelante.
 */
export function resolverToken(
  token: string,
  respuesta: string,
  catalogo: ArticuloCatalogo[],
): ResultadoResolver | null {
  const pendiente = pendientes.get(token)
  if (!pendiente) return null
  pendientes.delete(token)

  const valor = respuesta.trim()

  if (pendiente.motivo === 'ambiguedad') {
    const match = valor.match(/^articulo_id:(\d+)$/)
    if (match) {
      const elegido = buscarPorId(catalogo, match[1])
      if (!elegido) {
        return { status: 'no_catalogado', texto_capturado: match[1], cantidad: pendiente.cantidad, unidad: pendiente.unidad }
      }
      return confirmar(Number(elegido.nr_articulo), elegido.articulo, pendiente.cantidad, elegido.unidad, pendiente.fuente)
    }
    return { status: 'no_catalogado', texto_capturado: valor, cantidad: pendiente.cantidad, unidad: pendiente.unidad }
  }

  // motivo 'anomalia' | 'baja_confianza'
  if (valor === 'si') {
    return confirmar(pendiente.articulo_id, pendiente.articulo_nombre, pendiente.cantidad, pendiente.unidad, pendiente.fuente)
  }

  const cantidadMatch = valor.match(/^cantidad:([\d.,]+)$/)
  if (cantidadMatch) {
    const cantidad = Number(cantidadMatch[1].replace(',', '.'))
    return confirmar(pendiente.articulo_id, pendiente.articulo_nombre, cantidad, pendiente.unidad, pendiente.fuente)
  }

  if (valor === 'no') {
    // I2: igual que el backend real — "no" descarta sin persistir (cuarto
    // estado del contrato, exclusivo de /resolver).
    return { status: 'descartado' }
  }

  return confirmar(pendiente.articulo_id, pendiente.articulo_nombre, pendiente.cantidad, pendiente.unidad, pendiente.fuente)
}
