# I2 — Integración frontend (p3) + backend real — hallazgos

Rama: `integracion/i2` (desde main con I1 mergeado, PR #4). Cada hallazgo
con causa, solución y estado.

## H1 — Consolidación de main
- PR #4 (`integracion/i1` → main) mergeado sin squash, CI verde. La rama
  de P3 es `p3` plana (mismo namespace que p1/p2) y mergeó SIN conflictos.
- Umbral de embeddings (H11 de I1) aplicado por P2 porque P1 no lo empujó:
  `EmbedderGemini.umbral` 0.80 → 0.70 (medición: mejor coseno real de un
  sinónimo legítimo = 0.734). La prueba de integración acepta match o
  ambigüedad entre cintas; 5 pruebas de matching + la live pasan.

## H2 — El frontend inventaba la sesión (CRÍTICO)
- **Causa:** `nuevoConteoRequest` generaba `sesion_id: crypto.randomUUID()`
  en CADA conteo; el mock lo ignoraba, el backend real responde 404
  "sesión desconocida".
- **Solución:** la sesión REAL se crea al elegir bodega
  (POST /api/v1/sesiones, idempotente) y vive en `OperarioContext`
  (`sesionId`); `nuevoConteoRequest` la recibe obligatoria.

## H3 — El operario también era inventado
- **Causa:** `nuevoOperario(pin)` fabricaba un UUID local → 404 "operario
  desconocido" al crear la sesión real.
- **Solución:** endpoint nuevo POST /api/v1/operarios/login
  (find-or-create por PIN; ponytail: PIN en texto plano, auth real fuera
  de alcance del hackathon) + `LoginPin` async con manejo de error.

## H4 — Faltaban endpoints reales que el mock ya servía
- **Causa:** GET /api/v1/bodegas y GET /api/v1/articulos existían solo en
  el mock de P3 (que lee los CSV crudos, con bodegas duplicadas).
- **Solución:** router `app/api/catalogo.py`: /bodegas (fusionadas, de la
  BD) y /articulos?bodega_id (SIN SD — conteo ciego, con prueba que lo
  blinda). El frontend filtra artículos por la bodega elegida.

## H5 — El mock resolvía "no" fuera de contrato
- **Causa:** `mock-server/store.ts` re-preguntaba (baja_confianza) al
  responder "no"; el backend real devuelve `{status: "descartado"}`.
- **Solución:** mock alineado al contrato; ejemplos de anomalía ya traían
  el saldo en la pregunta desde I1 (el mock los recarga del disco, quedó
  coherente sin tocar nada).

## H6 — El frontend no manejaba `descartado`
- **Solución:** cuarto estado en `ConteoResponse` + toast breve
  ("Conteo descartado") y volver a escuchar, con anuncio por voz.

## H7 — @types/node declarado pero no instalado
- **Causa:** `npm install` no se había corrido tras el cambio de P3 que
  agregó `@types/node` → `tsc -b` fallaba con TS2688.
- **Solución:** `npm install` (lockfile ya lo cubría); tsc limpio.

## H8 — C8 no existía (ni el hook de polling que se esperaba)
- **Solución:** implementado desde cero: `useProgreso` se suscribe al
  WebSocket REAL `/ws/bodegas/{id}` (proxy `ws: true` en vite) y refresca
  GET /progreso con cada evento; si el WS no conecta o se cae, degrada a
  polling cada 10 s (el mock no tiene WS y funciona igual). UI: toggle
  Libre/Guiado (guiado recorre el catálogo con "Saltar"), barra global y
  por familia (`PanelProgreso`), punto verde = en vivo.
- El residuo `vite.config.ts.timestamp-*` quedó en los ignores de eslint
  (H10 de I1).

## Contrato de audio (paso 9)
- MediaRecorder produce `audio/webm;codecs=opus` (o el default del
  navegador); `blobABase64` manda SOLO el base64 (sin data-url ni mime) en
  `payload_audio_b64` — el contrato no tiene campo de mime y el backend
  guarda `.webm` por defecto (`storage.guardar_audio`). Coherente de punta
  a punta; verificación en navegador en el PASO 4.
