import type { Progreso } from '../lib/sesiones'

/** C8: barra de progreso global y por familia, alimentada por el WS real. */
export default function PanelProgreso({ progreso, enVivo }: { progreso: Progreso | null; enVivo: boolean }) {
  if (!progreso) return null
  const pct = progreso.total > 0 ? Math.round((progreso.contados / progreso.total) * 100) : 0

  return (
    <section className="w-full max-w-md rounded-tarjeta border border-borde-sutil bg-superficie1 p-4">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-texto-sec">
          Progreso: {progreso.contados}/{progreso.total}
        </p>
        <span
          className={`h-2.5 w-2.5 rounded-full ${enVivo ? 'bg-exito' : 'bg-texto-tenue'}`}
          title={enVivo ? 'En vivo (WebSocket)' : 'Actualización periódica'}
          aria-label={enVivo ? 'En vivo' : 'Actualización periódica'}
        />
      </div>
      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-superficie2">
        <div className="h-full rounded-full bg-primario transition-all" style={{ width: `${pct}%` }} />
      </div>

      {/* Solo las familias ya tocadas: con 566 artículos hay cientos de
          familias y listarlas todas entierra la señal. */}
      {progreso.por_familia.filter((f) => f.contados > 0).length > 0 && (
        <ul className="mt-3 space-y-2">
          {progreso.por_familia.filter((f) => f.contados > 0).map((f) => {
            const fpct = f.total > 0 ? Math.round((f.contados / f.total) * 100) : 0
            return (
              <li key={f.familia}>
                <div className="flex justify-between text-xs text-texto-sec">
                  <span className="capitalize">{f.familia}</span>
                  <span>
                    {f.contados}/{f.total}
                  </span>
                </div>
                <div className="mt-1 h-1 overflow-hidden rounded-full bg-superficie2">
                  <div className="h-full rounded-full bg-acento transition-all" style={{ width: `${fpct}%` }} />
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
