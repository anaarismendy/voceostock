export function esPinValido(pin: string): boolean {
  return /^\d{4}$/.test(pin)
}

export interface Operario {
  id: string
  pin: string
}

export function nuevoOperario(pin: string): Operario {
  return { id: crypto.randomUUID(), pin }
}
