"""Motor de anomalías (tarea A6) — el diferenciador de la solución.

Cinco reglas puras `(conteo_parseado, articulo) -> Anomalia`. Cada una decide si
frenar y guardar, y con qué pregunta en español. El contexto (SD del artículo,
unidad del catálogo) llega en el `ArticuloCtx`.

REGLA INVIOLABLE (conteo ciego): las preguntas NUNCA revelan el SD. Señalan que
la cantidad es inusual, no contra qué. El operario no debe poder deducir el
stock teórico desde la pregunta.
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
    if ratio > RATIO_ALTO:
        return Anomalia(
            flag=True, tipo="ratio_sd",
            pregunta=f"Registraste {_num(parse.cantidad)} de {art.nombre}. Es bastante "
                     f"más de lo habitual para este artículo. ¿Lo confirmas?",
        )
    if ratio < RATIO_BAJO:
        return Anomalia(
            flag=True, tipo="ratio_sd",
            pregunta=f"Registraste {_num(parse.cantidad)} de {art.nombre}. Es bastante "
                     f"menos de lo habitual para este artículo. ¿Lo confirmas?",
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
