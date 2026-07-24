export interface VozLike {
  lang: string
  name: string
}

/**
 * Las voces "Google español" (Chrome, red) suenan bastante más naturales
 * que las voces locales del sistema operativo — se priorizan por nombre
 * ya que la Web Speech API no expone ninguna señal de calidad.
 */
function puntaje(voz: VozLike): number {
  const nombre = voz.name.toLowerCase()
  let p = 0
  if (nombre.includes('google')) p += 2
  if (voz.lang.toLowerCase() === 'es-co') p += 1
  return p
}

export function elegirVozEspanol<T extends VozLike>(voces: T[]): T | undefined {
  const hispanas = voces.filter((v) => v.lang.toLowerCase().startsWith('es'))
  if (hispanas.length === 0) return undefined
  return [...hispanas].sort((a, b) => puntaje(b) - puntaje(a))[0]
}
