// F1: indicador de confianza en la UI del operario. Traduce la confianza (0..1)
// que devuelve el pipeline en una señal visual SUTIL de si el sistema confirmó
// solo o si necesitó una revisión. NUNCA usa ni muestra el SD (conteo ciego).
// Umbrales alineados con los defaults de D1 (auto 0.95 / rapida 0.90).

export type NivelConfianza = 'alta' | 'media' | 'revisar'

export interface Indicador {
  nivel: NivelConfianza
  etiqueta: string
}

export const UMBRAL_ALTA = 0.95
export const UMBRAL_MEDIA = 0.9

export function nivelConfianza(confianza: number): NivelConfianza {
  if (confianza >= UMBRAL_ALTA) return 'alta'
  if (confianza >= UMBRAL_MEDIA) return 'media'
  return 'revisar'
}

/** `viaAclaracion`: el conteo se confirmó DESPUÉS de que el operario respondiera
 * una pregunta (no fue automático). En ese caso manda sobre la confianza. */
export function indicadorConfianza(confianza: number, viaAclaracion = false): Indicador {
  if (viaAclaracion) {
    return { nivel: 'revisar', etiqueta: 'Confirmado tras tu revisión' }
  }
  const nivel = nivelConfianza(confianza)
  const etiqueta =
    nivel === 'alta' ? 'Confirmado al instante' : nivel === 'media' ? 'Confirmado' : 'Confirmado con dudas'
  return { nivel, etiqueta }
}
