"""Ingesta del Excel real a Postgres (Fase 1, tarea B2 — Persona 2).

Uso: python data/ingest.py [--dry-run] [ruta_excel]
Idempotente: re-ejecutar no duplica nada (upsert por claves naturales).
"""

import argparse
import os
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.models import Articulo, Bodega, StockTeorico  # noqa: E402

DEFAULT_DB = "postgresql+psycopg://voceo:voceo@localhost:5433/voceostock"
EXCEL_DEFAULT = Path(__file__).parent / "BODEGAS_Y_STOCK.xlsx"
HOJA_BODEGAS = "BODEGAS DISPONIBLES"
# Sufijos administrativos que no distinguen bodegas ("ayb"/"sumin" solo aparecen
# en nombres de hoja).
SUFIJOS = (" suministros", " piscilago", " ayb", " sumin")


def normalizar(s: str) -> str:
    """trim + colapso de espacios + minúsculas + sin tildes."""
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.lower().split())


def clave(nombre_normalizado: str) -> str:
    """Normalizado sin sufijos administrativos (se quitan repetidamente)."""
    k = nombre_normalizado
    while True:
        for suf in SUFIJOS:
            if k.endswith(suf):
                k = k[: -len(suf)].rstrip()
                break
        else:
            return k


def levenshtein(a: str, b: str) -> int:
    if len(a) < len(b):
        a, b = b, a
    fila = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        nueva = [i]
        for j, cb in enumerate(b, 1):
            nueva.append(min(fila[j] + 1, nueva[-1] + 1, fila[j - 1] + (ca != cb)))
        fila = nueva
    return fila[-1]


def _mismos_digitos(a: str, b: str) -> bool:
    return re.findall(r"\d+", a) == re.findall(r"\d+", b)


def claves_equivalentes(a: str, b: str) -> bool:
    """Iguales, o typo de ≤2 ediciones — nunca si difieren en números
    (evita fusionar "kiosco 1" con "kiosco 2")."""
    if a == b:
        return True
    return _mismos_digitos(a, b) and levenshtein(a, b) <= 2


@dataclass
class Resumen:
    bodegas_nuevas: int = 0
    bodegas_existentes: int = 0
    fusiones: list = field(default_factory=list)  # (originales, canonico)
    hojas_bodega: list = field(default_factory=list)  # (hoja, bodega)
    hojas_sin_match: list = field(default_factory=list)
    articulos_nuevos: int = 0
    articulos_existentes: int = 0
    articulos_sin_codigo: int = 0
    conflictos_unidad: list = field(default_factory=list)
    stock_nuevo: int = 0
    stock_existente: int = 0
    stock_duplicado: list = field(default_factory=list)

    @property
    def inserciones(self) -> int:
        return self.bodegas_nuevas + self.articulos_nuevos + self.stock_nuevo


def fusionar_bodegas(nombres_originales: list[str]) -> list[dict]:
    """Agrupa nombres crudos → [{canonico, claves, originales}]."""
    grupos: list[dict] = []
    for orig in nombres_originales:
        k = clave(normalizar(orig))
        for g in grupos:
            if any(claves_equivalentes(k, gk) for gk in g["claves"]):
                g["claves"].add(k)
                g["originales"].append(orig)  # con repetidos: "×2" también es fusión
                break
        else:
            grupos.append({"claves": {k}, "originales": [orig]})
    for g in grupos:
        # La clave más larga suele ser la mejor escrita ("parqueadero" > "paqueadero").
        g["canonico"] = max(g["claves"], key=len)
    return grupos


def _columnas(df: pd.DataFrame) -> dict[str, str] | None:
    """Matchea encabezados sucios por prefijo, insensible a caso/tildes."""
    cols = {}
    usadas = set()
    for logico, prefijo in [
        ("nr_articulo", "nr"),
        ("cantidad", "cantida"),  # tolera CANTIDA
        ("articulo", "articulo"),
        ("unidad", "unidad"),
        ("sd", "sd"),
    ]:
        for c in df.columns:
            if c in usadas or not isinstance(c, str):
                continue
            if normalizar(c).startswith(prefijo):
                cols[logico] = c
                usadas.add(c)
                break
    return cols if len(cols) == 5 else None


