export interface ConteoRequest {
  sesion_id: string
  bodega_id: number
  operario_id: string
  fuente: 'voz-tablet' | 'whatsapp' | 'manual' | 'rfid' | 'bascula'
  payload_texto: string | null
  payload_audio_b64: string | null
}

export function nuevoConteoRequest(texto: string, bodegaId = 13): ConteoRequest {
  return {
    sesion_id: crypto.randomUUID(),
    bodega_id: bodegaId,
    operario_id: crypto.randomUUID(),
    fuente: 'manual',
    payload_texto: texto,
    payload_audio_b64: null,
  }
}
