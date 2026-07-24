// Cliente + lógica del reporte de cierre (C9). Es el ÚNICO módulo del frontend
// que maneja el SD (stock teórico): el conteo ciego lo permite solo aquí, en el
// reporte de cierre del líder — nunca en pantallas de captura.

export interface FilaCierre {
  articulo_id: number
  articulo_nombre: string
  unidad: string
  sd: number
  contado: number
  diferencia: number // contado - sd
}

export async function getCierre(esperados: number[] = []): Promise<FilaCierre[]> {
  const query = esperados.length ? `?ids=${esperados.join(',')}` : ''
  const r = await fetch(`/api/v1/cierre${query}`)
  if (!r.ok) throw new Error(`Error ${r.status} al cargar el cierre`)
  return r.json()
}

export type EstadoFila = 'cuadra' | 'sobrante' | 'faltante' | 'sin_contar'

/** Clasifica una fila para el color/etiqueta de la tabla. */
export function estadoFila(fila: FilaCierre): EstadoFila {
  if (fila.contado === 0) return 'sin_contar'
  if (fila.diferencia === 0) return 'cuadra'
  return fila.diferencia > 0 ? 'sobrante' : 'faltante'
}

export interface TotalesCierre {
  articulos: number
  cuadran: number
  sobrantes: number
  faltantes: number
  sinContar: number
}

/** Resumen para el encabezado del reporte. */
export function totalesCierre(filas: FilaCierre[]): TotalesCierre {
  const t: TotalesCierre = { articulos: filas.length, cuadran: 0, sobrantes: 0, faltantes: 0, sinContar: 0 }
  for (const fila of filas) {
    switch (estadoFila(fila)) {
      case 'cuadra':
        t.cuadran++
        break
      case 'sobrante':
        t.sobrantes++
        break
      case 'faltante':
        t.faltantes++
        break
      case 'sin_contar':
        t.sinContar++
        break
    }
  }
  return t
}
