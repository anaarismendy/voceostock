# Pipeline de inteligencia (Persona 1)

El "cerebro" de VoceoStock: convierte lo que dice el operario en un conteo
validado, o en una pregunta antes de guardar. Vive en `backend/app/pipeline/`
(captura e inteligencia) y `backend/app/reportes/` (cierre del negocio).

## Flujo

```
payload (texto y/o audio)
   │
   ▼  parse_conteo()            NLU multimodal (Gemini 2.5 Flash) → ConteoParseado
   │                            artículo, cantidad, unidad canónica, confianza…
   ▼  match()                   cascada: exacto → fuzzy → embeddings
   │                            → match | ambigüedad | no_catalogado
   ▼  evaluar()                 5 reglas de anomalía sobre el SD del catálogo
   │
   ▼  ResultadoPipeline         confirmado | requiere_confirmacion | no_catalogado
```

Todo esto está detrás de la firma **CONGELADA** `core.procesar_conteo(payload,
contexto)`: la tarea A8 reemplazó el cuerpo del stub, nunca la firma.

## Piezas y sus abstracciones

Cada dependencia externa está tras un protocolo, con una implementación real y
otra offline. Por eso `pytest -m "not integration"` corre sin red y la demo
sobrevive a un wifi caído.

| Pieza | Real (producción) | Offline (CI / demo) |
|---|---|---|
| NLU (`nlu/cliente.py`) | `ClienteGemini` | `ClienteReplay` (respuestas grabadas) |
| Embeddings (`matching/embeddings.py`) | `EmbedderGemini` (+ caché en disco) | `EmbedderLexico` (n-gramas) |
| Catálogo (`datos/repos.py`) | `RepoDB` (Postgres + pgvector) | `RepoCSV` (`data/fixtures/`) |

`servicios.py` arma el `Pipeline` según el entorno:

- `PIPELINE_MODE = live | replay | auto` (auto: live si hay `GEMINI_API_KEY`).
- `PIPELINE_DATA = db | csv | auto` (auto: db si hay `DATABASE_URL`).
- `REPLAY_DIR` = carpeta de respuestas grabadas (modo replay/demo, tarea A10).

### Umbrales de matching

El coseno **no es comparable entre espacios de embedding**, así que el umbral
viaja con el embedder: `EmbedderGemini` usa 0.80 (spec del plan), `EmbedderLexico`
usa 0.62 (calibrado a su geometría). Aplicar el 0.80 de Gemini al léxico sería un
bug silencioso.

## Regla INVIOLABLE — conteo ciego

El SD (stock teórico) jamás sale hacia el operario. El motor de anomalías lo usa
para decidir si frenar, pero las preguntas señalan que la cantidad es *inusual*,
nunca *contra qué*: "es bastante más de lo habitual", no "el corte registró 10".
El SD solo aparece en el reporte de cierre (`app/reportes/`), que es para el
líder, no una pantalla de captura.

## Cómo correrlo

```bash
# CLI de demo (offline por defecto; usa Gemini si hay GEMINI_API_KEY)
cd backend && python cli.py "noventa cajas de cazuelas" --bodega "almacen general"
python cli.py --audio conteo.ogg --bodega "almacen general"

# Pruebas
uv run pytest -m "not integration"          # offline, sin red
GEMINI_API_KEY=... uv run pytest -m integration   # contra Gemini real

# Regrabar fixtures de NLU desde Gemini real (tarea A2)
GEMINI_API_KEY=... python -m scripts.record_parser --record

# Construir la caché de embeddings del catálogo (tarea A5)
GEMINI_API_KEY=... python -m scripts.build_embeddings
```

## Reporte de cierre y export (A9)

- `GET /api/v1/reportes/bodegas/{id}/diferencias` — cantidad física vs SD, con
  semáforo (normal <10 % · revisar 10–30 % · crítico >30 % o anomalía).
- `GET /api/v1/reportes/bodegas/{id}/export` — Excel 1:1 del insumo original
  (`CANTIDAD, Nr.Artículo, Artículo, Unidad, SD`, una hoja por bodega, con
  `SD = cantidad física contada`). El round-trip contra `data/ingest.py` está en
  las pruebas: lo que P1 exporta, la ingesta de P2 lo reconoce.
