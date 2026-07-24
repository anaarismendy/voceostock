"""Genera tests/fixtures/mini_stock.xlsx: reproduce cada suciedad conocida
del Excel real en 12 filas. Se regenera en cada corrida de pytest (conftest),
así el binario nunca se versiona y siempre es reproducible."""

from pathlib import Path

from openpyxl import Workbook

FIXTURE = Path(__file__).parent / "fixtures" / "mini_stock.xlsx"

BODEGAS = [
    "bodega central",
    "  bodega   central ",              # repetida con espacios distintos
    "movil fonda",
    "movil fonda suministros",          # par "X" / "X suministros"
    "kiosco parqueadero",
    "kiosco paqueadero suministros",    # typo "paqueadero" + sufijo
]

# (hoja, encabezado_cantidad, filas)
HOJAS = [
    ("STOCK BODEGA CENTRAL", "CANTIDAD", [
        (1, 100, "ACEITE", "Liter", 10.5),        # SD decimal
        (2, None, "AGUA MINI", "Unidad", 5),      # sin Nr.Artículo
        (3, 200, "AZUCAR", "Kilogram", 3),
    ]),
    ("STOCK MOVIL FONDA", "CANTIDA", [            # encabezado mal escrito
        (1, 100, "ACEITE", "Liter", 4),           # mismo Nr en dos hojas
        (2, 300, "CAFE", "Kilogram", 2),
    ]),
    ("KIOSCO PAQUEADERO SUMINISTROS", "CANTIDAD", [
        (1, 300, "CAFE", "Unidad", 7),            # unidad contradictoria
    ]),
    ("STOCK KIOSCO NUEVO AYB", "CANTIDAD", [      # hoja sin bodega en el listado
        (1, 400, "PAN", "Unidad", 8),
    ]),
]


def crear(destino: Path = FIXTURE) -> Path:
    wb = Workbook()
    hoja_bod = wb.active
    hoja_bod.title = "BODEGAS DISPONIBLES"
    hoja_bod.append([])                              # como el real: encabezado en fila 2
    hoja_bod.append([None, "CANTIDAD", "BODEGAS"])
    for i, nombre in enumerate(BODEGAS, 1):
        hoja_bod.append([None, i, nombre])

    for titulo, col_cantidad, filas in HOJAS:
        ws = wb.create_sheet(titulo)
        ws.append([col_cantidad, "Nr.Artículo", "Artículo", "Unidad", "SD"])
        for fila in filas:
            ws.append(fila)

    destino.parent.mkdir(parents=True, exist_ok=True)
    wb.save(destino)
    return destino


if __name__ == "__main__":
    print(crear())
