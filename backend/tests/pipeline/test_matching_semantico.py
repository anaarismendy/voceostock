"""Casos semánticos de matching + métricas + umbral de coseno configurable
(Fase 2 — D2). No reemplaza test_matcher.py (los 4 casos A4 siguen ahí): lo
extiende con una suite etiquetada sobre datos reales y el ejemplo del DoD.
"""

from typing import ClassVar

import numpy as np

from app.pipeline.datos.repos import RepoCSV
from app.pipeline.matching.embeddings import EmbedderLexico
from app.pipeline.matching.matcher import match
from app.pipeline.matching.metricas import CasoMatch, evaluar
from app.pipeline.normalizacion import normalizar
from app.pipeline.tipos import ArticuloCtx


def _art(nombre, unidad="Unidad", sd=10.0) -> ArticuloCtx:
    return ArticuloCtx(
        articulo_id=abs(hash(nombre)) % 10**6,
        nombre=nombre, nombre_normalizado=normalizar(nombre), unidad_base=unidad, sd=sd,
    )


# --- Ejemplo textual del DoD: query parcial → nombre canónico largo -----------

CORPUS_DOD = [
    _art("ACEITE DE OLIVA EXTRA VIRGEN", "Liter"),
    _art("ACEITE DE OLIVA", "Liter"),
    _art("ACEITE DE AJONJOLI", "Liter"),
    _art("VINAGRE BALSAMICO"),
]


def test_dod_aceite_oliva_extra_resuelve_al_nombre_largo():
    r = match("aceite oliva extra", CORPUS_DOD, embedder=EmbedderLexico())
    assert r.tipo == "match"
    assert r.articulo.nombre == "ACEITE DE OLIVA EXTRA VIRGEN"


# --- Suite etiquetada sobre el catálogo real (léxico offline) -----------------

CASOS_REALES = [
    CasoMatch("harina trigo", "HARINA DE TRIGO"),
    CasoMatch("crema leche", "CREMA DE LECHE"),
    CasoMatch("leche coco", "LECHE DE COCO"),
    CasoMatch("arroz basmati", "ARROZ BASMATI"),
    CasoMatch("azucar blanca", "AZUCAR BLANCA"),
    # Query genérica que compite con "ACEITE" y la variante en bolsa: ambigüedad
    # legítima, no un match forzado.
    CasoMatch("aceite oliva", "ACEITE DE OLIVA", ambiguo=True),
    CasoMatch("destornillador estrella", None),
    CasoMatch("chocolate suizo importado zzz", None),
]


def test_suite_semantica_real_precision_total():
    cat = RepoCSV().catalogo(3)  # almacen general (566 artículos)
    res = evaluar(CASOS_REALES, cat, embedder=EmbedderLexico())
    assert res.precision == 1.0, f"fallos: {res.fallos}"


# --- El umbral de coseno afina el match (regla global: umbral en config) ------

class _EmbControlado:
    """Coseno determinista: 'garrafa' cae a 0.75 de 'bidon plastico 20 l' (lo
    que Gemini haría por sinonimia) y lejos del resto."""

    margen = 0.05
    dim = 3
    _TABLA: ClassVar[dict[str, list[float]]] = {
        "garrafa": [1.0, 0.0, 0.0],
        "bidon plastico 20 l": [0.75, 0.6614378, 0.0],  # coseno 0.75 con 'garrafa'
        "cazuela 16 onz": [0.0, 0.0, 1.0],
    }

    def __init__(self, umbral: float):
        self.umbral = umbral

    def embed(self, textos):
        filas = []
        for t in textos:
            v = np.array(self._TABLA.get(normalizar(t), [0.0, 0.0, 0.0]))
            n = np.linalg.norm(v)
            filas.append(v / n if n else v)
        return np.vstack(filas)


CORPUS_SINONIMO = [_art("BIDON PLASTICO 20 L"), _art("CAZUELA 16 ONZ")]


def test_afinar_umbral_coseno_cambia_el_resultado():
    # Con umbral laxo el sinónimo entra; subiéndolo, el mismo caso muere.
    assert match("garrafa", CORPUS_SINONIMO, embedder=_EmbControlado(0.62)).tipo == "match"
    assert match("garrafa", CORPUS_SINONIMO, embedder=_EmbControlado(0.80)).tipo == "no_catalogado"


def test_umbral_lexico_configurable_por_entorno(monkeypatch):
    monkeypatch.delenv("UMBRAL_MATCH_LEXICO", raising=False)
    assert EmbedderLexico().umbral == 0.62  # default
    monkeypatch.setenv("UMBRAL_MATCH_LEXICO", "0.75")
    assert EmbedderLexico().umbral == 0.75  # sin tocar código
    # umbral explícito sigue mandando sobre el entorno
    assert EmbedderLexico(umbral=0.5).umbral == 0.5
