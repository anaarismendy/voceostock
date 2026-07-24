import { ArrowLeft, LogOut } from 'lucide-react'
import { useState } from 'react'
import { useOperario } from '../state/OperarioContext'
import Dashboard from './Dashboard'
import VistaCierre from './VistaCierre'

type Tab = 'vivo' | 'cierre'

// Shell del líder (C10): header compartido + pestañas En vivo / Cierre. El
// operario cuenta; el líder monitorea y cierra. No hay pantallas de captura
// aquí, así que el dashboard sí puede mostrar actividad y el cierre el SD.
export default function PanelLider() {
  const { bodega, cerrarSesion, volverASeleccionarBodega } = useOperario()
  const [tab, setTab] = useState<Tab>('vivo')

  return (
    <main className="flex min-h-screen flex-col bg-slate-900 p-6 text-white">
      <header className="flex items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <button
            type="button"
            onClick={volverASeleccionarBodega}
            aria-label="Cambiar de bodega"
            className="flex h-14 w-14 shrink-0 items-center justify-center rounded-xl bg-slate-800 active:bg-slate-700"
          >
            <ArrowLeft className="h-6 w-6" />
          </button>
          <div className="min-w-0">
            <p className="text-sm text-slate-400">Panel del líder</p>
            <h1 className="truncate text-2xl font-bold capitalize leading-tight">{bodega!.nombre}</h1>
          </div>
        </div>
        <button
          type="button"
          onClick={cerrarSesion}
          aria-label="Cerrar sesión"
          className="flex h-14 w-14 shrink-0 items-center justify-center rounded-xl bg-slate-800 active:bg-slate-700"
        >
          <LogOut className="h-6 w-6" />
        </button>
      </header>

      <div className="mt-4 grid grid-cols-2 gap-2" role="tablist" aria-label="Vista del líder">
        {(['vivo', 'cierre'] as const).map((t) => (
          <button
            key={t}
            type="button"
            role="tab"
            aria-selected={tab === t}
            onClick={() => setTab(t)}
            className={`h-14 rounded-xl text-lg font-semibold transition-colors ${
              tab === t ? 'bg-white text-slate-900' : 'bg-slate-800 text-slate-200 active:bg-slate-700'
            }`}
          >
            {t === 'vivo' ? 'En vivo' : 'Cierre'}
          </button>
        ))}
      </div>

      <section className="mt-4 flex-1 overflow-y-auto">
        {tab === 'vivo' ? <Dashboard /> : <VistaCierre />}
      </section>
    </main>
  )
}
