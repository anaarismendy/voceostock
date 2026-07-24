import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.catalogo import router as catalogo_router
from app.api.conteos import router as conteos_router
from app.api.evidencia import router as evidencia_router
from app.api.sesiones import router as sesiones_router
from app.api.ws import router as ws_router
from app.reportes.router import router as reportes_router

app = FastAPI(title="VoceoStock API")
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


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
