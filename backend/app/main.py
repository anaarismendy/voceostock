from fastapi import FastAPI

from app.api.conteos import router as conteos_router
from app.reportes.router import router as reportes_router

app = FastAPI(title="VoceoStock API")
app.include_router(conteos_router)
app.include_router(reportes_router)  # A9/I3: reporte de diferencias + export Excel


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
