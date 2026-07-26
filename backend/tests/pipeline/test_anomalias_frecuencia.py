"""Motor de anomalías extendido con frecuencia y comportamiento (Fase 2 — D4).

Casos nuevos de frecuencia/comportamiento; los 5 casos de A6 viven aparte en
test_anomalias.py y no se tocan. Conteo ciego: ninguna pregunta revela el SD.
"""

from app.pipeline.anomalias.reglas import (
    evaluar,
    regla_articulo_infrecuente,
    regla_recuento_repetido,
)
from app.pipeline.normalizacion import normalizar
from app.pipeline.tipos import ArticuloCtx, ConteoParseado


def _art(veces_en_sesion=0, frecuencia_historica=None, sd=47.0) -> ArticuloCtx:
    return ArticuloCtx(
        articulo_id=1, nombre="GARRAFA AZUL 20 L", nombre_normalizado=normalizar("GARRAFA AZUL 20 L"),
        unidad_base="Unidad", sd=sd,
        veces_en_sesion=veces_en_sesion, frecuencia_historica=frecuencia_historica,
    )


def _parse(cantidad=1.0, confianza=1.0) -> ConteoParseado:
    return ConteoParseado(articulo_texto="x", cantidad=cantidad, confianza=confianza)


# --- recuento repetido en sesión (frecuencia de captura) ----------------------

def test_recuento_repetido_dispara_si_ya_se_conto():
    a = regla_recuento_repetido(_parse(), _art(veces_en_sesion=1))
    assert a.flag and a.tipo == "recuento_repetido"
    assert "corrección" in a.pregunta
    assert "47" not in a.pregunta  # conteo ciego


def test_recuento_repetido_no_dispara_primera_vez():
    assert not regla_recuento_repetido(_parse(), _art(veces_en_sesion=0)).flag


def test_recuento_umbral_configurable_por_entorno(monkeypatch):
    # Subir el umbral a 2 hace que la primera repetición ya no pregunte.
    monkeypatch.setenv("UMBRAL_RECUENTO_SESION", "2")
    assert not regla_recuento_repetido(_parse(), _art(veces_en_sesion=1)).flag
    assert regla_recuento_repetido(_parse(), _art(veces_en_sesion=2)).flag


# --- artículo históricamente infrecuente (comportamiento esperado) ------------

def test_articulo_infrecuente_dispara_con_cantidad_positiva():
    a = regla_articulo_infrecuente(_parse(cantidad=5), _art(frecuencia_historica=0.03))
    assert a.flag and a.tipo == "articulo_infrecuente"
    assert "47" not in a.pregunta  # conteo ciego: no revela histórico exacto ni SD


def test_articulo_frecuente_no_dispara():
    assert not regla_articulo_infrecuente(_parse(cantidad=5), _art(frecuencia_historica=0.5)).flag


def test_infrecuente_sin_historico_no_dispara():
    # Modo offline/sin histórico: campo None → no dispara (comportamiento previo).
    assert not regla_articulo_infrecuente(_parse(cantidad=5), _art(frecuencia_historica=None)).flag


def test_infrecuente_en_cero_no_dispara():
    # Cantidad 0 lo maneja regla_cero_sospechoso; infrecuente solo aplica a >0.
    assert not regla_articulo_infrecuente(_parse(cantidad=0), _art(frecuencia_historica=0.01)).flag


# --- composición: las señales por defecto no cambian nada ---------------------

def test_evaluar_sin_senales_no_dispara_las_reglas_nuevas():
    # Cantidad normal (40 vs sd 47: sin ratio raro), sin señales → nada dispara.
    a = evaluar(_parse(cantidad=40, confianza=1.0), _art())
    assert not a.flag


def test_evaluar_dispara_recuento_repetido_en_cascada():
    a = evaluar(_parse(cantidad=40, confianza=1.0), _art(veces_en_sesion=1))
    assert a.flag and a.tipo == "recuento_repetido"
