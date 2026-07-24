"""Normalización de texto compartida por NLU, matching y anomalías.

Una sola definición de "normalizar" para todo el pipeline: así el nombre que
el parser entiende, el que el matcher compara y el que se cachea en embeddings
son exactamente el mismo string. Es intencional que coincida con la
normalización de `data/ingest.py` (Persona 2) — sin acoplarse a ese módulo,
que arrastra los modelos SQLAlchemy.
"""

import re
import unicodedata

_ESPACIOS = re.compile(r"\s+")


def normalizar(s: str | None) -> str:
    """trim + colapso de espacios + minúsculas + sin tildes."""
    if s is None:
        return ""
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return _ESPACIOS.sub(" ", s).strip().lower()


def tokens(s: str | None) -> list[str]:
    """Tokens alfanuméricos del texto normalizado."""
    return re.findall(r"[a-z0-9]+", normalizar(s))
