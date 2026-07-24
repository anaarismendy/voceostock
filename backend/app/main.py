from fastapi import FastAPI

from app.api.conteos import router as conteos_router
from app.api.evidencia import router as evidencia_router
from app.api.sesiones import router as sesiones_router
from app.api.ws import router as ws_router
from app.reportes.router import router as reportes_router

app = FastAPI(title="VoceoStock API")
app.include_router(conteos_router)
app.include_router(sesiones_router)
app.include_router(evidencia_router)
app.include_router(ws_router)
app.include_router(reportes_router)  # A9/I3: reporte de diferencias + export Excel


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
