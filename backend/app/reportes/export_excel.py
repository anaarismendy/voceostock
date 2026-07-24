"""Export Excel 1:1 del insumo original (tarea A9).

Reproduce EXACTAMENTE las columnas del Excel de entrada — `CANTIDAD`,
`Nr.Artículo`, `Artículo`, `Unidad`, `SD` — una hoja por bodega, respetando el
`orden_original`, con `SD = cantidad física contada`. La prueba reina es el
round-trip: exportar → pasar por el `ingest.py` de la Persona 2 → que reconozca
las columnas y los valores. Si el formato coincide, ingesta y export hablan el
mismo idioma.
"""

import io
import re

from openpyxl import Workbook

from app.reportes.diferencias import FilaCierre

ENCABEZADOS = ["CANTIDAD", "Nr.Artículo", "Artículo", "Unidad", "SD"]
_INVALIDOS_TITULO = re.compile(r"[\\/*?:\[\]]")


def _titulo_hoja(nombre: str) -> str:
    """Excel: título ≤31 chars y sin []:*?/\\ ."""
    limpio = _INVALIDOS_TITULO.sub(" ", nombre).strip()
    return (limpio or "bodega")[:31]


def construir_libro(hojas: dict[str, list[FilaCierre]]) -> Workbook:
    """`hojas`: nombre de bodega → filas de cierre. Una hoja por bodega."""
    wb = Workbook()
    wb.remove(wb.active)  # quitar la hoja vacía por defecto
    usados: set[str] = set()
    for nombre_bodega, filas in hojas.items():
        titulo = _titulo_hoja(nombre_bodega)
        # Evitar colisión de títulos truncados a 31 chars.
        base, i = titulo, 1
        while titulo in usados:
            i += 1
            titulo = f"{base[:28]}_{i}"
        usados.add(titulo)

        ws = wb.create_sheet(title=titulo)
        ws.append(ENCABEZADOS)
        for f in sorted(filas, key=lambda x: x.orden_original):
            # CANTIDAD = consecutivo original; SD = cantidad física contada.
            ws.append([f.orden_original, f.nr_articulo, f.articulo, f.unidad, f.cantidad_fisica])
    return wb


def a_bytes(hojas: dict[str, list[FilaCierre]]) -> bytes:
    buffer = io.BytesIO()
    construir_libro(hojas).save(buffer)
    return buffer.getvalue()
