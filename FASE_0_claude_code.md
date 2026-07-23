# FASE 0 — VoceoStock: monorepo, contrato, stub y fixtures

> **Instrucciones para Claude Code.** Este archivo es autocontenido: ejecuta todo lo que describe, en orden, y cierra con las verificaciones del final. El archivo `data/BODEGAS_Y_STOCK.xlsx` ya está en el repositorio (lo coloqué yo); los fixtures de datos se generan leyéndolo — no inventes datos.

## Contexto del producto (léelo antes de escribir código)

VoceoStock es una solución de hackathon: captura de inventario por voz con **validación conversacional en el punto de captura**. Un operario de bodega cuenta hablando ("treinta y tres litros de aceite de oliva"), el sistema entiende artículo + cantidad + unidad, valida contra el catálogo y el histórico **antes de guardar** (si dice "noventa cajas" donde históricamente hay diez, pregunta), y al cierre exporta un Excel idéntico al formato del ERP. La arquitectura es una **plataforma de ingesta con adaptadores de captura**: hoy voz en tablet y WhatsApp; mañana RFID o básculas, todos entrando por el mismo endpoint.

En esta fase NO se construye el pipeline de inteligencia ni la UI final: se construye el esqueleto que permite que tres personas trabajen en paralelo — el contrato congelado del API, un stub determinista del pipeline, y fixtures extraídos del Excel real.

---

## BLOQUE 1 — Estructura del monorepo

Crea el monorepo `voceostock`:

- `backend/` → FastAPI, Python 3.12, gestor **uv**. Estructura: `app/main.py`, `app/api/` (routers), `app/pipeline/` (subcarpetas nlu, matching, anomalias — vacías con `__init__.py`), `app/models/` (SQLAlchemy, vacío), `app/schemas/` (Pydantic), `tests/`.
- `frontend/` → React 18 + TypeScript + Vite + Tailwind, plantilla PWA (`vite-plugin-pwa`). Estructura: `src/screens/`, `src/components/`, `src/lib/`.
- `data/` → aquí vive `BODEGAS_Y_STOCK.xlsx` (ya está). Crea `data/fixtures/` (se llena en el Bloque 5), `data/ingest.py` vacío con un TODO ("Fase 1 — Persona 2").
- `docs/` → `docs/contrato/` y `docs/contrato/ejemplos/`, `docs/DEMO.md` vacío.
- `docker-compose.yml` → servicios: **db** (`pgvector/pgvector:pg16`, volumen persistente), **api** (backend con reload, monta `./storage` para audio), **frontend** (vite dev server). 
- Raíz: `.gitignore` completo Python+Node (incluye `.env`, `storage/`, `data/*.xlsx` NO se ignora — es insumo del repo privado, pero `data/fixtures/embeddings*` sí), `.env.example` con:
  ```
  GEMINI_API_KEY=
  DATABASE_URL=postgresql+psycopg://voceo:voceo@db:5432/voceostock
  WHATSAPP_TOKEN=
  WHATSAPP_VERIFY_TOKEN=
  ```
- `Makefile` con targets: `up`, `down`, `test`, `test-back`, `test-front`, `lint`, `demo` (por ahora `demo` = `up`).
- CI: `.github/workflows/ci.yml` que corre lint (ruff + eslint) y pruebas (`pytest -m "not integration"`; vitest) en cada push.

## BLOQUE 2 — Contrato congelado del API

Créalo como schemas Pydantic en `backend/app/schemas/conteos.py` y documenta el JSON en `docs/contrato/contrato.md`. Este contrato queda **CONGELADO**: cambiarlo requiere acuerdo del equipo completo.

`POST /api/v1/conteos` — request:

```json
{
  "sesion_id": "uuid",
  "bodega_id": 13,
  "operario_id": "uuid",
  "fuente": "voz-tablet | whatsapp | manual | rfid | bascula",
  "payload_texto": "texto transcrito o null",
  "payload_audio_b64": "audio base64 o null"
}
```

Respuesta — uno de tres estados:

```json
{ "status": "confirmado",
  "conteo": { "id": "uuid", "articulo_id": 7290,
              "articulo_nombre": "ACEITE DE OLIVA", "cantidad": 33.5,
              "unidad": "Liter", "confianza": 0.95,
              "fuente": "voz-tablet", "evidencia_url": null } }
```

