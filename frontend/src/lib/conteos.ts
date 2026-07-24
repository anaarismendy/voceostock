export type Unidad = 'Unidad' | 'Kilogram' | 'Liter' | 'Portion'
export type Fuente = 'voz-tablet' | 'whatsapp' | 'manual' | 'rfid' | 'bascula'

export interface ConteoRequest {
  sesion_id: string
  bodega_id: number
  operario_id: string
  fuente: Fuente
  payload_texto: string | null
  payload_audio_b64: string | null
}

export interface NuevoConteoParams {
  sesionId: string
  bodegaId: number
  operarioId: string
  fuente?: Fuente
  texto?: string
  audioBase64?: string
}

export function nuevoConteoRequest({
  sesionId,
  bodegaId,
  operarioId,
  fuente = 'manual',
  texto,
  audioBase64,
}: NuevoConteoParams): ConteoRequest {
  return {
    // I2: la sesión REAL creada al elegir bodega — el backend rechaza (404)
    // sesiones inventadas, así que aquí nunca se genera un UUID local.
    sesion_id: sesionId,
    bodega_id: bodegaId,
    operario_id: operarioId,
    fuente,
    payload_texto: texto ?? null,
    payload_audio_b64: audioBase64 ?? null,
  }
}

export interface Conteo {
  id: string
  articulo_id: number
  articulo_nombre: string
  cantidad: number
  unidad: Unidad
  confianza: number
  fuente: Fuente
  evidencia_url: string | null
}

export interface Candidato {
  articulo_id: number
  articulo_nombre: string
}

export type MotivoConfirmacion = 'ambiguedad' | 'anomalia' | 'baja_confianza'

export type ConteoResponse =
  | { status: 'confirmado'; conteo: Conteo }
  | {
      status: 'requiere_confirmacion'
      token_pendiente: string
      motivo: MotivoConfirmacion
      pregunta: string
      candidatos: Candidato[] | null
    }
  | { status: 'no_catalogado'; texto_capturado: string; cantidad: number | null; unidad: string | null }
  // Cuarto estado, exclusivo de /resolver: el operario respondió "no" y el
  // conteo se descarta sin persistir (docs/contrato/contrato.md).
  | { status: 'descartado' }

export function mensajeConfirmacion(conteo: Conteo): string {
  return `${conteo.cantidad} ${conteo.unidad} de ${conteo.articulo_nombre}`
}

/** Error HTTP del backend con su código: permite mensajes honestos por caso
 * (410 token expirado, 404 sesión/token, 409 sesión cerrada) en vez del
 * genérico de conexión. */
export class ApiError extends Error {
  constructor(
    public status: number,
    mensaje: string,
  ) {
    super(mensaje)
  }
}

async function lanzarApiError(r: Response, contexto: string): Promise<never> {
  let detalle = ''
  try {
    detalle = (await r.json()).detail ?? ''
  } catch {
    /* cuerpo no-JSON: se usa solo el código */
  }
  throw new ApiError(r.status, `Error ${r.status} ${contexto}: ${detalle}`)
}

export async function postConteo(request: ConteoRequest): Promise<ConteoResponse> {
  const r = await fetch('/api/v1/conteos', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
  if (!r.ok) await lanzarApiError(r, 'al enviar conteo')
  return r.json()
}

export async function resolverConteo(tokenPendiente: string, respuesta: string): Promise<ConteoResponse> {
  const r = await fetch(`/api/v1/conteos/${encodeURIComponent(tokenPendiente)}/resolver`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ respuesta }),
  })
  if (!r.ok) await lanzarApiError(r, 'al resolver conteo')
  return r.json()
}
