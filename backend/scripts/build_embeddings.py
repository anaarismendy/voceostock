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


def cargar_a_pgvector(emb: EmbedderGemini) -> None:
    """I1: los vectores de la caché van a la columna pgvector de `articulos`,
    no solo al disco — RepoDB los lee de ahí para el matching semántico."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL no configurada; no se cargó nada a pgvector")
        return
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session

    from app.models import Articulo

    with Session(create_engine(url)) as s:
        articulos = s.scalars(select(Articulo)).all()
        cargados = 0
        for a in articulos:
            vector = emb._cache.get(emb._clave(a.nombre_normalizado))
            if vector is not None:
                a.embedding = vector
                cargados += 1
        s.commit()
    print(f"pgvector: {cargados}/{len(articulos)} artículos con embedding")


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
    cargar_a_pgvector(emb)


if __name__ == "__main__":
    main()
