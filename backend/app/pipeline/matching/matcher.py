"""Matching de artículo en cascada (tarea A4).

`match(texto, articulos, embedder)` recorre: exacto → fuzzy (rapidfuzz) →
embeddings (coseno) → ambigüedad → no_catalogado. La lista de artículos y el
embedder se inyectan: en CSV vienen del fixture y el embedder es léxico; en
producción vienen de la BD y el embedder es Gemini (con el vector ya calculado
en la columna pgvector). La cascada no cambia; solo cambia de dónde salen los
datos.
"""

import numpy as np
from rapidfuzz import fuzz

from app.pipeline.matching.embeddings import Embedder
from app.pipeline.normalizacion import normalizar
from app.pipeline.tipos import ArticuloCtx, ResultadoMatch

UMBRAL_FUZZY = 88.0
MARGEN_FUZZY_TOKENSET = 3.0  # si top-1 y top-2 empatan así de cerca → ambigüedad
MARGEN_FUZZY_WRATIO = 8.0
TOP_K = 3


def _no_catalogado() -> ResultadoMatch:
    return ResultadoMatch(tipo="no_catalogado", metodo="ninguno")


def _matriz_embeddings(articulos: list[ArticuloCtx], embedder: Embedder) -> np.ndarray:
    """Vectores de los candidatos: usa el embedding precalculado (pgvector) si
    su dimensión coincide con el embedder; si no, lo calcula al vuelo."""
    mat = np.zeros((len(articulos), embedder.dim))
    faltan = []
    for i, a in enumerate(articulos):
        if a.embedding is not None and len(a.embedding) == embedder.dim:
            v = np.array(a.embedding, dtype=np.float64)
            n = np.linalg.norm(v)
            mat[i] = v / n if n else v
        else:
            faltan.append(i)
    if faltan:
        calculados = embedder.embed([articulos[i].nombre_normalizado for i in faltan])
        for k, i in enumerate(faltan):
            mat[i] = calculados[k]
    return mat


def _match_embeddings(
    query: str, articulos: list[ArticuloCtx], embedder: Embedder
) -> ResultadoMatch:
    mat = _matriz_embeddings(articulos, embedder)
    q = embedder.embed([query])[0]
    cos = mat @ q
    orden = np.argsort(-cos)
    top = int(orden[0])
    top_cos = float(cos[top])

    if top_cos < embedder.umbral:
        return _no_catalogado()

    if len(orden) > 1:
        segundo_cos = float(cos[int(orden[1])])
        if top_cos - segundo_cos < embedder.margen:
            candidatos = [articulos[int(i)] for i in orden[:TOP_K] if cos[int(i)] >= embedder.umbral]
            if len(candidatos) >= 2:
                return ResultadoMatch(
                    tipo="ambiguedad", candidatos=candidatos, score=top_cos, metodo="embedding"
                )

    art = articulos[top]
    return ResultadoMatch(
        tipo="match", articulo=art, candidatos=[art], score=top_cos, metodo="embedding"
    )


def match(texto: str | None, articulos: list[ArticuloCtx], *, embedder: Embedder) -> ResultadoMatch:
    query = normalizar(texto)
    if not query or not articulos:
        return _no_catalogado()

    # (1) exacto sobre nombre normalizado
    exactos = [a for a in articulos if a.nombre_normalizado == query]
    if len(exactos) == 1:
        return ResultadoMatch(
            tipo="match", articulo=exactos[0], candidatos=exactos, score=1.0, metodo="exacto"
        )
    if len(exactos) > 1:
        return ResultadoMatch(
            tipo="ambiguedad", candidatos=exactos[:TOP_K], score=1.0, metodo="exacto"
        )

    # (2) fuzzy token_set_ratio ≥ 88, con WRatio de desempate
    puntajes = sorted(
        (
            (fuzz.token_set_ratio(query, a.nombre_normalizado),
             fuzz.WRatio(query, a.nombre_normalizado), a)
            for a in articulos
        ),
        key=lambda p: (p[0], p[1]),
        reverse=True,
    )
    top_ts, top_wr, top_a = puntajes[0]
    if top_ts >= UMBRAL_FUZZY:
        if len(puntajes) > 1:
            seg_ts, seg_wr, _ = puntajes[1]
            empate = (
                seg_ts >= UMBRAL_FUZZY
                and (top_ts - seg_ts) <= MARGEN_FUZZY_TOKENSET
                and (top_wr - seg_wr) <= MARGEN_FUZZY_WRATIO
            )
            if empate:
                candidatos = [p[2] for p in puntajes[:TOP_K] if p[0] >= UMBRAL_FUZZY]
                return ResultadoMatch(
                    tipo="ambiguedad", candidatos=candidatos, score=top_ts / 100, metodo="fuzzy"
                )
        return ResultadoMatch(
            tipo="match", articulo=top_a, candidatos=[top_a], score=top_ts / 100, metodo="fuzzy"
        )

    # (3) embeddings coseno
    return _match_embeddings(query, articulos, embedder)