def cargar(ruta_excel: Path, engine, dry_run: bool = False) -> Resumen:
    r = Resumen()
    xl = pd.ExcelFile(ruta_excel)

    bod_df = pd.read_excel(xl, HOJA_BODEGAS, header=1)
    nombres = [str(n) for n in bod_df["BODEGAS"].dropna()]
    grupos = fusionar_bodegas(nombres)

    with Session(engine) as session:
        # --- bodegas (upsert por nombre_normalizado del canónico) ---
        registro: list[tuple[Bodega, set[str]]] = []  # (fila, claves del grupo)
        for g in grupos:
            norm = normalizar(g["canonico"])
            fila = session.scalar(select(Bodega).where(Bodega.nombre_normalizado == norm))
            aliases = sorted({o.strip() for o in g["originales"]})
            if fila is None:
                fila = Bodega(nombre=g["canonico"], nombre_normalizado=norm, alias=aliases)
                session.add(fila)
                r.bodegas_nuevas += 1
            else:
                fila.alias = sorted(set(fila.alias) | set(aliases))
                r.bodegas_existentes += 1
            if len(g["originales"]) > 1:
                r.fusiones.append((g["originales"], g["canonico"]))
            registro.append((fila, set(g["claves"])))
        session.flush()
        # Bodegas ya en BD que no vienen del listado (creadas desde hojas en
        # corridas anteriores): sin esto la segunda corrida las re-insertaría.
        ids_registradas = {b.id for b, _ in registro}
        for b in session.scalars(select(Bodega)):
            if b.id not in ids_registradas:
                registro.append((b, {clave(b.nombre_normalizado)}))

        # --- catálogo de artículos + stock por hoja ---
        arts_nr = {a.nr_articulo: a for a in session.scalars(select(Articulo)) if a.nr_articulo}
        arts_nom = {
            a.nombre_normalizado: a
            for a in session.scalars(select(Articulo))
            if a.nr_articulo is None
        }
        # ponytail: idempotencia por (bodega, articulo) sin fecha — un corte por
        # carga; cortes históricos por fecha llegan con la fase de reportes.
        stock_previo = {
            (s.bodega_id, s.articulo_id) for s in session.scalars(select(StockTeorico))
        }
        stock_run: set[tuple[int, int]] = set()

        for hoja in xl.sheet_names:
            if hoja == HOJA_BODEGAS:
                continue
            bodega = _resolver_bodega(hoja, registro, session, r)
            df = pd.read_excel(xl, hoja)
            cols = _columnas(df)
            if cols is None:
                r.hojas_sin_match.append(f"{hoja} (encabezados irreconocibles)")
                continue
            for _, row in df.iterrows():
                nombre = row[cols["articulo"]]
                if pd.isna(nombre):
                    continue
                nombre = str(nombre)
                norm = normalizar(nombre)
                nr = row[cols["nr_articulo"]]
                nr = int(nr) if pd.notna(nr) else None
                unidad = str(row[cols["unidad"]]).strip()

                art = arts_nr.get(nr) if nr is not None else arts_nom.get(norm)
                if art is None:
                    art = Articulo(
                        nr_articulo=nr, nombre=nombre.strip(), nombre_normalizado=norm,
                        unidad_base=unidad,
                    )
                    session.add(art)
                    session.flush()
                    r.articulos_nuevos += 1
                    if nr is None:
                        arts_nom[norm] = art
                        r.articulos_sin_codigo += 1
                    else:
                        arts_nr[nr] = art
                else:
                    r.articulos_existentes += 1
                    if art.unidad_base != unidad:
                        r.conflictos_unidad.append(
                            f"{art.nombre.strip()} ({hoja}): {unidad} vs {art.unidad_base} — gana {art.unidad_base}"
                        )

                pk = (bodega.id, art.id)
                if pk in stock_run:
                    r.stock_duplicado.append(
                        f"{art.nombre.strip()} repetido en {bodega.nombre!r} (hoja {hoja!r}) — se conserva el primero"
                    )
                    continue
                if pk in stock_previo:
                    r.stock_existente += 1
                    continue
                stock_run.add(pk)
                session.add(
                    StockTeorico(
                        bodega_id=bodega.id, articulo_id=art.id,
                        sd=row[cols["sd"]],
                        orden_original=int(row[cols["cantidad"]])
                        if pd.notna(row[cols["cantidad"]]) else 0,
                    )
                )
                r.stock_nuevo += 1

        if dry_run:
            session.rollback()
        else:
            session.commit()
    return r


