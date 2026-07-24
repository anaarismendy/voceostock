"""Origen de datos del catálogo, tras un protocolo (tareas A4 y A8).

`RepoCatalogo` es la interfaz que el pipeline consume. Dos implementaciones:
- `RepoCSV`: lee los fixtures de `data/fixtures/` con pandas. Es contra lo que
  la Persona 1 trabaja sin depender de BD ni de nadie (tareas A1–A7).
- `RepoDB`: lee de Postgres (stock_teorico ⋈ articulos) con el embedding ya en
  pgvector. Es lo que usa el pipeline real en producción (tarea A8).

Migrar de CSV a BD es cambiar de implementación, no reescribir la cascada: esa
es toda la gracia del protocolo.
"""

from pathlib import Path
from typing import Protocol

from app.pipeline.normalizacion import normalizar
from app.pipeline.tipos import ArticuloCtx

RAIZ = Path(__file__).resolve().parents[4]
DIR_FIXTURES = RAIZ / "data" / "fixtures"

# Sufijos administrativos que no distinguen bodegas (igual criterio que ingest).
_SUFIJOS = (" suministros", " piscilago", " ayb", " sumin", " sumi")


class RepoCatalogo(Protocol):
    def nombre_bodega(self, bodega_id: int) -> str | None: ...
    def catalogo(self, bodega_id: int) -> list[ArticuloCtx]: ...


def _clave_bodega(nombre: str) -> str:
    """Nombre normalizado sin prefijo 'stock' ni sufijos administrativos."""
    k = normalizar(nombre)
    k = k.removeprefix("stock ")
    cambiando = True
    while cambiando:
        cambiando = False
        for suf in _SUFIJOS:
            if k.endswith(suf):
                k = k[: -len(suf)].strip()
                cambiando = True
    return k


def _mismos_digitos(a: str, b: str) -> bool:
    import re

    return re.findall(r"\d+", a) == re.findall(r"\d+", b)


def _equivalentes(a: str, b: str) -> bool:
    """Iguales, o uno contenido en el otro — nunca si difieren en números
    (evita fusionar 'kiosco 1' con 'kiosco 2')."""
    if not a or not b or not _mismos_digitos(a, b):
        return False
    return a == b or a in b or b in a


class RepoCSV:
    """Catálogo desde los CSV de fixtures. `catalogo.csv` viene indexado por el
    nombre de hoja del Excel; este repo mapea esos nombres a las bodegas del
    listado (bodegas.csv) con el mismo criterio de fusión que la ingesta."""

    def __init__(self, dir_fixtures: Path = DIR_FIXTURES):
        import pandas as pd

        self._pd = pd
        self._cat = pd.read_csv(dir_fixtures / "catalogo.csv")
        self._bodegas = pd.read_csv(dir_fixtures / "bodegas.csv")
        self._cat["_bodega_clave"] = self._cat["bodega"].map(_clave_bodega)
        # id artificial estable por artículo (los fixtures no traen id de BD).
        self._cat = self._cat.reset_index(drop=True)

    def nombre_bodega(self, bodega_id: int) -> str | None:
        fila = self._bodegas.loc[self._bodegas["id"] == bodega_id]
        return None if fila.empty else str(fila.iloc[0]["nombre"]).strip()

    def _hojas_de(self, nombre: str) -> list[str]:
        objetivo = _clave_bodega(nombre)
        hojas = [
            c for c in self._cat["_bodega_clave"].unique() if _equivalentes(objetivo, c)
        ]
        return hojas

    @staticmethod
    def _nr_a_int(valor) -> int | None:
        try:
            return int(valor)
        except (ValueError, TypeError):
            return None  # filas basura tipo "TOTAL  ARTICULO 297"

    def _a_articulo(self, fila) -> ArticuloCtx:
        pd = self._pd
        nr = self._nr_a_int(fila["nr_articulo"]) if pd.notna(fila["nr_articulo"]) else None
        nombre = str(fila["articulo"]).strip()
        unidad = fila["unidad"]
        unidad = str(unidad).strip() if pd.notna(unidad) else ""
        sd = float(fila["sd"]) if pd.notna(fila["sd"]) else 0.0
        # id: código real si existe; si no, surrogate estable por índice de fila.
        articulo_id = nr if nr is not None else 1_000_000 + int(fila.name)
        return ArticuloCtx(
            articulo_id=articulo_id,
            nr_articulo=nr,
            nombre=nombre,
            nombre_normalizado=normalizar(nombre),
            unidad_base=unidad,
            sd=sd,
            factor_empaque=None,
            embedding=None,
        )

    def catalogo_por_nombre(self, nombre: str) -> list[ArticuloCtx]:
        hojas = self._hojas_de(nombre)
        sub = self._cat[self._cat["_bodega_clave"].isin(hojas)]
        arts: dict[str, ArticuloCtx] = {}
        for _, fila in sub.iterrows():
            if self._pd.isna(fila["articulo"]):
                continue  # filas de total o vacías del Excel sucio
            a = self._a_articulo(fila)
            clave = str(a.nr_articulo) if a.nr_articulo is not None else a.nombre_normalizado
            arts.setdefault(clave, a)  # dedup entre hojas; se conserva el primero
        return list(arts.values())

    def catalogo(self, bodega_id: int) -> list[ArticuloCtx]:
        nombre = self.nombre_bodega(bodega_id)
        return self.catalogo_por_nombre(nombre) if nombre else []


class RepoDB:
    """Catálogo desde Postgres (tarea A8). Import perezoso de los modelos para no
    arrastrar SQLAlchemy/pgvector cuando se trabaja en modo CSV."""

    def __init__(self, engine):
        self._engine = engine

    def nombre_bodega(self, bodega_id: int) -> str | None:
        from sqlalchemy import select
        from sqlalchemy.orm import Session

        from app.models import Bodega

        with Session(self._engine) as s:
            return s.scalar(select(Bodega.nombre).where(Bodega.id == bodega_id))

    def catalogo(self, bodega_id: int) -> list[ArticuloCtx]:
        from sqlalchemy import select
        from sqlalchemy.orm import Session

        from app.models import Articulo, StockTeorico

        with Session(self._engine) as s:
            filas = s.execute(
                select(
                    Articulo.id, Articulo.nr_articulo, Articulo.nombre,
                    Articulo.nombre_normalizado, Articulo.unidad_base,
                    Articulo.factor_empaque, Articulo.embedding, StockTeorico.sd,
                )
                .join(StockTeorico, StockTeorico.articulo_id == Articulo.id)
                .where(StockTeorico.bodega_id == bodega_id)
                .order_by(StockTeorico.corte_fecha.desc())  # corte más reciente primero
            ).all()

        catalogo: list[ArticuloCtx] = []
        vistos: set[int] = set()
        for f in filas:
            if f.id in vistos:  # un solo corte por artículo (el más reciente)
                continue
            vistos.add(f.id)
            emb = list(f.embedding) if f.embedding is not None else None
            catalogo.append(
                ArticuloCtx(
                    articulo_id=f.id,
                    nr_articulo=f.nr_articulo,
                    nombre=f.nombre,
                    nombre_normalizado=f.nombre_normalizado,
                    unidad_base=f.unidad_base,
                    sd=float(f.sd),
                    factor_empaque=float(f.factor_empaque) if f.factor_empaque is not None else None,
                    embedding=emb,
                )
            )
        return catalogo
