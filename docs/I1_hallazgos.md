# I1 — Integración pipeline real (p1) + plataforma (p2) — hallazgos

Rama: `integracion/i1`. Cada hallazgo con causa y solución; lo no resuelto
queda marcado **PENDIENTE**.

## H1 — p2/api NO estaba mergeado a main
- **Hallazgo:** la premisa "main ya con p2/datos y p2/api" era falsa: main
  solo tenía p2/datos (el PR de p2/api quedó ofrecido pero nunca creado).
  Por eso `git merge origin/p1` entró como fast-forward sin conflictos.
- **Solución:** en `integracion/i1` se mergeó primero `origin/p1` (ff) y
  luego `origin/p2/api`; los conflictos aparecieron en este segundo merge.

## H2 — La rama de P1 se llama `p1`, no `p1/pipeline`
- **Causa:** mismo tema de namespace de refs que con p2 (una rama plana
  `p1` impide crear `p1/pipeline`).
- **Solución:** se integró `origin/p1` (tip 32a2f26).

## H3 — Conflictos del merge p2/api
- `backend/app/main.py`: P1 agregó el router de reportes; p2/api traía
  sesiones, evidencia y ws. Resolución: se conservan TODOS los routers
  (conteos, sesiones, evidencia, ws, reportes).
- `backend/app/pipeline/core.py`: p2/api había ajustado el STUB (anomalía
  con articulo/cantidad/unidad); P1 ya reemplazó el cuerpo por el pipeline
  real (`get_pipeline()`). Resolución: gana el cuerpo real de P1; el ajuste
  del stub queda obsoleto. OJO: el requisito "la anomalía trae los valores
  determinados antes de preguntar" ahora debe cumplirlo el pipeline real
  (verificar en flujos E2E, PASO 5.13).

## H4 — No hay .env ni GEMINI_API_KEY
- **Hallazgo:** el repo no tiene `.env` (solo `.env.example`). Sin key,
  `PIPELINE_MODE=auto` resuelve **replay** (NLU desde `data/replay/nlu/`).
- **Estado:** los flujos E2E y la demo corren en replay. **PENDIENTE**:
  crear `.env` con `GEMINI_API_KEY` para modo live.

## H5 — ingest revienta en consola Windows (cp1252)
- **Causa:** `data/ingest.py` imprime "→" y la consola cp1252 no lo codifica.
  Es del entorno, no del código.
- **Solución:** correr con `PYTHONIOENCODING=utf-8`. La ingesta es
  idempotente (0 inserciones nuevas en la recorrida).

## H6 — El pipeline caía a RepoCSV dentro de la API local
- **Causa:** `PIPELINE_DATA=auto` decide db/csv mirando `os.environ`
  ["DATABASE_URL"], pero `app/db.py` usaba su default local sin publicarlo
  al entorno → el pipeline no veía la variable y usaba CSV.
- **Solución:** `app/db.py` hace `os.environ.setdefault("DATABASE_URL", …)`;
  el pipeline y la API usan la MISMA BD siempre.

## H7 — La ambigüedad perdía cantidad/unidad (misma clase del bug de /resolver)
- **Causa:** la rama de ambigüedad de `servicios.py` no copiaba
  `parse.cantidad`/`parse.unidad_normalizada` al `ResultadoPipeline`; al
  resolver con "articulo_id:N" se persistía cantidad 0.
- **Solución:** la ambigüedad ahora viaja con cantidad, unidad y confianza
  parseadas; prueba en la suite de API (`elegido.cantidad == 1`).

## H8 — Embeddings en pgvector: 0 (PENDIENTE, bloqueado por H4)
- **Hallazgo:** `SELECT count(*) FROM articulos WHERE embedding IS NOT
  NULL;` → **0**. No hay GEMINI_API_KEY ni caché `embeddings.pkl` de la
  que cargar.
- **Qué se hizo:** `scripts/build_embeddings.py` ahora carga la caché a la
  columna pgvector al final (`cargar_a_pgvector`). Con key es un comando:
  `GEMINI_API_KEY=… DATABASE_URL=… uv run python -m scripts.build_embeddings`.
- **Mitigación:** en replay el matcher calcula embeddings léxicos al vuelo
  (el guard de dimensión en `matcher.py` ignora la columna vacía), así que
  el matching sí opera; semántico real queda pendiente de la key.

## H9 — Suite de API migrada del stub al pipeline real
- **Causa:** las pruebas B8 usaban textos del stub eliminado; con replay
  real habrían dado `ReplayNoEncontrado`.
- **Solución:** fixtures propios en `backend/tests/fixtures/replay_api/`
  (REPLAY_DIR en conftest), semilla con TAPA CAZUELA 16 ONZ para
  ambigüedad real y SD centinela solo en artículos que no rompen el flujo
  feliz. La guardiana del conteo ciego mantiene todo blindado con la
  excepción explícita del campo `pregunta` cuando `motivo == "anomalia"`
  (y también vigila el formato con coma "9137,25").
