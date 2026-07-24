import { useCallback, useRef, useState } from 'react'

export type EstadoVoz = 'inactivo' | 'escuchando' | 'no_soportado' | 'error'

interface UseVozResultado {
  estado: EstadoVoz
  escuchar: () => void
  detener: () => void
  hablar: (texto: string) => void
}

function obtenerConstructor(): (new () => SpeechRecognitionInstance) | null {
  if (typeof window === 'undefined') return null
  return window.SpeechRecognition ?? window.webkitSpeechRecognition ?? null
}

/**
 * Encapsula Web Speech API (reconocimiento + síntesis) para reutilizar en
 * C4 (confirmar por voz) y C6 (fallback de audio grabado). Requiere HTTPS
 * o localhost en Chrome Android — ver plan_por_persona.md, tarea C3.
 */
export function useVoz(onResultado: (texto: string) => void): UseVozResultado {
  const [estado, setEstado] = useState<EstadoVoz>('inactivo')
  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null)

  const escuchar = useCallback(() => {
    const Ctor = obtenerConstructor()
    if (!Ctor) {
      setEstado('no_soportado')
      return
    }

    const recognition = new Ctor()
    recognition.lang = 'es-CO'
    recognition.continuous = false
    recognition.interimResults = false

    recognition.onresult = (event) => {
      const ultimo = event.results[event.results.length - 1]
      onResultado(ultimo[0].transcript)
    }
    recognition.onerror = () => setEstado('error')
    recognition.onend = () => {
      setEstado((actual) => (actual === 'escuchando' ? 'inactivo' : actual))
    }

    recognitionRef.current = recognition
    recognition.start()
    setEstado('escuchando')
  }, [onResultado])

  const detener = useCallback(() => {
    recognitionRef.current?.stop()
    setEstado('inactivo')
  }, [])

  const hablar = useCallback((texto: string) => {
    if (typeof window === 'undefined' || !window.speechSynthesis) return
    const utterance = new SpeechSynthesisUtterance(texto)
    utterance.lang = 'es-CO'
    window.speechSynthesis.speak(utterance)
  }, [])

  return { estado, escuchar, detener, hablar }
}
