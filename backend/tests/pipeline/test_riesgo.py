"""Score de riesgo histórico por artículo (Fase 2 — D6)."""

from app.pipeline.riesgo import (
    UmbralesRiesgo,
    calcular_riesgo_desde_historial,
    frecuencia_inconsistencia,
    nivel_riesgo,
)


def test_frecuencia_inconsistencia():
    assert frecuencia_inconsistencia(3, 6) == 0.5
    assert frecuencia_inconsistencia(0, 6) == 0.0
    assert frecuencia_inconsistencia(0, 0) == 0.0  # sin ciclos, no revienta


def test_dod_articulo_inconsistente_es_alto():
    # Anomalía en 4 de los últimos 6 ciclos → 0.67 → riesgo alto.
    assert nivel_riesgo(inconsistentes=4, ciclos=6) == "alto"


def test_dod_articulo_estable_es_bajo():
    # Sin anomalías históricas → bajo.
    assert nivel_riesgo(inconsistentes=0, ciclos=6) == "bajo"


def test_nivel_medio_en_banda_intermedia():
    assert nivel_riesgo(inconsistentes=2, ciclos=6) == "medio"  # 0.33
    assert nivel_riesgo(inconsistentes=1, ciclos=6) == "bajo"   # 0.167 < 0.2


def test_historia_insuficiente_es_bajo():
    # Un solo ciclo (con anomalía) no basta para marcar riesgo.
    assert nivel_riesgo(inconsistentes=1, ciclos=1) == "bajo"


def test_umbrales_configurables_por_entorno(monkeypatch):
    monkeypatch.setenv("RIESGO_ALTO", "0.9")
    cfg = UmbralesRiesgo.desde_entorno()
    # 4/6 = 0.67: con el umbral alto en 0.9 ya no es "alto", cae a "medio".
    assert nivel_riesgo(4, 6, cfg) == "medio"


def test_no_usa_sd_solo_el_patron():
    # La firma no recibe SD ni cantidad actual: sólo el conteo histórico de
    # ciclos inconsistentes. (Garantía estructural del conteo ciego histórico.)
    assert nivel_riesgo.__code__.co_argcount == 3  # inconsistentes, ciclos, umbrales


def test_calcular_desde_historial_por_articulo():
    historial = {
        100: [True, True, True, False],   # 3/4 = 0.75 → alto
        200: [False, True, False, False],  # 1/4 = 0.25 → medio
        300: [False, False, False, False],  # 0/4 → bajo
        400: [True],                        # historia insuficiente → bajo
    }
    niveles = calcular_riesgo_desde_historial(historial)
    assert niveles == {100: "alto", 200: "medio", 300: "bajo", 400: "bajo"}
