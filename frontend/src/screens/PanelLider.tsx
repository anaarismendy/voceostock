import { ArrowLeft, LogOut } from 'lucide-react'
import { useState } from 'react'
import BarraInventario from '../components/BarraInventario'
import type { Inventario } from '../lib/inventarios'
import { useOperario } from '../state/OperarioContext'
import Dashboard from './Dashboard'
import PanelConfig from './PanelConfig'
import VistaCierre from './VistaCierre'

type Tab = 'vivo' | 'cierre' | 'ajustes'

const ETIQUETA_TAB: Record<Tab, string> = { vivo: 'En vivo', cierre: 'Cierre', ajustes: 'Ajustes' }

// Shell del líder (C10): header compartido + pestañas En vivo / Cierre. El
// operario cuenta; el líder monitorea y cierra. No hay pantallas de captura
// aquí, así que el dashboard sí puede mostrar actividad y el cierre el SD.
export default function PanelLider() {
  const { bodega, cerrarSesion, volverASeleccionarBodega } = useOperario()
  const [tab, setTab] = useState<Tab>('vivo')
  // Qué ciclo se está mirando. `version` fuerza el remontaje de las vistas al
  // abrir/cerrar/cambiar de inventario, para que recarguen contra el nuevo.
  const [inventario, setInventario] = useState<Inventario | null>(null)
  const [version, setVersion] = useState(0)

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-5xl flex-col bg-pantalla p-4 text-texto sm:p-7">
      <header className="flex items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <button
            type="button"
            onClick={volverASeleccionarBodega}
            aria-label="Cambiar de bodega"
            className="transicion-estado flex h-16 w-16 shrink-0 items-center justify-center clay-tecla rounded-control bg-superficie2 active:bg-grafito"
          >
            <ArrowLeft className="h-6 w-6" />
          </button>
          <div className="min-w-0">
            <p className="text-xs tracking-widest text-texto-tenue">PANEL DEL LÍDER</p>
            <h1 className="truncate text-xl font-semibold capitalize leading-tight">{bodega!.nombre}</h1>
          </div>
        </div>
        <button
          type="button"
          onClick={cerrarSesion}
          aria-label="Cerrar sesión"
          className="transicion-estado flex h-16 w-16 shrink-0 items-center justify-center clay-tecla rounded-control bg-superficie2 active:bg-grafito"
        >
          <LogOut className="h-6 w-6" />
        </button>
      </header>

      <div className="mt-4 grid grid-cols-3 gap-2" role="tablist" aria-label="Vista del líder">
        {(['vivo', 'cierre', 'ajustes'] as const).map((t) => (
          <button
            key={t}
            type="button"
            role="tab"
            aria-selected={tab === t}
            onClick={() => setTab(t)}
            className={`transicion-estado h-16 rounded-control text-base font-semibold ${
              tab === t ? 'clay-tecla bg-superficie2 font-semibold text-texto' : 'bg-superficie1 text-texto-sec active:bg-superficie2'
            }`}
          >
            {ETIQUETA_TAB[t]}
          </button>
        ))}
      </div>

      <div className="mt-4">
        <BarraInventario
          bodegaId={bodega!.id}
          seleccionado={inventario}
          onSeleccionar={setInventario}
          onCambio={() => setVersion((v) => v + 1)}
        />
      </div>

      <section className="mt-4 flex-1 overflow-y-auto">
        {tab === 'vivo' && <Dashboard key={version} inventarioId={inventario?.id ?? null} />}
        {tab === 'cierre' && <VistaCierre key={version} inventarioId={inventario?.id ?? null} />}
        {tab === 'ajustes' && <PanelConfig />}
      </section>
    </main>
  )
}
