import { createContext, useContext, useMemo, useState, type ReactNode } from 'react'
import { loginOperario, type Operario } from '../lib/operario'
import { crearSesion } from '../lib/sesiones'
import type { Bodega } from '../lib/bodegas'

interface SesionOperario {
  operario: Operario | null
  bodega: Bodega | null
  /** id de la sesión de conteo REAL en BD (I2); null hasta elegir bodega. */
  sesionId: string | null
  totalArticulos: number
  /** El rol ya no se pasa: lo determina el backend según el PIN. */
  iniciarSesion: (pin: string) => Promise<void>
  seleccionarBodega: (bodega: Bodega) => Promise<void>
  volverASeleccionarBodega: () => void
  cerrarSesion: () => void
}

const OperarioContext = createContext<SesionOperario | null>(null)

export function OperarioProvider({ children }: { children: ReactNode }) {
  const [operario, setOperario] = useState<Operario | null>(null)
  const [bodega, setBodega] = useState<Bodega | null>(null)
  const [sesionId, setSesionId] = useState<string | null>(null)
  const [totalArticulos, setTotalArticulos] = useState(0)

  const value = useMemo<SesionOperario>(
    () => ({
      operario,
      bodega,
      sesionId,
      totalArticulos,
      iniciarSesion: async (pin) => {
        setOperario(await loginOperario(pin))
      },
      seleccionarBodega: async (b) => {
        const sesion = await crearSesion(b.id, operario!.id)
        setBodega(b)
        setSesionId(sesion.sesion_id)
        setTotalArticulos(sesion.total_articulos)
      },
      volverASeleccionarBodega: () => {
        setBodega(null)
        setSesionId(null)
        setTotalArticulos(0)
      },
      cerrarSesion: () => {
        setOperario(null)
        setBodega(null)
        setSesionId(null)
        setTotalArticulos(0)
      },
    }),
    [operario, bodega, sesionId, totalArticulos],
  )

  return <OperarioContext.Provider value={value}>{children}</OperarioContext.Provider>
}

export function useOperario(): SesionOperario {
  const ctx = useContext(OperarioContext)
  if (!ctx) throw new Error('useOperario debe usarse dentro de <OperarioProvider>')
  return ctx
}
