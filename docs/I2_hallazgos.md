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

## Flujos desde el navegador (PASO 4, bodega 3 "almacen general", live Gemini)
Ejecutados con Playwright contra vite (:5173, VITE_API=real) → backend
(:8020) → BD del contenedor. Evidencia: snapshots de accesibilidad,
requests de red y queries SQL.
10. Login PIN 1234 → operario "Operario 1234" creado (find-or-create) →
    41 bodegas reales paginadas → sesión abierta en BD (estado=abierta).
11. Feliz: "treinta y tres litros de aceite de oliva" (dictado por texto,
    NLU live) → tarjeta 33 Liter ACEITE DE OLIVA → ✓ → BD: 33/Liter/
    voz-tablet.
12. Anomalía: pantalla muestra "¿Confirmas 90? El corte anterior registró
    10." → Sí → BD: 90 CAZUELA 16 ONZ, anomalia_flag=t, resuelta=t.
13. Ambigüedad: "una cazuela" → botones CAZUELA/TAPA CAZUELA → elegido
    TAPA → BD: TAPA CAZUELA cantidad 1 (la dictada).
14. Corrección: "Otra cantidad: 19" → BD: 90 activo=f, 19 activo=t con
    supersede_id.
15. No catalogado: "cinco flurbos galacticos" → pantalla "No encontré…"
    → BD: articulo_id NULL, texto "flurbos galacticos", cantidad 5.
16. Teclado manual: buscador con artículos reales de la bodega → cantidad
    → BD: fuente=manual con supersede del conteo por voz anterior.
17. Ruta B de audio: Web Speech deshabilitado a mano → botón pasa a
    grabar (MediaRecorder, mic falsificado con oscilador) → webm de 218KB
    al backend → evidencia firmada: GET 200 con firma / 403 sin firma.
    Gemini live procesó el audio (onda seno → no_catalogado vacío: la
    tubería multimodal completa funciona).
18. Reintento C7: fetch caído 10 s en pleno conteo → badge "1 pendiente"
    + "Sin conexión, reintentando… (intento 3)" → al volver la red el
    conteo llegó a BD sin perderse (7 ARROZ BASMATI).
19. Auditoría conteo ciego UI: bodegas/articulos/progreso sin claves ni
    valores de SD; DOM sin rastro de stock teórico. Única aparición: el
    número dentro de la pregunta de anomalía (excepción sancionada).
C8 en pantalla: toggle Libre/Guiado, "Cuenta ahora (7 de 566): …" con
Saltar, barra global y por familia, punto "En vivo" (WS conectado vía
proxy) actualizando el progreso con cada conteo.

## H9 — Falso positivo semántico con umbral 0.70 (observación para P1)
- Con embeddings reales, "diez destornilladores" matcheó "PASTA EN
  TORNILLOS" (raíz "tornillo"). La validación conversacional lo atrapó
  (regla unidad_incoherente preguntó y el "No" lo descartó), así que no
  llegó nada malo a la BD — pero es el costo del umbral 0.70 (H11 de I1).
  Si P1 prefiere, un margen mayor o un umbral 0.72–0.75 lo mitiga.

## H10 — Latencia live dictado→tarjeta: 2,5–2,7 s (objetivo <2 s) — PENDIENTE
- Medida en navegador (performance.now, 2 corridas) con gemini-flash-latest.
  El backend solo (curl) da ~2,0 s; el resto es proxy+render. Opciones si
  importa: modelo más liviano para NLU (flash-lite), recortar el prompt del
  parser, o presumir el catálogo. En modo replay el ciclo es <300 ms.

## Nota de eficiencia (aceptada para la demo)
- Cada evento WS dispara un refetch de GET /progreso (2–3 por conteo).
  Chatty pero inofensivo a escala de demo; si molestara, bastaría
  debounce en useProgreso.
