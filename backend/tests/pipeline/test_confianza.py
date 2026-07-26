"""Política de confianza configurable (Fase 2 — D1).

Prueba los buckets, la validación de umbrales, el loader por entorno, y —el DoD—
que cambiar la config cambia el comportamiento de `regla_baja_confianza` sin
tocar código.
"""

import pytest

from app.pipeline.anomalias.reglas import regla_baja_confianza
from app.pipeline.confianza import (
    DEFECTO,
    UmbralesConfianza,
    clasificar,
    configurar,
    restablecer,
    umbrales_actuales,
)
from app.pipeline.config import cargar_umbrales
from app.pipeline.normalizacion import normalizar
from app.pipeline.tipos import ArticuloCtx, ConteoParseado


@pytest.fixture(autouse=True)
def _sin_fugas():
    """Cada prueba parte de los defaults y no filtra estado a las demás."""
    restablecer()
    yield
    restablecer()


def _art() -> ArticuloCtx:
    return ArticuloCtx(
        articulo_id=1, nombre="CINTA", nombre_normalizado=normalizar("CINTA"),
        unidad_base="Unidad", sd=47.0,
    )


def _parse(confianza: float) -> ConteoParseado:
    return ConteoParseado(articulo_texto="x", cantidad=1.0, confianza=confianza)


def test_clasificar_buckets_por_defecto():
    assert clasificar(0.98) == "auto"        # >= 0.95
    assert clasificar(0.95) == "auto"        # frontera inclusiva
    assert clasificar(0.92) == "rapida"      # 0.90–0.95
    assert clasificar(0.90) == "rapida"
    assert clasificar(0.80) == "aclaracion"  # 0.70–0.90
    assert clasificar(0.70) == "aclaracion"
    assert clasificar(0.60) == "candidatos"  # < 0.70


def test_clasificar_respeta_umbrales_a_medida():
    laxos = UmbralesConfianza(auto=0.99, rapida=0.60, aclaracion=0.30)
    assert clasificar(0.70, laxos) == "rapida"       # con defaults sería aclaracion
    assert clasificar(0.40, laxos) == "aclaracion"   # con defaults sería candidatos


def test_umbrales_inconsistentes_revientan():
    with pytest.raises(ValueError):
        UmbralesConfianza(auto=0.90, rapida=0.95, aclaracion=0.70)  # rapida > auto
    with pytest.raises(ValueError):
        UmbralesConfianza(auto=1.5, rapida=0.9, aclaracion=0.7)     # fuera de [0,1]


def test_dod_cambiar_config_cambia_comportamiento_sin_tocar_codigo():
    # Con los defaults (rapida=0.90), una captura al 0.85 se pregunta.
    assert umbrales_actuales() == DEFECTO
    assert regla_baja_confianza(_parse(0.85), _art()).flag is True

    # Bajar el umbral por config (lo que hará la tabla/API) y el MISMO 0.85 pasa
    # sin preguntar — sin editar la regla.
    configurar(UmbralesConfianza(auto=0.99, rapida=0.80, aclaracion=0.50))
    assert regla_baja_confianza(_parse(0.85), _art()).flag is False


def test_loader_por_entorno(monkeypatch):
    monkeypatch.delenv("UMBRAL_CONFIANZA_AUTO", raising=False)
    monkeypatch.delenv("UMBRAL_CONFIANZA_RAPIDA", raising=False)
    monkeypatch.delenv("UMBRAL_CONFIANZA_ACLARACION", raising=False)
    assert cargar_umbrales() == DEFECTO  # sin env ni BD → defaults

    monkeypatch.setenv("UMBRAL_CONFIANZA_RAPIDA", "0.85")
    assert cargar_umbrales().rapida == 0.85
