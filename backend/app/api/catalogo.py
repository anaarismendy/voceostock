"""Endpoints de apoyo del frontend (I2): bodegas, artículos y login por PIN.

Conteo ciego: /articulos jamás incluye SD ni nada que huela a stock teórico.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from app import models
from app.db import Db

router = APIRouter(prefix="/api/v1", tags=["catalogo"])


class BodegaResumen(BaseModel):
    id: int
    nombre: str
    # Rediseño (pantalla B): la tarjeta muestra tamaño y estado de la bodega.
    total_articulos: int = 0
    en_conteo: bool = False


class ArticuloResumen(BaseModel):
    articulo_id: int
    articulo_nombre: str
    unidad: str
    # E5: nivel de riesgo histórico (alto/medio/bajo) en el MISMO payload del
    # catálogo → el frontend lo tiene offline sin request extra. None = sin dato.
    riesgo: str | None = None


class LoginRequest(BaseModel):
    pin: str = Field(pattern=r"^\d{4}$")


class OperarioResumen(BaseModel):
    id: str
    nombre: str
    rol: str  # lo decide el backend, no el cliente: define a qué panel entra


@router.get("/bodegas", response_model=list[BodegaResumen])
def listar_bodegas(s: Db) -> list[BodegaResumen]:
    from sqlalchemy import func

    filas = s.execute(select(models.Bodega.id, models.Bodega.nombre).order_by(models.Bodega.nombre)).all()
    conteo_articulos = dict(
        s.execute(
            select(models.StockTeorico.bodega_id, func.count(func.distinct(models.StockTeorico.articulo_id)))
            .group_by(models.StockTeorico.bodega_id)
        ).all()
    )
    abiertas = {
        b
        for (b,) in s.execute(
            select(models.SesionConteo.bodega_id)
            .where(models.SesionConteo.estado == "abierta")
            .distinct()
        ).all()
    }
    return [
        BodegaResumen(
            id=f.id, nombre=f.nombre,
            total_articulos=conteo_articulos.get(f.id, 0),
            en_conteo=f.id in abiertas,
        )
        for f in filas
    ]


@router.get("/articulos", response_model=list[ArticuloResumen])
def listar_articulos(s: Db, bodega_id: int | None = None) -> list[ArticuloResumen]:
    # E5: outerjoin al riesgo global (sede_id NULL) para traerlo en el mismo payload.
    q = (
        select(
            models.Articulo.id,
            models.Articulo.nombre,
            models.Articulo.unidad_base,
            models.RiesgoArticulo.nivel,
        )
        .outerjoin(
            models.RiesgoArticulo,
            (models.RiesgoArticulo.articulo_id == models.Articulo.id)
            & (models.RiesgoArticulo.sede_id.is_(None)),
        )
    )
    if bodega_id is not None:
        q = q.join(
            models.StockTeorico, models.StockTeorico.articulo_id == models.Articulo.id
        ).where(models.StockTeorico.bodega_id == bodega_id).distinct()
    filas = s.execute(q.order_by(models.Articulo.nombre)).all()
    return [
        ArticuloResumen(
            articulo_id=f.id,
            articulo_nombre=f.nombre,
            unidad=f.unidad_base or "Unidad",
            riesgo=f.nivel,
        )
        for f in filas
    ]


@router.post("/operarios/login", response_model=OperarioResumen)
def login_operario(req: LoginRequest, s: Db) -> OperarioResumen:
    """El PIN identifica a un operario YA registrado. Antes esto hacía
    find-or-create: un dígito mal tecleado no fallaba, creaba un operario nuevo
    y el de verdad perdía su historial de precisión (D5). Ahora el alta la hace
    el líder desde su panel; aquí solo se entra."""
    operario = s.scalar(select(models.Operario).where(models.Operario.pin == req.pin))
    if operario is None:
        raise HTTPException(404, "PIN no registrado. Pídele a tu líder que te dé de alta.")
    return OperarioResumen(
        id=str(operario.id), nombre=operario.nombre, rol=operario.rol or "operario"
    )
