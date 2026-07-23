from fastapi import FastAPI

from app.api.conteos import router as conteos_router

app = FastAPI(title="VoceoStock API")
app.include_router(conteos_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
