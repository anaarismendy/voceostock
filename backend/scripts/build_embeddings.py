"""Genera y cachea los embeddings del catálogo con gemini-embedding-001 (A5).

    GEMINI_API_KEY=... python -m scripts.build_embeddings

Lee los nombres de artículo de `data/fixtures/catalogo.csv`, los embebe por lotes
con reintentos y guarda la caché en `data/fixtures/embeddings.pkl` (en
.gitignore). La segunda corrida no vuelve a llamar a la API: todo sale de caché.
"""

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.pipeline.datos.repos import DIR_FIXTURES
from app.pipeline.matching.embeddings import EmbedderGemini
from app.pipeline.normalizacion import normalizar

CACHE = DIR_FIXTURES / "embeddings.pkl"


def nombres_catalogo() -> list[str]:
    import pandas as pd

    cat = pd.read_csv(DIR_FIXTURES / "catalogo.csv")
    nombres = {normalizar(n) for n in cat["articulo"].dropna()}
    return sorted(nombres)


def main() -> None:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        sys.exit("GEMINI_API_KEY no configurada")

    nombres = nombres_catalogo()
    emb = EmbedderGemini(api_key=key, ruta_cache=CACHE)
    ya = len(emb._cache)
    print(f"{len(nombres)} nombres distintos; {ya} ya en caché")

    t0 = time.perf_counter()
    emb.embed(nombres)
    dt = time.perf_counter() - t0
    print(f"caché en {CACHE} ({len(emb._cache)} vectores) — {dt:.1f}s")
    print("Vuelve a correrlo: debería tardar <5s y hacer 0 llamadas a la API.")


if __name__ == "__main__":
    main()
