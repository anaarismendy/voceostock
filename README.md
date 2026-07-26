# VoceoStock

Captura de inventario por voz con **validación conversacional en el punto de
captura**. El operario dicta ("noventa cajas de cazuelas"), el sistema entiende
(Gemini NLU multimodal), matchea contra el catálogo real de la bodega
(exacto → fuzzy → embeddings pgvector) y, si algo no cuadra contra el
histórico, **pregunta antes de guardar** — con voz natural (ElevenLabs). Al
cierre, el líder ve las diferencias con semáforo y exporta un Excel idéntico
al del ERP.

Construido para el reto Colsubsidio (hackathon) sobre los datos reales de
`data/BODEGAS_Y_STOCK.xlsx`: 48 bodegas y ~1.420 registros de stock.

**Objetivo:** reemplazar el flujo papel → transcripción manual → Excel del ERP
por contar hablando, con los errores atrapados *en el momento de contar*, no
días después en el cierre.

## Qué hace hoy (funcionalidades reales)

### Operario (tablet / PWA)

- **Login por PIN** de 4 dígitos; el rol (operario/líder) lo decide el backend,
  no la pantalla. PIN no registrado → mensaje claro, sin operarios fantasma.
- **Selección de bodega** con búsqueda, tamaño del catálogo y estado "en conteo".
- **Conteo por voz** (Web Speech API): dictar "treinta y tres litros y medio de
  aceite" produce una tarjeta de confirmación grande que el sistema **lee en
  voz alta** (TTS ElevenLabs con caché en disco; degrada a la voz del navegador).
- **Validación conversacional** — el diferenciador. Antes de guardar, el
  pipeline puede frenar y preguntar:
  - **Anomalía**: 5 reglas contra el histórico (p. ej. orden de magnitud vs. el
    último corte, decimales en unidades enteras). "¿Confirmas 90 unidades de
    CAZUELA 16 ONZ? El corte anterior registró 10."
  - **Ambigüedad**: "cazuela" matchea 2 artículos → tarjetas para elegir.
  - **Baja confianza**: umbrales configurables (auto / rápida / aclaración /
    candidatos) que el líder edita sin redeploy.
  - La pregunta se responde **tocando o por voz** ("sí", "el segundo",
    "no, son catorce").
- **Modo guiado**: el sistema dicta QUÉ contar ahora, el operario solo aporta la
  cantidad; barra de progreso, saltar, cobertura garantizada del checklist.
- **Lista de inventario** de la bodega con filtro "solo pendientes" — sin
  adivinar qué dictar.
- **Fallbacks siempre listos**: teclado manual visible junto al micrófono; tras
  2 fallos de reconocimiento pasa solo a **grabar audio** (Gemini lo transcribe);
  si el wifi cae, el conteo queda "pendiente" y **reintenta con backoff** — nunca
  se pierde.

### Líder (panel)

- **Ciclos de inventario por bodega** ("Inventario #2, del 25 al 26 de julio"):
  el líder los abre y los cierra; las sesiones de los operarios se enganchan al
  abierto y el cierre/dashboard filtran por ciclo — un conteo nuevo no arrastra
  los anteriores.
- **Dashboard en vivo**: conteos entrando en tiempo real (feed "hace X"),
  totales, anomalías, capturas/minuto. Se recupera solo si la red parpadea.
- **Cierre con semáforo**: contado vs. teórico por artículo — Cuadra / Sobra /
  Falta / Sin contar — con filtros y auto-refresco. Único lugar donde aparece
  el SD (ver conteo ciego, abajo).
- **Export Excel 1:1**: mismas columnas del insumo original (`CANTIDAD`,
  `Nr.Artículo`, `Artículo`, `Unidad`, `SD`), una hoja por bodega; el
  round-trip por `ingest.py` es la prueba reina.
