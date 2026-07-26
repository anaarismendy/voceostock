"""Ciclos de conteo por bodega: "Inventario #2, del 25 al 26 de julio".

El líder los abre y los cierra; las sesiones de los operarios se enganchan al
que esté abierto. El cierre y el dashboard filtran por inventario, así que un
ciclo ya no arrastra lo contado en los anteriores.

Conteo ciego: nada de aquí devuelve SD.
"""

from datetime import UTC, date, datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models
from app.db import Db

router = APIRouter(prefix="/api/v1/inventarios", tags=["inventarios"])


class InventarioOut(BaseModel):
    id: int
    bodega_id: int
    numero: int
    estado: str
    corte_fecha: date | None
    abierto_en: datetime
    cerrado_en: datetime | None
    # Resumen del ciclo (sin SD): cuántos artículos distintos se contaron y
    # cuántos operarios participaron.
    articulos_contados: int = 0
    operarios: int = 0


class InventarioNuevo(BaseModel):
    bodega_id: int
    corte_fecha: date | None = None


def inventario_abierto(s: Session, bodega_id: int) -> models.Inventario | None:
    return s.scalar(
        select(models.Inventario).where(
            models.Inventario.bodega_id == bodega_id,
            models.Inventario.estado == "abierto",
        )
    )


def _resumen(s: Session, inventario_id: int) -> tuple[int, int]:
    fila = s.execute(
        select(
            func.count(func.distinct(models.Conteo.articulo_id)),
            func.count(func.distinct(models.SesionConteo.operario_id)),
        )
        .select_from(models.SesionConteo)
        .outerjoin(
            models.Conteo,
            (models.Conteo.sesion_id == models.SesionConteo.id)
            & (models.Conteo.activo.is_(True)),
        )
        .where(models.SesionConteo.inventario_id == inventario_id)
    ).one()
    return int(fila[0] or 0), int(fila[1] or 0)


def _a_salida(s: Session, inv: models.Inventario) -> InventarioOut:
    articulos, operarios = _resumen(s, inv.id)
    return InventarioOut(
        id=inv.id, bodega_id=inv.bodega_id, numero=inv.numero, estado=inv.estado,
        corte_fecha=inv.corte_fecha, abierto_en=inv.abierto_en, cerrado_en=inv.cerrado_en,
        articulos_contados=articulos, operarios=operarios,
    )


@router.get("", response_model=list[InventarioOut])
def listar(s: Db, bodega_id: int) -> list[InventarioOut]:
    """Los ciclos de la bodega, el más reciente primero."""
    filas = s.scalars(
        select(models.Inventario)
        .where(models.Inventario.bodega_id == bodega_id)
        .order_by(models.Inventario.numero.desc())
    ).all()
    return [_a_salida(s, f) for f in filas]


@router.post("", response_model=InventarioOut, status_code=201)
def abrir(body: InventarioNuevo, s: Db) -> InventarioOut:
    if s.get(models.Bodega, body.bodega_id) is None:
        raise HTTPException(404, "bodega desconocida")
    if inventario_abierto(s, body.bodega_id) is not None:
        raise HTTPException(409, "esta bodega ya tiene un inventario abierto; ciérralo primero")

    ultimo = s.scalar(
        select(func.max(models.Inventario.numero)).where(
            models.Inventario.bodega_id == body.bodega_id
        )
    )
    inv = models.Inventario(
        bodega_id=body.bodega_id, numero=(ultimo or 0) + 1, corte_fecha=body.corte_fecha
    )
    s.add(inv)
    try:
        s.commit()
    except IntegrityError as e:  # carrera contra otro líder abriendo a la vez
        s.rollback()
        raise HTTPException(409, "esta bodega ya tiene un inventario abierto") from e
    return _a_salida(s, inv)


@router.post("/{inventario_id}/cerrar", response_model=InventarioOut)
def cerrar(inventario_id: int, s: Db) -> InventarioOut:
    inv = s.get(models.Inventario, inventario_id)
    if inv is None:
        raise HTTPException(404, "inventario desconocido")
    if inv.estado == "cerrado":
        raise HTTPException(409, "el inventario ya está cerrado")

    ahora = datetime.now(UTC)
    inv.estado, inv.cerrado_en = "cerrado", ahora
    # Cerrar el ciclo cierra también las sesiones que quedaron abiertas: si no,
    # el operario seguiría contando contra un inventario ya cerrado.
    for sesion in s.scalars(
        select(models.SesionConteo).where(
            models.SesionConteo.inventario_id == inv.id,
            models.SesionConteo.estado != "cerrada",
        )
    ).all():
        sesion.estado, sesion.cerrada_en = "cerrada", ahora
    s.commit()
    return _a_salida(s, inv)
