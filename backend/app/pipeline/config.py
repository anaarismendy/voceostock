"""Carga de umbrales de confianza (Fase 2 — D1).

Prioridad: fila global de la tabla `umbrales_confianza` (si hay BD) → variables
de entorno → defaults. El fallback deja al pipeline funcionar en modo csv/replay
y en pruebas sin Postgres, sin dejar de ser configurable en producción.
"""

import os

from app.pipeline.confianza import DEFECTO, UmbralesConfianza


def _de_entorno() -> UmbralesConfianza:
    def val(nombre: str, defecto: float) -> float:
        crudo = os.environ.get(nombre)
        return float(crudo) if crudo else defecto

    return UmbralesConfianza(
        auto=val("UMBRAL_CONFIANZA_AUTO", DEFECTO.auto),
        rapida=val("UMBRAL_CONFIANZA_RAPIDA", DEFECTO.rapida),
        aclaracion=val("UMBRAL_CONFIANZA_ACLARACION", DEFECTO.aclaracion),
    )


def cargar_umbrales(engine=None) -> UmbralesConfianza:
    """Umbrales activos. Con `engine` intenta la fila global (sede_id IS NULL);
    ante cualquier problema (BD caída, tabla aún sin migrar) cae a entorno."""
    if engine is not None:
        try:
            from sqlalchemy import select
            from sqlalchemy.orm import Session

            from app.models import UmbralConfianza

            with Session(engine) as s:
                fila = s.scalars(
                    select(UmbralConfianza).where(UmbralConfianza.sede_id.is_(None))
                ).first()
            if fila is not None:
                return UmbralesConfianza(
                    auto=float(fila.auto),
                    rapida=float(fila.rapida),
                    aclaracion=float(fila.aclaracion),
                )
        except Exception:  # noqa: BLE001, S110 — BD caída o tabla sin migrar: degradar a entorno/defaults
            pass
    return _de_entorno()
