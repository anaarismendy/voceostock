"""Consultas de cierre contra Postgres (tarea A9).

Aísla el acceso a BD del cálculo puro de `diferencias.py`: así el reporte y el
export se prueban con datos en memoria y estas consultas se prueban (en
integración) contra la BD real.
"""

from app.reportes.diferencias import FilaCierre


def filas_cierre(engine, bodega_id: int) -> tuple[str, list[FilaCierre]]:
    """(nombre de bodega, filas de cierre) = último conteo activo por artículo
    contra el SD del corte más reciente."""
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from app.models import Articulo, Bodega, Conteo, SesionConteo, StockTeorico

    with Session(engine) as s:
        nombre = s.scalar(select(Bodega.nombre).where(Bodega.id == bodega_id)) or f"bodega {bodega_id}"
        filas = s.execute(
            select(
                Conteo.articulo_id, Articulo.nr_articulo, Articulo.nombre, Conteo.unidad,
                StockTeorico.sd, Conteo.cantidad, StockTeorico.orden_original,
                Conteo.anomalia_flag, Conteo.anomalia_resuelta,
            )
            .join(SesionConteo, SesionConteo.id == Conteo.sesion_id)
            .join(Articulo, Articulo.id == Conteo.articulo_id)
            .join(
                StockTeorico,
                (StockTeorico.articulo_id == Conteo.articulo_id)
                & (StockTeorico.bodega_id == bodega_id),
            )
            .where(SesionConteo.bodega_id == bodega_id, Conteo.activo.is_(True))
            .order_by(StockTeorico.corte_fecha.desc())
        ).all()

    vistos: set[int] = set()
    cierre: list[FilaCierre] = []
    for f in filas:
        if f.articulo_id in vistos:  # corte más reciente ya tomado
            continue
        vistos.add(f.articulo_id)
        cierre.append(
            FilaCierre(
                articulo_id=f.articulo_id, nr_articulo=f.nr_articulo, articulo=f.nombre,
                unidad=f.unidad, sd_teorico=float(f.sd), cantidad_fisica=float(f.cantidad),
                orden_original=f.orden_original,
                anomalia_confirmada=bool(f.anomalia_flag and f.anomalia_resuelta),
            )
        )
    return nombre, cierre
