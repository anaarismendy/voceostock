// Módulo por operario: precisión histórica y cuánto le ajusta la confianza el
// sistema (D5). Solo métricas de proceso — nunca SD ni cantidades.

export interface OperarioStats {
  id: string
  nombre: string
  rol: string | null
  capturas_totales: number
  capturas_correctas: number
  precision: number | null
  ajuste: number
  perfil_activo: boolean
}

export async function getOperarios(): Promise<OperarioStats[]> {
  const r = await fetch('/api/v1/operarios')
  if (!r.ok) throw new Error(`Error ${r.status} al listar operarios`)
  return r.json()
}

export async function recalcularOperarios(): Promise<OperarioStats[]> {
  const r = await fetch('/api/v1/operarios/recalcular', { method: 'POST' })
  if (!r.ok) throw new Error(`Error ${r.status} al recalcular`)
  return r.json()
}

export interface OperarioForm {
  nombre: string
  pin: string
  rol: string
}

async function enviar(url: string, method: string, body: Partial<OperarioForm>) {
  const r = await fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (r.status === 409) throw new Error('Ese PIN ya está asignado a otro operario.')
  if (!r.ok) throw new Error('No se pudo guardar. Revisa los datos.')
  return r.json() as Promise<OperarioStats>
}

export function crearOperario(datos: OperarioForm): Promise<OperarioStats> {
  return enviar('/api/v1/operarios', 'POST', datos)
}

/** Cambiar el PIN no cambia el id: el operario conserva su historial. */
export function editarOperario(id: string, datos: Partial<OperarioForm>): Promise<OperarioStats> {
  return enviar(`/api/v1/operarios/${id}`, 'PATCH', datos)
}

export function pinValido(pin: string): boolean {
  return /^\d{4}$/.test(pin)
}

/** Qué le está haciendo el sistema a este operario, en una frase. */
export function efectoConfianza(o: OperarioStats): string {
  if (!o.perfil_activo) return 'Sin historial suficiente todavía'
  if (o.ajuste > 0.005) return 'Menos confirmaciones (más acertado)'
  if (o.ajuste < -0.005) return 'Más confirmaciones (más errores)'
  return 'Confirmaciones normales'
}
