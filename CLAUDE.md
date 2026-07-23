# VoceoStock — contexto para Claude Code

Producto: captura de inventario por voz con validación conversacional en el
punto de captura. Hackathon; prioridad: demo confiable > elegancia.

Stack: FastAPI + Postgres 16/pgvector + React 18/TS/Tailwind (PWA) + Gemini
API (2.5 Flash para NLU multimodal, gemini-embedding-001 para matching).

## Reglas de dominio (INVIOLABLES)
- Unidades canónicas: Unidad, Kilogram, Liter, Portion. Ninguna otra llega
  a la BD; el parser normaliza sinónimos (kilo/kg/kilito→Kilogram,
  lt/litros→Liter, paquete/unidades→Unidad, porción→Portion,
  arroba→12.5 Kilogram).
- Conteo ciego: el SD (stock teórico) NUNCA aparece en endpoints usados
  durante la captura, ni en el frontend de conteo, ni en mensajes de
  WhatsApp. Solo existe en reportes de cierre.
- `conteos` es append-only: una corrección crea un registro nuevo con
  vínculo al que supersede. Nunca UPDATE de cantidad.
- Contrato único de ingesta: POST /api/v1/conteos; el campo `fuente`
  identifica el adaptador. Ver docs/contrato/contrato.md. El contrato está
  CONGELADO: cambiarlo requiere acuerdo de las 3 personas.
- La firma de app/pipeline/core.py::procesar_conteo está CONGELADA.
  P1 reemplaza el cuerpo, no la firma.

## Reglas técnicas
- Español en UI, mensajes al usuario y preguntas del agente; inglés en
  código, identificadores y commits.
- API keys solo en backend vía .env. Nunca en frontend, nunca en commits.
- Toda función de pipeline (nlu/matching/anomalías) con prueba unitaria.
  Pruebas contra Gemini real: marker @pytest.mark.integration (CI las salta).
- Latencia objetivo captura→confirmación: <2 s (tablet, ruta texto).
- Commits: feat|fix|chore|test(scope): descripción. Ramas: main protegida,
  ramas p1/*, p2/*, p3/* por persona.
- Propiedad de carpetas: P1=app/pipeline/, app/reportes/; P2=app/models/,
  app/api/, data/ingest.py, alembic/; P3=frontend/, docs/DEMO.md. Tocar
  carpeta ajena = avisar por chat antes.

## Datos reales (data/BODEGAS_Y_STOCK.xlsx)
- 9 hojas: 1 listado de 48 bodegas + 8 hojas de stock (~1.420 registros).
- Columnas: CANTIDAD (consecutivo), Nr.Artículo (a veces vacío), Artículo,
  Unidad, SD (decimal).
- Suciedades conocidas: bodegas duplicadas ("cafeteria acuario suministros"
  ×2; "movil fonda" vs "movil fonda suministros"), encabezado "CANTIDA" en
  una hoja, espacios sobrantes, artículos sin Nr.Artículo (ej. AGUA 280 ML).
