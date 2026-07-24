export interface SesionCreada {
  sesion_id: string
  bodega: { id: number; nombre: string }
  total_articulos: number
}

/** I2: la sesión REAL se crea al elegir bodega; el backend es idempotente
 * (misma bodega+operario abierta → misma sesión). */
export async function crearSesion(bodegaId: number, operarioId: string): Promise<SesionCreada> {
  const r = await fetch('/api/v1/sesiones', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ bodega_id: bodegaId, operario_id: operarioId, tipo: 'primario' }),
  })
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
