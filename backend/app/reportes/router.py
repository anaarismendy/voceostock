"""Endpoints de cierre del líder (tarea A9).

Se montan bajo `/api/v1/reportes`. Se integran a la app en I3 (una línea en
`app/main.py`). El reporte de diferencias y el export leen de la BD que cargó la
Persona 2.
"""

import io
import os
from functools import lru_cache

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.reportes.consultas import filas_cierre
from app.reportes.diferencias import ReporteDiferencias, calcular_diferencias
from app.reportes.export_excel import a_bytes

router = APIRouter(prefix="/api/v1/reportes", tags=["reportes"])

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@lru_cache(maxsize=1)
def _engine():
    from sqlalchemy import create_engine

    url = os.environ.get("DATABASE_URL")
    if not url:
        raise HTTPException(status_code=503, detail="DATABASE_URL no configurada")
    return create_engine(url)


@router.get("/bodegas/{bodega_id}/diferencias", response_model=ReporteDiferencias)
def diferencias_bodega(bodega_id: int) -> ReporteDiferencias:
    nombre, filas = filas_cierre(_engine(), bodega_id)
    return calcular_diferencias(bodega_id, nombre, filas)


@router.get("/bodegas/{bodega_id}/export")
def export_bodega(bodega_id: int) -> StreamingResponse:
    nombre, filas = filas_cierre(_engine(), bodega_id)
    contenido = a_bytes({nombre: filas})
    archivo = f"cierre_bodega_{bodega_id}.xlsx"
    return StreamingResponse(
        io.BytesIO(contenido),
        media_type=XLSX_MIME,
        headers={"Content-Disposition": f'attachment; filename="{archivo}"'},
    )
