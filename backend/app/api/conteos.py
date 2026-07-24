"""POST /conteos y /resolver contra el stub del pipeline (B5).

Persiste en BD respetando: conteos append-only (supersede, nunca UPDATE de
cantidad) y conteo ciego (ninguna respuesta ni evento incluye SD).
"""

import base64
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.api import ws
from app.api.sesiones import contados_sesion, total_articulos
from app.db import Db
from app.pipeline.core import ContextoBodega, PayloadConteo, ResultadoPipeline, procesar_conteo
from app.schemas.conteos import (
    Candidato,
    Conteo,
    ConteoRequest,
    ResolverRequest,
    RespuestaConfirmado,
    RespuestaConteo,
    RespuestaDescartado,
    RespuestaNoCatalogado,
    RespuestaRequiereConfirmacion,
    RespuestaResolver,
)
from app.services import storage

router = APIRouter(prefix="/api/v1/conteos", tags=["conteos"])

TOKEN_TTL = timedelta(minutes=10)


def _sesion_abierta(s: Session, sesion_id: UUID) -> models.SesionConteo:
    sesion = s.get(models.SesionConteo, sesion_id)
    if sesion is None:
        raise HTTPException(404, "sesión desconocida")
    if sesion.estado != "abierta":
        raise HTTPException(409, "la sesión no está abierta")
    return sesion


def _buscar_articulo(s: Session, articulo_id: int | None) -> models.Articulo | None:
    if articulo_id is None:
        return None
    # ponytail: el stub habla en nr_articulo (7290); el pipeline real de P1
    # devolverá ids del catálogo y el fallback sobra.
    art = s.get(models.Articulo, articulo_id)
    return art or s.scalar(
        select(models.Articulo).where(models.Articulo.nr_articulo == articulo_id)
    )


def _persistir(
    s: Session,
    sesion: models.SesionConteo,
    fuente: str,
    *,
    articulo: models.Articulo | None,
    cantidad: float,
    unidad: str,
    confianza: float | None = None,
    texto: str | None = None,
    evidencia_url: str | None = None,
    anomalia_tipo: str | None = None,
) -> models.Conteo:
    """Append-only: si había un conteo activo del mismo artículo en la sesión,
    el nuevo lo supersede (viejo activo=false); nunca UPDATE de cantidad."""
    previo = None
    if articulo is not None:
        previo = s.scalar(
            select(models.Conteo).where(
                models.Conteo.sesion_id == sesion.id,
                models.Conteo.articulo_id == articulo.id,
                models.Conteo.activo.is_(True),
            )
        )
    nuevo = models.Conteo(
        sesion_id=sesion.id,
        articulo_id=articulo.id if articulo else None,
        texto_capturado=texto,
        cantidad=cantidad,
        unidad=unidad,
        fuente=fuente,
        confianza=confianza,
        evidencia_url=evidencia_url,
        anomalia_flag=anomalia_tipo is not None,
        anomalia_tipo=anomalia_tipo,
        anomalia_resuelta=True if anomalia_tipo else None,
        supersede_id=previo.id if previo else None,
    )
    if previo is not None:
        previo.activo = False
        s.flush()  # libera el índice único parcial antes de insertar el nuevo
    s.add(nuevo)
    s.commit()
    return nuevo


async def _eventos_conteo(
    s: Session,
    sesion: models.SesionConteo,
    fuente: str,
    articulo: models.Articulo | None,
    nombre: str,
    cantidad: float,
    unidad: str,
) -> None:
    await ws.emitir(
        sesion.bodega_id, "conteo_nuevo", sesion.id, sesion.operario_id, fuente,
        {"articulo_nombre": nombre, "cantidad": cantidad, "unidad": unidad},
    )
    await ws.emitir(
        sesion.bodega_id, "progreso", sesion.id, sesion.operario_id, fuente,
        {"contados": contados_sesion(s, sesion.id),
         "total": total_articulos(s, sesion.bodega_id)},
    )
    if articulo is None:
        return
    otras = s.scalars(
        select(models.Conteo.sesion_id)
        .join(models.SesionConteo, models.SesionConteo.id == models.Conteo.sesion_id)
        .where(
            models.Conteo.articulo_id == articulo.id,
            models.Conteo.activo.is_(True),
            models.Conteo.sesion_id != sesion.id,
            models.SesionConteo.bodega_id == sesion.bodega_id,
            models.SesionConteo.estado == "abierta",
        )
        .distinct()
    ).all()
    if otras:  # colisión: se avisa, nunca se bloquea ni se rechaza
        await ws.emitir(
            sesion.bodega_id, "colision", sesion.id, sesion.operario_id, fuente,
            {"articulo_nombre": nombre,
             "sesiones": sorted([str(sesion.id)] + [str(o) for o in otras])},
        )


def _respuesta_confirmado(
    conteo: models.Conteo, articulo: models.Articulo, fuente: str
) -> RespuestaConfirmado:
    return RespuestaConfirmado(
        conteo=Conteo(
            id=conteo.id,
            articulo_id=articulo.id,
            articulo_nombre=articulo.nombre,
            cantidad=float(conteo.cantidad),
            unidad=conteo.unidad,
            confianza=float(conteo.confianza) if conteo.confianza is not None else 1.0,
            fuente=fuente,
            evidencia_url=conteo.evidencia_url,
        )
    )


