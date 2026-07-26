"""Job de recálculo del riesgo histórico por artículo (Fase 2 — E5).

Arma, por artículo, la frecuencia de inconsistencia en los últimos N ciclos de
conteo (un ciclo = una sesión; inconsistente = algún conteo del artículo en esa
sesión quedó marcado como anomalía) y delega el nivel a D6
(`calcular_riesgo_desde_historial`). Persiste el resultado en `riesgo_articulo`.

No usa el SD del ciclo actual: solo el patrón histórico de anomalías. Pensado
para correr periódicamente (nocturno) o al cierre de sesión.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Conteo, RiesgoArticulo, SesionConteo
from app.pipeline.riesgo import calcular_riesgo_desde_historial

CICLOS_POR_DEFECTO = 6


def _historial(engine, n_ciclos: int) -> dict[int, list[bool]]:
    """{articulo_id -> [inconsistente_por_ciclo]} de los últimos N ciclos."""
    with Session(engine) as s:
        filas = s.execute(
            select(
                Conteo.articulo_id,
                SesionConteo.iniciada_en,
                func.bool_or(Conteo.anomalia_flag),
            )
            .join(SesionConteo, SesionConteo.id == Conteo.sesion_id)
            .where(Conteo.articulo_id.is_not(None))
            .group_by(Conteo.articulo_id, Conteo.sesion_id, SesionConteo.iniciada_en)
        ).all()

    por_articulo: dict[int, list[tuple]] = {}
    for articulo_id, iniciada_en, inconsistente in filas:
        por_articulo.setdefault(articulo_id, []).append((iniciada_en, bool(inconsistente)))

    historial: dict[int, list[bool]] = {}
    for articulo_id, pares in por_articulo.items():
        pares.sort(key=lambda p: p[0], reverse=True)  # más reciente primero
        historial[articulo_id] = [inc for _, inc in pares[:n_ciclos]]
    return historial


def recalcular_riesgo(engine, n_ciclos: int = CICLOS_POR_DEFECTO) -> dict[int, str]:
    """Recalcula y persiste el nivel global (sede_id NULL) por artículo. Devuelve
    {articulo_id -> nivel}."""
    niveles = calcular_riesgo_desde_historial(_historial(engine, n_ciclos))
    with Session(engine) as s:
        for articulo_id, nivel in niveles.items():
            fila = s.scalar(
                select(RiesgoArticulo).where(
                    RiesgoArticulo.articulo_id == articulo_id,
                    RiesgoArticulo.sede_id.is_(None),
                )
            )
            if fila is None:
                s.add(RiesgoArticulo(articulo_id=articulo_id, sede_id=None, nivel=nivel))
            else:
                fila.nivel = nivel
        s.commit()
    return niveles
