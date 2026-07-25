# VoceoStock

Captura de inventario por voz con **validación conversacional en el punto de
captura**: el operario dicta ("noventa cajas de cazuelas"), el sistema
entiende (Gemini), matchea contra el catálogo real (pgvector) y, si algo no
cuadra contra el histórico, **pregunta antes de guardar** — con voz natural
(ElevenLabs). Al cierre, el líder ve diferencias con semáforo y exporta el
Excel idéntico al del ERP.

Stack: **FastAPI + Postgres 16/pgvector + React 18 PWA + Gemini
(2.5 Flash NLU multimodal, gemini-embedding-001) + ElevenLabs TTS**.
Las reglas de dominio inviolables (conteo ciego, unidades canónicas,
conteos append-only, contrato congelado) viven en `CLAUDE.md`.

## Cómo correrlo

Guía paso a paso (Windows/PowerShell, verificada): **[docs/COMO_CORRER.md](docs/COMO_CORRER.md)**

TL;DR:

```powershell
docker compose up -d db                # Postgres en :5433
cd backend; uv sync
$env:DATABASE_URL='postgresql+psycopg://voceo:voceo@localhost:5433/voceostock'
uv run alembic upgrade head
uv run python ..\data\ingest.py        # Excel real → BD (idempotente)
uv run uvicorn app.main:app --port 8020
# en otra terminal:
cd frontend; npm install
$env:VITE_API='real'; $env:VITE_API_PROXY='http://localhost:8020'; npm run dev
```

Abrir http://localhost:5173 · PIN de 4 dígitos · bodega **"almacen general"**.

- **Live vs replay**: con `GEMINI_API_KEY` la NLU es Gemini real; sin key (o
  `PIPELINE_MODE='replay'`) todo corre offline con respuestas grabadas.
- **Mock vs real**: `npm run dev` a secas levanta el frontend con un mock del
  contrato — sin backend ni BD.
- La voz del agente sale de una caché en disco (`data/tts_cache/`): habla con
  ElevenLabs aunque no haya red ni keys.

## Guion de demo

**[docs/DEMO.md](docs/DEMO.md)** — el guion de 5 minutos con plan B por paso,
el estado sembrado (`POST /api/v1/demo/seed?bodega_id=3`) y el checklist de
arranque. Ensayado de punta a punta en live y en replay.

## El contrato (congelado)

Toda captura entra por `POST /api/v1/conteos` (el campo `fuente` identifica el
adaptador: voz-tablet hoy; WhatsApp, RFID o báscula mañana). Respuestas:
`confirmado` / `requiere_confirmacion` (+ `/resolver`) / `no_catalogado`.
Detalle y ejemplos: **[docs/contrato/contrato.md](docs/contrato/contrato.md)**
— cambiarlo requiere acuerdo de las 3 personas.

## Estructura

```
backend/
  app/pipeline/    NLU + matching + anomalías (P1)
  app/reportes/    diferencias y export Excel 1:1 (P1)
  app/api/         sesiones, conteos, catálogo, cierre, WS, TTS (P2)
  app/models/      SQLAlchemy + alembic (P2)
  scripts/         embeddings, familia, fixtures de audio, caché TTS
data/              ingest del Excel real, replay de NLU, caché de voz
frontend/          PWA (P3): conteo por voz, modo guiado, panel del líder
docs/              COMO_CORRER, DEMO y el contrato congelado
```

## Pruebas

```powershell
cd backend; uv run pytest -q          # unitarias + API (BD de prueba en :5433)
cd frontend; npm test; npm run lint   # vitest + eslint
```

Las pruebas contra Gemini real llevan el marker `integration` (CI las salta;
localmente corren con `GEMINI_API_KEY` en el entorno).
