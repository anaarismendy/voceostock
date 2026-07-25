# Cómo correr VoceoStock (Windows / PowerShell)

Guía verificada ejecutando cada comando en una terminal PowerShell desde la
raíz del repo. Copia y pega en orden.

## 0. Prerrequisitos

Versiones con las que se verificó (cualquier versión igual o más nueva sirve):

| Herramienta | Verificar con | Verificado |
|---|---|---|
| Docker Desktop (corriendo) | `docker --version` | 29.1.3 |
| uv (Python) | `uv --version` | 0.10.8 |
| Node.js | `node --version` | v24.11.0 |
| npm | `npm --version` | 11.6.1 |

Además: el archivo `.env` en la raíz (NO va en git). Mínimo:

```
GEMINI_API_KEY=            # vacío = modo replay (sin red); con key = live
GEMINI_MODEL_NLU=gemini-flash-latest
SECRET_KEY=demo-secret
WARMUP_BODEGA_ID=3
```

## 1. Base de datos

```powershell
docker compose up -d db
docker ps --filter "name=db" --format "{{.Names}} {{.Status}} {{.Ports}}"
# → colsubsidiohackaton-db-1 Up ... 0.0.0.0:5433->5432/tcp
```

## 2. Backend (migraciones + datos + servidor)

```powershell
cd backend
uv sync

$env:DATABASE_URL='postgresql+psycopg://voceo:voceo@localhost:5433/voceostock'
$env:PYTHONIOENCODING='utf-8'          # la consola Windows (cp1252) revienta sin esto

uv run alembic upgrade head            # debe terminar en: 0003 (head)
uv run python ..\data\ingest.py        # idempotente: re-correrlo da "0 nuevas"
```

Levantar la API (puerto **8020** — el 8000 y el 8010 pueden estar ocupados):

```powershell
# --- Modo LIVE (Gemini real; requiere key con saldo en .env) ---
$env:SECRET_KEY='demo-secret'
$env:WARMUP_BODEGA_ID='3'
$env:GEMINI_API_KEY=(Get-Content ..\.env | Where-Object { $_ -match '^GEMINI_API_KEY=' }) -replace '^GEMINI_API_KEY=',''
$env:GEMINI_MODEL_NLU='gemini-flash-latest'
uv run uvicorn app.main:app --port 8020
```

```powershell
# --- Modo REPLAY (sin key, sin red: respuestas grabadas del guion) ---
$env:SECRET_KEY='demo-secret'
$env:WARMUP_BODEGA_ID='3'
$env:PIPELINE_MODE='replay'
uv run uvicorn app.main:app --port 8020
```

Comprobar (en OTRA terminal):

```powershell
Invoke-RestMethod http://localhost:8020/health   # → status: ok
```

> **Live vs replay:** `PIPELINE_MODE` manda; si no está, la key decide
> (hay `GEMINI_API_KEY` → live; no hay → replay). En replay solo entienden
> las frases grabadas en `data/replay/nlu/` (las 4 del guion de DEMO.md).

## 3. Sembrar la demo (estado de docs/DEMO.md)

```powershell
Invoke-RestMethod -Method Post 'http://localhost:8020/api/v1/demo/seed?bodega_id=3'
# → ok=True, total=3  (aceite cuadra, cazuela +2, costilla −3)
# Para vaciar:  Invoke-RestMethod -Method Post 'http://localhost:8020/api/v1/demo/reset?bodega_id=3'
```

## 4. Frontend

```powershell
cd ..\frontend
npm install                            # solo la primera vez

# --- Contra el backend REAL ---
$env:VITE_API='real'
$env:VITE_API_PROXY='http://localhost:8020'
npm run dev
```

```powershell
# --- Modo MOCK (sin backend ni BD: el propio vite responde el contrato) ---
Remove-Item Env:VITE_API -ErrorAction SilentlyContinue
npm run dev
```

Abrir **http://localhost:5173** en Chrome (Web Speech funciona mejor ahí).

## 5. Credenciales y datos de prueba

- **PIN:** cualquiera de 4 dígitos — el login crea el operario si no existe
  (p. ej. `7777` como Operario, `9999` como Líder; el rol se elige arriba
  del teclado). El PIN `0000` es el operario "Demo" de la semilla.
- **Bodega recomendada:** `almacen general` (566 artículos).
  **Nunca** `administracion` (tiene 0 artículos).
- Frases que el modo replay entiende (dictado por texto o voz):
  - `treinta y tres litros de aceite de oliva` → confirmado
  - `noventa cajas de cazuelas` → anomalía ("¿Confirmas 90? El corte anterior registró 10.")
  - `una cazuela` → ambigüedad (2 candidatos)
  - `siete kilos de arroz basmati` → confirmado
  - En modo guiado: cantidades `12` (POLLO ENTERO) y `5` (ABRELATAS) están grabadas.

## 6. Si algo falla

1. **`/health` no responde o la BD no conecta**
   Docker Desktop no está corriendo o el contenedor está abajo:
   `docker compose up -d db` y reintenta. El puerto de la BD es **5433**
   (no el 5432 default).

2. **Los conteos responden "No pude entender…" o el backend loguea 429/401 de Gemini**
   La key no tiene saldo o caducó (las `AQ.…` caducan en ~1 h). Solución
   inmediata: correr en **replay** (bloque de arriba) — el guion completo
   funciona sin red. La app nunca muestra error 500: degrada al teclado.

3. **El frontend carga pero "No se pudo cargar la lista de bodegas"**
   Estás en modo real sin backend, o el proxy apunta mal. Verifica
   `Invoke-RestMethod http://localhost:8020/health`, y que la terminal del
   frontend tenga `VITE_API='real'` y `VITE_API_PROXY='http://localhost:8020'`
   (las env vars de PowerShell viven por terminal: si abriste una nueva,
   vuelve a ponerlas). Si `tsc`/vite fallan con `TS2688 ... 'node'`,
   falta `npm install`.
