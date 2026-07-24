"""Endpoints de sesiones de conteo (B4).

REGLA INVIOLABLE: nada de aquí devuelve SD (conteo ciego).
"""

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import Db
from app.models import Articulo, Bodega, Conteo, Operario, SesionConteo, StockTeorico

router = APIRouter(prefix="/api/v1/sesiones", tags=["sesiones"])


class SesionRequest(BaseModel):
    bodega_id: int
    operario_id: UUID
    tipo: Literal["primario", "auditoria"]


class BodegaOut(BaseModel):
    id: int
    nombre: str


class SesionOut(BaseModel):
    sesion_id: UUID
    bodega: BodegaOut
    total_articulos: int


class FamiliaProgreso(BaseModel):
    familia: str
    contados: int
    total: int


class ProgresoOut(BaseModel):
    contados: int
    total: int
    por_familia: list[FamiliaProgreso]
    colisiones: int


def total_articulos(s: Session, bodega_id: int) -> int:
    return s.scalar(
        select(func.count(func.distinct(StockTeorico.articulo_id))).where(
            StockTeorico.bodega_id == bodega_id
        )
    ) or 0


def contados_sesion(s: Session, sesion_id: UUID) -> int:
    return s.scalar(
        select(func.count()).select_from(Conteo).where(
            Conteo.sesion_id == sesion_id, Conteo.activo.is_(True)
        )
    ) or 0


def _sesion_o_404(s: Session, sesion_id: UUID) -> SesionConteo:
    sesion = s.get(SesionConteo, sesion_id)
    if sesion is None:
        raise HTTPException(404, "sesión desconocida")
    return sesion


@router.post("", response_model=SesionOut)
async def crear_sesion(req: SesionRequest, s: Db) -> SesionOut:
    bodega = s.get(Bodega, req.bodega_id)
    if bodega is None:
        raise HTTPException(404, "bodega desconocida")
    if s.get(Operario, req.operario_id) is None:
        raise HTTPException(404, "operario desconocido")

    # Idempotencia práctica: si ya hay una sesión abierta igual, se responde esa.
    sesion = s.scalar(
        select(SesionConteo).where(
            SesionConteo.bodega_id == req.bodega_id,
            SesionConteo.operario_id == req.operario_id,
            SesionConteo.tipo == req.tipo,
            SesionConteo.estado == "abierta",
        )
    )
    if sesion is None:
        sesion = SesionConteo(
            bodega_id=req.bodega_id, operario_id=req.operario_id, tipo=req.tipo
        )
        s.add(sesion)
        s.commit()
    return SesionOut(
        sesion_id=sesion.id,
        bodega=BodegaOut(id=bodega.id, nombre=bodega.nombre),
        total_articulos=total_articulos(s, bodega.id),
    )


@router.get("/{sesion_id}/progreso", response_model=ProgresoOut)
async def progreso(sesion_id: UUID, s: Db) -> ProgresoOut:
    sesion = _sesion_o_404(s, sesion_id)
    familia = func.coalesce(Articulo.familia, "General")

    totales = dict(
        s.execute(
            select(familia, func.count(func.distinct(StockTeorico.articulo_id)))
            .join(Articulo, Articulo.id == StockTeorico.articulo_id)
            .where(StockTeorico.bodega_id == sesion.bodega_id)
            .group_by(familia)
        ).all()
    )
    contados_familia = dict(
        s.execute(
            select(familia, func.count())
            .select_from(Conteo)
            .outerjoin(Articulo, Articulo.id == Conteo.articulo_id)
            .where(Conteo.sesion_id == sesion.id, Conteo.activo.is_(True))
            .group_by(familia)
        ).all()
    )

    otras = (
        select(Conteo.articulo_id)
        .join(SesionConteo, SesionConteo.id == Conteo.sesion_id)
        .where(
            Conteo.activo.is_(True),
            Conteo.sesion_id != sesion.id,
            SesionConteo.bodega_id == sesion.bodega_id,
            SesionConteo.estado == "abierta",
            Conteo.articulo_id.is_not(None),
        )
    )
    colisiones = s.scalar(
        select(func.count(func.distinct(Conteo.articulo_id))).where(
            Conteo.sesion_id == sesion.id,
            Conteo.activo.is_(True),
            Conteo.articulo_id.in_(otras),
        )
    ) or 0

    return ProgresoOut(
        contados=contados_sesion(s, sesion.id),
        total=total_articulos(s, sesion.bodega_id),
        por_familia=[
            FamiliaProgreso(
                familia=f, contados=contados_familia.get(f, 0), total=totales.get(f, 0)
            )
            for f in sorted(set(totales) | set(contados_familia))
        ],
        colisiones=colisiones,
    )


@router.post("/{sesion_id}/cerrar")
async def cerrar_sesion(sesion_id: UUID, s: Db) -> dict:
    sesion = _sesion_o_404(s, sesion_id)
    if sesion.estado == "cerrada":
        raise HTTPException(409, "la sesión ya está cerrada")
    sesion.estado = "cerrada"
    sesion.cerrada_en = datetime.now(UTC)
    s.commit()
    return {
        "sesion_id": str(sesion.id),
        "estado": sesion.estado,
        "cerrada_en": sesion.cerrada_en.isoformat(),
    }
