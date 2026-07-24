export function esPinValido(pin: string): boolean {
  return /^\d{4}$/.test(pin)
}

// El líder ve el reporte de cierre (C9); el operario cuenta. No hay auth real
// todavía (B1 solo define la tabla `operarios`), así que el rol se elige en el
// login — placeholder hasta que P2 exponga un endpoint de autenticación.
export type Rol = 'operario' | 'lider'

export interface Operario {
  id: string
  pin: string
  rol: Rol
}

export function nuevoOperario(pin: string, rol: Rol = 'operario'): Operario {
  return { id: crypto.randomUUID(), pin, rol }
}
