# Demo completa en 2 minutos — VoceoStock

Recorrido cronometrado que abre con **el problema que se resuelve y el stack**
como intro, y luego muestra **toda la navegación y todas las funcionalidades**
de la plataforma: captura por voz, validación conversacional
(anomalía + ambigüedad), modo guiado, panel del líder (en vivo, cierre,
ajustes) y ciclos de inventario. Pensado para correrse en **modo mock** (cero
setup, determinista); al final está la variante contra el backend real.

> Guion largo de pitch (5 min, con plan B por paso): [DEMO.md](DEMO.md).

---

## Preparación (antes de arrancar el cronómetro)

```powershell
cd frontend
npm install        # solo la primera vez
npm run dev        # modo mock por defecto: vite responde todo el contrato
```

- [ ] Abrir **http://localhost:5173** en **Chrome** (Web Speech funciona mejor ahí).
- [ ] Conceder **permiso de micrófono** cuando lo pida (una vez).
- [ ] **Volumen audible**: la app responde hablando.
- [ ] El mock ya viene **sembrado**: el panel del líder no está vacío
      (aceite cuadra, cazuela +2, costilla −3, varios sin contar).

Para reiniciar entre ensayos: recargar `npm run dev`, o en la consola F12:
`fetch('/api/v1/demo/seed', {method:'POST'})`.

---

## El recorrido (2:00)

### 0:00 – 0:20 · Intro: el problema y el stack (hablado, sobre la pantalla de login)

> "Hoy el inventario en bodega se cuenta con papel y lápiz y se transcribe a
> mano a un Excel del ERP: lento, con errores de digitación que se descubren
> días después. **VoceoStock** deja contar hablando y valida en el momento —
> antes de guardar — contra el catálogo y el histórico.
>
> El stack: **FastAPI + Postgres con pgvector** en el backend, **React PWA**
> en tablet, **Gemini 2.5 Flash** para entender el dictado (texto o audio),
> **embeddings de Gemini** para matchear contra el catálogo real de 48
> bodegas, y **ElevenLabs** para que el agente responda con voz natural."

### 0:20 – 0:35 · Login y bodega

1. Teclear PIN **0000** → entra como **operario** (el rol lo decide el
   backend, no la pantalla; un PIN no dado de alta es rechazado).
2. En **Selección de bodega**: usar el buscador, tocar una bodega
   (p. ej. "bodega principal" en mock / "almacen general" en real).

*Qué se demostró: login por PIN con rol del backend, catálogo real de bodegas
con búsqueda.*

### 0:35 – 0:50 · Contar por voz (camino feliz)

3. En la **pantalla de conteo** (Modo libre), tocar el **micrófono** y decir:

   > "treinta y tres litros de aceite de oliva"

   → Tarjeta de confirmación grande (33 · Liter · ACEITE DE OLIVA) y el
   sistema **lo dice en voz alta**. Tocar ✓.

   *Si el mic falla:* el **teclado manual** de abajo hace exactamente lo mismo
   (buscar artículo, teclear cantidad, Registrar) — ese fallback es una
   funcionalidad, muéstralo con una frase.

### 0:50 – 1:15 · Validación conversacional (el momento estelar)

4. Micrófono: **"noventa cajas de cazuelas"**
   → **Anomalía**: en vez de guardar a ciegas, pregunta con voz:
   *"¿Confirmas 90 unidades de CAZUELA 16 ONZ? El corte anterior registró
   10."* Responder **Sí** (tocando o por voz).
5. Micrófono: **"una cazuela"**
   → **Ambigüedad**: dos tarjetas candidatas. Tocar la correcta.

*Qué se demostró: el pipeline valida EN el punto de captura — anomalías contra
el histórico y desambiguación del catálogo, respondibles por toque o voz.
Nótese que durante la captura nunca se ve el stock teórico (conteo ciego).*

### 1:15 – 1:30 · Modo guiado + inventario de la bodega

6. Arriba, cambiar a **Modo guiado**: el sistema dicta *qué* contar ahora
   ("Cuenta ahora: POLLO ENTERO"). Decir o teclear **12** → Registrar →
   avanza solo; la **barra de progreso** sube. Tocar **Saltar** una vez.
7. Abrir la **lista de inventario** (botón de progreso): artículos de la
   bodega con ✓ en los contados y filtro "solo pendientes". Cerrarla.

*Qué se demostró: cobertura garantizada sin memorizar la lista, y visibilidad
de qué falta — sin mostrar jamás cantidades teóricas.*

### 1:30 – 1:35 · Cambio de rol

8. **Cerrar sesión** → PIN **1111** → misma bodega → entra al **Panel del
   líder**.

### 1:35 – 1:55 · Panel del líder

9. Arriba, la **barra de inventario**: qué ciclo se está viendo
   ("Inventario #N", fechas) y los controles para **abrir/cerrar** un ciclo —
   el cierre y el dashboard filtran por ese ciclo.
10. Pestaña **En vivo**: los conteos que acabas de dictar aparecen en el feed
    ("hace X s"), totales y anomalías subiendo.
11. Pestaña **Cierre**: tabla contado vs. teórico con semáforo **Cuadra /
    Sobra / Falta / Sin contar**, filtros y botón de **export Excel** (formato
    1:1 con el del ERP). *Este es el único lugar de toda la app donde aparece
    el SD.*
