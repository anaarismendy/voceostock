"""Núcleo del pipeline de ingesta.

La firma de `procesar_conteo` está CONGELADA: la Persona 1 reemplaza solo el
cuerpo (tarea A8), nunca la firma ni los tipos de este módulo.
"""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel

Fuente = Literal["voz-tablet", "whatsapp", "manual", "rfid", "bascula"]


class PayloadConteo(BaseModel):
    """Espejo del request del contrato (docs/contrato/contrato.md)."""

    sesion_id: UUID
    bodega_id: int
    operario_id: UUID
    fuente: Fuente
    payload_texto: str | None = None
    payload_audio_b64: str | None = None


class ContextoBodega(BaseModel):
    """Contexto que el pipeline necesita de la bodega. Fase 1 lo enriquece
    (catálogo, histórico); por ahora solo identifica la bodega."""

    bodega_id: int


class Candidato(BaseModel):
    articulo_id: int
    articulo_nombre: str


class ResultadoPipeline(BaseModel):
    status: Literal["confirmado", "requiere_confirmacion", "no_catalogado"]
    articulo_id: int | None = None
    articulo_nombre: str | None = None
    cantidad: float | None = None
    unidad: str | None = None      # Unidad | Kilogram | Liter | Portion
    confianza: float | None = None
    motivo: str | None = None      # ambiguedad | anomalia | baja_confianza
    pregunta: str | None = None
    candidatos: list[Candidato] | None = None
    texto_capturado: str | None = None


async def procesar_conteo(payload: PayloadConteo,
                          contexto: ContextoBodega) -> ResultadoPipeline:
    # A8: cuerpo real detrás de la firma CONGELADA. Toda la inteligencia (parser
    # NLU, matching en cascada, motor de anomalías) vive en app.pipeline; aquí
    # solo se delega. El pipeline concreto (Gemini vs replay, BD vs CSV) lo arma
    # `servicios.get_pipeline()` según el entorno. Import perezoso para no crear
    # un ciclo con servicios, que importa los tipos de este módulo.
    import asyncio

    from app.pipeline.servicios import get_pipeline

    pipeline = get_pipeline()
    # El pipeline es síncrono (el SDK de Gemini lo es); se corre en un hilo para
    # no bloquear el event loop de FastAPI.
    return await asyncio.to_thread(pipeline.procesar, payload, contexto)
