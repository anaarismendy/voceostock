"""Normalización de unidades a las 4 canónicas (regla INVIOLABLE de CLAUDE.md).

Ninguna unidad fuera de {Unidad, Kilogram, Liter, Portion} llega a la BD. El
parser de Gemini ya intenta devolver la canónica, pero esto es la red de
seguridad determinista: aunque el modelo devuelva "arroba" o "gramos", aquí se
resuelve la unidad y el factor que multiplica la cantidad.

`normalizar_unidad("arroba") -> ("Kilogram", 12.5)` — una arroba son 12.5 kg,
así que la cantidad se multiplica por 12.5 y la unidad queda en Kilogram.
"""

from app.pipeline.normalizacion import normalizar

UNIDADES_CANONICAS = ("Unidad", "Kilogram", "Liter", "Portion")

# sinónimo normalizado -> (unidad canónica, factor sobre la cantidad)
_SINONIMOS: dict[str, tuple[str, float]] = {
    # Unidad
    "unidad": ("Unidad", 1.0),
    "unidades": ("Unidad", 1.0),
    "und": ("Unidad", 1.0),
    "un": ("Unidad", 1.0),
    "u": ("Unidad", 1.0),
    "paquete": ("Unidad", 1.0),
    "paquetes": ("Unidad", 1.0),
    "pieza": ("Unidad", 1.0),
    "piezas": ("Unidad", 1.0),
    "caja": ("Unidad", 1.0),  # el factor real de la caja lo aporta factor_empaque
    "cajas": ("Unidad", 1.0),
    # Kilogram
    "kilogram": ("Kilogram", 1.0),
    "kilogramo": ("Kilogram", 1.0),
    "kilogramos": ("Kilogram", 1.0),
    "kilo": ("Kilogram", 1.0),
    "kilos": ("Kilogram", 1.0),
    "kilito": ("Kilogram", 1.0),
    "kilitos": ("Kilogram", 1.0),
    "kg": ("Kilogram", 1.0),
    "kgs": ("Kilogram", 1.0),
    "gramo": ("Kilogram", 0.001),
    "gramos": ("Kilogram", 0.001),
    "g": ("Kilogram", 0.001),
    "gr": ("Kilogram", 0.001),
    "arroba": ("Kilogram", 12.5),
    "arrobas": ("Kilogram", 12.5),
    # Liter
    "liter": ("Liter", 1.0),
    "litro": ("Liter", 1.0),
    "litros": ("Liter", 1.0),
    "lt": ("Liter", 1.0),
    "lts": ("Liter", 1.0),
    "l": ("Liter", 1.0),
    "mililitro": ("Liter", 0.001),
    "mililitros": ("Liter", 0.001),
    "ml": ("Liter", 0.001),
    # Portion
    "portion": ("Portion", 1.0),
    "porcion": ("Portion", 1.0),
    "porciones": ("Portion", 1.0),
    "porcin": ("Portion", 1.0),  # "porción" sin tilde tras normalizar mantiene la ó->o
    "racion": ("Portion", 1.0),
    "raciones": ("Portion", 1.0),
}


def normalizar_unidad(unidad_texto: str | None) -> tuple[str | None, float]:
    """Devuelve (unidad_canónica | None, factor sobre la cantidad).

    None si el texto no corresponde a ninguna unidad conocida (deja que el
    llamador decida; no inventamos unidad)."""
    clave = normalizar(unidad_texto)
    if not clave:
        return None, 1.0
    if clave in UNIDADES_CANONICAS_NORM:
        return UNIDADES_CANONICAS_NORM[clave], 1.0
    return _SINONIMOS.get(clave, (None, 1.0))


# Mapa auxiliar: forma normalizada de cada canónica -> canónica original.
UNIDADES_CANONICAS_NORM = {normalizar(u): u for u in UNIDADES_CANONICAS}


def es_unidad_entera(unidad: str | None) -> bool:
    """Unidad, paquete, porción: no admiten fracciones. Kilogram/Liter sí."""
    return unidad in ("Unidad", "Portion")
