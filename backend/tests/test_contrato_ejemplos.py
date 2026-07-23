"""Si el contrato divergiera de los ejemplos publicados, esto revienta."""

import json
from pathlib import Path

import pytest

from app.schemas.conteos import (
    ResolverRequest,
    RespuestaConfirmado,
    RespuestaNoCatalogado,
    RespuestaRequiereConfirmacion,
)

EJEMPLOS = Path(__file__).parents[2] / "docs" / "contrato" / "ejemplos"

CASOS = [
    ("confirmado.json", RespuestaConfirmado),
    ("requiere_confirmacion_anomalia.json", RespuestaRequiereConfirmacion),
    ("requiere_confirmacion_ambiguedad.json", RespuestaRequiereConfirmacion),
    ("no_catalogado.json", RespuestaNoCatalogado),
    ("resolver_request.json", ResolverRequest),
]


@pytest.mark.parametrize("nombre,schema", CASOS)
def test_ejemplo_valida_contra_contrato(nombre, schema):
    datos = json.loads((EJEMPLOS / nombre).read_text(encoding="utf-8"))
    schema.model_validate(datos)


def test_motivos_correctos():
    anomalia = json.loads((EJEMPLOS / "requiere_confirmacion_anomalia.json").read_text("utf-8"))
    ambiguedad = json.loads((EJEMPLOS / "requiere_confirmacion_ambiguedad.json").read_text("utf-8"))
    assert anomalia["motivo"] == "anomalia"
    assert ambiguedad["motivo"] == "ambiguedad"
    assert len(ambiguedad["candidatos"]) == 2
