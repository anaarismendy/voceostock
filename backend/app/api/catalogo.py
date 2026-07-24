"""Endpoints de apoyo del frontend (I2): bodegas, artículos y login por PIN.

Conteo ciego: /articulos jamás incluye SD ni nada que huela a stock teórico.
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import select

from app import models
from app.db import Db

router = APIRouter(prefix="/api/v1", tags=["catalogo"])


class BodegaResumen(BaseModel):
    id: int
    nombre: str


class ArticuloResumen(BaseModel):
    articulo_id: int
    articulo_nombre: str
    unidad: str


class LoginRequest(BaseModel):
    pin: str = Field(pattern=r"^\d{4}$")


class OperarioResumen(BaseModel):
    id: str
    nombre: str


@router.get("/bodegas", response_model=list[BodegaResumen])
def listar_bodegas(s: Db) -> list[BodegaResumen]:
    filas = s.execute(select(models.Bodega.id, models.Bodega.nombre).order_by(models.Bodega.nombre)).all()
    return [BodegaResumen(id=f.id, nombre=f.nombre) for f in filas]


@router.get("/articulos", response_model=list[ArticuloResumen])
def listar_articulos(s: Db, bodega_id: int | None = None) -> list[ArticuloResumen]:
    q = select(models.Articulo.id, models.Articulo.nombre, models.Articulo.unidad_base)
    if bodega_id is not None:
        q = q.join(
            models.StockTeorico, models.StockTeorico.articulo_id == models.Articulo.id
        ).where(models.StockTeorico.bodega_id == bodega_id).distinct()
    filas = s.execute(q.order_by(models.Articulo.nombre)).all()
    return [
        ArticuloResumen(articulo_id=f.id, articulo_nombre=f.nombre, unidad=f.unidad_base or "Unidad")
        for f in filas
    ]


@router.post("/operarios/login", response_model=OperarioResumen)
def login_operario(req: LoginRequest, s: Db) -> OperarioResumen:
    # ponytail: find-or-create por PIN en texto plano — auth real (hash + roles)
    # queda fuera del alcance del hackathon; el PIN solo identifica al operario.
    operario = s.scalar(select(models.Operario).where(models.Operario.pin == req.pin))
    if operario is None:
        operario = models.Operario(nombre=f"Operario {req.pin}", pin=req.pin, rol="operario")
        s.add(operario)
        s.commit()
    return OperarioResumen(id=str(operario.id), nombre=operario.nombre)
