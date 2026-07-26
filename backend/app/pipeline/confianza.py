"""Política de confianza configurable (Fase 2 — D1).

Convierte la confianza del parser (0–1) en una acción, según umbrales que viven
en CONFIGURACIÓN (tabla `umbrales_confianza` o entorno), no hardcodeados. Mover
un umbral cambia el comportamiento del pipeline sin tocar este código ni
redeploy de lógica.

Buckets (`auto >= rapida >= aclaracion`):
- conf >= auto            -> "auto":       confirmar automático.
- rapida <= conf < auto   -> "rapida":     confirmar, la UI puede pedir un toque
                                            extra (indicador de confianza, F1).
- aclaracion <= conf<rapida -> "aclaracion": preguntar (aclaración sí/no).
- conf < aclaracion       -> "candidatos": baja confianza, ofrecer alternativas.
"""

from dataclasses import dataclass
from typing import Literal

Accion = Literal["auto", "rapida", "aclaracion", "candidatos"]


@dataclass(frozen=True)
class UmbralesConfianza:
    auto: float = 0.95
    rapida: float = 0.90
    aclaracion: float = 0.70

    def __post_init__(self) -> None:
        if not (0.0 <= self.aclaracion <= self.rapida <= self.auto <= 1.0):
            raise ValueError(
                "umbrales inconsistentes: se requiere "
                f"0 <= aclaracion({self.aclaracion}) <= rapida({self.rapida}) "
                f"<= auto({self.auto}) <= 1"
            )


DEFECTO = UmbralesConfianza()

# Umbrales activos del proceso. `configurar()` los reemplaza al construir el
# pipeline (leídos de BD o entorno); las reglas y el orquestador leen de aquí.
_actuales: UmbralesConfianza = DEFECTO


def umbrales_actuales() -> UmbralesConfianza:
    return _actuales


def configurar(umbrales: UmbralesConfianza) -> None:
    global _actuales
    _actuales = umbrales


def restablecer() -> None:
    """Vuelve a los defaults. Útil en pruebas para no filtrar estado."""
    global _actuales
    _actuales = DEFECTO


def clasificar(confianza: float, umbrales: UmbralesConfianza | None = None) -> Accion:
    u = umbrales or _actuales
    if confianza >= u.auto:
        return "auto"
    if confianza >= u.rapida:
        return "rapida"
    if confianza >= u.aclaracion:
        return "aclaracion"
    return "candidatos"
