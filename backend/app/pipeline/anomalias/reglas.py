"""Motor de anomalías (tarea A6) — el diferenciador de la solución.

Cinco reglas puras `(conteo_parseado, articulo) -> Anomalia`. Cada una decide si
frenar y guardar, y con qué pregunta en español. El contexto (SD del artículo,
unidad del catálogo) llega en el `ArticuloCtx`.

Conteo ciego: el SD no se muestra ANTES de que el operario dicte su cantidad.
ÚNICA excepción (decisión de producto, reto Colsubsidio): la pregunta de una
anomalía de orden de magnitud (`ratio_sd`) SÍ cita el saldo del último corte,
porque ocurre después de que el operario ya comprometió su número. Las otras
cuatro reglas siguen sin revelar el SD.
"""

from app.pipeline.nlu.unidades import es_unidad_entera
from app.pipeline.tipos import Anomalia, ArticuloCtx, ConteoParseado

# Umbrales
RATIO_ALTO = 5.0
RATIO_BAJO = 0.2
SD_ALTO = 20.0  # "hay bastante de esto normalmente"
CONFIANZA_MINIMA = 0.8

_UNIDAD_ES = {"Unidad": "unidades", "Kilogram": "kilos", "Liter": "litros", "Portion": "porciones"}


def _num(cantidad: float | None) -> str:
    """Formatea con coma decimal (Colombia): 90.0→'90', 33.5→'33,5'."""
    if cantidad is None:
        return "esa cantidad"
    return f"{cantidad:g}".replace(".", ",")


def _sin_anomalia() -> Anomalia:
    return Anomalia(flag=False)


def regla_ratio_sd(parse: ConteoParseado, art: ArticuloCtx) -> Anomalia:
    """Cantidad muy por encima (>5×) o muy por debajo (<0.2×) de lo habitual."""
    if parse.cantidad is None or parse.cantidad <= 0 or art.sd <= 0:
        return _sin_anomalia()
    ratio = parse.cantidad / art.sd
    if ratio > RATIO_ALTO or ratio < RATIO_BAJO:
        # Única regla que revela el SD: la pregunta ocurre DESPUÉS de que el
        # operario ya comprometió su número (ver regla de conteo ciego).
        return Anomalia(
            flag=True, tipo="ratio_sd",
            pregunta=f"¿Confirmas {_num(parse.cantidad)}? "
                     f"El corte anterior registró {_num(art.sd)}.",
        )
    return _sin_anomalia()


def regla_unidad_incoherente(parse: ConteoParseado, art: ArticuloCtx) -> Anomalia:
    """La unidad dicha no coincide con la del catálogo (p. ej. gramos en un
    artículo que va en litros)."""
    dicha = parse.unidad_normalizada
    base = art.unidad_base
    if dicha and base in _UNIDAD_ES and dicha != base:
        return Anomalia(
            flag=True, tipo="unidad_incoherente",
            pregunta=f"Contaste {art.nombre} en {_UNIDAD_ES[dicha]}, pero suele medirse "
                     f"en {_UNIDAD_ES[base]}. ¿Es correcto?",
        )
    return _sin_anomalia()


def regla_decimal_en_entero(parse: ConteoParseado, art: ArticuloCtx) -> Anomalia:
    """Un decimal en un artículo que se cuenta por unidades enteras."""
    if parse.cantidad is None or not es_unidad_entera(art.unidad_base):
        return _sin_anomalia()
    if parse.cantidad != int(parse.cantidad):
        return Anomalia(
            flag=True, tipo="decimal_en_entero",
            pregunta=f"Registraste {_num(parse.cantidad)} de {art.nombre}, pero este "
                     f"artículo se cuenta por unidades enteras. ¿Seguro?",
        )
    return _sin_anomalia()


def regla_cero_sospechoso(parse: ConteoParseado, art: ArticuloCtx) -> Anomalia:
    """Cero (o negativo) en un artículo del que normalmente hay bastante."""
    if parse.cantidad is not None and parse.cantidad <= 0 and art.sd >= SD_ALTO:
        return Anomalia(
            flag=True, tipo="cero_sospechoso",
            pregunta=f"Registraste cero de {art.nombre}, pero es un artículo del que "
                     f"suele haber bastante. ¿Confirmas que no queda ninguno?",
        )
    return _sin_anomalia()


def regla_baja_confianza(parse: ConteoParseado, art: ArticuloCtx) -> Anomalia:
    """El parser no quedó seguro de haber entendido."""
    if parse.confianza < CONFIANZA_MINIMA:
        unidad = _UNIDAD_ES.get(parse.unidad_normalizada or "", "").strip()
        cola = f" {unidad}" if unidad else ""
        return Anomalia(
            flag=True, tipo="baja_confianza",
            pregunta=f"No estoy seguro de haber entendido bien. ¿Contaste "
                     f"{_num(parse.cantidad)}{cola} de {art.nombre}?",
        )
    return _sin_anomalia()


# Orden de evaluación: una incoherencia de unidad o un decimal imposible pesan
# más que un ratio raro; la baja confianza es el último recurso.
REGLAS = (
    regla_unidad_incoherente,
    regla_decimal_en_entero,
    regla_cero_sospechoso,
    regla_ratio_sd,
    regla_baja_confianza,
)


def evaluar(parse: ConteoParseado, art: ArticuloCtx) -> Anomalia:
    """Devuelve la primera anomalía que se dispare, o Anomalia(flag=False)."""
    for regla in REGLAS:
        resultado = regla(parse, art)
        if resultado.flag:
            return resultado
    return _sin_anomalia()
