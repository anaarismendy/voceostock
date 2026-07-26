"""Endpoints reales para el panel del líder y la demo (fase final).

P3 construyó C9–C11 contra el mock (/api/v1/cierre, /dashboard, /demo/*);
esto los respalda con la BD real, mismo contrato del frontend.

- /cierre es del LÍDER: es el único lugar sancionado donde viaja el SD
  (reporte de cierre, ver CLAUDE.md). /dashboard NO expone SD.
- /demo/seed deja el estado exacto de docs/DEMO.md: un artículo que cuadra,
  uno que sobra (+2) y uno que falta (−3), escalonados en el tiempo.
"""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app import models
from app.db import Db

router = APIRouter(prefix="/api/v1", tags=["demo"])

PIN_DEMO = "0000"
PIN_LIDER_DEMO = "1111"


def _operario_demo(s, pin: str, nombre: str, rol: str):
    """Alta idempotente por PIN (el índice único no perdona el segundo seed)."""
    fila = s.scalar(select(models.Operario).where(models.Operario.pin == pin))
    if fila is None:
        fila = models.Operario(nombre=nombre, pin=pin, rol=rol)
        s.add(fila)
        s.flush()
    return fila


class FilaCierre(BaseModel):
    articulo_id: int
    articulo_nombre: str
    unidad: str
    sd: float
    contado: float
    diferencia: float
    evidencia_url: str | None = None


class ConteoReciente(BaseModel):
    articulo_id: int
    articulo_nombre: str
    cantidad: float
    unidad: str
    creado_en: int  # epoch ms, como espera el frontend
    # Rediseño (pantalla I): el feed destaca en amarillo las anomalías
    # confirmadas. Es un flag del conteo, nunca el SD (conteo ciego).
    es_anomalia: bool = False


class ResumenDashboard(BaseModel):
    total_conteos: int
    articulos_unicos: int
    anomalias: int
    recientes: list[ConteoReciente]


def _sd_bodega(s: Session, bodega_id: int) -> dict[int, float]:
    filas = s.execute(
        select(models.StockTeorico.articulo_id, models.StockTeorico.sd).where(
            models.StockTeorico.bodega_id == bodega_id
        )
    ).all()
    return {f.articulo_id: float(f.sd) for f in filas}


def _resolver_ids(s: Session, crudos: list[int]) -> dict[int, models.Articulo]:
    """El checklist del frontend habla en nr_articulo; la BD en id. Acepta ambos."""
    resueltos: dict[int, models.Articulo] = {}
    for crudo in crudos:
        art = s.get(models.Articulo, crudo) or s.scalar(
            select(models.Articulo).where(models.Articulo.nr_articulo == crudo)
        )
        if art is not None:
            resueltos[art.id] = art
    return resueltos


@router.get("/cierre", response_model=list[FilaCierre])
def cierre(s: Db, bodega_id: int, ids: str = "") -> list[FilaCierre]:
    esperados = [int(x) for x in ids.split(",") if x.strip().isdigit()]
    sd_por_articulo = _sd_bodega(s, bodega_id)

    activos = s.execute(
        select(models.Conteo, models.Articulo)
        .join(models.SesionConteo, models.SesionConteo.id == models.Conteo.sesion_id)
        .join(models.Articulo, models.Articulo.id == models.Conteo.articulo_id)
        .where(models.SesionConteo.bodega_id == bodega_id, models.Conteo.activo.is_(True))
        .order_by(models.Conteo.creado_en)
    ).all()

    filas: dict[int, FilaCierre] = {}
    for conteo, art in activos:
        fila = filas.get(art.id)
        if fila is None:
            fila = FilaCierre(
                articulo_id=art.id, articulo_nombre=art.nombre,
                unidad=conteo.unidad, sd=sd_por_articulo.get(art.id, 0.0),
                contado=0.0, diferencia=0.0,
            )
            filas[art.id] = fila
        fila.contado = round(fila.contado + float(conteo.cantidad), 3)
        if conteo.evidencia_url:
            fila.evidencia_url = conteo.evidencia_url

    for art_id, art in _resolver_ids(s, esperados).items():
        if art_id not in filas:
            filas[art_id] = FilaCierre(
                articulo_id=art_id, articulo_nombre=art.nombre,
                unidad=art.unidad_base or "Unidad",
                sd=sd_por_articulo.get(art_id, 0.0), contado=0.0, diferencia=0.0,
            )

    for fila in filas.values():
        fila.diferencia = round(fila.contado - fila.sd, 3)

    return sorted(
        filas.values(),
        key=lambda f: (-abs(f.diferencia), f.articulo_nombre),
    )


