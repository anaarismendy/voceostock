import { useState } from 'react'
import { useOperario } from '../state/OperarioContext'

const TECLAS = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '', '0', 'borrar'] as const

export default function LoginPin() {
  const { iniciarSesion } = useOperario()
  const [pin, setPin] = useState('')
  const [error, setError] = useState<string | null>(null)

  function agregarDigito(d: string) {
    if (pin.length >= 4) return
    const siguiente = pin + d
    setPin(siguiente)
    setError(null)
    // El PIN identifica a un operario ya dado de alta por el líder; el rol
    // (operario/líder) viene del backend, no se elige aquí.
    if (siguiente.length === 4) {
      iniciarSesion(siguiente).catch((e: Error) => {
        setError(
          e.message === 'PIN_DESCONOCIDO'
            ? 'PIN no registrado. Pídele a tu líder que te dé de alta.'
            : 'No se pudo iniciar sesión. Intenta de nuevo.',
        )
        setPin('')
      })
    }
  }

  function borrar() {
    setPin((p) => p.slice(0, -1))
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-5 bg-pantalla p-4 text-texto sm:gap-8 sm:p-6">
      <div className="flex flex-col items-center gap-3">
        <div className="flex items-center gap-2.5">
          <div className="h-6 w-2 rounded-full bg-marca" />
          <div className="text-lg font-semibold tracking-wide">VOCEOSTOCK</div>
        </div>
        <div className="text-xl font-semibold">Ingresa tu PIN</div>
        <div className="text-base text-texto-sec">Cuatro dígitos, los mismos del carné</div>
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

      <div
        className="flex min-h-6 items-center gap-2 px-4 text-center text-base text-critico"
        aria-live="polite"
      >
        {error && (
          <>
            <span>✕</span> {error}
          </>
        )}
      </div>

      {/* w-full + ancho tope: el teclado se adapta al móvil sin desbordar. */}
      <div className="grid w-full max-w-[420px] grid-cols-3 gap-3 sm:gap-4">
        {TECLAS.map((tecla, i) => {
          if (tecla === '') return <div key={`vacio-${i}`} className="h-[72px] w-full sm:h-[84px]" />
          if (tecla === 'borrar')
            return (
              <button
                key={tecla}
                type="button"
                onClick={borrar}
                className="transicion-estado h-[72px] w-full sm:h-[84px] rounded-control bg-superficie1 text-base text-texto-tenue active:bg-superficie2"
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
              className="clay-tecla transicion-estado h-[72px] w-full sm:h-[84px] rounded-control bg-superficie2 text-xl font-semibold active:bg-grafito"
            >
              {tecla}
            </button>
          )
        })}
      </div>
    </main>
  )
}
