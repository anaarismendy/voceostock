"""Módulo por operario: visibilidad y control del ajuste de confianza (D5).

El líder ve, por operario, cuántas capturas lleva, qué precisión histórica tiene
y cuánto le está subiendo o bajando la confianza el sistema — es decir, quién
recibe más confirmaciones y por qué. `recalcular` dispara el job de la capa E.

No expone SD ni cantidades: solo métricas de proceso (conteo ciego intacto).
"""

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app import models
from app.db import Db, engine
from app.pipeline.perfil import AjusteConfianza, PerfilOperario, ajustar_confianza
from app.services.operarios import recalcular_estadisticas

router = APIRouter(prefix="/api/v1/operarios", tags=["operarios"])

# Punto medio para medir el ajuste sin que el clamp a [0,1] lo recorte.
_SONDA = 0.5


class OperarioStats(BaseModel):
    id: uuid.UUID
    nombre: str
    rol: str | None
    capturas_totales: int
    capturas_correctas: int
    precision: float | None  # None mientras no haya ninguna captura
    ajuste: float  # delta aplicado a la confianza de cada captura (+/-)
    perfil_activo: bool  # False si aún no llega al mínimo de muestras


def _listar(s) -> list[OperarioStats]:
    cfg = AjusteConfianza.desde_entorno()
    filas = s.execute(
        select(models.Operario, models.EstadisticaOperario)
        .outerjoin(
            models.EstadisticaOperario,
            models.EstadisticaOperario.operario_id == models.Operario.id,
        )
        .order_by(models.Operario.nombre)
    ).all()

    salida = []
    for op, stats in filas:
        totales = stats.capturas_totales if stats else 0
        correctas = stats.capturas_correctas if stats else 0
        perfil = (
            PerfilOperario(str(op.id), correctas / totales, totales) if totales else None
        )
        salida.append(
            OperarioStats(
                id=op.id,
                nombre=op.nombre,
                rol=op.rol,
                capturas_totales=totales,
                capturas_correctas=correctas,
                precision=correctas / totales if totales else None,
                ajuste=ajustar_confianza(_SONDA, perfil, cfg) - _SONDA,
                perfil_activo=totales >= cfg.minimo_muestras,
            )
        )
    return salida


@router.get("", response_model=list[OperarioStats])
def listar_operarios(s: Db) -> list[OperarioStats]:
    return _listar(s)


@router.post("/recalcular", response_model=list[OperarioStats])
def recalcular(s: Db) -> list[OperarioStats]:
    """Reconstruye las estadísticas desde `conteos` y devuelve la lista al día.
    El cierre de sesión ya lo hace solo; esto es el botón manual del líder."""
    recalcular_estadisticas(engine)
    s.expire_all()  # la sesión del request no vio el commit del job
    return _listar(s)


ROLES = "^(operario|auditor|lider)$"  # mismo conjunto que ck_operarios_rol


class OperarioNuevo(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)
    pin: str = Field(pattern=r"^\d{4}$")
    rol: str = Field(default="operario", pattern=ROLES)


class OperarioEdicion(BaseModel):
    """Todo opcional: el líder cambia solo lo que toca (p. ej. reasignar el PIN)."""

    nombre: str | None = Field(default=None, min_length=1, max_length=80)
    pin: str | None = Field(default=None, pattern=r"^\d{4}$")
    rol: str | None = Field(default=None, pattern=ROLES)


def _uno(s, operario_id: uuid.UUID) -> OperarioStats:
    fila = next((o for o in _listar(s) if o.id == operario_id), None)
    if fila is None:
        raise HTTPException(404, "operario no encontrado")
    return fila


def _guardar(s, fila: "models.Operario") -> OperarioStats:
    """Commit traduciendo el choque del índice único de PIN a un 409 legible.
    El flush primero: en un alta, el id lo genera Postgres."""
    try:
        s.flush()
        operario_id = fila.id
        s.commit()
    except IntegrityError as e:
        s.rollback()
        raise HTTPException(409, "ese PIN ya está asignado a otro operario") from e
    return _uno(s, operario_id)


@router.post("", response_model=OperarioStats, status_code=201)
def crear_operario(body: OperarioNuevo, s: Db) -> OperarioStats:
    fila = models.Operario(nombre=body.nombre, pin=body.pin, rol=body.rol)
    s.add(fila)
    return _guardar(s, fila)


@router.patch("/{operario_id}", response_model=OperarioStats)
def editar_operario(operario_id: uuid.UUID, body: OperarioEdicion, s: Db) -> OperarioStats:
    fila = s.get(models.Operario, operario_id)
    if fila is None:
        raise HTTPException(404, "operario no encontrado")
    # Cambiar el PIN NO toca el id: el historial de precisión sigue siendo suyo.
    for campo, valor in body.model_dump(exclude_none=True).items():
        setattr(fila, campo, valor)
    return _guardar(s, fila)
