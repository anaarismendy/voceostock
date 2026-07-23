from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException

from app.pipeline.core import ContextoBodega, PayloadConteo, ResultadoPipeline, procesar_conteo
from app.schemas.conteos import (
    Candidato,
    Conteo,
    ConteoRequest,
    ResolverRequest,
    RespuestaConfirmado,
    RespuestaConteo,
    RespuestaNoCatalogado,
    RespuestaRequiereConfirmacion,
)

router = APIRouter(prefix="/api/v1/conteos", tags=["conteos"])

# ponytail: tokens pendientes en dict en memoria; pasan a BD en Fase 1.
_pendientes: dict[UUID, PayloadConteo] = {}


def _a_respuesta(r: ResultadoPipeline, payload: PayloadConteo) -> RespuestaConteo:
    if r.status == "confirmado":
        return RespuestaConfirmado(
            conteo=Conteo(
                id=uuid4(),
                articulo_id=r.articulo_id,
                articulo_nombre=r.articulo_nombre,
                cantidad=r.cantidad,
                unidad=r.unidad,
                confianza=r.confianza,
                fuente=payload.fuente,
                evidencia_url=None,
            )
        )
    if r.status == "requiere_confirmacion":
        token = uuid4()
        _pendientes[token] = payload
        return RespuestaRequiereConfirmacion(
            token_pendiente=token,
            motivo=r.motivo,
            pregunta=r.pregunta,
            candidatos=[Candidato(**c.model_dump()) for c in r.candidatos] if r.candidatos else None,
        )
    return RespuestaNoCatalogado(
        texto_capturado=r.texto_capturado or "",
        cantidad=r.cantidad,
        unidad=r.unidad,
    )


@router.post("", response_model=RespuestaConteo)
async def crear_conteo(req: ConteoRequest) -> RespuestaConteo:
    payload = PayloadConteo(**req.model_dump())
    resultado = await procesar_conteo(payload, ContextoBodega(bodega_id=req.bodega_id))
    return _a_respuesta(resultado, payload)


@router.post("/{token_pendiente}/resolver", response_model=RespuestaConteo)
async def resolver_conteo(token_pendiente: UUID, req: ResolverRequest) -> RespuestaConteo:
    payload = _pendientes.pop(token_pendiente, None)
    if payload is None:
        raise HTTPException(status_code=404, detail="token_pendiente desconocido")

    # ponytail: resolución stub — P1 la vuelve real en Fase 1.
    if req.respuesta == "no":
        return RespuestaNoCatalogado(texto_capturado=payload.payload_texto or "")

    articulo_id, cantidad = 7290, 33.5
    if req.respuesta.startswith("articulo_id:"):
        articulo_id = int(req.respuesta.split(":", 1)[1])
    elif req.respuesta.startswith("cantidad:"):
        cantidad = float(req.respuesta.split(":", 1)[1])
    return RespuestaConfirmado(
        conteo=Conteo(
            id=uuid4(),
            articulo_id=articulo_id,
            articulo_nombre="ACEITE DE OLIVA",
            cantidad=cantidad,
            unidad="Liter",
            confianza=0.95,
            fuente=payload.fuente,
            evidencia_url=None,
        )
    )
