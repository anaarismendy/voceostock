# `factor_empaque` — definición (A3 · P1 → P2)

**Sincronización dura del plan.** Esta es la definición de 5 líneas que la
Persona 1 le entrega a la Persona 2 para la columna `articulos.factor_empaque`.
Ya está en el DDL como `Numeric` nullable (tarea B1); esto documenta su
semántica.

## Qué es

`factor_empaque` = **cuántas unidades base trae una caja** de ese artículo.
Ej: si una caja de vasos trae 50 vasos, `factor_empaque = 50`.

## Cómo lo usa el pipeline

Cuando el operario cuenta por empaque ("una caja y tres sueltas"), el parser NLU
devuelve `empaque = {cajas, sueltas}` (ver `ConteoParseado`). La conversión a
unidad base es:

```
cantidad_base = cajas * factor_empaque + sueltas
```

## Regla de aprendizaje (NULL)

- `factor_empaque = NULL` significa "no sabemos cuántas trae la caja".
- Si llega un conteo por cajas y el factor es NULL, el agente **pregunta**
  ("¿cuántas unidades trae la caja de {artículo}?") y la respuesta se **persiste**
  en `articulos.factor_empaque` para no volver a preguntar (aprendizaje).
- Contar por sueltas nunca necesita el factor.

## Contrato con P2

- Tipo: `Numeric` nullable (ya existe). Un valor por artículo, no por bodega.
- La escritura del factor aprendido la hace el flujo de resolución (endpoint
  `/resolver`, territorio de P2) cuando el operario responde la pregunta.
