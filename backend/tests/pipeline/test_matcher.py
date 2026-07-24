"""Matching en cascada (tarea A4).

Cuatro pruebas de la DoD sobre un corpus controlado (para aislar la lógica de la
cascada del ruido de los datos), más una prueba contra los datos reales del
fixture y una de integración con embeddings reales de Gemini.
"""

from typing import ClassVar

import numpy as np
import pytest

from app.pipeline.datos.repos import RepoCSV
from app.pipeline.matching.embeddings import EmbedderLexico
from app.pipeline.matching.matcher import match
from app.pipeline.normalizacion import normalizar
from app.pipeline.tipos import ArticuloCtx


def _art(nombre, unidad="Unidad", sd=10.0, articulo_id=None) -> ArticuloCtx:
    return ArticuloCtx(
        articulo_id=articulo_id if articulo_id is not None else abs(hash(nombre)) % 10**6,
        nombre=nombre, nombre_normalizado=normalizar(nombre), unidad_base=unidad, sd=sd,
    )


CORPUS = [
    _art("CAZUELA 16 ONZ"),
    _art("TAPA CAZUELA 16 ONZ"),
    _art("CALDERO RECORT TAPA 50X60 CM"),
    _art("CINTA SELLAMIENTO 48 MM X 50 MTS"),
    _art("CINTA ENMASCARAR USO GENERAL 48MMX40MTS"),
    _art("ACEITE DE OLIVA", unidad="Liter", sd=33.0),
]


class _EmbedderControlado:
    """Coseno determinista para la rama semántica: 'cinta pegante' cae cerca de
    'sellamiento' y lejos de 'enmascarar' (lo que Gemini haría por sinonimia)."""

    umbral = 0.80
    margen = 0.05
    dim = 3
    _TABLA: ClassVar[dict[str, list[float]]] = {
        "cinta pegante": [1.0, 0.0, 0.0],
        "cinta sellamiento 48 mm x 50 mts": [0.96, 0.28, 0.0],
        "cinta enmascarar uso general 48mmx40mts": [0.5, 0.87, 0.0],
    }

    def embed(self, textos):
        filas = []
        for t in textos:
            v = np.array(self._TABLA.get(normalizar(t), [0.0, 0.0, 0.0]))
            n = np.linalg.norm(v)
            filas.append(v / n if n else v)
        return np.vstack(filas)


def test_cinta_pegante_resuelve_por_semantica():
    r = match("cinta pegante", CORPUS, embedder=_EmbedderControlado())
    assert r.tipo == "match"
    assert r.metodo == "embedding"
    assert r.articulo.nombre == "CINTA SELLAMIENTO 48 MM X 50 MTS"


def test_cazuela_es_ambigua():
    r = match("cazuela", CORPUS, embedder=_EmbedderControlado())
    assert r.tipo == "ambiguedad"
    nombres = {c.nombre for c in r.candidatos}
    assert {"CAZUELA 16 ONZ", "TAPA CAZUELA 16 ONZ"} <= nombres


def test_aceite_oliva_match_unico():
    r = match("aceite oliva", CORPUS, embedder=_EmbedderControlado())
    assert r.tipo == "match"
    assert r.articulo.nombre == "ACEITE DE OLIVA"


def test_nombre_inexistente_no_catalogado():
    r = match("destornillador estrella", CORPUS, embedder=_EmbedderControlado())
    assert r.tipo == "no_catalogado"


def test_datos_reales_del_fixture():
    """El léxico offline sobre el catálogo real de 'almacen general'."""
    cat = RepoCSV().catalogo(3)
    emb = EmbedderLexico()
    assert match("cazuela", cat, embedder=emb).tipo == "ambiguedad"
    assert match("cazuelas", cat, embedder=emb).articulo.nombre == "CAZUELA 16 ONZ"
    assert match("arroz", cat, embedder=emb).articulo.nombre == "ARROZ"
    assert match("chocolate suizo importado zzz", cat, embedder=emb).tipo == "no_catalogado"


@pytest.mark.integration
def test_cinta_pegante_embeddings_reales(tmp_path):
    """Con embeddings reales, 'cinta pegante' → CINTA SELLAMIENTO por sinonimia."""
    import os

    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        pytest.skip("GEMINI_API_KEY no configurada")
    from app.pipeline.matching.embeddings import EmbedderGemini

    emb = EmbedderGemini(api_key=key, ruta_cache=tmp_path / "emb.pkl")
    r = match("cinta pegante", CORPUS, embedder=emb)
    # H11: las dos cintas del corpus quedan a <margen de coseno (0.734 vs
    # 0.725 medidos), así que la sinonimia resuelve como match o como
    # ambigüedad entre cintas — nunca no_catalogado.
    if r.tipo == "match":
        assert r.articulo.nombre == "CINTA SELLAMIENTO 48 MM X 50 MTS"
    else:
        assert r.tipo == "ambiguedad"
        assert r.candidatos[0].nombre == "CINTA SELLAMIENTO 48 MM X 50 MTS"
