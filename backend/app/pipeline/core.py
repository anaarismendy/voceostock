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
    # STUB determinista — P1 lo reemplaza en la tarea A8 sin cambiar la firma.
    texto = (payload.payload_texto or "").lower()

    if texto:
        if "noventa" in texto:
            # La anomalía SIEMPRE trae lo que el pipeline ya determinó antes
            # de preguntar: /resolver "si" persiste exactamente estos valores.
            return ResultadoPipeline(
                status="requiere_confirmacion",
                motivo="anomalia",
                pregunta="¿Confirmas 90? El corte anterior registró 10.",
                articulo_id=1,
                articulo_nombre="CAZUELA 16 ONZ",
                cantidad=90,
                unidad="Unidad",
            )
        if "cazuela" in texto:
            return ResultadoPipeline(
                status="requiere_confirmacion",
                motivo="ambiguedad",
                pregunta="¿Cuál artículo es?",
                candidatos=[
                    Candidato(articulo_id=1, articulo_nombre="CAZUELA 16 ONZ"),
                    Candidato(articulo_id=2, articulo_nombre="CALDERO RECORT TAPA 50X60 CM"),
                ],
            )
        if "xyz" in texto:
            return ResultadoPipeline(
                status="no_catalogado",
                texto_capturado=payload.payload_texto,
                cantidad=4,
                unidad="Unidad",
            )

    # Cualquier otro texto, o cualquier audio → confirmado con datos plausibles.
    return ResultadoPipeline(
        status="confirmado",
        articulo_id=7290,
        articulo_nombre="ACEITE DE OLIVA",
        cantidad=33.5,
        unidad="Liter",
        confianza=0.95,
    )
