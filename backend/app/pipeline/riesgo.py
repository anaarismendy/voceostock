"""Score de riesgo histórico por artículo (Fase 2 — D6).

Mide, por artículo, la FRECUENCIA DE INCONSISTENCIA a través de los últimos N
ciclos de conteo (un ciclo es "inconsistente" si el conteo de ese artículo quedó
marcado como anomalía). Produce un nivel: alto / medio / bajo.

Sólo mira el patrón histórico: NO usa el SD ni la captura del ciclo actual. El
cálculo es puro; un job (E5) le pasa el historial leído de la BD y persiste el
resultado en `riesgo_articulo`.
"""

import os
from dataclasses import dataclass
from typing import Literal

NivelRiesgo = Literal["alto", "medio", "bajo"]


@dataclass(frozen=True)
class UmbralesRiesgo:
    alto: float = 0.5        # >= 50% de ciclos inconsistentes → alto
    medio: float = 0.2       # >= 20% → medio; por debajo → bajo
    minimo_ciclos: int = 2   # con menos historia no hay patrón → bajo

    @classmethod
    def desde_entorno(cls) -> "UmbralesRiesgo":
        def val(nombre, defecto):
            crudo = os.environ.get(nombre)
            return type(defecto)(crudo) if crudo else defecto

        return cls(
            alto=val("RIESGO_ALTO", cls.alto),
            medio=val("RIESGO_MEDIO", cls.medio),
            minimo_ciclos=val("RIESGO_MIN_CICLOS", cls.minimo_ciclos),
        )


def frecuencia_inconsistencia(inconsistentes: int, ciclos: int) -> float:
    return inconsistentes / ciclos if ciclos else 0.0


def nivel_riesgo(
    inconsistentes: int, ciclos: int, umbrales: UmbralesRiesgo | None = None
) -> NivelRiesgo:
    umbrales = umbrales or UmbralesRiesgo()
    if ciclos < umbrales.minimo_ciclos:
        return "bajo"  # historia insuficiente: no marcar riesgo sin evidencia
    f = frecuencia_inconsistencia(inconsistentes, ciclos)
    if f >= umbrales.alto:
        return "alto"
    if f >= umbrales.medio:
        return "medio"
    return "bajo"


def calcular_riesgo_desde_historial(
    historial: dict[int, list[bool]], umbrales: UmbralesRiesgo | None = None
) -> dict[int, NivelRiesgo]:
    """`historial`: {articulo_id -> [inconsistente_ciclo_1, ...]} de los últimos N
    ciclos (más reciente o no, da igual: es una frecuencia). Devuelve el nivel por
    artículo. Es lo que el job periódico (E5) llama tras leer la BD."""
    return {
        articulo_id: nivel_riesgo(sum(ciclos), len(ciclos), umbrales)
        for articulo_id, ciclos in historial.items()
    }
