import { useEffect, useState } from 'react'
import { nuevoConteoRequest } from './lib/conteos'

// Herramienta de desarrollo, no UI final: comprueba /health y permite
// postear texto crudo a /api/v1/conteos para ver la respuesta del contrato.
export default function App() {
  const [health, setHealth] = useState('conectando…')
  const [texto, setTexto] = useState('')
  const [respuesta, setRespuesta] = useState('')

  useEffect(() => {
    fetch('/health')
      .then((r) => r.json())
      .then((d) => setHealth(d.status === 'ok' ? 'VoceoStock OK' : JSON.stringify(d)))
      .catch(() => setHealth('backend no disponible'))
  }, [])

  async function enviar() {
    const r = await fetch('/api/v1/conteos', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(nuevoConteoRequest(texto)),
    })
    setRespuesta(JSON.stringify(await r.json(), null, 2))
  }

  return (
    <main className="mx-auto max-w-2xl p-8 font-sans">
      <h1 className="text-2xl font-bold">{health}</h1>
      <section className="mt-6">
        <textarea
          className="w-full rounded border p-2"
          rows={3}
          placeholder="ej: noventa cajas de cazuelas"
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
        />
        <button
          className="mt-2 rounded bg-slate-900 px-4 py-2 text-white"
          onClick={enviar}
        >
          Enviar a /conteos
        </button>
        {respuesta && (
          <pre className="mt-4 overflow-x-auto rounded bg-slate-100 p-4 text-sm">{respuesta}</pre>
        )}
      </section>
    </main>
  )
}
