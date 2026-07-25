"""E5: job de riesgo histórico + exposición en el catálogo. Corre contra la BD
de prueba; reusa las fixtures de test_api_conteos."""
# ruff: noqa: F811 — las fixtures importadas se "redefinen" como parámetros

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from app.db import engine
from app.models import Conteo, SesionConteo
from app.services.riesgo import recalcular_riesgo
from tests.test_api_conteos import _bootstrap_db, client, seed  # noqa: F401


def _ciclos(seed, cazuela_anomala: list[bool]) -> None:
    """Crea una sesión por elemento; en cada una cuenta cazuela (anómala segun
    la lista) y aceite (siempre limpio)."""
    with Session(engine) as s:
        for i, anomala in enumerate(cazuela_anomala):
            ses = SesionConteo(
                bodega_id=seed.bodega_id, operario_id=UUID(seed.op1), tipo="primario",
                iniciada_en=datetime.now(UTC) - timedelta(days=i),
            )
            s.add(ses)
            s.flush()
            s.add(Conteo(
                sesion_id=ses.id, articulo_id=seed.cazuela_id, cantidad=1, unidad="Unidad",
                fuente="voz-tablet", anomalia_flag=anomala,
            ))
            s.add(Conteo(
                sesion_id=ses.id, articulo_id=seed.aceite_id, cantidad=30, unidad="Liter",
                fuente="voz-tablet", anomalia_flag=False,
            ))
        s.commit()


def test_dod_articulo_inconsistente_alto_estable_bajo(client, seed):
    # cazuela: anomalía en 3 de 4 ciclos → alto; aceite: 0 → bajo.
    _ciclos(seed, [True, True, True, False])
    niveles = recalcular_riesgo(engine)
    assert niveles[seed.cazuela_id] == "alto"
    assert niveles[seed.aceite_id] == "bajo"


def test_dod_catalogo_expone_riesgo_sin_request_extra(client, seed):
    _ciclos(seed, [True, True, True, False])
    recalcular_riesgo(engine)
    arts = client.get(f"/api/v1/articulos?bodega_id={seed.bodega_id}").json()
    por_id = {a["articulo_id"]: a for a in arts}
    # El MISMO payload del catálogo trae el nivel de riesgo (E5).
    assert por_id[seed.cazuela_id]["riesgo"] == "alto"
    assert por_id[seed.aceite_id]["riesgo"] == "bajo"


def test_articulo_sin_historial_riesgo_none(client, seed):
    # Sin conteos → sin fila de riesgo → el catálogo lo trae como None (sin aviso).
    arts = client.get(f"/api/v1/articulos?bodega_id={seed.bodega_id}").json()
    assert all(a["riesgo"] is None for a in arts)
