"""Contrato CONGELADO del API de conteos.

Cambiar cualquier schema de este archivo requiere acuerdo de las 3 personas.
REGLA INVIOLABLE: ninguna respuesta incluye jamás el stock teórico (SD).
"""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel

Fuente = Literal["voz-tablet", "whatsapp", "manual", "rfid", "bascula"]
UnidadCanonica = Literal["Unidad", "Kilogram", "Liter", "Portion"]
Motivo = Literal["ambiguedad", "anomalia", "baja_confianza"]


class ConteoRequest(BaseModel):
    sesion_id: UUID
    bodega_id: int
    operario_id: UUID
    fuente: Fuente
    payload_texto: str | None = None
    payload_audio_b64: str | None = None


class Candidato(BaseModel):
    articulo_id: int
    articulo_nombre: str


class Conteo(BaseModel):
    id: UUID
    articulo_id: int
    articulo_nombre: str
    cantidad: float
    unidad: UnidadCanonica
    confianza: float
    fuente: Fuente
    evidencia_url: str | None = None


class RespuestaConfirmado(BaseModel):
    status: Literal["confirmado"] = "confirmado"
    conteo: Conteo


class RespuestaRequiereConfirmacion(BaseModel):
    status: Literal["requiere_confirmacion"] = "requiere_confirmacion"
    token_pendiente: UUID
    motivo: Motivo
    pregunta: str
    candidatos: list[Candidato] | None = None


class RespuestaNoCatalogado(BaseModel):
    status: Literal["no_catalogado"] = "no_catalogado"
    texto_capturado: str
    cantidad: float | None = None
    unidad: str | None = None


RespuestaConteo = RespuestaConfirmado | RespuestaRequiereConfirmacion | RespuestaNoCatalogado


class ResolverRequest(BaseModel):
    # "si" | "no" | "articulo_id:<int>" | "cantidad:<float>"
    respuesta: str


class RespuestaDescartado(BaseModel):
    """Cuarto estado SOLO como respuesta de POST /conteos/{token}/resolver
    (respuesta "no"). POST /conteos no cambia — acordado, ver contrato.md."""

    status: Literal["descartado"] = "descartado"


RespuestaResolver = RespuestaConteo | RespuestaDescartado