@router.post("", response_model=RespuestaConteo)
async def crear_conteo(req: ConteoRequest, s: Db) -> RespuestaConteo:
    sesion = _sesion_abierta(s, req.sesion_id)

    evidencia_url = None
    if req.payload_audio_b64:
        archivo = storage.guardar_audio(base64.b64decode(req.payload_audio_b64))
        evidencia_url = storage.url_firmada(archivo)

    payload = PayloadConteo(**req.model_dump())
    r = await procesar_conteo(payload, ContextoBodega(bodega_id=req.bodega_id))

    if r.status == "confirmado":
        articulo = _buscar_articulo(s, r.articulo_id)
        if articulo is None:
            raise HTTPException(422, f"artículo {r.articulo_id} no existe en el catálogo")
        conteo = _persistir(
            s, sesion, req.fuente,
            articulo=articulo, cantidad=r.cantidad, unidad=r.unidad,
            confianza=r.confianza, texto=req.payload_texto, evidencia_url=evidencia_url,
        )
        await _eventos_conteo(
            s, sesion, req.fuente, articulo, articulo.nombre, float(conteo.cantidad), r.unidad
        )
        return _respuesta_confirmado(conteo, articulo, req.fuente)

    if r.status == "requiere_confirmacion":
        token = models.TokenPendiente(
            sesion_id=sesion.id,
            payload_original=req.model_dump(mode="json"),
            resultado_pipeline=r.model_dump(mode="json"),
            expira_en=datetime.now(UTC) + TOKEN_TTL,
        )
        s.add(token)
        s.commit()
        await ws.emitir(
            sesion.bodega_id, "anomalia", sesion.id, sesion.operario_id, req.fuente,
            {"pregunta": r.pregunta, "motivo": r.motivo},
        )
        return RespuestaRequiereConfirmacion(
            token_pendiente=token.id,
            motivo=r.motivo,
            pregunta=r.pregunta,
            candidatos=[Candidato(**c.model_dump()) for c in r.candidatos]
            if r.candidatos else None,
        )

    # no_catalogado: se persiste con articulo_id NULL y texto_capturado
    texto = r.texto_capturado or req.payload_texto or ""
    conteo = _persistir(
        s, sesion, req.fuente,
        articulo=None, cantidad=r.cantidad or 0, unidad=r.unidad or "Unidad",
        texto=texto, evidencia_url=evidencia_url,
    )
    await _eventos_conteo(
        s, sesion, req.fuente, None, texto, float(conteo.cantidad), conteo.unidad
    )
    return RespuestaNoCatalogado(texto_capturado=texto, cantidad=r.cantidad, unidad=r.unidad)


@router.post("/{token_pendiente}/resolver", response_model=RespuestaResolver)
async def resolver_conteo(
    token_pendiente: UUID, req: ResolverRequest, s: Db
) -> RespuestaResolver:
    token = s.get(models.TokenPendiente, token_pendiente)
    if token is None:
        raise HTTPException(404, "token_pendiente desconocido")
    if token.expira_en < datetime.now(UTC):
        raise HTTPException(410, "token_pendiente expirado")
    if token.resuelto:
        raise HTTPException(409, "token_pendiente ya resuelto")

    original = ConteoRequest(**token.payload_original)
    r = ResultadoPipeline(**token.resultado_pipeline)
    sesion = s.get(models.SesionConteo, token.sesion_id)
    token.resuelto = True

    if req.respuesta == "no":
        s.commit()
        await ws.emitir(
            sesion.bodega_id, "anomalia", sesion.id, sesion.operario_id, original.fuente,
            {"pregunta": r.pregunta, "motivo": r.motivo, "resolucion": "descartado"},
        )
        return RespuestaDescartado()

    articulo = _buscar_articulo(s, r.articulo_id)
    cantidad = r.cantidad
    if req.respuesta.startswith("articulo_id:"):
        articulo = s.get(models.Articulo, int(req.respuesta.split(":", 1)[1]))
        if articulo is None:
            raise HTTPException(404, "articulo_id desconocido")
    elif req.respuesta.startswith("cantidad:"):
        cantidad = float(req.respuesta.split(":", 1)[1])
    elif req.respuesta != "si":
        raise HTTPException(422, "respuesta no reconocida")

    anomalia_tipo = r.motivo if r.motivo == "anomalia" else None
    # ponytail: el stub no trae articulo/cantidad en sus resultados pendientes;
    # defaults seguros hasta que P1 llene el ResultadoPipeline completo.
    unidad = r.unidad or (articulo.unidad_base if articulo else "Unidad")
    conteo = _persistir(
        s, sesion, original.fuente,
        articulo=articulo, cantidad=cantidad or 0, unidad=unidad,
        confianza=r.confianza, texto=original.payload_texto,
        anomalia_tipo=anomalia_tipo,
    )
    nombre = articulo.nombre if articulo else (original.payload_texto or "")
    await ws.emitir(
        sesion.bodega_id, "anomalia", sesion.id, sesion.operario_id, original.fuente,
        {"pregunta": r.pregunta, "motivo": r.motivo, "resolucion": req.respuesta},
    )
    await _eventos_conteo(
        s, sesion, original.fuente, articulo, nombre, float(conteo.cantidad), unidad
    )
    if articulo is not None:
        return _respuesta_confirmado(conteo, articulo, original.fuente)
    return RespuestaNoCatalogado(
        texto_capturado=nombre, cantidad=float(conteo.cantidad), unidad=unidad
    )
