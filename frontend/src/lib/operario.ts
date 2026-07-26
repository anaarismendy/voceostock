export function esPinValido(pin: string): boolean {
  return /^\d{4}$/.test(pin)
}

// El líder ve el reporte de cierre (C9) y el dashboard; el operario cuenta.
// El rol lo manda el BACKEND según lo que el líder configuró: ya no es un
// selector del cliente, porque eso dejaba entrar a cualquiera al panel del líder.
export type Rol = 'operario' | 'auditor' | 'lider'

export interface Operario {
  id: string
  nombre: string
  rol: Rol
}

/** El PIN identifica a un operario ya dado de alta. PIN desconocido → 404. */
export async function loginOperario(pin: string): Promise<Operario> {
  const r = await fetch('/api/v1/operarios/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ pin }),
  })
  if (r.status === 404) throw new Error('PIN_DESCONOCIDO')
  if (!r.ok) throw new Error(`Error ${r.status} al iniciar sesión`)
  return r.json()
}
