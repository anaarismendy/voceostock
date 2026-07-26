"""Métricas de acierto/falla del matching (Fase 2 — D2).

Un evaluador reutilizable sobre un set etiquetado de casos: corre la cascada
`match()` y reporta aciertos, fallos y precisión. Sirve para (a) los tests de
regresión de calidad del matcher y (b) re-afinar el umbral de coseno con
evidencia en vez de a ojo (los umbrales viven en config/entorno).
"""

from dataclasses import dataclass, field

from app.pipeline.matching.embeddings import Embedder
from app.pipeline.matching.matcher import match
from app.pipeline.tipos import ArticuloCtx


@dataclass(frozen=True)
class CasoMatch:
    """Un caso etiquetado. `esperado`:
    - nombre de artículo  -> se espera match (o ambigüedad que lo contenga).
    - None                -> se espera no_catalogado.
    """

    query: str
    esperado: str | None
    ambiguo: bool = False  # True: se acepta 'ambiguedad' con `esperado` entre candidatos


@dataclass
class ResultadoEval:
    total: int = 0
    aciertos: int = 0
    fallos: list[tuple[str, str, str]] = field(default_factory=list)  # (query, esperado, obtenido)

    @property
    def precision(self) -> float:
        return self.aciertos / self.total if self.total else 0.0


def _obtenido(r) -> str:
    if r.tipo == "match":
        return f"match:{r.articulo.nombre}"
    if r.tipo == "ambiguedad":
        return "ambiguedad:[" + ", ".join(c.nombre for c in r.candidatos) + "]"
    return "no_catalogado"


def _acierta(caso: CasoMatch, r) -> bool:
    if caso.esperado is None:
        return r.tipo == "no_catalogado"
    if caso.ambiguo:
        return r.tipo == "ambiguedad" and any(c.nombre == caso.esperado for c in r.candidatos)
    return r.tipo == "match" and r.articulo is not None and r.articulo.nombre == caso.esperado


def evaluar(
    casos: list[CasoMatch], catalogo: list[ArticuloCtx], *, embedder: Embedder
) -> ResultadoEval:
    res = ResultadoEval(total=len(casos))
    for caso in casos:
        r = match(caso.query, catalogo, embedder=embedder)
        if _acierta(caso, r):
            res.aciertos += 1
        else:
            esperado = "no_catalogado" if caso.esperado is None else (
                ("ambiguedad~" if caso.ambiguo else "match:") + caso.esperado
            )
            res.fallos.append((caso.query, esperado, _obtenido(r)))
    return res
