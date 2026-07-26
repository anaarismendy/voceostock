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

import os

from app.pipeline.confianza import umbrales_actuales
from app.pipeline.nlu.unidades import es_unidad_entera
from app.pipeline.tipos import Anomalia, ArticuloCtx, ConteoParseado

# Umbrales estructurales (propios de estas reglas). El de confianza NO vive aquí:
# es configurable (D1) y se lee de `umbrales_actuales()` en cada evaluación.
RATIO_ALTO = 5.0
RATIO_BAJO = 0.2
SD_ALTO = 20.0  # "hay bastante de esto normalmente"

# D4: umbrales de frecuencia/comportamiento. Van a configuración (regla global):
# se leen del entorno en cada evaluación, con default. `_umbral` respeta el tipo.
RECUENTO_SESION_DEFECTO = 1  # a partir de cuántos conteos previos se pregunta
FRECUENCIA_INFRECUENTE_DEFECTO = 0.1  # < 10% de los cortes → "casi nunca aparece"


def _umbral(nombre_env: str, defecto):
    crudo = os.environ.get(nombre_env)
    return type(defecto)(crudo) if crudo else defecto

_UNIDAD_ES = {"Unidad": "unidades", "Kilogram": "kilos", "Liter": "litros", "Portion": "porciones"}


def _num(cantidad: float | None) -> str:
    """Formatea con coma decimal (Colombia): 90.0→'90', 33.5→'33,5'."""
    if cantidad is None:
        return "esa cantidad"
    return f"{cantidad:g}".replace(".", ",")


def _sin_anomalia() -> Anomalia:
    return Anomalia(flag=False)


def _cantidad_articulo(parse: ConteoParseado, art: ArticuloCtx) -> str:
    """'40 unidades de HUEVOS' — la cantidad sola es ambigua cuando el operario
    dicta seguido, así que toda pregunta de confirmación repite el artículo."""
    unidad = _UNIDAD_ES.get(parse.unidad_normalizada or art.unidad_base or "", "")
    cola = f" {unidad}" if unidad else ""
    return f"{_num(parse.cantidad)}{cola} de {art.nombre}"


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
            pregunta=f"¿Confirmas {_cantidad_articulo(parse, art)}? "
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
    """El parser no quedó seguro de haber entendido. El umbral por debajo del
    cual se pregunta es CONFIGURABLE (D1): `rapida` de `umbrales_actuales()`."""
    if parse.confianza < umbrales_actuales().rapida:
        return Anomalia(
            flag=True, tipo="baja_confianza",
            pregunta=f"No estoy seguro de haber entendido bien. "
                     f"¿Contaste {_cantidad_articulo(parse, art)}?",
        )
    return _sin_anomalia()


def regla_recuento_repetido(parse: ConteoParseado, art: ArticuloCtx) -> Anomalia:
    """D4 (frecuencia): el mismo artículo ya se contó en esta sesión. Append-only:
    contar de nuevo suele ser una corrección, y vale la pena confirmarlo (no
    bloquea). No revela SD."""
    if art.veces_en_sesion >= _umbral("UMBRAL_RECUENTO_SESION", RECUENTO_SESION_DEFECTO):
        return Anomalia(
            flag=True, tipo="recuento_repetido",
            pregunta=f"Ya registraste {art.nombre} en esta sesión. "
                     f"¿Esta cuenta es una corrección?",
        )
    return _sin_anomalia()


def regla_articulo_infrecuente(parse: ConteoParseado, art: ArticuloCtx) -> Anomalia:
    """D4 (comportamiento esperado): un artículo que casi nunca aparece en el
    inventario y ahora se cuenta con cantidad positiva. Solo pregunta si hay
    señal histórica; no revela el valor histórico exacto (conteo ciego)."""
    if (
        parse.cantidad is not None
        and parse.cantidad > 0
        and art.frecuencia_historica is not None
        and art.frecuencia_historica < _umbral(
            "UMBRAL_ARTICULO_INFRECUENTE", FRECUENCIA_INFRECUENTE_DEFECTO
        )
    ):
        return Anomalia(
            flag=True, tipo="articulo_infrecuente",
            pregunta=f"{art.nombre} casi nunca aparece en el inventario. "
                     f"¿Confirmas que lo tienes?",
        )
    return _sin_anomalia()


# Orden de evaluación: una incoherencia de unidad o un decimal imposible pesan
# más que un ratio raro; la frecuencia/comportamiento van después; la baja
# confianza es el último recurso.
REGLAS = (
    regla_unidad_incoherente,
    regla_decimal_en_entero,
    regla_cero_sospechoso,
    regla_ratio_sd,
    regla_recuento_repetido,
    regla_articulo_infrecuente,
    regla_baja_confianza,
)


def evaluar(parse: ConteoParseado, art: ArticuloCtx) -> Anomalia:
    """Devuelve la primera anomalía que se dispare, o Anomalia(flag=False)."""
    for regla in REGLAS:
        resultado = regla(parse, art)
        if resultado.flag:
            return resultado
    return _sin_anomalia()
