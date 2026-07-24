"""Puebla `articulos.familia` con la primera palabra significativa del nombre.

HEURÍSTICA, no taxonomía: "ACEITE DE OLIVA"→ACEITE, "TAPA CAZUELA 16 ONZ"→TAPA,
"ARROZ BASMATI"→ARROZ. Suficiente para agrupar la barra de progreso por
familia (C8); una clasificación real vendría del ERP, no de un split().

Rerunnable (idempotente): pisa siempre familia con la heurística.
    DATABASE_URL=... uv run python -m scripts.populate_familia
La migración alembic 0003 aplica esta misma función a BDs ya migradas.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Palabras que no distinguen familias: artículos, preposiciones y la "x" de
# las medidas (50X60). Los números tampoco (16 ONZ no es una familia).
STOPWORDS = {"de", "del", "la", "el", "en", "con", "para", "x", "y", "los", "las"}


def familia_de(nombre_normalizado: str) -> str:
    for token in nombre_normalizado.split():
        if token in STOPWORDS or token.isdigit():
            continue
        return token.upper()
    return "GENERAL"


def poblar(engine) -> int:
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from app.models import Articulo

    with Session(engine) as s:
        articulos = s.scalars(select(Articulo)).all()
        for a in articulos:
            a.familia = familia_de(a.nombre_normalizado)
        s.commit()
        return len(articulos)


def main() -> None:
    from sqlalchemy import create_engine

    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("DATABASE_URL no configurada")
    n = poblar(create_engine(url))
    print(f"familia poblada en {n} artículos")


if __name__ == "__main__":
    main()
