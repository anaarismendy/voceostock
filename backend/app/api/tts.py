"""POST /api/v1/tts — voz del agente vía ElevenLabs con caché en disco.

503 cuando no se puede sintetizar (sin key y miss, o API caída): el frontend
degrada a speechSynthesis del navegador — nunca silencio, nunca error visible.
"""

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from app.services import tts

router = APIRouter(prefix="/api/v1", tags=["tts"])


class TTSRequest(BaseModel):
    texto: str = Field(min_length=1, max_length=500)


@router.post("/tts")
def hablar(req: TTSRequest) -> Response:
    try:
        audio, hit = tts.sintetizar(req.texto)
    except tts.TTSNoDisponible as e:
        raise HTTPException(503, f"TTS no disponible: {e}") from e
    return Response(
        content=audio,
        media_type="audio/mpeg",
        headers={"X-TTS-Cache": "hit" if hit else "miss"},
    )
