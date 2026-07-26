// F4: aviso preventivo por voz cuando el operario cuenta un artículo de riesgo
// alto (nivel que viene del catálogo, E5). Suena UNA sola vez por sesión por
// artículo. NUNCA menciona el SD ni el valor histórico exacto: solo la
// advertencia genérica (conteo ciego intacto).

export type NivelRiesgo = 'alto' | 'medio' | 'bajo'

export const AVISO_RIESGO_TEXTO = 'Cuidado con este producto, cuenta una vez más'

/** True si hay que avisar: el artículo es de riesgo alto y NO se avisó ya en
 * esta sesión. `yaAvisados` acumula los ids ya avisados. */
export function debeAvisar(
  articuloId: number,
  riesgo: NivelRiesgo | undefined,
  yaAvisados: ReadonlySet<number>,
): boolean {
  return riesgo === 'alto' && !yaAvisados.has(articuloId)
}
