import type { Candidato } from './conteos'

function sinTildes(texto: string): string {
  return texto
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
}

/**
 * Traduce una transcripción hablada al protocolo de `respuesta` del
 * contrato (si | no | articulo_id:<int> | cantidad:<float>). Devuelve
 * null si no se pudo interpretar (la UI debe seguir ofreciendo los
 * botones/teclado como camino confiable).
 */
export function interpretarRespuestaVoz(texto: string, candidatos: Candidato[] | null): string | null {
  const normalizado = sinTildes(texto)

  if (candidatos) {
    const encontrado = candidatos.find((c) => normalizado.includes(sinTildes(c.articulo_nombre)))
    return encontrado ? `articulo_id:${encontrado.articulo_id}` : null
  }

  if (/\bno\b/.test(normalizado)) return 'no'
  if (/\bsi\b/.test(normalizado)) return 'si'

  const numero = normalizado.match(/\d+([.,]\d+)?/)
  if (numero) return `cantidad:${numero[0].replace(',', '.')}`

  return null
}
