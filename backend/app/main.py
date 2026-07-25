import asyncio
import logging
import os
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.catalogo import router as catalogo_router
from app.api.conteos import router as conteos_router
from app.api.demo import router as demo_router
from app.api.evidencia import router as evidencia_router
from app.api.sesiones import router as sesiones_router
from app.api.tts import router as tts_router
from app.api.ws import router as ws_router
from app.reportes.router import router as reportes_router

logger = logging.getLogger(__name__)


async def _warmup_nlu() -> None:
    """Calentamiento del pipeline al arrancar (fase final): la primera llamada
    a Gemini paga ~3,5 s de construcción del cliente + TLS. Un parse dummy que
    no toca la BD ni persiste nada deja la primera frase real en ~2 s."""
    from app.pipeline.core import ContextoBodega, PayloadConteo, procesar_conteo

    # WARMUP_BODEGA_ID: además del cliente Gemini, precalienta el catálogo de
    # la bodega de la demo (con 566 artículos + embeddings, cargarlo en frío
    # cuesta ~1 s). 0 = solo NLU.
    bodega_id = int(os.environ.get("WARMUP_BODEGA_ID", "0"))
    payload = PayloadConteo(
        sesion_id=uuid4(), bodega_id=bodega_id, operario_id=uuid4(),
        fuente="manual", payload_texto="warmup",
    )
    try:
        await procesar_conteo(payload, ContextoBodega(bodega_id=bodega_id))
    except Exception as e:  # noqa: BLE001 — replay sin fixture, red caída: da igual
        logger.debug("warmup terminó con %r (esperado en replay)", e)
    logger.info("warmup del pipeline NLU completado")


@asynccontextmanager
async def _lifespan(app: FastAPI):
    tarea = asyncio.create_task(_warmup_nlu())  # no bloquea el arranque
    yield
    tarea.cancel()


app = FastAPI(title="VoceoStock API", lifespan=_lifespan)
# B9/I2: orígenes explícitos por env (coma-separados), nunca "*". El default
# cubre el dev server de vite en localhost.
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get(
        "ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(conteos_router)
app.include_router(catalogo_router)
app.include_router(sesiones_router)
app.include_router(evidencia_router)
app.include_router(ws_router)
app.include_router(reportes_router)  # A9/I3: reporte de diferencias + export Excel
app.include_router(demo_router)  # C9-C11 reales: cierre del líder, dashboard, seed
app.include_router(tts_router)  # voz del agente (ElevenLabs + caché en disco)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