- **Ajustes sin tocar código**: umbrales de confianza (se aplican en la
  siguiente captura, sin reiniciar), sinónimos aprendidos/manuales por sede, y
  gestión de operarios con su **precisión histórica** y cuánto les sube o baja
  la confianza el sistema.

### Plataforma / pipeline

- **Contrato único de ingesta** (`POST /api/v1/conteos`, CONGELADO): el campo
  `fuente` identifica el adaptador — `voz-tablet` y `manual` hoy; `whatsapp`,
  `rfid`, `bascula` son enchufables mañana por el mismo contrato. Respuestas:
  `confirmado` / `requiere_confirmacion` (+ `/resolver`) / `no_catalogado`.
  Detalle: [docs/contrato/contrato.md](docs/contrato/contrato.md).
- **NLU**: una sola llamada multimodal a Gemini 2.5 Flash (texto y/o audio) +
  red de seguridad determinista de unidades: a la BD solo llegan las 4
  canónicas (`Unidad | Kilogram | Liter | Portion`); "kilito", "arroba"
  (=12.5 kg), "lt" se normalizan con su factor.
- **Matching en cascada**: exacto → fuzzy (rapidfuzz) → embeddings
  (gemini-embedding-001 sobre pgvector) → ambigüedad → no catalogado. Los
  sinónimos por sede entran a la cascada.
- **Confianza por operario** (D5): la precisión histórica ajusta la confianza
  efectiva — el operario acertado recibe menos confirmaciones, el impreciso más.
- **Riesgo por artículo** (D6): frecuencia de inconsistencia en los últimos
  ciclos → nivel alto/medio/bajo, con aviso en captura.
- **Conteo ciego (regla inviolable)**: el stock teórico (SD) **nunca** se
  muestra antes de que el operario dicte su cantidad. Única excepción: la
  pregunta de una anomalía ya disparada puede citar el saldo del último corte.
- **`conteos` append-only**: una corrección crea un registro nuevo vinculado al
  que supersede; jamás UPDATE de cantidad.
- **Evidencia de audio** servida solo con URL firmada con expiración.
- **WebSocket por bodega** para eventos en vivo; warmup del pipeline al
  arrancar (primera frase real ~2 s).

## Modos de ejecución

| Modo | Qué necesita | Para qué |
|---|---|---|
| **Mock** | Solo `npm run dev` en `frontend/` | Demo/desarrollo del frontend sin backend ni BD: vite responde el contrato completo, ya sembrado |
| **Replay** | Backend + Postgres, sin API keys ni red | Todo el pipeline real con respuestas de NLU grabadas (`data/replay/`) — la demo completa funciona offline |
| **Live** | `GEMINI_API_KEY` en `.env` | NLU real (dicta lo que quieras) |

La voz del agente sale de una caché en disco (`data/tts_cache/`): habla "con
ElevenLabs" aunque no haya red ni keys. `PIPELINE_MODE` manda; sin ella, la
presencia de la key decide.

## Cómo correrlo

Guía paso a paso (Windows/PowerShell, verificada): **[docs/COMO_CORRER.md](docs/COMO_CORRER.md)**

TL;DR:

```powershell
docker compose up -d db                # Postgres+pgvector en :5433
cd backend; uv sync
$env:DATABASE_URL='postgresql+psycopg://voceo:voceo@localhost:5433/voceostock'
uv run alembic upgrade head
uv run python ..\data\ingest.py        # Excel real → BD (idempotente)
uv run uvicorn app.main:app --port 8020
# en otra terminal:
cd frontend; npm install
$env:VITE_API='real'; $env:VITE_API_PROXY='http://localhost:8020'; npm run dev
```

Abrir http://localhost:5173 en Chrome · PIN **0000** (operario) / **1111**
(líder) · bodega **"almacen general"** (566 artículos).

¿Solo quieres verlo andar? `cd frontend; npm run dev` (modo mock, cero setup).

## Demos

- **[docs/DEMO_2MIN.md](docs/DEMO_2MIN.md)** — recorrido completo en 2 minutos:
  toda la navegación y funcionalidades, con tiempos por paso.
