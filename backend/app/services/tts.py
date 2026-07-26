"""TTS con ElevenLabs y caché en disco (p2/tts).

Mismo patrón que la caché de embeddings: indexada por hash del texto (más
modelo y voz, para que cambiar la voz invalide sola la caché). Un hit se
sirve del disco sin tocar la API; solo un miss llama a ElevenLabs. La key
vive SOLO en el backend (checklist B9).

Env:
- ELEVENLABS_API_KEY   sin ella, los misses fallan (TTSNoDisponible) y el
                       frontend cae a speechSynthesis; los hits siguen.
- ELEVENLABS_VOICE_ID  configurable; default una voz multilingüe premade.
- ELEVENLABS_TIMEOUT   segundos antes de degradar (E3). Default 2.5: la
                       confirmación en vivo va <2 s, así que un ElevenLabs lento
                       debe caer RÁPIDO al fallback nativo, no bloquear. El warm
                       de caché puede subirlo por env (no es camino en vivo).
- TTS_CACHE_DIR        default data/tts_cache (los audios del guion se
                       commitean para que la demo hable sin red).
"""

import hashlib
import logging
import os
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

MODELO_TTS = "eleven_flash_v2_5"  # Flash: baja latencia, multilingüe
# Voz default: "Jessica" (premade, elegida por el equipo — el plan free de
# ElevenLabs solo permite voces premade por API; las de biblioteca dan 402).
# Para otra voz: ELEVENLABS_VOICE_ID en .env + scripts.warm_tts_cache — el
# hash de caché incluye la voz y regenera todo solo.
VOZ_DEFECTO = "cgSgspJ2msm6clMCkdW9"

RAIZ = Path(__file__).resolve().parents[3]
DIR_CACHE_DEFECTO = RAIZ / "data" / "tts_cache"

# E3: timeout corto para el camino en vivo — un ElevenLabs lento degrada rápido
# al fallback nativo en vez de bloquear la confirmación (meta de latencia <2 s).
TIMEOUT_DEFECTO = 2.5

# Contador de llamadas reales a la API (verificación: un hit no suma).
llamadas_api = 0


class TTSNoDisponible(RuntimeError):
    """Miss de caché sin API key o con la API caída: el caller degrada."""


def _dir_cache() -> Path:
    return Path(os.environ.get("TTS_CACHE_DIR", str(DIR_CACHE_DEFECTO)))


def voice_id() -> str:
    return os.environ.get("ELEVENLABS_VOICE_ID", VOZ_DEFECTO)


def _timeout() -> float:
    crudo = os.environ.get("ELEVENLABS_TIMEOUT")
    return float(crudo) if crudo else TIMEOUT_DEFECTO


def clave(texto: str) -> str:
    crudo = f"{MODELO_TTS}:{voice_id()}:{texto}"
    return hashlib.sha1(crudo.encode("utf-8")).hexdigest()


def ruta_cache(texto: str) -> Path:
    return _dir_cache() / f"{clave(texto)}.mp3"


def _llamar_elevenlabs(texto: str) -> bytes:
    global llamadas_api
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        raise TTSNoDisponible("ELEVENLABS_API_KEY no configurada")
    llamadas_api += 1
    r = httpx.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id()}",
        params={"output_format": "mp3_44100_64"},
        headers={"xi-api-key": api_key},
        json={"text": texto, "model_id": MODELO_TTS},
        timeout=_timeout(),
    )
    r.raise_for_status()
    return r.content


def sintetizar(texto: str) -> tuple[bytes, bool]:
    """(audio mp3, fue_hit). Hit → disco, 0 llamadas; miss → ElevenLabs + caché."""
    ruta = ruta_cache(texto)
    if ruta.exists():
        return ruta.read_bytes(), True
    try:
        audio = _llamar_elevenlabs(texto)
    except TTSNoDisponible:
        raise
    except Exception as e:  # red caída, cuota, 4xx: el caller degrada
        raise TTSNoDisponible(str(e)) from e
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_bytes(audio)
    logger.info("tts cacheado: %s (%d bytes)", ruta.name, len(audio))
    return audio, False
