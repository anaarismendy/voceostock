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

## H4 — GEMINI_API_KEY: RESUELTO (con matices)
- `.env` creado (gitignored). Dos credenciales disponibles:
  - **AIza… (free tier)**: estable, funciona con `gemini-2.5-flash`;
    límites: 100 items/min en embeddings.
  - **AQ… (cuenta con créditos)**: sin límites free-tier, pero el proyecto
    no expone `gemini-2.5-flash` (404 usuarios nuevos) → usar
    `GEMINI_MODEL_NLU=gemini-flash-latest`. OJO: los tokens `AQ.…` caducan
    rápido (el primero pasó a 401 en <1 h). Para la demo conviene generar
    una key `AIza…` permanente DESDE la cuenta con créditos.
- **Verificado live** (bodega 3): NLU real "veinte litros de aceite de
  oliva" → confirmado ACEITE DE OLIVA 20 L (2,0 s en estado estable);
  "dieciocho kilos de arroz basmati" → anomalía real "¿Confirmas 18? El
  corte anterior registró 2." con el SD de la BD.

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

## H8 — Embeddings en pgvector: RESUELTO
- `SELECT count(*) FROM articulos WHERE embedding IS NOT NULL;` → **936**
  (936/936, cargados con gemini-embedding-001 a 768 dims vía la cuenta
  con créditos; 16,5 s).
- `scripts/build_embeddings.py` carga la caché a pgvector al final
  (`cargar_a_pgvector`) y ahora respeta el free tier: lotes de 20 con
  pausa de 15 s (`EMBED_LOTE`/`EMBED_PAUSA`); `EmbedderGemini` guarda la
  caché por lote para que un 429 a mitad de camino no pierda el progreso.
- En replay el matcher sigue calculando embeddings léxicos al vuelo (el
  guard de dimensión ignora los vectores de otro espacio).

## H9 — Suite de API migrada del stub al pipeline real
- **Causa:** las pruebas B8 usaban textos del stub eliminado; con replay
  real habrían dado `ReplayNoEncontrado`.
- **Solución:** fixtures propios en `backend/tests/fixtures/replay_api/`
  (REPLAY_DIR en conftest), semilla con TAPA CAZUELA 16 ONZ para
  ambigüedad real y SD centinela solo en artículos que no rompen el flujo
  feliz. La guardiana del conteo ciego mantiene todo blindado con la
  excepción explícita del campo `pregunta` cuando `motivo == "anomalia"`
  (y también vigila el formato con coma "9137,25").

## H10 — eslint del frontend reventaba por un artefacto de vite
- **Causa:** `frontend/vite.config.ts.timestamp-*.mjs` (residuo de un vite
  interrumpido) disparaba `no-undef`. No es código fuente.
- **Solución:** borrado; lint verde. Sugerencia a P3: agregar el patrón a
  `.eslintignore`/ignores de eslint.config.js.

## Flujos E2E ejecutados (bodega 3 "almacen general", 566 artículos, replay)
Todos verificados contra la API real en :8020 y la BD del contenedor:
1. Feliz: "treinta y tres litros de aceite de oliva" → confirmado ACEITE
   DE OLIVA (id 299) 33 Liter.
2. Anomalía: "noventa cajas de cazuelas" → pregunta "¿Confirmas 90? El
   corte anterior registró 10." (SD real) → "si" → BD: cantidad 90,
   CAZUELA 16 ONZ, anomalia_flag=t, anomalia_resuelta=t.
3. Ambigüedad: "una cazuela" → candidatos CAZUELA/TAPA CAZUELA →
   "articulo_id:269" → BD: TAPA CAZUELA cantidad 1 (la cantidad dictada
   sobrevive, fix H7).
4. Corrección: "cantidad:19" → supersede verificado (90 activo=f; 19
   activo=t con supersede_id al viejo).
5. No catalogado: "diez destornilladores" → articulo_id NULL,
   texto_capturado "destornillador".
6. Audio: payload_audio_b64 → evidencia_url firmada; GET firmado 200
   (bytes exactos), sin firma 403. Fixture de replay
   data/replay/nlu/audio-cf340b8b772b838d.json.
7. WebSocket: 18 eventos coherentes (conteo_nuevo/progreso/anomalia con
   resolucion); el único SD visible viaja en la pregunta de anomalía.
8. Reporte A9: diferencias con semáforo (3 filas, resumen critico=3) y
   export.xlsx con columnas 1:1 (CANTIDAD=orden_original, Nr.Artículo,
   Artículo, Unidad, SD=cantidad física) ordenado por orden_original.

## Suite y lint
- backend: 84 passed, 16 skipped (integration, sin GEMINI_API_KEY), ruff OK.
- frontend: 1 test OK, eslint OK (tras H10).

## H11 — Umbral de embeddings reales descalibrado (PENDIENTE, decisión de P1)
- **Hallazgo:** con la key viva, 16/17 pruebas de integración pasan. La
  única falla real: `test_cinta_pegante_embeddings_reales` — "cinta
  pegante" da `no_catalogado` porque el coseno máximo real de
  gemini-embedding-001 (768d) es 0,734 y el umbral de EmbedderGemini es
  0,80. Ranking correcto: cinta sellamiento 0,734 > cinta enmascarar
  0,725 > resto <0,58.
- **Dato extra:** el top-2 queda a 0,009 (< margen 0,05), así que con
  umbral ~0,70 el resultado sería AMBIGÜEDAD entre las dos cintas — UX
  razonable ("¿cuál cinta?").
- **Propuesta para P1:** bajar umbral a ~0,70 y aceptar ambigüedad en esa
  prueba (o ajustar margen). No se tocó por ser calibración del matcher
  (dominio P1). CI no se ve afectado (las integration se saltan sin key).

## Credenciales fijadas (decisión del equipo)
- `.env`: key AQ de la cuenta con créditos + `GEMINI_MODEL_NLU=
  gemini-flash-latest` (ese proyecto no expone gemini-2.5-flash).
- RIESGO CONOCIDO: los tokens `AQ.…` caducan (~1 h observada). Antes de la
  demo, generar una key permanente `AIzaSy…` desde ESA cuenta en
  https://aistudio.google.com/apikey y reemplazarla en .env.
- Con la key gratuita (AIza actual de respaldo) el free tier limita:
  10 req/min de NLU (11 pruebas de integración fallaron por 429, no por
  bugs) y 100 items/min de embeddings.
