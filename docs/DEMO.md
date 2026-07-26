# Guion de demo — VoceoStock (C11)

> Objetivo del guion: que la demo **nunca se caiga** y que en < 5 minutos el
> jurado entienda la propuesta: **captura de inventario por voz con validación
> conversacional en el punto de captura**, sobre una plataforma de ingesta con
> adaptadores. Prioridad: robusto > bonito. Cada paso trae su **plan B**.

Este guion corre en DOS modos (fase final):

- **Mock** (`npm run dev` a secas): sin backend ni BD ni llaves. Determinista.
- **Real**: backend + Postgres, con Gemini **live** (si hay key con saldo) o
  **replay** (sin red — los dictados del guion están grabados). Arranque:
  ```
  docker compose up -d db
  cd backend && uv run uvicorn app.main:app --port 8020        # live si hay GEMINI_API_KEY en el entorno; replay si no
  cd frontend && VITE_API=real VITE_API_PROXY=http://localhost:8020 npm run dev
  ```
  Sembrar/reiniciar la demo real: `POST /api/v1/demo/seed?bodega_id=3` y
  `POST /api/v1/demo/reset?bodega_id=3` (misma consola F12 del navegador).
  OJO replay: la ruta de audio usa los archivos de `data/replay/audio/`
  (regrabar las 4 frases reales y correr
  `uv run python -m scripts.record_audio_fixtures` antes de la demo).
  En modo real usa la bodega **"almacen general"** (566 artículos; AGUACATE
  del checklist no existe en esa bodega y sale "sin contar").

---

## 0. Preparación (antes de que entre el jurado)

1. Instalar/verificar el entorno (una sola vez):
   ```
   setup-frontend.bat        (doble clic, o en terminal desde la raíz del repo)
   ```
2. Levantar la app en modo demo:
   ```
   cd frontend
   npm run dev               (usa el mock por defecto: VITE_API=mock)
   ```
3. Abrir `http://localhost:5173` en **Chrome** (Web Speech API funciona mejor ahí).
   Idealmente una **tablet** o Chrome en modo dispositivo táctil.
4. **Dar permiso de micrófono** cuando el navegador lo pida (una vez).
5. Al arrancar, el mock ya viene **sembrado** (C11): el panel del líder no está
   vacío. Ver "Estado sembrado" abajo.

### Reiniciar la demo entre ensayos / entre jurados

- **Opción fácil:** reiniciar `npm run dev` → vuelve al estado sembrado.
- **Sin reiniciar** (desde la consola del navegador, F12):
  ```js
  fetch('/api/v1/demo/reset', { method: 'POST' })  // vacía todo (contar desde cero en vivo)
  fetch('/api/v1/demo/seed',  { method: 'POST' })  // vuelve al estado sembrado
  ```

### Estado sembrado (lo que el líder ve al abrir)

| Artículo | Contado | Teórico | Estado |
|---|---|---|---|
| ACEITE DE OLIVA | 33 | 33 | **Cuadra** |
| CAZUELA 16 ONZ | 12 | 10 | **Sobra +2** |
| COSTILLA DE RES | 63.14 | 66.14 | **Falta −3** |
| POLLO ENTERO, AGUACATE, ABRELATAS, CHORIZO, ACEITE DE AJONJOLI | 0 | — | Sin contar |

> Los "sin contar" son los que se van a **contar en vivo** durante la demo.

---

## 1. El problema (30 s, hablado, sin tocar la app)

"Hoy el inventario en bodega se cuenta con papel y lápiz y se transcribe a un
Excel del ERP. Es lento, se equivocan al digitar, y los errores se descubren
tarde. VoceoStock deja **contar hablando** y valida en el momento —antes de
guardar— contra el catálogo y el histórico."

---

## 2. Operario: contar por voz (90 s)

