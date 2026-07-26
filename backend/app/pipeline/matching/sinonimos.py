"""Resolución de sinónimos por sede (Fase 2 — D3).

El matching consulta esta capa ANTES de la cascada general: si el texto dictado
coincide (normalizado) con un sinónimo registrado para la sede de la bodega
actual, resuelve directo a ese artículo. Los sinónimos son una capa aparte;
NUNCA modifican el catálogo oficial (`articulos`).
"""

from app.pipeline.normalizacion import normalizar


def resolver_sinonimo(texto: str | None, mapa: dict[str, int]) -> int | None:
    """`mapa`: {texto_normalizado -> articulo_id} de la sede de la bodega.
    Devuelve el articulo_id si hay sinónimo, o None para caer a la cascada."""
    if not texto or not mapa:
        return None
    return mapa.get(normalizar(texto))