12. Pestaña **Ajustes** (vistazo de 5 s): umbrales de confianza editables en
    caliente, sinónimos aprendidos, y operarios con su precisión histórica y
    ajuste de confianza.

### 1:55 – 2:00 · Cierre

"Todo entró por un único contrato de ingesta — hoy voz y teclado; mañana
WhatsApp, RFID o básculas se enchufan sin tocar nada más. Y el cierre exporta
el Excel idéntico al del ERP."

---

## Variante contra el backend real (mismo guion)

Arranque (detalle en [COMO_CORRER.md](COMO_CORRER.md)):

```powershell
docker compose up -d db
cd backend
$env:DATABASE_URL='postgresql+psycopg://voceo:voceo@localhost:5433/voceostock'
$env:SECRET_KEY='demo-secret'; $env:WARMUP_BODEGA_ID='3'
uv run uvicorn app.main:app --port 8020     # live con GEMINI_API_KEY; replay sin ella
# otra terminal:
cd frontend
$env:VITE_API='real'; $env:VITE_API_PROXY='http://localhost:8020'
npm run dev
```

Sembrar: `Invoke-RestMethod -Method Post 'http://localhost:8020/api/v1/demo/seed?bodega_id=3'`

Diferencias con el mock:

- Bodega: **"almacen general"** (566 artículos reales). Nunca "administracion" (0).
- El líder debe tener un **inventario abierto** (barra del panel) para que las
  sesiones de los operarios enganchen.
- En **replay** (sin key/red) solo se entienden las frases grabadas — que son
  exactamente las de este guion: *treinta y tres litros de aceite de oliva* ·
  *noventa cajas de cazuelas* · *una cazuela* · *siete kilos de arroz basmati*;
  en guiado, cantidades **12** y **5**.
- En **live** puedes dictar lo que quieras, con muletillas incluidas
  ("mmm… eeh… cinta pegante, como catorce").

## Si algo falla en vivo

1. **Mic no capta** → teclado manual (siempre visible), misma demo.
2. **Reconocimiento raro** → tras 2 fallos la app pasa sola a grabar audio.
3. **Wifi cae** → badge "N pendiente(s)": sigue contando, reintenta con
   backoff y se envía solo al volver la red. (Esto también es demostrable a
   propósito: modo avión 10 s.)
4. **Se traba** → recargar la pestaña; reiniciar `npm run dev` re-siembra.

---

## Guion de narración para ElevenLabs (~2 min)

Texto listo para pegar en ElevenLabs como voz en off del video. Cada bloque
corresponde a un tramo del recorrido de arriba; los `[tiempo]` son referencia
para sincronizar en la edición, **no se pegan** en el sintetizador. Voz
sugerida: español latino, tono conversacional, velocidad normal.

**[0:00 — pantalla de login]**
En las bodegas de Colsubsidio, el inventario todavía se cuenta con papel y
lápiz, y después alguien lo transcribe a mano al Excel del ERP. Es lento,
se digita mal, y los errores se descubren días después. VoceoStock lo
resuelve dejando contar con la voz, y validando cada captura en el momento,
antes de guardarla. Está construido con FastAPI y Postgres con pgvector,
una PWA en React para la tablet, Gemini dos punto cinco Flash que entiende
el dictado en texto o audio, embeddings de Gemini para matchear contra el
catálogo real de cuarenta y ocho bodegas, y ElevenLabs para que el agente
responda con voz natural.

**[0:20 — login y bodega]**
El operario entra con su PIN. El sistema decide su rol, y elige la bodega
donde va a contar.

**[0:35 — conteo por voz]**
Ahora, simplemente habla: "treinta y tres litros de aceite de oliva". El
sistema entiende, matchea el artículo, y confirma en voz alta. Un toque, y
queda guardado. Si el micrófono falla, el teclado de abajo hace exactamente
lo mismo.

**[0:50 — validación conversacional]**
Y aquí está el diferenciador. "Noventa cajas de cazuelas". En vez de guardar
a ciegas, el sistema detecta que ese número no cuadra con el histórico, y
pregunta antes de guardar. Si el dictado es ambiguo, como "una cazuela",
ofrece los candidatos para elegir con un toque. El error se atrapa en el
punto de captura, no días después.

**[1:15 — modo guiado]**
En modo guiado, el sistema le dicta al operario qué contar ahora. Él solo
pone la cantidad, y la barra de progreso garantiza que nada se quede sin
contar. Y ojo: durante toda la captura, el operario nunca ve el stock
teórico. Conteo ciego, siempre.

**[1:30 — panel del líder]**
Del otro lado, el líder abre el ciclo de inventario y lo ve todo en vivo:
cada conteo entrando, las anomalías, el avance. Y en el cierre, la tabla de
diferencias con semáforo: qué cuadra, qué sobra, qué falta. De ahí exporta
un Excel idéntico al del ERP. Y en ajustes, afina los umbrales de confianza,
revisa los sinónimos aprendidos y gestiona a sus operarios con su precisión
histórica, todo sin tocar código.

**[1:50 — cierre]**
Todo entró por un único contrato de ingesta. Hoy es voz en una tablet;
mañana, WhatsApp, RFID o básculas se enchufan sin cambiar nada más. Con
VoceoStock, contar deja de ser el cuello de botella.
