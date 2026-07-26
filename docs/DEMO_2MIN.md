# Demo completa en 2 minutos — VoceoStock

Recorrido cronometrado que muestra **toda la navegación y todas las
funcionalidades** de la plataforma: captura por voz, validación conversacional
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

### 0:00 – 0:15 · Login y bodega

1. Teclear PIN **0000** → entra como **operario** (el rol lo decide el
   backend, no la pantalla; un PIN no dado de alta es rechazado).
2. En **Selección de bodega**: usar el buscador, tocar una bodega
   (p. ej. "bodega principal" en mock / "almacen general" en real).

*Qué se demostró: login por PIN con rol del backend, catálogo real de bodegas
con búsqueda.*

### 0:15 – 0:35 · Contar por voz (camino feliz)

3. En la **pantalla de conteo** (Modo libre), tocar el **micrófono** y decir:

   > "treinta y tres litros de aceite de oliva"

   → Tarjeta de confirmación grande (33 · Liter · ACEITE DE OLIVA) y el
   sistema **lo dice en voz alta**. Tocar ✓.

   *Si el mic falla:* el **teclado manual** de abajo hace exactamente lo mismo
   (buscar artículo, teclear cantidad, Registrar) — ese fallback es una
   funcionalidad, muéstralo con una frase.

### 0:35 – 1:00 · Validación conversacional (el momento estelar)

4. Micrófono: **"noventa cajas de cazuelas"**
   → **Anomalía**: en vez de guardar a ciegas, pregunta con voz:
   *"¿Confirmas 90 unidades de CAZUELA 16 ONZ? El corte anterior registró
   10."* Responder **Sí** (tocando o por voz).
5. Micrófono: **"una cazuela"**
   → **Ambigüedad**: dos tarjetas candidatas. Tocar la correcta.

*Qué se demostró: el pipeline valida EN el punto de captura — anomalías contra
el histórico y desambiguación del catálogo, respondibles por toque o voz.
Nótese que durante la captura nunca se ve el stock teórico (conteo ciego).*

### 1:00 – 1:20 · Modo guiado + inventario de la bodega

6. Arriba, cambiar a **Modo guiado**: el sistema dicta *qué* contar ahora
   ("Cuenta ahora: POLLO ENTERO"). Decir o teclear **12** → Registrar →
   avanza solo; la **barra de progreso** sube. Tocar **Saltar** una vez.
7. Abrir la **lista de inventario** (botón de progreso): artículos de la
   bodega con ✓ en los contados y filtro "solo pendientes". Cerrarla.

*Qué se demostró: cobertura garantizada sin memorizar la lista, y visibilidad
de qué falta — sin mostrar jamás cantidades teóricas.*

### 1:20 – 1:30 · Cambio de rol

8. **Cerrar sesión** → PIN **1111** → misma bodega → entra al **Panel del
   líder**.

### 1:30 – 1:55 · Panel del líder

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
