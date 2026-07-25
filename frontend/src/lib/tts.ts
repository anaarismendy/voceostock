/** Voz del agente vía backend (ElevenLabs + caché en disco). El caller decide
 * el fallback: si esto rechaza (red caída, 503 sin caché), se usa
 * speechSynthesis del navegador — nunca silencio. */
export async function reproducirTTSBackend(texto: string): Promise<void> {
  const r = await fetch('/api/v1/tts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ texto }),
  })
  if (!r.ok) throw new Error(`TTS ${r.status}`)
  const url = URL.createObjectURL(await r.blob())
  const audio = new Audio(url)
  audio.onended = () => URL.revokeObjectURL(url)
  await audio.play()
}
