"""Clientes de NLU: el que habla con Gemini y el que reproduce respuestas
grabadas (para CI sin red y para el modo replay de la demo — tarea A10).

Ambos cumplen el protocolo `ClienteNLU`, así que el parser (A1) no sabe con
cuál está hablando. Esa indirección es lo que hace que `pytest -m "not
integration"` corra sin red y que la demo sobreviva a un wifi caído.
"""

import re
from hashlib import sha1
from pathlib import Path
from typing import Protocol, TypeVar

from pydantic import BaseModel

from app.pipeline.normalizacion import normalizar

T = TypeVar("T", bound=BaseModel)

MODELO_NLU = "gemini-2.5-flash"


class ReplayNoEncontrado(RuntimeError):
    """No hay respuesta grabada para esta entrada. Corre con --record."""

    def __init__(self, clave: str, texto: str | None):
        self.clave = clave
        super().__init__(
            f"sin fixture de replay para clave {clave!r} (texto={texto!r}). "
            f"Genera fixtures con: python -m scripts.record_parser --record"
        )


class ClienteNLU(Protocol):
    def parsear(
        self,
        sistema: str,
        texto: str | None,
        audio_bytes: bytes | None,
        mime_audio: str,
        esquema: type[T],
    ) -> T: ...


def clave_replay(texto: str | None, audio_bytes: bytes | None) -> str:
    """Nombre de archivo estable y legible para la respuesta grabada.

    Texto → slug ("cincuenta kilos de arroz" → "cincuenta-kilos-de-arroz");
    audio → "audio-<hash>" (los bytes no son legibles)."""
    if audio_bytes is not None:
        return "audio-" + sha1(audio_bytes).hexdigest()[:16]
    slug = re.sub(r"[^a-z0-9]+", "-", normalizar(texto)).strip("-")
    return slug or "vacio"


class ClienteReplay:
    """Sirve respuestas grabadas desde un directorio. Sin red."""

    def __init__(self, directorio: Path):
        self.directorio = directorio

    def parsear(self, sistema, texto, audio_bytes, mime_audio, esquema: type[T]) -> T:
        clave = clave_replay(texto, audio_bytes)
        ruta = self.directorio / f"{clave}.json"
        if not ruta.exists():
            raise ReplayNoEncontrado(clave, texto)
        return esquema.model_validate_json(ruta.read_text("utf-8"))


class ClienteGemini:
    """Cliente real contra Gemini 2.5 Flash (multimodal: texto y/o audio en la
    MISMA llamada; no hay un paso de STT separado)."""

    def __init__(self, api_key: str, modelo: str = MODELO_NLU):
        # Import perezoso: google-genai solo se necesita en modo live.
        from google import genai

        self._genai = genai
        self._cliente = genai.Client(api_key=api_key)
        self._modelo = modelo

    def parsear(self, sistema, texto, audio_bytes, mime_audio, esquema: type[T]) -> T:
        from google.genai import types

        partes: list[object] = []
        if texto:
            partes.append(texto)
        if audio_bytes is not None:
            partes.append(types.Part.from_bytes(data=audio_bytes, mime_type=mime_audio))
        if not partes:
            raise ValueError("parse_conteo requiere texto o audio")

        respuesta = self._cliente.models.generate_content(
            model=self._modelo,
            contents=partes,
            config=types.GenerateContentConfig(
                system_instruction=sistema,
                response_mime_type="application/json",
                response_schema=esquema,
                temperature=0.0,
            ),
        )
        parsed = respuesta.parsed
        if parsed is None:  # el modelo devolvió algo que no valida contra el esquema
            parsed = esquema.model_validate_json(respuesta.text)
        return parsed