- **[docs/DEMO.md](docs/DEMO.md)** — el guion de pitch de 5 minutos con plan B
  por paso y el estado sembrado (`POST /api/v1/demo/seed?bodega_id=3`).

## API (resumen)

| Endpoint | Qué hace |
|---|---|
| `POST /api/v1/conteos` · `POST /api/v1/conteos/{token}/resolver` | Ingesta y resolución de pendientes (contrato congelado) |
| `GET /api/v1/bodegas` · `GET /api/v1/articulos` · `POST /api/v1/operarios/login` | Catálogo y login por PIN |
| `POST /api/v1/sesiones` · `GET .../progreso` · `POST .../cerrar` | Sesiones de conteo del operario |
| `GET/POST /api/v1/inventarios` · `POST .../cerrar` | Ciclos de inventario por bodega |
| `GET /api/v1/cierre` · `GET /api/v1/dashboard` | Panel del líder (cierre con SD; dashboard sin SD) |
| `GET /api/v1/reportes/bodegas/{id}/diferencias` · `.../export` | Semáforo de diferencias y Excel 1:1 |
| `GET/PUT /api/v1/config/umbrales` · `GET/POST/DELETE /api/v1/config/sinonimos` | Configuración del líder en caliente |
| `GET/POST /api/v1/operarios` · `POST .../recalcular` | Estadísticas y ajuste de confianza por operario |
| `POST /api/v1/tts` · `GET /api/v1/evidencia/{archivo}` · `WS /ws/bodegas/{id}` | Voz del agente, evidencia firmada, eventos en vivo |
| `POST /api/v1/demo/seed` · `POST /api/v1/demo/reset` | Sembrar/reiniciar el estado de demo |

## Estructura

```
backend/
  app/pipeline/    NLU (Gemini) + matching en cascada + anomalías + confianza/riesgo (P1)
  app/reportes/    diferencias con semáforo y export Excel 1:1 (P1)
  app/api/         conteos, sesiones, inventarios, catálogo, cierre, WS, TTS, config (P2)
  app/models/      SQLAlchemy + migraciones alembic (P2)
  scripts/         embeddings, fixtures de audio, caché TTS
data/              Excel real + ingest, replay de NLU, caché de voz
frontend/          PWA React 18 (P3): conteo por voz, modo guiado, panel del líder
  mock-server/     el contrato completo servido por vite (modo mock)
docs/              COMO_CORRER, DEMO, DEMO_2MIN y el contrato congelado
```

Stack: **FastAPI + Postgres 16/pgvector + React 18/TS/Tailwind (PWA) + Gemini
(2.5 Flash NLU, gemini-embedding-001) + ElevenLabs TTS**. Deploy: Docker
(compose para dev, `Dockerfile` raíz para Railway — la PWA compilada la sirve
el propio FastAPI). Las reglas de dominio inviolables viven en `CLAUDE.md`.

## Pruebas

```powershell
cd backend; uv run pytest -q          # unitarias + API (BD de prueba en :5433)
cd frontend; npm test; npm run lint   # vitest + eslint
```

Toda función del pipeline tiene prueba unitaria; las que pegan a Gemini real
llevan el marker `integration` (CI las salta). CI: `.github/workflows/ci.yml`.

## Posibilidades (siguiente paso natural)

- **Nuevos adaptadores por el mismo contrato**: WhatsApp (dictar por nota de
  voz), RFID, básculas — `fuente` ya los contempla y nada más cambia.
- **Multi-sede**: los sinónimos ya son por sede; el modelo de bodegas viene del
  listado real de 48.
- **Cola offline persistente** (IndexedDB) si el reintento con backoff se queda
  corto en bodegas sin señal prolongada.
- **Aprendizaje de sinónimos** cerrando el ciclo: lo que el operario corrige
  hoy alimenta la cascada de matching de mañana (la tabla y el origen
  "aprendido" ya existen).
