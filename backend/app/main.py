from fastapi import FastAPI

from app.api.conteos import router as conteos_router
from app.api.sesiones import router as sesiones_router

app = FastAPI(title="VoceoStock API")
app.include_router(conteos_router)
app.include_router(sesiones_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
