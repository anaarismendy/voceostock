# FASE 1 — VoceoStock: modelo de datos e ingesta del Excel real

> **Instrucciones para Claude Code.** Prerrequisito: Fase 0 completada (existe el monorepo, el contrato congelado, el stub y `data/fixtures/`). El insumo es `data/BODEGAS_Y_STOCK.xlsx`, ya presente en el repo. Esta fase corresponde a las tareas B1–B3 de la Persona 2. Respeta todo lo declarado en `CLAUDE.md` — en particular: unidades canónicas, `conteos` append-only, y que las carpetas `app/models/`, `alembic/` y `data/ingest.py` son propiedad de esta persona.

**Objetivo:** convertir el Excel real en un catálogo maestro limpio + stock teórico por bodega dentro de PostgreSQL, con las suciedades conocidas resueltas y demostrables por pruebas. Al cerrar esta fase, la Persona 1 puede conectar su pipeline a datos reales (tarea A8) y el resto del backend tiene BD.

---

## BLOQUE 1 — Migraciones (alembic)

Configura alembic en `backend/` (env.py leyendo `DATABASE_URL` del entorno) y crea la migración inicial con este modelo. Activa la extensión `vector` en la propia migración (`CREATE EXTENSION IF NOT EXISTS vector`).

```sql
bodegas (
  id            SERIAL PK,
  nombre        TEXT NOT NULL,            -- nombre canónico limpio
  nombre_normalizado TEXT NOT NULL UNIQUE,-- lower, sin tildes, trim
  alias         TEXT[] DEFAULT '{}'       -- nombres originales fusionados
)

articulos (
  id            SERIAL PK,
  nr_articulo   BIGINT NULL,              -- hay artículos sin código
  nombre        TEXT NOT NULL,
  nombre_normalizado TEXT NOT NULL,
  unidad_base   TEXT NOT NULL CHECK (unidad_base IN
                  ('Unidad','Kilogram','Liter','Portion')),
  familia       TEXT NULL,                -- criterio pendiente de decisión;
                                          -- dejar NULL en esta fase
  factor_empaque NUMERIC NULL,            -- unidades por caja; lo llena el
                                          -- aprendizaje del agente (A3)
  embedding     vector(768) NULL          -- lo llena P1 en A8
)
-- índice único parcial: (nr_articulo) WHERE nr_articulo IS NOT NULL
-- índice: (nombre_normalizado)

stock_teorico (
  bodega_id     INT FK bodegas,
  articulo_id   INT FK articulos,
  sd            NUMERIC NOT NULL,
  corte_fecha   DATE NOT NULL DEFAULT CURRENT_DATE,
  orden_original INT NOT NULL,            -- consecutivo CANTIDAD del Excel,
                                          -- necesario para el export 1:1
  PRIMARY KEY (bodega_id, articulo_id, corte_fecha)
)

operarios (
  id            UUID PK DEFAULT gen_random_uuid(),
  nombre        TEXT NOT NULL,
  pin           TEXT NOT NULL,            -- hash, no texto plano
  rol           TEXT CHECK (rol IN ('operario','auditor','lider')),
  telefono      TEXT NULL                 -- para el adaptador WhatsApp
)

sesiones_conteo (
  id            UUID PK DEFAULT gen_random_uuid(),
  bodega_id     INT FK,
  operario_id   UUID FK,
  tipo          TEXT CHECK (tipo IN ('primario','auditoria')),
  estado        TEXT CHECK (estado IN ('abierta','pausada','cerrada'))
                DEFAULT 'abierta',
  iniciada_en   TIMESTAMPTZ DEFAULT now(),
  cerrada_en    TIMESTAMPTZ NULL
)

conteos (
  id            UUID PK DEFAULT gen_random_uuid(),
  sesion_id     UUID FK,
  articulo_id   INT FK NULL,              -- NULL si no_catalogado
  texto_capturado TEXT NULL,              -- lo dicho, para no_catalogado
  cantidad      NUMERIC NOT NULL,
  unidad        TEXT NOT NULL CHECK (unidad IN
                  ('Unidad','Kilogram','Liter','Portion')),
  fuente        TEXT NOT NULL CHECK (fuente IN
                  ('voz-tablet','whatsapp','manual','rfid','bascula')),
  payload_crudo TEXT NULL,
  confianza     NUMERIC NULL,
  anomalia_flag BOOLEAN DEFAULT false,
  anomalia_tipo TEXT NULL,
  anomalia_resuelta BOOLEAN NULL,
  supersede_id  UUID NULL FK conteos(id), -- corrección: apunta al anterior
  activo        BOOLEAN DEFAULT true,     -- false cuando fue superseded
  evidencia_url TEXT NULL,
  creado_en     TIMESTAMPTZ DEFAULT now()
)
-- índice único parcial: (sesion_id, articulo_id) WHERE activo = true
--   → evita duplicados activos dentro de una sesión; entre sesiones
--     distintas NO se bloquea (las colisiones se marcan por evento).

alias_articulos (
  articulo_id   INT FK,
  alias         TEXT NOT NULL,
  PRIMARY KEY (articulo_id, alias)
)
```

Modelos SQLAlchemy espejo en `app/models/`. **DoD del bloque:** `alembic upgrade head` sobre un Postgres pgvector limpio crea todo sin errores; `alembic downgrade base` lo revierte.

