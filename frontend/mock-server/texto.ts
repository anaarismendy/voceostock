const NUMEROS_SIMPLES: Record<string, number> = {
  cero: 0,
  un: 1,
  uno: 1,
  una: 1,
  dos: 2,
  tres: 3,
  cuatro: 4,
  cinco: 5,
  seis: 6,
  siete: 7,
  ocho: 8,
  nueve: 9,
  diez: 10,
  once: 11,
  doce: 12,
  trece: 13,
  catorce: 14,
  quince: 15,
  dieciseis: 16,
  diecisiete: 17,
  dieciocho: 18,
  diecinueve: 19,
  veinte: 20,
  treinta: 30,
  cuarenta: 40,
  cincuenta: 50,
  sesenta: 60,
  setenta: 70,
  ochenta: 80,
  noventa: 90,
  cien: 100,
}

/**
 * Extractor de cantidad deliberadamente simple para el mock: suma palabras
 * numéricas conocidas ("treinta y tres" = 30 + 3). No es el parser NLU real
 * (eso es la tarea A1 de P1) — solo alcanza para que el mock responda algo
 * plausible al resolver ambigüedades/anomalías en la demo.
 */
export function extraerCantidad(texto: string, porDefecto = 1): number {
  const normalizado = texto
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')

  const numerico = normalizado.match(/\d+([.,]\d+)?/)
  if (numerico) {
    return Number(numerico[0].replace(',', '.'))
  }

  let total = 0
  let encontrada = false
  for (const palabra of normalizado.split(/\s+/)) {
    const limpio = palabra.replace(/[^a-z]/g, '')
    if (limpio in NUMEROS_SIMPLES) {
      total += NUMEROS_SIMPLES[limpio]
      encontrada = true
    }
  }

  return encontrada ? total : porDefecto
}
