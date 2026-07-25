// F2: KPIs del dashboard del líder. Estos dos se derivan del feed reciente en el
// cliente (son REALES, no sintéticos); el resto (dispositivos offline, precisión
// de reconocimiento, % correcciones) los agrega el backend (E-stats). Conteo
// ciego intacto: nada de esto toca el SD.

import type { ConteoReciente } from './dashboard'

function round1(x: number): number {
  return Math.round(x * 10) / 10
}

function tiempos(recientes: ConteoReciente[]): number[] {
  return recientes
    .map((c) => c.creado_en)
    .filter((t): t is number => typeof t === 'number')
    .sort((a, b) => a - b)
}

/** Capturas por minuto estimadas a partir del rango de tiempos del feed.
 * `null` si no hay suficientes marcas de tiempo. */
export function capturasPorMinuto(recientes: ConteoReciente[]): number | null {
  const t = tiempos(recientes)
  if (t.length < 2) return null
  const spanMin = Math.max((t[t.length - 1] - t[0]) / 60000, 1 / 60) // evita /0
  return round1((t.length - 1) / spanMin)
}

/** Segundos promedio entre capturas consecutivas. `null` si no hay dos marcas. */
export function tiempoPromedioCapturaS(recientes: ConteoReciente[]): number | null {
  const t = tiempos(recientes)
  if (t.length < 2) return null
  let suma = 0
  for (let i = 1; i < t.length; i++) suma += t[i] - t[i - 1]
  return round1(suma / (t.length - 1) / 1000)
}
