import { useState } from 'react'
import { useOperario } from '../state/OperarioContext'

const TECLAS = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '', '0', 'borrar'] as const

export default function LoginPin() {
  const { iniciarSesion } = useOperario()
  const [pin, setPin] = useState('')
  const [error, setError] = useState(false)

  function agregarDigito(d: string) {
    if (pin.length >= 4) return
    const siguiente = pin + d
    setPin(siguiente)
    setError(false)
    // I2: login real contra POST /api/v1/operarios/login (find-or-create).
    if (siguiente.length === 4) {
      iniciarSesion(siguiente).catch(() => {
        setError(true)
        setPin('')
      })
    }
  }

  function borrar() {
    setPin((p) => p.slice(0, -1))
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-10 bg-slate-900 p-6 text-white">
      <div>
        <h1 className="text-center text-3xl font-bold">VoceoStock</h1>
        <p className="mt-2 text-center text-lg text-slate-300">Ingresa tu PIN</p>
      </div>

      {error && <p className="text-lg text-red-400">No se pudo iniciar sesión. Intenta de nuevo.</p>}

      <div className="flex gap-4" aria-label={`PIN, ${pin.length} de 4 dígitos ingresados`}>
        {[0, 1, 2, 3].map((i) => (
          <div
            key={i}
            className={`h-6 w-6 rounded-full border-2 border-white ${i < pin.length ? 'bg-white' : 'bg-transparent'}`}
          />
        ))}
      </div>

      <div className="grid grid-cols-3 gap-4">
        {TECLAS.map((tecla, i) => {
          if (tecla === '') return <div key={`vacio-${i}`} className="h-20 w-20" />
          if (tecla === 'borrar')
            return (
              <button
                key={tecla}
                type="button"
                onClick={borrar}
                className="h-20 w-20 rounded-2xl bg-slate-800 text-xl font-semibold active:bg-slate-700"
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
              className="h-20 w-20 rounded-2xl bg-slate-800 text-3xl font-semibold active:bg-slate-700"
            >
              {tecla}
            </button>
          )
        })}
      </div>
    </main>
  )
}
