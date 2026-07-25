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

# Endurecimiento para la demo (rama p2/endurecimiento)

## E1 — El replay ya cubre la ruta de audio
- `scripts/record_audio_fixtures.py`: los audios del guion viven en
  `data/replay/audio/<slug>.webm` y el script genera
  `data/replay/nlu/audio-<hash>.json` copiando el fixture de texto del
  mismo slug (sin red). Con `--live` los regraba contra Gemini.
- OJO: los .webm commiteados son PLACEHOLDERS (bytes de relleno). Antes de
  la demo hay que grabar las 4 frases reales, reemplazar los archivos y
  re-correr el script (2 min, documentado en el docstring).
- E2E verificado con PIPELINE_MODE=replay y sin key: los 4 dictados por
  texto Y por audio → 200 (confirmado/anomalía/ambigüedad/confirmado),
  guion completo en el navegador sin un solo error en pantalla.

## E2 — Degradación con gracia del NLU (adiós al 500)
- Backend: cualquier excepción del pipeline (ReplayNoEncontrado, Gemini
  caído, cuota) o texto capturado vacío → 200 `no_catalogado` con
  `texto_capturado:""` y SIN persistir nada (guardia de texto vacío).
  Prueba: `test_fallo_del_nlu_degrada_sin_500_y_sin_persistir`.
- Frontend: ese estado cae automáticamente al teclado con toast "No pude
  entender el audio, usa el teclado" (+ voz). Verificado en navegador
  grabando audio desconocido en replay.

## E3 — Errores honestos en /resolver y /conteos
- `ApiError` con código en el cliente: 410 → "La pregunta expiró, vuelve a
  dictar el conteo" (verificado en navegador expirando el token por SQL);
  409 → "Esa pregunta ya fue respondida"; 404 token → "La pregunta ya no
  existe"; 404/409 de sesión → mensajes propios de volver a elegir bodega.
  Todos vuelven al estado de escucha; solo la red cae al genérico.

## E4 — articulos.familia poblada (heurística, no taxonomía)
- Migración 0003 + `scripts/populate_familia.py` (rerunnable): primera
  palabra significativa del nombre normalizado, ignorando de/del/la/el/
  en/con/para/x/y/los/las y números. Top: BOLSA 20, CUCHILLO 19,
  PORCION 16, VINO 13, TABLA 13, CAJA 13, SALSA 12…
- La barra por familia del frontend ya muestra grupos reales (ACEITE 1/5,
  etc.); se listan solo las familias con conteos para no enterrar la señal.
- Ruido conocido de la heurística: nombres sucios generan familias tipo
  "AFVT)". Es cosmético y está asumido.

## E5 — Umbral del matcher 0.70 → 0.72 (medición, no corazonada)
- cos("cinta pegante","cinta sellamiento…") = 0.734 (legítimo, pasa);
  cos("destornillador","pasta en tornillos") = 0.704 (falso positivo,
  muere). 0.72 corta en medio. 5 pruebas de matching + la live verdes;
  no hizo falta bajar a 0.71.

## E6 — Latencia percibida
- La transcripción cruda + "Procesando…" aparecen al enviar el dictado:
  **percibido 27 ms** (2 corridas). El ciclo real live quedó en 2,2 s en
  caliente (5,7 s la primera llamada por warmup del pipeline; en replay
  <300 ms). El objetivo <2 s del ciclo real sigue PENDIENTE y es decisión
  de P1 (modelo/prompt intocables por acuerdo).

# Fase final (rama integracion/final → main, tag v1.0-demo)

## F1 — Merges en orden
- PR #7 (endurecimiento) → main. Luego el PR #6 de P3 (rama `p4`, C8–C13):
  6 archivos en conflicto, resueltos conservando ambos lados — login REAL
  por PIN + rol operario/líder de P3; ModoGuiado + checklist de P3 con el
  progreso real por WS, toast, degradación y errores honestos de P2; mock
  con las rutas de ambos. El progreso de la guía se marca por NOMBRE
  (el checklist habla en nr_articulo y el backend real en ids de BD).

## F2 — Warmup del NLU
- Al arrancar, un parse dummy en background (lifespan) calienta el cliente
  Gemini; `WARMUP_BODEGA_ID` precalienta además el catálogo de la bodega
  de la demo. Primera frase real: 5,7 s → 3,0–3,7 s (estable de esa
  corrida: 2,4–2,8 s por varianza de red). El delta de primera llamada
  quedó en ~1 s; no llega a los ~2 s ideales — PENDIENTE menor.

