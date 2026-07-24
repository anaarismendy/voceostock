"""Parser NLU (tarea A1): dictado del operario → `ConteoParseado`.

`parse_conteo(texto, audio_bytes)` hace una sola llamada multimodal a Gemini
(texto y/o audio juntos) y luego pasa una red de seguridad determinista sobre
las unidades: aunque el modelo devuelva "arroba" o "gramos", aquí la unidad
queda en una de las 4 canónicas y la cantidad con su factor aplicado.
"""

from functools import lru_cache
from pathlib import Path

from app.pipeline.nlu.cliente import ClienteNLU
from app.pipeline.nlu.unidades import normalizar_unidad
from app.pipeline.tipos import ConteoParseado

_PROMPTS = Path(__file__).parent / "prompts"
MIME_AUDIO_DEFECTO = "audio/ogg"


@lru_cache(maxsize=8)
def cargar_prompt(version: str = "parser_v1") -> str:
    """Prompt versionado como archivo — se itera decenas de veces (A3)."""
    return (_PROMPTS / f"{version}.md").read_text("utf-8")


def _aplicar_unidad(parse: ConteoParseado) -> ConteoParseado:
    """Red de seguridad: normaliza la unidad a canónica y aplica su factor
    (arroba×12.5, gramos÷1000...) sobre la cantidad. Idempotente respecto a lo
    que ya haya hecho el modelo porque siempre parte de `unidad_texto`."""
    canonica, factor = normalizar_unidad(parse.unidad_texto)
    if canonica is not None:
        parse.unidad_normalizada = canonica
    if parse.cantidad is not None and factor != 1.0:
        parse.cantidad = round(parse.cantidad * factor, 6)
    return parse


def parse_conteo(
    texto: str | None,
    audio_bytes: bytes | None = None,
    *,
    cliente: ClienteNLU,
    mime_audio: str = MIME_AUDIO_DEFECTO,
    version_prompt: str = "parser_v1",
) -> ConteoParseado:
    """Convierte lo dicho en datos. `cliente` se inyecta (Gemini o replay)."""
    if not texto and audio_bytes is None:
        raise ValueError("parse_conteo requiere texto o audio")

    parse = cliente.parsear(
        sistema=cargar_prompt(version_prompt),
        texto=texto,
        audio_bytes=audio_bytes,
        mime_audio=mime_audio,
        esquema=ConteoParseado,
    )
    return _aplicar_unidad(parse)
