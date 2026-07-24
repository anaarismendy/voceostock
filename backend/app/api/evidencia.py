"""Sirve la evidencia de audio solo con URL firmada vigente (B6)."""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.services import storage

router = APIRouter(prefix="/api/v1/evidencia", tags=["evidencia"])


@router.get("/{archivo}")
async def obtener_evidencia(archivo: str, exp: int = 0, sig: str = "") -> FileResponse:
    if Path(archivo).name != archivo:  # sin path traversal
        raise HTTPException(403, "archivo inválido")
    if not storage.firma_valida(archivo, exp, sig):
        raise HTTPException(403, "firma inválida o expirada")
    ruta = storage.directorio() / archivo
    if not ruta.is_file():
        raise HTTPException(404, "evidencia no encontrada")
    return FileResponse(ruta)
