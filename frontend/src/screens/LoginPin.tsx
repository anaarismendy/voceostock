import { useState } from 'react'
import { useOperario } from '../state/OperarioContext'
import type { Rol } from '../lib/operario'

const TECLAS = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '', '0', 'borrar'] as const

export default function LoginPin() {
  const { iniciarSesion } = useOperario()
  const [pin, setPin] = useState('')
  const [error, setError] = useState(false)
  const [rol, setRol] = useState<Rol>('operario')

  function agregarDigito(d: string) {
    if (pin.length >= 4) return
    const siguiente = pin + d
    setPin(siguiente)
    setError(false)
    // I2: login real contra POST /api/v1/operarios/login (find-or-create),
    // con el rol elegido arriba (solo del cliente, C9).
    if (siguiente.length === 4) {
      iniciarSesion(siguiente, rol).catch(() => {
        setError(true)
        setPin('')
      })
    }
  }

  function borrar() {
    setPin((p) => p.slice(0, -1))
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-10 bg-fondo p-6 text-texto">
      <div>
        <h1 className="text-center text-xl font-semibold tracking-tight">VoceoStock</h1>
        <p className="mt-2 text-center text-base text-texto-sec">Ingresa tu PIN</p>
      </div>

      {error && <p className="text-base text-critico">No se pudo iniciar sesión. Intenta de nuevo.</p>}

      <div className="flex gap-2 rounded-control border border-borde-sutil bg-superficie1 p-1" role="radiogroup" aria-label="Rol">
        {(['operario', 'lider'] as const).map((r) => (
          <button
            key={r}
            type="button"
            role="radio"
            aria-checked={rol === r}
            onClick={() => setRol(r)}
            className={`transicion-estado h-16 w-36 rounded-control text-base font-semibold capitalize ${
              rol === r ? 'bg-primario text-texto' : 'text-texto-sec active:bg-superficie2'
            }`}
          >
            {r === 'operario' ? 'Operario' : 'Líder'}
          </button>
        ))}
      </div>

      <div className="flex gap-4" aria-label={`PIN, ${pin.length} de 4 dígitos ingresados`}>
        {[0, 1, 2, 3].map((i) => (
          <div
            key={i}
            className={`transicion-estado h-4 w-4 rounded-full border-2 ${
              i < pin.length ? 'border-primario bg-primario' : 'border-borde-fuerte bg-transparent'
            }`}
          />
        ))}
      </div>

      <div className="grid grid-cols-3 gap-3">
        {TECLAS.map((tecla, i) => {
          if (tecla === '') return <div key={`vacio-${i}`} className="h-20 w-20" />
          if (tecla === 'borrar')
            return (
              <button
                key={tecla}
                type="button"
                onClick={borrar}
                className="transicion-estado h-20 w-20 rounded-control border border-borde-sutil bg-superficie1 text-lg font-semibold text-texto-sec active:bg-superficie2"
                aria-label="Borrar"
              >
                ⌫
              </button>
            )
          return (
            <button
              key={tecla}
              type="button"
              onClick={() => agregarDigito(tecla)}
              className="transicion-estado h-20 w-20 rounded-control border border-borde-sutil bg-superficie1 text-lg font-semibold active:border-borde-fuerte active:bg-superficie2"
            >
              {tecla}
            </button>
          )
        })}
      </div>
    </main>
  )
}
