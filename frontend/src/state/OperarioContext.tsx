import { createContext, useContext, useMemo, useState, type ReactNode } from 'react'
import { nuevoOperario, type Operario, type Rol } from '../lib/operario'
import type { Bodega } from '../lib/bodegas'

interface SesionOperario {
  operario: Operario | null
  bodega: Bodega | null
  iniciarSesion: (pin: string, rol: Rol) => void
  seleccionarBodega: (bodega: Bodega) => void
  volverASeleccionarBodega: () => void
  cerrarSesion: () => void
}

const OperarioContext = createContext<SesionOperario | null>(null)

export function OperarioProvider({ children }: { children: ReactNode }) {
  const [operario, setOperario] = useState<Operario | null>(null)
  const [bodega, setBodega] = useState<Bodega | null>(null)

  const value = useMemo<SesionOperario>(
    () => ({
      operario,
      bodega,
      iniciarSesion: (pin, rol) => setOperario(nuevoOperario(pin, rol)),
      seleccionarBodega: (b) => setBodega(b),
      volverASeleccionarBodega: () => setBodega(null),
      cerrarSesion: () => {
        setOperario(null)
        setBodega(null)
      },
    }),
    [operario, bodega],
  )

  return <OperarioContext.Provider value={value}>{children}</OperarioContext.Provider>
}

export function useOperario(): SesionOperario {
  const ctx = useContext(OperarioContext)
  if (!ctx) throw new Error('useOperario debe usarse dentro de <OperarioProvider>')
  return ctx
}
