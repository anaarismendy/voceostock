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
    <main className="flex min-h-screen flex-col items-center justify-center gap-8 bg-pantalla p-6 text-texto">
      <div className="flex flex-col items-center gap-3">
        <div className="flex items-center gap-2.5">
          <div className="h-6 w-2 rounded-full bg-marca" />
          <div className="text-lg font-semibold tracking-wide">VOCEOSTOCK</div>
        </div>
        <div className="text-xl font-semibold">Ingresa tu PIN</div>
        <div className="text-base text-texto-sec">Cuatro dígitos, los mismos del carné</div>
      </div>

      <div
        className="clay-hundido flex gap-1 rounded-control bg-superficie2 p-1"
        role="radiogroup"
        aria-label="Rol"
      >
        {(['operario', 'lider'] as const).map((r) => (
          <button
            key={r}
            type="button"
            role="radio"
            aria-checked={rol === r}
            onClick={() => setRol(r)}
            className={`transicion-estado h-16 w-36 rounded-chip text-base font-semibold capitalize ${
              rol === r ? 'clay-tecla bg-accion text-white' : 'text-texto-tenue'
            }`}
          >
            {r === 'operario' ? 'Operario' : 'Líder'}
          </button>
        ))}
      </div>

      <div className="flex gap-5" aria-label={`PIN, ${pin.length} de 4 dígitos ingresados`}>
        {[0, 1, 2, 3].map((i) => (
          <div
            key={i}
            className={`clay-hundido flex h-16 w-16 items-center justify-center rounded-control bg-superficie2 ${
              i === pin.length ? 'outline outline-[3px] outline-offset-[3px] outline-azul-texto' : ''
            }`}
          >
            {i < pin.length && <div className="h-4 w-4 rounded-full bg-texto" />}
          </div>
        ))}
      </div>

      <div className="flex h-6 items-center gap-2 text-base text-critico" aria-live="polite">
        {error && (
          <>
            <span>✕</span> No se pudo iniciar sesión. Intenta de nuevo.
          </>
        )}
      </div>

      <div className="grid grid-cols-3 gap-4">
        {TECLAS.map((tecla, i) => {
          if (tecla === '') return <div key={`vacio-${i}`} className="h-[84px] w-[132px]" />
          if (tecla === 'borrar')
            return (
              <button
                key={tecla}
                type="button"
                onClick={borrar}
                className="transicion-estado h-[84px] w-[132px] rounded-control bg-superficie1 text-base text-texto-tenue active:bg-superficie2"
                aria-label="Borrar"
              >
                Borrar
              </button>
            )
          return (
            <button
              key={tecla}
              type="button"
              onClick={() => agregarDigito(tecla)}
              className="clay-tecla transicion-estado h-[84px] w-[132px] rounded-control bg-superficie2 text-xl font-semibold active:bg-grafito"
            >
              {tecla}
            </button>
          )
        })}
      </div>
    </main>
  )
}
