# Contrato del API de ingesta — CONGELADO

Fuente de verdad ejecutable: `backend/app/schemas/conteos.py`. Cambiar este
contrato requiere acuerdo de las 3 personas del equipo.

> **REGLA INVIOLABLE:** ninguna respuesta de estos endpoints incluye jamás el
> stock teórico (SD). Conteo ciego.

## `POST /api/v1/conteos`

Único punto de entrada de todos los adaptadores de captura (`fuente` los
identifica: voz en tablet hoy, WhatsApp hoy, RFID o básculas mañana).

### Request

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

### Respuesta — uno de tres estados

**1. `confirmado`** — el pipeline entendió y validó; el conteo quedó guardado.

```json
{ "status": "confirmado",
  "conteo": { "id": "uuid", "articulo_id": 7290,
              "articulo_nombre": "ACEITE DE OLIVA", "cantidad": 33.5,
              "unidad": "Liter", "confianza": 0.95,
              "fuente": "voz-tablet", "evidencia_url": null } }
```

`unidad` solo admite las canónicas: `Unidad | Kilogram | Liter | Portion`.

**2. `requiere_confirmacion`** — el sistema pregunta antes de guardar.

```json
{ "status": "requiere_confirmacion",
  "token_pendiente": "uuid",
  "motivo": "ambiguedad | anomalia | baja_confianza",
  "pregunta": "¿Confirmas 90? El corte anterior registró 10.",
  "candidatos": [ { "articulo_id": 1, "articulo_nombre": "CAZUELA 16 ONZ" } ] }
```

**3. `no_catalogado`** — el artículo no existe en el catálogo de la bodega.

```json
{ "status": "no_catalogado",
  "texto_capturado": "producto xyz", "cantidad": 4, "unidad": "Unidad" }
```

## `POST /api/v1/conteos/{token_pendiente}/resolver`

Resuelve una captura pendiente de confirmación.

### Request

```json
{ "respuesta": "si | no | articulo_id:<int> | cantidad:<float>" }
```

### Respuesta

La misma estructura (los mismos tres estados) que `POST /conteos`.

## Ejemplos

Ver `docs/contrato/ejemplos/` — generados llamando al stub real y validados
contra los schemas Pydantic en las pruebas del backend.
