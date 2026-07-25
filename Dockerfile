# Imagen de producción (Railway). Compila la PWA y la sirve como estáticos desde
# FastAPI, así el frontend, /api, /health y /ws quedan en el mismo origen: las
# llamadas relativas de src/ funcionan tal cual y no hace falta tocar CORS.
# Para desarrollo local se sigue usando backend/Dockerfile vía docker-compose.

FROM node:22-alpine AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# VITE_API=real desactiva el mock-server del build (ver frontend/vite.config.ts).
ENV VITE_API=real
RUN npm run build

FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app

COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev

COPY backend/app ./app
COPY backend/alembic ./alembic
COPY backend/alembic.ini ./
# La migración 0003 importa scripts.populate_familia, así que scripts/ va en la imagen.
COPY backend/scripts ./scripts
# data/ trae el catálogo de la demo, los fixtures de replay y la caché de TTS
# ya calentada (tts.py la busca en /app/data/tts_cache).
COPY data ./data
COPY --from=frontend /build/dist ./static

# Migra y arranca. Sin --reload (eso es solo para local) y en $PORT, que es lo
# que Railway inyecta en tiempo de ejecución.
CMD ["sh", "-c", "uv run --frozen --no-dev alembic upgrade head && uv run --frozen --no-dev uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
