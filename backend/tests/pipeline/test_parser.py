"""Suite de 15 casos del parser NLU (tarea A2).

`pytest -m "not integration"` corre offline contra fixtures grabadas.
`pytest -m integration` corre contra Gemini real (necesita GEMINI_API_KEY).
`pytest --record -m integration` regraba las fixtures desde Gemini real.
"""


import pytest

from app.pipeline.nlu.cliente import clave_replay
from app.pipeline.nlu.parser import parse_conteo
from app.pipeline.tipos import ConteoParseado
from tests.pipeline.conftest import DIR_FIXTURES_NLU

# (texto, cantidad esperada, unidad canónica esperada, aserciones extra)
CASOS = [
    ("cincuenta kilos de arroz", 50.0, "Kilogram", {}),
    ("medio kilo de sal", 0.5, "Kilogram", {}),
    ("kilo y medio de harina", 1.5, "Kilogram", {}),
    ("treinta y tres litros y medio de aceite", 33.5, "Liter", {}),
    ("noventa cajas de cazuelas", 90.0, "Unidad", {}),
    ("nueve, no espera, diecinueve unidades de plato blanco", 19.0, "Unidad", {"hubo_correccion": True}),
    ("una arroba de papa", 12.5, "Kilogram", {}),  # 1 arroba × 12.5
    ("tres cuartos de litro de esencia", 0.75, "Liter", {}),
    ("doscientas unidades de vaso", 200.0, "Unidad", {}),
    ("dos porciones de arroz preparado", 2.0, "Portion", {}),
    ("mmm eeh cinta pegante como catorce", 14.0, None, {}),
    ("cero unidades de caldero", 0.0, "Unidad", {}),
    ("hay harto ibuprofeno", None, None, {"ambiguo": True}),
    ("tres coma cinco litros de leche", 3.5, "Liter", {}),
    ("diez kilitos de azúcar", 10.0, "Kilogram", {}),
]

AUDIO_FIXTURE = b"VOCEOSTOCK_AUDIO_FIXTURE::cincuenta kilos de arroz"


def _verificar(parse: ConteoParseado, cantidad, unidad, extra):
    assert parse.articulo_texto  # nunca vacío
    if cantidad is None:
        assert parse.cantidad is None
    else:
        assert parse.cantidad == pytest.approx(cantidad)
    assert parse.unidad_normalizada == unidad
    if extra.get("hubo_correccion"):
        assert parse.hubo_correccion is True
    if extra.get("ambiguo"):
        assert parse.ambiguedad  # describió qué falta, no inventó cantidad
        assert parse.cantidad is None


@pytest.mark.parametrize("texto,cantidad,unidad,extra", CASOS, ids=[c[0][:30] for c in CASOS])
def test_parser_15_casos_replay(cliente_replay, texto, cantidad, unidad, extra):
    parse = parse_conteo(texto, cliente=cliente_replay)
    _verificar(parse, cantidad, unidad, extra)


def test_parser_audio_replay(cliente_replay):
    """Ruta multimodal: el audio entra como bytes en la misma llamada (A1)."""
    parse = parse_conteo(None, AUDIO_FIXTURE, cliente=cliente_replay)
    assert parse.articulo_texto == "arroz"
    assert parse.cantidad == pytest.approx(50.0)
    assert parse.unidad_normalizada == "Kilogram"


def test_parser_exige_texto_o_audio(cliente_replay):
    with pytest.raises(ValueError):
        parse_conteo(None, None, cliente=cliente_replay)


@pytest.mark.integration
@pytest.mark.parametrize("texto,cantidad,unidad,extra", CASOS, ids=[c[0][:30] for c in CASOS])
def test_parser_15_casos_gemini(cliente_gemini, modo_record, texto, cantidad, unidad, extra):
    """Contra Gemini real. Con --record, persiste la respuesta cruda a disco."""
    from app.pipeline.nlu.parser import cargar_prompt

    crudo = cliente_gemini.parsear(
        sistema=cargar_prompt(), texto=texto, audio_bytes=None,
        mime_audio="audio/ogg", esquema=ConteoParseado,
    )
    if modo_record:
        ruta = DIR_FIXTURES_NLU / f"{clave_replay(texto, None)}.json"
        ruta.write_text(crudo.model_dump_json(indent=2), encoding="utf-8")

    parse = parse_conteo(texto, cliente=cliente_gemini)
    _verificar(parse, cantidad, unidad, extra)
