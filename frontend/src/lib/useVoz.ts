import { useCallback, useRef, useState } from 'react'
import { blobABase64 } from './audioBase64'

export type EstadoVoz = 'inactivo' | 'escuchando' | 'no_soportado' | 'error' | 'grabando'

interface UseVozResultado {
  estado: EstadoVoz
  /** true cuando toca ofrecer la ruta B (C6): sin soporte de Web Speech, o 2 fallos seguidos. */
  usarAudio: boolean
  escuchar: () => void
  detener: () => void
  hablar: (texto: string) => void
  grabarAudio: () => void
  detenerGrabacion: () => void
}

const FALLOS_PARA_RUTA_B = 2

function obtenerConstructor(): (new () => SpeechRecognitionInstance) | null {
  if (typeof window === 'undefined') return null
  return window.SpeechRecognition ?? window.webkitSpeechRecognition ?? null
}

function elegirMimeType(): string | undefined {
  if (typeof MediaRecorder === 'undefined') return undefined
  return MediaRecorder.isTypeSupported('audio/webm;codecs=opus') ? 'audio/webm;codecs=opus' : undefined
}

/**
 * Encapsula la entrada de voz: reconocimiento + síntesis (C3/C4) y, cuando
 * Web Speech no está disponible o falla 2 veces seguidas, la ruta B de C6
 * (grabar con MediaRecorder y mandar el audio en vez de texto).
 */
export function useVoz(
  onResultado: (texto: string) => void,
  onAudioListo: (audioBase64: string) => void = () => {},
): UseVozResultado {
  const [estado, setEstado] = useState<EstadoVoz>('inactivo')
  const [fallosSeguidos, setFallosSeguidos] = useState(0)
  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null)
  const recorderRef = useRef<MediaRecorder | null>(null)
  const streamRef = useRef<MediaStream | null>(null)

  const usarAudio = !obtenerConstructor() || fallosSeguidos >= FALLOS_PARA_RUTA_B

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
      setFallosSeguidos(0)
      const ultimo = event.results[event.results.length - 1]
      onResultado(ultimo[0].transcript)
    }
    recognition.onerror = () => {
      setFallosSeguidos((f) => f + 1)
      setEstado('error')
    }
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

  const grabarAudio = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mimeType = elegirMimeType()
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined)
      const chunks: BlobPart[] = []

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunks.push(e.data)
      }
      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop())
        streamRef.current = null
        const blob = new Blob(chunks, { type: recorder.mimeType || 'audio/webm' })
        const base64 = await blobABase64(blob)
        setEstado('inactivo')
        onAudioListo(base64)
      }

      streamRef.current = stream
      recorderRef.current = recorder
      recorder.start()
      setEstado('grabando')
    } catch {
      setEstado('error')
    }
  }, [onAudioListo])

  const detenerGrabacion = useCallback(() => {
    recorderRef.current?.stop()
  }, [])

  return { estado, usarAudio, escuchar, detener, hablar, grabarAudio, detenerGrabacion }
}
