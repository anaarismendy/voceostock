# VoceoStock

Captura de inventario por voz con validación conversacional. Stack: FastAPI +
Postgres 16/pgvector + React PWA + Gemini. Ver `CLAUDE.md` para las reglas de
dominio (conteo ciego, unidades canónicas, conteos append-only).

## Arranque

```bash
docker compose up -d            # db en host:5433, api en host:8010
cd backend
uv run alembic upgrade head     # migraciones (DATABASE_URL apunta a localhost:5433)
uv run python ../data/ingest.py # carga el Excel real
uv run uvicorn app.main:app --reload  # API local en :8000 (o usa el contenedor :8010)
```

## Secuencia de demo con httpie (B4–B5)

Necesitas un operario (la ingesta no crea ninguno):

```sql
INSERT INTO operarios (nombre, pin, rol) VALUES ('Ana', 'hash-pin', 'operario');
```

```bash
API=http://localhost:8000
OP=$(psql ... -c "SELECT id FROM operarios LIMIT 1")   # uuid del operario

# 1. Crear sesión (idempotente: repetirla devuelve la misma sesión abierta)
http POST $API/api/v1/sesiones bodega_id:=1 operario_id=$OP tipo=primario
# → { "sesion_id": "...", "bodega": {...}, "total_articulos": N }

# 2. Conteo confirmado
http POST $API/api/v1/conteos sesion_id=$SESION bodega_id:=1 operario_id=$OP \
    fuente=voz-tablet payload_texto="treinta litros de aceite"
# → { "status": "confirmado", "conteo": {...} }

# 3. Conteo con anomalía → requiere confirmación
http POST $API/api/v1/conteos sesion_id=$SESION bodega_id:=1 operario_id=$OP \
    fuente=voz-tablet payload_texto="noventa cajas de cazuelas"
# → { "status": "requiere_confirmacion", "token_pendiente": "...", ... }

# 4. Resolver con "si"
http POST $API/api/v1/conteos/$TOKEN/resolver respuesta=si
# ("no" → { "status": "descartado" }; también articulo_id:<int> / cantidad:<float>)

# 5. Progreso — muestra 2 contados y NUNCA el SD (conteo ciego)
http GET $API/api/v1/sesiones/$SESION/progreso

# 6. Audio como evidencia: la respuesta trae evidencia_url firmada (60 min)
http POST $API/api/v1/conteos sesion_id=$SESION bodega_id:=1 operario_id=$OP \
    fuente=voz-tablet payload_audio_b64="$(base64 -w0 audio.webm)"
http GET "$API<evidencia_url>"       # 200 con firma; sin firma → 403

# 7. Eventos en vivo (conteo_nuevo / anomalia / progreso / colision)
npx wscat -c ws://localhost:8000/ws/bodegas/1
```

## Pruebas

```bash
cd backend && uv run pytest      # usa la BD voceostock_test en localhost:5433
```
