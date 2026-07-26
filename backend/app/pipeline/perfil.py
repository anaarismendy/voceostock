"""Perfil de confianza por operario (Fase 2 — D5).

Ajusta la confianza EFECTIVA de una captura según el historial del operario: uno
muy acertado recibe un pequeño empujón (menos confirmaciones), uno impreciso una
penalización (más confirmaciones). El ajuste está acotado y sólo aplica con
muestra suficiente. Los parámetros van a configuración (entorno), no hardcodeados.

No decide por sí mismo el ask/no-ask: alimenta la política de confianza de D1
(`clasificar`/`regla_baja_confianza`) con una confianza corregida por operario.
"""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class PerfilOperario:
    operario_id: str
    precision: float  # 0..1 — % de capturas correctas históricas
    total_capturas: int


@dataclass(frozen=True)
class AjusteConfianza:
    base: float = 0.90        # precisión "neutra": ni empuje ni penalización
    ganancia: float = 0.5     # cuánto pesa la desviación de precisión
    maximo: float = 0.08      # tope del ajuste (±), para no desbordar los buckets
    minimo_muestras: int = 20  # bajo esto el perfil no es fiable → no se ajusta

    @classmethod
    def desde_entorno(cls) -> "AjusteConfianza":
        def val(nombre, defecto):
            crudo = os.environ.get(nombre)
            return type(defecto)(crudo) if crudo else defecto

        return cls(
            base=val("AJUSTE_CONF_BASE", cls.base),
            ganancia=val("AJUSTE_CONF_GANANCIA", cls.ganancia),
            maximo=val("AJUSTE_CONF_MAXIMO", cls.maximo),
            minimo_muestras=val("AJUSTE_CONF_MIN_MUESTRAS", cls.minimo_muestras),
        )


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def ajustar_confianza(
    confianza: float, perfil: PerfilOperario | None, cfg: AjusteConfianza | None = None
) -> float:
    """Confianza corregida por el historial del operario. Sin perfil o con muestra
    insuficiente, devuelve la confianza sin tocar."""
    cfg = cfg or AjusteConfianza()
    if perfil is None or perfil.total_capturas < cfg.minimo_muestras:
        return confianza
    ajuste = _clamp(cfg.ganancia * (perfil.precision - cfg.base), -cfg.maximo, cfg.maximo)
    return _clamp(confianza + ajuste, 0.0, 1.0)