## F3 — C9–C11 contra el sistema real
- P3 los construyó contra el mock: /cierre, /dashboard y /demo/* no
  existían en el backend real → implementados con el mismo contrato
  (app/api/demo.py, con pruebas). El checklist AGUACATE no existe en
  "almacen general": sale "sin contar" (asumido).
- Verificado en navegador con datos reales: cierre con semáforo
  (1 cuadra / 2 sobran / 1 falta / 5 sin contar), filtros, descarga del
  Excel (abierto: columnas 1:1, CANTIDAD/Nr.Artículo/Artículo/Unidad/SD)
  y reproductor de audio de evidencia por fila (HTTP 200 firmado).
- Dashboard en vivo con DOS sesiones simultáneas: el conteo de la segunda
  sesión apareció en el feed en <3 s ("hace 12 s"). "Modo demo corriendo
  solo" NO existe (P3 no lo construyó); la semilla C11 cubre el arranque.
- Seed C11 real: /demo/seed deja el estado EXACTO de docs/DEMO.md
  (aceite cuadra, cazuela +2, costilla −3, resto sin contar, escalonados).

## F4 — Ensayo cronometrado del guion (Playwright, sin errores en pantalla)
- LIVE (Gemini real): login+bodega 0,8s · feliz 3,0s · anomalía 6,6s ·
  ambigüedad 10,3s · guiado 13,7s · corte de red+retry 31,3s · líder
  32,1s. Total interacción ~32 s (la demo hablada será mayor).
- REPLAY (sin key): mismo guion completo en 19,3 s. Cero errores en
  pantalla en ambos modos.

## Pendientes finales (quién)
- Regrabar los 4 audios reales del guion y correr record_audio_fixtures
  (P3/P2, 5 min, antes de la demo).
- Key AIzaSy… permanente de la cuenta con créditos (Ana). La AQ caduca.
- Ciclo live ~2,2–2,8 s vs objetivo 2 s (P1: modelo/prompt congelados).
- Umbral 0.72 quedó verde; si P1 quiere otro corte, tiene las mediciones.

# TTS con ElevenLabs (rama p2/tts)

## T1 — Arquitectura
- POST /api/v1/tts {texto} → mp3. La key vive SOLO en el backend
  (ELEVENLABS_API_KEY en .env). Caché en disco `data/tts_cache/` indexada
  por sha1(modelo:voz:texto) — mismo patrón que los embeddings; cambiar la
  voz invalida la caché sola. Modelo eleven_flash_v2_5 (baja latencia),
  voz por ELEVENLABS_VOICE_ID.
- Cascada en el frontend (useVoz.hablar): backend/caché → si falla
  cualquier cosa, speechSynthesis del navegador. Nunca silencio ni error.
- El mock sirve la misma caché commiteada (hash idéntico); miss → 503 →
  fallback. La demo en mock también habla con ElevenLabs.
- `scripts/warm_tts_cache.py` pre-genera las 18 frases del guion
  (confirmaciones, las 5 preguntas de anomalía con valores del guion,
  ambigüedad y plantillas). Los .mp3 (~0.5 MB) SÍ están commiteados.

## T2 — La voz de la cuenta free (hallazgo)
- La voz elegida ("Marcela - Colombian Girl", 86V9x9hrQds83qf7zaGn) es de
  BIBLIOTECA: el plan free de ElevenLabs devuelve 402 paid_plan_required
  por API (igual "Ana Sofía" es-MX). Solo las voces premade funcionan.
- Default actual: "Bella" (premade, multilingüe — habla español por el
  modelo Flash). Con plan Starter+, poner la Marcela en
  ELEVENLABS_VOICE_ID y re-correr warm_tts_cache (la caché se regenera
  sola). PENDIENTE de decisión/presupuesto del equipo.

## T3 — Verificaciones (ejecutadas)
- Segunda reproducción: X-TTS-Cache: hit, 0 llamadas a la API, **1 ms**
  estable con conexión persistente (la primera medición daba 2,4 s por el
  penalti localhost→IPv6 de Windows: medir contra 127.0.0.1).
- Guion completo en PIPELINE_MODE=replay, backend SIN ninguna key:
  **11/11 frases habladas vía /tts desde la caché** (un 200 sin key solo
  puede salir del disco), 0 fallbacks, 0 errores en pantalla.
- Caché vacía + sin key: /tts 503 → **fallback a speechSynthesis**
  verificado en navegador (spy: 1 speak), tarjeta OK, sin errores.
- Suites: backend 94 passed + ruff OK; frontend 46 + eslint + tsc OK.
