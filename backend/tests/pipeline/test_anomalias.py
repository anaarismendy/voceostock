"""Motor de anomalías: 5 reglas × 1 prueba (tarea A6), con datos reales del Excel."""

from app.pipeline.anomalias.reglas import (
    evaluar,
    regla_baja_confianza,
    regla_cero_sospechoso,
    regla_decimal_en_entero,
    regla_ratio_sd,
    regla_unidad_incoherente,
)
from app.pipeline.normalizacion import normalizar
from app.pipeline.tipos import ArticuloCtx, ConteoParseado


def _art(nombre, unidad, sd) -> ArticuloCtx:
    return ArticuloCtx(
        articulo_id=1, nombre=nombre, nombre_normalizado=normalizar(nombre),
        unidad_base=unidad, sd=sd,
    )


def _parse(**kw) -> ConteoParseado:
    base = {"articulo_texto": "x", "cantidad": 1.0, "confianza": 1.0}
    return ConteoParseado(**{**base, **kw})


def test_ratio_sd_cazuelas_90_vs_10():
    # cazuelas: SD 10 vs conteo 90 → ratio 9× → anomalía
    a = regla_ratio_sd(_parse(cantidad=90), _art("CAZUELA 16 ONZ", "Unidad", 10.0))
    assert a.flag and a.tipo == "ratio_sd"
    assert "10" not in a.pregunta  # conteo ciego: no revela el SD


def test_unidad_incoherente_gramos_en_liter():
    a = regla_unidad_incoherente(
        _parse(unidad_normalizada="Kilogram"), _art("ACEITE DE OLIVA", "Liter", 33.0)
    )
    assert a.flag and a.tipo == "unidad_incoherente"


def test_decimal_en_articulo_de_unidad_entera():
    a = regla_decimal_en_entero(_parse(cantidad=3.5), _art("CALDERO", "Unidad", 4.0))
    assert a.flag and a.tipo == "decimal_en_entero"


def test_cero_en_articulo_con_sd_alto():
    a = regla_cero_sospechoso(_parse(cantidad=0), _art("IBUPROFENO", "Unidad", 100.0))
    assert a.flag and a.tipo == "cero_sospechoso"


def test_baja_confianza_del_parser():
    a = regla_baja_confianza(_parse(confianza=0.6), _art("CINTA", "Unidad", 14.0))
    assert a.flag and a.tipo == "baja_confianza"


def test_conteo_normal_no_dispara_nada():
    a = evaluar(_parse(cantidad=33, unidad_normalizada="Liter"), _art("ACEITE DE OLIVA", "Liter", 33.0))
    assert not a.flag


def test_ratio_no_dispara_con_sd_negativo():
    # SD negativo es basura de datos; el ratio no debe inventar una anomalía.
    a = regla_ratio_sd(_parse(cantidad=50, unidad_normalizada="Kilogram"), _art("ARROZ", "Kilogram", -720.0))
    assert not a.flag
