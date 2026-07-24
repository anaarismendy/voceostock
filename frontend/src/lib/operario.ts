export function esPinValido(pin: string): boolean {
  return /^\d{4}$/.test(pin)
}

export interface Operario {
  id: string
  nombre: string
}

/** I2: login real contra el backend — el PIN identifica (find-or-create). */
export async function loginOperario(pin: string): Promise<Operario> {
  const r = await fetch('/api/v1/operarios/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ pin }),
  })
  if (!r.ok) throw new Error(`Error ${r.status} al iniciar sesión`)
  return r.json()
}
