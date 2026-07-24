"""Evidencia de audio en disco local + URLs firmadas HMAC (B6).

ponytail: filesystem local basta para la demo; S3/GCS si algún día hay
más de un nodo de API.
"""

import hashlib
import hmac
import os
import time
import uuid
from pathlib import Path

_EXT = {"audio/webm": ".webm", "audio/ogg": ".ogg", "audio/mpeg": ".mp3", "audio/wav": ".wav"}


def directorio() -> Path:
    d = Path(os.environ.get("STORAGE_DIR", "storage"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _clave() -> bytes:
    return os.environ.get("SECRET_KEY", "dev-secret-cambiame").encode()


def guardar_audio(datos: bytes, mime: str | None = None) -> str:
    """Guarda el audio decodificado y devuelve el nombre de archivo."""
    archivo = f"{uuid.uuid4()}{_EXT.get(mime, '.webm')}"
    (directorio() / archivo).write_bytes(datos)
    return archivo


def _firmar(archivo: str, exp: int) -> str:
    return hmac.new(_clave(), f"{archivo}:{exp}".encode(), hashlib.sha256).hexdigest()


def url_firmada(archivo: str, minutos: int = 60) -> str:
    exp = int(time.time()) + minutos * 60
    return f"/api/v1/evidencia/{archivo}?exp={exp}&sig={_firmar(archivo, exp)}"


def firma_valida(archivo: str, exp: int, sig: str) -> bool:
    return exp > time.time() and hmac.compare_digest(_firmar(archivo, exp), sig)
