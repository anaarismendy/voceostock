export interface SesionCreada {
  sesion_id: string
  bodega: { id: number; nombre: string }
  total_articulos: number
  /** A qué ciclo quedó enganchada la sesión ("Inventario #2"). */
  inventario_id: number
  inventario_numero: number
}

/** I2: la sesión REAL se crea al elegir bodega; el backend es idempotente
 * (mismo ciclo+operario abierta → misma sesión). */
export async function crearSesion(bodegaId: number, operarioId: string): Promise<SesionCreada> {
  const r = await fetch('/api/v1/sesiones', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ bodega_id: bodegaId, operario_id: operarioId, tipo: 'primario' }),
  })
  // 409 = la bodega no tiene un ciclo abierto. Es el caso normal cuando el
  // líder aún no lo abrió, así que merece un mensaje propio y no un "Error 409".
  if (r.status === 409) throw new Error('SIN_INVENTARIO')
  if (!r.ok) throw new Error(`Error ${r.status} al crear la sesión`)
  return r.json()
}

export interface ProgresoFamilia {
  familia: string
  contados: number
  total: number
}

export interface Progreso {
  contados: number
  total: number
  por_familia: ProgresoFamilia[]
  colisiones: number
}

export async function getProgreso(sesionId: string): Promise<Progreso> {
  const r = await fetch(`/api/v1/sesiones/${encodeURIComponent(sesionId)}/progreso`)
  if (!r.ok) throw new Error(`Error ${r.status} al consultar progreso`)
  return r.json()
}