1. **Login**: elegir **Operario**, teclear cualquier PIN de 4 dígitos.
2. **Bodega**: buscar y tocar una bodega (ej. "almacen general").
3. Estás en la **pantalla de conteo** (Modo libre). Tocar el **micrófono** y decir:

   > "treinta y tres litros de aceite de oliva"

   → Aparece la **tarjeta de confirmación** grande (33 · Liter · ACEITE DE OLIVA)
   y el sistema **lo dice en voz alta**. Tocar ✓.

   **Plan B (mic falla o auditorio ruidoso):** usar el **teclado** de abajo —
   buscar "aceite de oliva", teclear la cantidad, Registrar. Mismo resultado.

### 2a. El momento estelar — validación conversacional

4. Tocar el micrófono y decir:

   > "noventa cazuelas"

   → En vez de guardar a ciegas, **pregunta**: *"¿Confirmas 90 unidades de
   CAZUELA 16 ONZ? El corte anterior registró 10."* (anomalía). Responder **Sí**
   (o "otra cantidad").

5. Decir solo:

   > "cazuela"

   → **Ambigüedad**: ofrece 2 candidatos (CAZUELA 16 ONZ / CALDERO…). Tocar el
   correcto. *(Este es el corazón del pitch: valida en el punto de captura.)*

   **Plan B:** la pregunta también se puede responder por voz (botón 🎤 en la
   tarjeta), pero los botones táctiles nunca dependen del reconocimiento.

---

## 3. Modo guiado + progreso (45 s)

6. Arriba, cambiar a **Modo guiado**.
   → El sistema dice **qué contar ahora** ("Cuenta ahora: POLLO ENTERO"). Decir
   la cantidad (o teclearla) → **Registrar**. Avanza solo al siguiente.
   La **barra de progreso** sube. Se puede **Saltar** un artículo.

   "Así garantizamos cobertura: el operario no tiene que recordar la lista, el
   sistema lo lleva de la mano."

---

## 4. Robustez ante fallos de red (30 s) — opcional pero potente

7. Cortar el wifi (o modo avión) y contar un artículo.
   → El conteo **no se pierde**: aparece el badge **"N pendiente(s)"** y el
   sistema **reintenta con backoff**. Reconectar → se envía solo.

   "En una bodega el wifi se cae. Ningún conteo se pierde nunca."

---

## 5. Líder: dashboard en vivo + cierre (60 s)

8. **Cerrar sesión** → entrar de nuevo como **Líder** (cualquier PIN) → elegir bodega.
9. Pestaña **En vivo**: el **dashboard** muestra, en tiempo real, los conteos que
   acaban de entrar (feed "hace X", totales subiendo). Indicador **EN VIVO**.
10. Pestaña **Cierre**: la **tabla de diferencias** contado vs. teórico, con
    **Cuadra / Sobra / Falta / Sin contar** y el resumen arriba.

    > **Conteo ciego:** el stock teórico (SD) **solo aparece aquí**, en el reporte
    > del líder. Nunca durante la captura. Es una regla de diseño inviolable.

---

## 6. Cierre del pitch (20 s)

"Es una **plataforma de ingesta con adaptadores**: hoy voz en tablet, mañana
WhatsApp, RFID o básculas — todos entran por el mismo contrato. Y al cierre
exporta el Excel idéntico al del ERP. Contar deja de ser el cuello de botella."

---

## Checklist de arranque (imprimir/tener a mano)

- [ ] `npm run dev` corriendo, `http://localhost:5173` abierto en Chrome.
- [ ] Permiso de micrófono concedido.
- [ ] Volumen del equipo audible (la app responde hablando).
- [ ] Demo sembrada (o `demo/seed` ejecutado).
- [ ] Plan B repasado: teclado (mic), botones (voz), badge de pendientes (wifi).

## Si algo falla en vivo (orden de rescate)

1. **Mic no capta** → teclado numérico + buscador (siempre visible).
2. **Reconocimiento raro** → tras 2 fallos la app pasa sola a **grabar audio**.
3. **Wifi cae** → badge de pendientes; sigue contando, se reintenta.
4. **La app se traba** → recargar la pestaña; el mock re-siembra al reiniciar `npm run dev`.
5. **Todo falla** → **video de respaldo** (C12).