```json
{ "status": "requiere_confirmacion",
  "token_pendiente": "uuid",
  "motivo": "ambiguedad | anomalia | baja_confianza",
  "pregunta": "¿Confirmas 90? El corte anterior registró 10.",
  "candidatos": [ { "articulo_id": 1, "articulo_nombre": "CAZUELA 16 ONZ" } ] }
```

```json
{ "status": "no_catalogado",
  "texto_capturado": "producto xyz", "cantidad": 4, "unidad": "Unidad" }
```

`POST /api/v1/conteos/{token_pendiente}/resolver` — request:

```json
{ "respuesta": "si | no | articulo_id:<int> | cantidad:<float>" }
```

→ responde con la misma estructura que `POST /conteos`.

**REGLA INVIOLABLE:** ninguna respuesta de estos endpoints incluye jamás el stock teórico (SD). Conteo ciego.

## BLOQUE 3 — Stub determinista del pipeline

En `backend/app/pipeline/core.py` define los tipos y la función que todo el backend usará. La **firma queda congelada**; la Persona 1 reemplazará solo el cuerpo (tarea A8).

```python
class PayloadConteo(BaseModel): ...   # espejo del request del contrato

class Candidato(BaseModel):
    articulo_id: int
    articulo_nombre: str

class ResultadoPipeline(BaseModel):
    status: Literal["confirmado", "requiere_confirmacion", "no_catalogado"]
    articulo_id: int | None = None
    articulo_nombre: str | None = None
    cantidad: float | None = None
    unidad: str | None = None      # Unidad | Kilogram | Liter | Portion
    confianza: float | None = None
    motivo: str | None = None      # ambiguedad | anomalia | baja_confianza
    pregunta: str | None = None
    candidatos: list[Candidato] | None = None
    texto_capturado: str | None = None

async def procesar_conteo(payload: PayloadConteo,
                          contexto: ContextoBodega) -> ResultadoPipeline:
    # STUB — P1 lo reemplaza en la tarea A8 sin cambiar la firma.
```

Comportamiento del stub (determinista, para que backend y frontend prueben los tres estados sin pipeline real):

- texto contiene `"noventa"` → `requiere_confirmacion`, motivo `anomalia`, pregunta `"¿Confirmas 90? El corte anterior registró 10."`
- texto contiene `"cazuela"` → `requiere_confirmacion`, motivo `ambiguedad`, 2 candidatos ficticios (CAZUELA 16 ONZ / CALDERO RECORT TAPA 50X60 CM).
- texto contiene `"xyz"` → `no_catalogado`.
- llega `payload_audio_b64` (cualquiera) → `confirmado` con datos fijos plausibles.
- cualquier otro texto → `confirmado` con datos fijos plausibles.

## BLOQUE 4 — Endpoints mínimos vivos

- `GET /health` → `{"status":"ok"}`.
- `POST /api/v1/conteos` y `POST /api/v1/conteos/{token}/resolver` cableados **al stub** (sin BD todavía; los tokens pendientes viven en un dict en memoria).
- Frontend: página inicial que consume `/health` y muestra "VoceoStock OK", más un textarea de prueba interna que postea a `/conteos` y pinta la respuesta JSON cruda. Es herramienta de desarrollo, no UI final.

## BLOQUE 5 — Fixtures extraídos del Excel real

### 5a. Fixture de datos (`data/make_fixtures.py`)

Lee `data/BODEGAS_Y_STOCK.xlsx` con pandas y genera:

- `data/fixtures/catalogo.csv` — columnas `bodega, nr_articulo, articulo, unidad, sd`: una fila por registro de **cada hoja de stock** (todas menos "BODEGAS DISPONIBLES"), usando el nombre de la hoja como `bodega`. Tolera que una hoja traiga el encabezado mal escrito `CANTIDA` en vez de `CANTIDAD`. **No limpies nada más**: los datos sucios (espacios, duplicados, `Nr.Artículo` vacíos) se conservan a propósito — la limpieza es de la Fase 1.
- `data/fixtures/bodegas.csv` — columnas `id, nombre`, desde la hoja "BODEGAS DISPONIBLES" tal cual.

Ejecuta el script y muéstrame `wc -l` y `head -5` de ambos archivos. Referencia de lo esperado: ~1.420 filas de catálogo y 48 bodegas.

### 5b. Fixtures del contrato (`docs/contrato/ejemplos/`)

