"""Genera data/fixtures/{catalogo,bodegas}.csv desde data/BODEGAS_Y_STOCK.xlsx.

Sin limpieza deliberada: espacios, duplicados y Nr.Artículo vacíos se
conservan — la limpieza es de la Fase 1 (data/ingest.py).
"""

from pathlib import Path

import pandas as pd

BASE = Path(__file__).parent
FIXTURES = BASE / "fixtures"
HOJA_BODEGAS = "BODEGAS DISPONIBLES"

xl = pd.ExcelFile(BASE / "BODEGAS_Y_STOCK.xlsx")

# La hoja de bodegas trae el encabezado real en la segunda fila.
bodegas = pd.read_excel(xl, HOJA_BODEGAS, header=1, usecols=["CANTIDAD", "BODEGAS"])
bodegas = bodegas.rename(columns={"CANTIDAD": "id", "BODEGAS": "nombre"})
bodegas.to_csv(FIXTURES / "bodegas.csv", index=False)

frames = []
for hoja in xl.sheet_names:
    if hoja == HOJA_BODEGAS:
        continue
    df = pd.read_excel(xl, hoja)
    # Una hoja trae "CANTIDA" en vez de "CANTIDAD"; el consecutivo no se exporta.
    df = df.rename(
        columns={"Nr.Artículo": "nr_articulo", "Artículo": "articulo", "Unidad": "unidad", "SD": "sd"}
    )
    df["bodega"] = hoja
    if df["nr_articulo"].dtype.kind == "f":
        # Evita el ".0" que pandas agrega cuando la columna trae vacíos; no es limpieza.
        df["nr_articulo"] = df["nr_articulo"].astype("Int64")
    frames.append(df[["bodega", "nr_articulo", "articulo", "unidad", "sd"]])

catalogo = pd.concat(frames, ignore_index=True)
catalogo.to_csv(FIXTURES / "catalogo.csv", index=False)

print(f"catalogo.csv: {len(catalogo)} filas | bodegas.csv: {len(bodegas)} filas")
