export function esPinValido(pin: string): boolean {
  return /^\d{4}$/.test(pin)
}

// El líder ve el reporte de cierre (C9) y el dashboard; el operario cuenta.
// El rol se elige en el login (placeholder de P3): el backend identifica al
// operario por PIN (find-or-create) y el rol viaja solo en el cliente.
export type Rol = 'operario' | 'lider'

export interface Operario {
  id: string
  nombre: string
  rol: Rol
}

/** I2: login real contra el backend — el PIN identifica (find-or-create). */
export async function loginOperario(pin: string, rol: Rol = 'operario'): Promise<Operario> {
  const r = await fetch('/api/v1/operarios/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ pin }),
  })
  if (!r.ok) throw new Error(`Error ${r.status} al iniciar sesión`)
  const datos: { id: string; nombre: string } = await r.json()
  return { ...datos, rol }
}