Genera 5 archivos JSON **llamando al stub real** con los payloads que disparan cada estado y guardando las respuestas: `confirmado.json`, `requiere_confirmacion_ambiguedad.json`, `requiere_confirmacion_anomalia.json`, `no_catalogado.json`, `resolver_request.json`. Agrega una prueba que valide cada ejemplo contra el schema Pydantic del contrato (si el contrato divergiera, la prueba revienta).

## BLOQUE 6 — CLAUDE.md

Crea en la raíz `CLAUDE.md` con este contenido exacto:

```markdown
# VoceoStock — contexto para Claude Code

Producto: captura de inventario por voz con validación conversacional en el
punto de captura. Hackathon; prioridad: demo confiable > elegancia.

Stack: FastAPI + Postgres 16/pgvector + React 18/TS/Tailwind (PWA) + Gemini
API (2.5 Flash para NLU multimodal, gemini-embedding-001 para matching).

## Reglas de dominio (INVIOLABLES)
- Unidades canónicas: Unidad, Kilogram, Liter, Portion. Ninguna otra llega
  a la BD; el parser normaliza sinónimos (kilo/kg/kilito→Kilogram,
  lt/litros→Liter, paquete/unidades→Unidad, porción→Portion,
  arroba→12.5 Kilogram).
- Conteo ciego: el SD (stock teórico) NUNCA aparece en endpoints usados
  durante la captura, ni en el frontend de conteo, ni en mensajes de
  WhatsApp. Solo existe en reportes de cierre.
- `conteos` es append-only: una corrección crea un registro nuevo con
  vínculo al que supersede. Nunca UPDATE de cantidad.
- Contrato único de ingesta: POST /api/v1/conteos; el campo `fuente`
  identifica el adaptador. Ver docs/contrato/contrato.md. El contrato está
  CONGELADO: cambiarlo requiere acuerdo de las 3 personas.
- La firma de app/pipeline/core.py::procesar_conteo está CONGELADA.
  P1 reemplaza el cuerpo, no la firma.

## Reglas técnicas
- Español en UI, mensajes al usuario y preguntas del agente; inglés en
  código, identificadores y commits.
- API keys solo en backend vía .env. Nunca en frontend, nunca en commits.
- Toda función de pipeline (nlu/matching/anomalías) con prueba unitaria.
  Pruebas contra Gemini real: marker @pytest.mark.integration (CI las salta).
- Latencia objetivo captura→confirmación: <2 s (tablet, ruta texto).
- Commits: feat|fix|chore|test(scope): descripción. Ramas: main protegida,
  ramas p1/*, p2/*, p3/* por persona.
- Propiedad de carpetas: P1=app/pipeline/, app/reportes/; P2=app/models/,
  app/api/, data/ingest.py, alembic/; P3=frontend/, docs/DEMO.md. Tocar
  carpeta ajena = avisar por chat antes.

## Datos reales (data/BODEGAS_Y_STOCK.xlsx)
- 9 hojas: 1 listado de 48 bodegas + 8 hojas de stock (~1.420 registros).
- Columnas: CANTIDAD (consecutivo), Nr.Artículo (a veces vacío), Artículo,
  Unidad, SD (decimal).
- Suciedades conocidas: bodegas duplicadas ("cafeteria acuario suministros"
  ×2; "movil fonda" vs "movil fonda suministros"), encabezado "CANTIDA" en
  una hoja, espacios sobrantes, artículos sin Nr.Artículo (ej. AGUA 280 ML).
```

## VERIFICACIONES DE CIERRE (ejecútalas y muéstrame la salida)

1. `docker compose up -d && curl localhost:8000/health` → `{"status":"ok"}`.
2. `curl -X POST localhost:8000/api/v1/conteos` con payload de texto "noventa cajas de cazuelas" → responde `requiere_confirmacion` con motivo `anomalia`.
3. Mismo curl con "cazuela sola" → `ambiguedad` con 2 candidatos; con "producto xyz" → `no_catalogado`.
4. `make test` en verde: incluye una prueba del stub por cada estado + la validación de los ejemplos del contrato.
5. `python data/make_fixtures.py` ya ejecutado; `data/fixtures/` con los 2 CSV (~1.420 y 48 filas).
6. Git: un commit por bloque (`chore(repo)`, `feat(contrato)`, `feat(stub)`, `feat(front-shell)`, `feat(fixtures)`, `chore(ci)`), tag `fase-0`.
