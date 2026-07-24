"""WebSocket de eventos por bodega (B7).

Pub/sub en memoria: dict {bodega_id: set[WebSocket]} con lock asyncio.
ponytail: un solo proceso de API en la demo; Redis pub/sub si algún día
hay varios workers.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["ws"])

_salas: dict[int, set[WebSocket]] = {}
_lock = asyncio.Lock()


async def emitir(
    bodega_id: int,
    tipo: str,
    sesion_id: UUID | str,
    operario_id: UUID | str | None,
    fuente: str | None,
    data: dict[str, Any],
) -> None:
    """Envía un evento a todos los suscriptores de la bodega. Nunca lanza."""
    evento = {
        "tipo": tipo,
        "sesion_id": str(sesion_id),
        "operario_id": str(operario_id) if operario_id else None,
        "fuente": fuente,
        "data": data,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    async with _lock:
        sockets = list(_salas.get(bodega_id, ()))
    for ws in sockets:
        try:
            await ws.send_json(evento)
        except Exception:  # noqa: BLE001 — socket muerto: su handler lo saca de la sala
            pass


@router.websocket("/ws/bodegas/{bodega_id}")
async def ws_bodega(ws: WebSocket, bodega_id: int) -> None:
    await ws.accept()
    async with _lock:
        _salas.setdefault(bodega_id, set()).add(ws)
    try:
        while True:  # solo escuchamos; el cliente no manda nada útil
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        async with _lock:
            _salas.get(bodega_id, set()).discard(ws)
