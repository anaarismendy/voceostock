"""Job de recálculo de estadísticas por operario (capa E — pareja de riesgo.py).

Rellena `estadisticas_operario`, la tabla que D5 (`RepoPerfilDB`) lee para
ajustar la confianza efectiva de cada captura. Sin este job la tabla queda
vacía y el ajuste por operario nunca se activa.

Señal de "captura incorrecta": el conteo fue SUPERSEDIDO, es decir alguien tuvo
que corregirlo (`conteos.supersede_id` apunta a él). Es la única evidencia dura
de error que deja el modelo append-only: una anomalía marcada puede ser un
hallazgo legítimo, una corrección no.

Se recalcula entero (no incremental): son cientos de filas, no millones.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Conteo, EstadisticaOperario, SesionConteo

# ponytail: recálculo completo en cada llamada. Si `conteos` pasa de ~1e6 filas,
# pasar a incremental por sesión (WHERE sesion_id = ...) sobre los contadores.


def _agregado(engine) -> dict[uuid.UUID, tuple[int, int]]:
    """{operario_id -> (totales, correctas)} sobre todo el historial."""
    # Ids de conteos que alguien corrigió después. El IS NOT NULL evita que el
    # NOT IN se envenene con NULLs (en SQL, `x NOT IN (NULL)` nunca es cierto).
    corregidos = select(Conteo.supersede_id).where(Conteo.supersede_id.is_not(None))

    with Session(engine) as s:
        filas = s.execute(
            select(
                SesionConteo.operario_id,
                func.count(Conteo.id),
                func.count(Conteo.id).filter(Conteo.id.not_in(corregidos)),
            )
            .join(SesionConteo, SesionConteo.id == Conteo.sesion_id)
            .group_by(SesionConteo.operario_id)
        ).all()
    return {op_id: (totales, correctas) for op_id, totales, correctas in filas}


def recalcular_estadisticas(engine) -> dict[uuid.UUID, tuple[int, int]]:
    """Recalcula y persiste totales/correctas por operario. Devuelve
    {operario_id -> (totales, correctas)}."""
    agregado = _agregado(engine)
    with Session(engine) as s:
        for operario_id, (totales, correctas) in agregado.items():
            fila = s.get(EstadisticaOperario, operario_id)
            if fila is None:
                s.add(
                    EstadisticaOperario(
                        operario_id=operario_id,
                        capturas_totales=totales,
                        capturas_correctas=correctas,
                    )
                )
            else:
                fila.capturas_totales, fila.capturas_correctas = totales, correctas
        s.commit()
    return agregado