def _resolver_bodega(hoja: str, registro, session, r: Resumen) -> Bodega:
    k = clave(normalizar(re.sub(r"^stock\s+", "", hoja, flags=re.IGNORECASE)))
    # 1) clave equivalente (igual o typo ≤2)
    candidatos = [b for b, claves in registro if any(claves_equivalentes(k, gk) for gk in claves)]
    # 2) contención única ("almacen" ⊂ "almacen general")
    if not candidatos:
        candidatos = [
            b for b, claves in registro
            if any(k in gk or gk in k for gk in claves if k and gk)
        ]
    if len(candidatos) == 1:
        bodega = candidatos[0]
    else:
        bodega = Bodega(nombre=k, nombre_normalizado=normalizar(k), alias=[hoja.strip()])
        session.add(bodega)
        session.flush()
        registro.append((bodega, {k}))
        r.bodegas_nuevas += 1
        r.hojas_sin_match.append(
            f"{hoja} ({'ambigua' if candidatos else 'sin match'}) → creada '{k}'"
        )
    r.hojas_bodega.append((hoja, bodega.nombre))
    return bodega


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("excel", nargs="?", default=EXCEL_DEFAULT, type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    engine = create_engine(os.environ.get("DATABASE_URL", DEFAULT_DB))
    r = cargar(args.excel, engine, dry_run=args.dry_run)

    print("== REPORTE DE FUSIONES DE BODEGAS ==")
    for originales, canonico in r.fusiones:
        for o in originales:
            print(f"  {o!r} → {canonico!r}")
    print("\n== MAPEO HOJA → BODEGA ==")
    for hoja, bodega in r.hojas_bodega:
        print(f"  {hoja!r} → {bodega!r}")
    if r.hojas_sin_match:
        print("\n== HOJAS SIN MATCH DE BODEGA ==")
        for h in r.hojas_sin_match:
            print(f"  {h}")
    if r.conflictos_unidad:
        print("\n== CONFLICTOS DE UNIDAD ==")
        for c in r.conflictos_unidad:
            print(f"  {c}")
    if r.stock_duplicado:
        print("\n== STOCK DUPLICADO EN LA MISMA CORRIDA ==")
        for d in r.stock_duplicado:
            print(f"  {d}")
    print("\n== RESUMEN ==")
    print(f"  bodegas: {r.bodegas_nuevas} nuevas, {r.bodegas_existentes} existentes, "
          f"{len(r.fusiones)} grupos fusionados")
    print(f"  articulos: {r.articulos_nuevos} nuevos ({r.articulos_sin_codigo} sin código), "
          f"{r.articulos_existentes} repetidos entre hojas")
    print(f"  stock: {r.stock_nuevo} filas nuevas, {r.stock_existente} ya existentes")
    print(f"  conflictos de unidad: {len(r.conflictos_unidad)}")
    print(f"  TOTAL inserciones nuevas: {r.inserciones}"
          + (" (dry-run: nada se escribió)" if args.dry_run else ""))


if __name__ == "__main__":
    main()
