"""Reporte de diferencias por bodega (tarea A9).

Compara la cantidad física (último conteo activo) contra el SD del corte, calcula
diferencia absoluta y %, y pinta el semáforo:
- normal   < 10 %
- revisar   10 %–30 %
- crítico  > 30 %  o  anomalía confirmada

A diferencia de la captura, aquí el SD SÍ aparece: es un reporte de cierre, para
el líder, no una pantalla de conteo. El conteo ciego aplica a la captura.
"""

from typing import Literal

from pydantic import BaseModel

Semaforo = Literal["normal", "revisar", "critico"]

UMBRAL_REVISAR = 0.10
UMBRAL_CRITICO = 0.30


class FilaCierre(BaseModel):
    """Entrada cruda del reporte: un artículo contado en una bodega."""

    articulo_id: int
    nr_articulo: int | None
    articulo: str
    unidad: str
    sd_teorico: float
    cantidad_fisica: float
    orden_original: int
    anomalia_confirmada: bool = False


class DiferenciaArticulo(BaseModel):
    articulo_id: int
    nr_articulo: int | None
    articulo: str
    unidad: str
    sd_teorico: float
    cantidad_fisica: float
    diferencia: float
    diferencia_pct: float  # 0.25 == 25 %
    semaforo: Semaforo


class ResumenSemaforo(BaseModel):
    normal: int = 0
    revisar: int = 0
    critico: int = 0


class ReporteDiferencias(BaseModel):
    bodega_id: int
    bodega_nombre: str
    filas: list[DiferenciaArticulo]
    resumen: ResumenSemaforo
    criticos: list[DiferenciaArticulo]


def clasificar(sd: float, fisica: float, anomalia_confirmada: bool) -> tuple[float, float, Semaforo]:
    """Devuelve (diferencia, diferencia_pct, semáforo)."""
    diferencia = fisica - sd
    base = abs(sd)
    if base == 0:
        pct = 0.0 if fisica == 0 else 1.0
    else:
        pct = abs(diferencia) / base
    if anomalia_confirmada or pct > UMBRAL_CRITICO:
        semaforo: Semaforo = "critico"
    elif pct >= UMBRAL_REVISAR:
        semaforo = "revisar"
    else:
        semaforo = "normal"
    return diferencia, pct, semaforo


def calcular_diferencias(
    bodega_id: int, bodega_nombre: str, filas: list[FilaCierre]
) -> ReporteDiferencias:
    diferencias: list[DiferenciaArticulo] = []
    resumen = ResumenSemaforo()
    for f in filas:
        diff, pct, semaforo = clasificar(f.sd_teorico, f.cantidad_fisica, f.anomalia_confirmada)
        diferencias.append(
            DiferenciaArticulo(
                articulo_id=f.articulo_id, nr_articulo=f.nr_articulo, articulo=f.articulo,
                unidad=f.unidad, sd_teorico=f.sd_teorico, cantidad_fisica=f.cantidad_fisica,
                diferencia=diff, diferencia_pct=pct, semaforo=semaforo,
            )
        )
        setattr(resumen, semaforo, getattr(resumen, semaforo) + 1)

    # Más urgente primero: crítico arriba, y dentro del semáforo, mayor descuadre.
    orden = {"critico": 0, "revisar": 1, "normal": 2}
    diferencias.sort(key=lambda d: (orden[d.semaforo], -abs(d.diferencia_pct)))
    criticos = [d for d in diferencias if d.semaforo == "critico"]
    return ReporteDiferencias(
        bodega_id=bodega_id, bodega_nombre=bodega_nombre,
        filas=diferencias, resumen=resumen, criticos=criticos,
    )


def descuadres_recurrentes(reportes: list[ReporteDiferencias], minimo: int = 2) -> list[dict]:
    """Artículos descuadrados (revisar/crítico) en ≥`minimo` bodegas — el patrón
    que le interesa al líder por encima de un descuadre aislado."""
    por_articulo: dict[str, list[str]] = {}
    for rep in reportes:
        for d in rep.filas:
            if d.semaforo != "normal":
                por_articulo.setdefault(d.articulo, []).append(rep.bodega_nombre)
    recurrentes = [
        {"articulo": art, "bodegas": bodegas, "veces": len(bodegas)}
        for art, bodegas in por_articulo.items()
        if len(bodegas) >= minimo
    ]
    recurrentes.sort(key=lambda r: -r["veces"])
    return recurrentes