@router.get("/dashboard", response_model=ResumenDashboard)
def dashboard(s: Db, bodega_id: int) -> ResumenDashboard:
    # Actividad de captura del líder — sin SD (conteo ciego).
    conteos = s.execute(
        select(models.Conteo, models.Articulo.nombre)
        .join(models.SesionConteo, models.SesionConteo.id == models.Conteo.sesion_id)
        .outerjoin(models.Articulo, models.Articulo.id == models.Conteo.articulo_id)
        .where(models.SesionConteo.bodega_id == bodega_id)
        .order_by(models.Conteo.creado_en.desc())
    ).all()

    recientes = [
        ConteoReciente(
            articulo_id=c.articulo_id or 0,
            articulo_nombre=nombre or (c.texto_capturado or "(sin catálogo)"),
            cantidad=float(c.cantidad),
            unidad=c.unidad,
            creado_en=int(c.creado_en.timestamp() * 1000),
            es_anomalia=bool(c.anomalia_flag),
        )
        for c, nombre in conteos[:8]
    ]
    unicos = {c.articulo_id for c, _ in conteos if c.articulo_id is not None}
    anomalias = sum(1 for c, _ in conteos if c.anomalia_flag)
    return ResumenDashboard(
        total_conteos=len(conteos), articulos_unicos=len(unicos),
        anomalias=anomalias, recientes=recientes,
    )


# --- Semilla de demo (C11) sobre la BD real ---

# contado = sd + delta: uno que cuadra, uno que sobra y uno que falta, igual
# que la semilla del mock y el "estado sembrado" de docs/DEMO.md.
SEMILLA = (("ACEITE DE OLIVA", 0.0), ("CAZUELA 16 ONZ", 2.0), ("COSTILLA DE RES", -3.0))


def _limpiar_bodega(s: Session, bodega_id: int) -> None:
    sesiones = s.scalars(
        select(models.SesionConteo.id).where(models.SesionConteo.bodega_id == bodega_id)
    ).all()
    if not sesiones:
        return
    s.execute(delete(models.TokenPendiente).where(models.TokenPendiente.sesion_id.in_(sesiones)))
    s.execute(delete(models.Conteo).where(models.Conteo.sesion_id.in_(sesiones)))
    s.execute(delete(models.SesionConteo).where(models.SesionConteo.id.in_(sesiones)))
    s.commit()


@router.post("/demo/reset")
def demo_reset(s: Db, bodega_id: int = 3) -> dict:
    _limpiar_bodega(s, bodega_id)
    return {"ok": True, "total": 0}


@router.post("/demo/seed")
def demo_seed(s: Db, bodega_id: int = 3) -> dict:
    _limpiar_bodega(s, bodega_id)

    operario = _operario_demo(s, PIN_DEMO, "Demo", "operario")
    # El login ya no crea operarios y el rol lo manda el backend: sin este
    # líder sembrado no habría forma de entrar al panel del líder en la demo.
    _operario_demo(s, PIN_LIDER_DEMO, "Líder Demo", "lider")
    sesion = models.SesionConteo(bodega_id=bodega_id, operario_id=operario.id, tipo="primario")
    s.add(sesion)
    s.flush()

    sd_por_articulo = _sd_bodega(s, bodega_id)
    ahora = datetime.now(UTC)
    total = 0
    for i, (nombre, delta) in enumerate(SEMILLA):
        art = s.scalar(select(models.Articulo).where(models.Articulo.nombre == nombre))
        if art is None or art.id not in sd_por_articulo:
            continue
        s.add(
            models.Conteo(
                sesion_id=sesion.id, articulo_id=art.id,
                cantidad=round(sd_por_articulo[art.id] + delta, 3),
                unidad=art.unidad_base or "Unidad", fuente="voz-tablet",
                confianza=0.95,
                creado_en=ahora - timedelta(minutes=3 * (len(SEMILLA) - i)),
            )
        )
        total += 1
    s.commit()
    return {"ok": True, "total": total}
