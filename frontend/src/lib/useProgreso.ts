import { useCallback, useEffect, useRef, useState } from 'react'
import { getProgreso, type Progreso } from './sesiones'

const POLLING_MS = 10_000

/**
 * C8: progreso en vivo. Se suscribe al WebSocket real /ws/bodegas/{id} y
 * refresca GET /progreso con cada evento (el WS avisa "algo cambió"; el GET
 * trae el detalle por familia). Si el WS no conecta o se cae, degrada a
 * polling cada 10 s — el mock de dev no tiene WS y funciona igual.
 */
export function useProgreso(bodegaId: number, sesionId: string): {
  progreso: Progreso | null
  enVivo: boolean
} {
  const [progreso, setProgreso] = useState<Progreso | null>(null)
  const [enVivo, setEnVivo] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)

  const refrescar = useCallback(() => {
    getProgreso(sesionId).then(setProgreso).catch(() => {})
  }, [sesionId])

  useEffect(() => {
    refrescar()

    let ws: WebSocket | null = null
    try {
      const proto = location.protocol === 'https:' ? 'wss' : 'ws'
      ws = new WebSocket(`${proto}://${location.host}/ws/bodegas/${bodegaId}`)
    } catch {
      ws = null
    }

    let intervalo: ReturnType<typeof setInterval> | null = null
    const activarPolling = () => {
      setEnVivo(false)
      if (!intervalo) intervalo = setInterval(refrescar, POLLING_MS)
    }

    if (ws) {
      ws.onopen = () => setEnVivo(true)
      ws.onmessage = refrescar
      ws.onerror = activarPolling
      ws.onclose = activarPolling
      wsRef.current = ws
    } else {
      activarPolling()
    }

    return () => {
      if (intervalo) clearInterval(intervalo)
      if (ws) {
        ws.onclose = null
        ws.close()
      }
    }
  }, [bodegaId, refrescar])

  return { progreso, enVivo }
}
