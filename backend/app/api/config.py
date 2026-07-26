"""E2: endpoints de configuración para el líder — umbrales de confianza y
sinónimos, editables sin tocar código.

Editar un umbral se refleja en la SIGUIENTE captura sin reiniciar el servicio:
tras persistir, se recarga la config del pipeline vivo (`configurar`). No expone
SD (conteo ciego).
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app import models
from app.db import Db, engine
from app.pipeline.confianza import UmbralesConfianza, configurar
from app.pipeline.config import cargar_umbrales
from app.pipeline.normalizacion import normalizar

router = APIRouter(prefix="/api/v1/config", tags=["config"])


class Umbrales(BaseModel):
    auto: float = Field(ge=0, le=1)
    rapida: float = Field(ge=0, le=1)
    aclaracion: float = Field(ge=0, le=1)


def _umbral_global(s) -> models.UmbralConfianza | None:
    return s.scalar(
        select(models.UmbralConfianza).where(models.UmbralConfianza.sede_id.is_(None))
    )


@router.get("/umbrales", response_model=Umbrales)
def obtener_umbrales(s: Db) -> Umbrales:
    fila = _umbral_global(s)
    if fila is None:  # sin fila: los defaults del dominio
        d = UmbralesConfianza()
        return Umbrales(auto=d.auto, rapida=d.rapida, aclaracion=d.aclaracion)
    return Umbrales(auto=float(fila.auto), rapida=float(fila.rapida), aclaracion=float(fila.aclaracion))


@router.put("/umbrales", response_model=Umbrales)
def actualizar_umbrales(body: Umbrales, s: Db) -> Umbrales:
    # Valida el orden (auto>=rapida>=aclaracion) reutilizando la regla del dominio.
    try:
        UmbralesConfianza(auto=body.auto, rapida=body.rapida, aclaracion=body.aclaracion)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e

    fila = _umbral_global(s)
    if fila is None:
        s.add(
            models.UmbralConfianza(
                sede_id=None, auto=body.auto, rapida=body.rapida, aclaracion=body.aclaracion
            )
        )
    else:
        fila.auto, fila.rapida, fila.aclaracion = body.auto, body.rapida, body.aclaracion
    s.commit()
    # J1: reflejar en el pipeline VIVO sin reiniciar el servicio.
    configurar(cargar_umbrales(engine))
    return body


class SinonimoNuevo(BaseModel):
    articulo_id: int
    texto_sinonimo: str = Field(min_length=1, max_length=120)
    sede_id: int | None = None
    origen: str = Field(default="manual", pattern="^(aprendido|manual)$")


class Sinonimo(BaseModel):
    id: int
    sede_id: int | None
    articulo_id: int
    texto_sinonimo: str
    origen: str


def _a_salida(f: models.SinonimoArticulo) -> Sinonimo:
    return Sinonimo(
        id=f.id, sede_id=f.sede_id, articulo_id=f.articulo_id,
        texto_sinonimo=f.texto_sinonimo, origen=f.origen,
    )


@router.get("/sinonimos", response_model=list[Sinonimo])
def listar_sinonimos(s: Db, sede_id: int | None = None) -> list[Sinonimo]:
    q = select(models.SinonimoArticulo)
    if sede_id is not None:
        q = q.where(models.SinonimoArticulo.sede_id == sede_id)
    filas = s.scalars(q.order_by(models.SinonimoArticulo.texto_sinonimo)).all()
    return [_a_salida(f) for f in filas]


@router.post("/sinonimos", response_model=Sinonimo, status_code=201)
def crear_sinonimo(body: SinonimoNuevo, s: Db) -> Sinonimo:
    fila = models.SinonimoArticulo(
        sede_id=body.sede_id,
        articulo_id=body.articulo_id,
        texto_sinonimo=body.texto_sinonimo,
        texto_normalizado=normalizar(body.texto_sinonimo),
        origen=body.origen,
    )
    s.add(fila)
    try:
        s.commit()
    except IntegrityError as e:
        s.rollback()
        raise HTTPException(409, "ese sinónimo ya existe para la sede") from e
    return _a_salida(fila)


@router.delete("/sinonimos/{sinonimo_id}", status_code=204)
def borrar_sinonimo(sinonimo_id: int, s: Db) -> None:
    fila = s.get(models.SinonimoArticulo, sinonimo_id)
    if fila is None:
        raise HTTPException(404, "sinónimo no encontrado")
    s.delete(fila)
    s.commit()