## BLOQUE 2 — Ingesta del Excel real (`data/ingest.py`)

Script ejecutable (`python data/ingest.py [--dry-run]`) que lee `data/BODEGAS_Y_STOCK.xlsx` y puebla la BD. Reglas:

1. **Normalización de bodegas:** trim, colapso de espacios múltiples, minúsculas, sin tildes → `nombre_normalizado`. 
2. **Fusión de duplicados de bodega:** dos nombres se fusionan si sus normalizados son iguales O si uno es igual al otro quitándole el sufijo " suministros" o " piscilago". Casos reales que DEBEN quedar fusionados: "cafeteria acuario suministros" (aparece 2 veces), "movil fonda" + "movil fonda suministros", "kiosco bosque suministros" + "kiosco bosques", "caf. Velas suministros" + "caf.velas", "kiosco parqueadero piscilago" + "kiosco paqueadero suministros piscilago" (nota el typo "paqueadero" — usa distancia de edición ≤2 en la comparación sin sufijos). Los nombres originales fusionados se conservan en `alias`. Imprime un **reporte de fusiones** en consola (original → canónico).
3. **Catálogo maestro de artículos:** deduplicar por `Nr.Artículo` cuando exista (el mismo código en varias hojas es UN artículo); cuando `Nr.Artículo` esté vacío (ej. "AGUA 280 ML"), deduplicar por `nombre_normalizado`. Conservar la unidad de la primera aparición; si el mismo artículo aparece con unidades distintas en dos hojas, reportarlo en consola como conflicto (no abortar: gana la primera).
4. **Encabezados sucios:** tolerar `CANTIDA` en vez de `CANTIDAD` (y en general, matchear encabezados por prefijo insensible a mayúsculas/tildes).
5. **Stock teórico:** una fila por (bodega, artículo) con `sd` NUMERIC tal cual viene (decimales incluidos) y `orden_original` = el consecutivo CANTIDAD de la hoja (imprescindible para el export 1:1 de la fase de reportes).
6. **Mapeo hoja→bodega:** el nombre de la hoja de stock se normaliza con las mismas reglas y se resuelve contra la tabla de bodegas fusionada (ej. "STOCK ALMACEN  SUMINISTROS" → "almacen general"… si no hay match razonable, crear la bodega con el nombre de la hoja y reportarlo).
7. **Idempotencia:** re-ejecutar el script no duplica nada (upsert por claves naturales: bodega por normalizado, artículo por nr_articulo/normalizado, stock por PK).
8. **Resumen final en consola:** bodegas creadas y fusionadas, artículos totales y sin código, registros de stock cargados, conflictos de unidad, hojas sin match de bodega.

**DoD del bloque:** dos ejecuciones seguidas → segundo resumen reporta 0 inserciones nuevas; los conteos del resumen son plausibles contra el Excel (~48 bodegas antes de fusión, ~1.420 registros de stock, ≥1 artículo sin código).

## BLOQUE 3 — Fixture de suciedades y pruebas

Crea `backend/tests/fixtures/mini_stock.xlsx` **generado por código** (script `tests/make_mini_excel.py` con openpyxl, así el binario es reproducible) con 10–15 filas que reproduzcan cada suciedad:

- Una bodega repetida con espacios distintos.
- Un par "X" / "X suministros".
- Un par con typo tipo "paqueadero"/"parqueadero".
- Una hoja con encabezado `CANTIDA`.
- Un artículo sin `Nr.Artículo`.
- El mismo `Nr.Artículo` en dos hojas (debe quedar UN artículo, DOS filas de stock).
- Un artículo con unidades contradictorias entre hojas (debe reportar conflicto).
- Un SD decimal.

Pruebas pytest (`tests/test_ingest.py`) que corren la ingesta contra el mini-Excel sobre una BD de prueba y verifican cada caso + la idempotencia (segunda corrida = 0 nuevos). Estas pruebas van a CI; el Excel real NO se usa en CI.

## VERIFICACIONES DE CIERRE (ejecútalas y muéstrame la salida)

1. `alembic upgrade head` en limpio → OK; `\dt` muestra las 7 tablas.
2. `python data/ingest.py` → resumen completo en consola con reporte de fusiones (deben aparecer los casos reales: acuario, fonda, bosques, velas, parqueadero).
3. Segunda ejecución → 0 inserciones nuevas.
4. Query de sanidad: `SELECT count(*) FROM articulos WHERE nr_articulo IS NULL;` ≥ 1; `SELECT count(*) FROM stock_teorico;` ≈ total de filas de stock del Excel; `SELECT nombre, alias FROM bodegas WHERE array_length(alias,1) > 0;` muestra las fusiones.
5. `pytest tests/test_ingest.py` en verde (contra el mini-Excel).
6. Commits `feat(db): migración inicial`, `feat(ingesta): carga del Excel real`, `test(ingesta): fixture de suciedades`, tag `fase-1`.

## Nota de coordinación (humana, no para Claude Code)

- `familia` queda NULL en esta fase: el criterio (¿primera palabra significativa? ¿lista manual?) se decide con el equipo en 10 minutos y se aplica en una migración corta posterior. No bloquea nada del pipeline.
- `factor_empaque` queda NULL: lo definirá la Persona 1 en su tarea A3 (lógica de "una caja y tres sueltas") y se llena por aprendizaje del agente, no por ingesta.
