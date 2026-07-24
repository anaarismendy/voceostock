/**
 * fetch() rechaza con TypeError cuando la red no responde (wifi caído,
 * host inalcanzable) — a diferencia de un 4xx/5xx del servidor, que
 * postConteo/resolverConteo ya convierten en un Error normal. Solo los
 * primeros vale la pena reintentar.
 */
export function esErrorDeRed(error: unknown): boolean {
  return error instanceof TypeError
}

export function calcularEsperaMs(intento: number): number {
  return Math.min(1000 * 2 ** (intento - 1), 16000)
}

interface OpcionesReintento {
  intentos?: number
  onReintento?: (intento: number, esperaMs: number) => void
}

/**
 * Reintento simple con backoff exponencial (C7). No es cola persistente en
 * IndexedDB a propósito — plan_por_persona.md marca eso como "solo si sobra
 * tiempo"; esto ya cubre el riesgo real de la demo (wifi del auditorio
 * cayendo 10-15 s en medio de un conteo).
 */
export async function conReintento<T>(fn: () => Promise<T>, opciones: OpcionesReintento = {}): Promise<T> {
  const intentos = opciones.intentos ?? 5

  for (let intento = 1; intento <= intentos; intento++) {
    try {
      return await fn()
    } catch (error) {
      if (!esErrorDeRed(error) || intento === intentos) throw error
      const esperaMs = calcularEsperaMs(intento)
      opciones.onReintento?.(intento, esperaMs)
      await new Promise((resolve) => setTimeout(resolve, esperaMs))
    }
  }

  throw new Error('conReintento: agotó los intentos')
}
