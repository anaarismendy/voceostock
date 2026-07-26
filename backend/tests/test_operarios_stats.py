"""Estadísticas por operario (D5, capa E): el job que faltaba + su módulo API.

DoD: un operario al que hay que corregirle conteos baja su precisión, y esa
precisión le baja la confianza efectiva → recibe más confirmaciones.
"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.db import engine
from app.models import Conteo, SesionConteo
from app.pipeline.datos.repos import RepoPerfilDB
from app.pipeline.perfil import ajustar_confianza
from app.services.operarios import recalcular_estadisticas
from tests.test_api_conteos import _bootstrap_db, client, seed  # noqa: F401


def _capturas(seed, operario: str, n: int, corregidas: int) -> None:  # noqa: F811
    """`n` conteos del operario, de los cuales `corregidas` quedan supersedidos
    (alguien tuvo que arreglarlos) — o sea, capturas incorrectas."""
    articulo_id = seed.aceite_id
    with Session(engine) as s:
        sesion = SesionConteo(
            bodega_id=seed.bodega_id, operario_id=UUID(operario), tipo="primario"
        )
        s.add(sesion)
        s.flush()
        for i in range(n):
            original = Conteo(
                sesion_id=sesion.id, articulo_id=articulo_id, cantidad=1,
                unidad="Unidad", fuente="manual", activo=False,
            )
            s.add(original)
            s.flush()
            if i < corregidas:
                s.add(Conteo(
                    sesion_id=sesion.id, articulo_id=articulo_id, cantidad=2,
                    unidad="Unidad", fuente="manual", activo=False,
                    supersede_id=original.id,
                ))
        s.commit()


def test_job_calcula_precision_desde_las_correcciones(client, seed):  # noqa: F811
    _capturas(seed, seed.op1, n=25, corregidas=10)
    _capturas(seed, seed.op2, n=25, corregidas=0)

    stats = recalcular_estadisticas(engine)
    # op1: 25 originales + 10 correcciones = 35 capturas, 10 supersedidas.
    assert stats[UUID(seed.op1)] == (35, 25)
    assert stats[UUID(seed.op2)] == (25, 25)


def test_dod_operario_impreciso_recibe_mas_confirmaciones(client, seed):  # noqa: F811
    _capturas(seed, seed.op1, n=25, corregidas=10)
    _capturas(seed, seed.op2, n=25, corregidas=0)
    recalcular_estadisticas(engine)

    repo = RepoPerfilDB(engine)
    flojo = repo.para_operario(UUID(seed.op1))
    bueno = repo.para_operario(UUID(seed.op2))
    assert flojo is not None and bueno is not None
    assert flojo.precision < bueno.precision

    # Una captura idéntica (0.92) cae por debajo del umbral `rapida` (0.90) para
    # el impreciso y se mantiene arriba para el acertado: más preguntas al que
    # más se equivoca. Esto es exactamente lo que D5 prometía y no ocurría.
    assert ajustar_confianza(0.92, flojo) < 0.90 <= ajustar_confianza(0.92, bueno)


def test_modulo_api_lista_y_recalcula(client, seed):  # noqa: F811
    _capturas(seed, seed.op1, n=25, corregidas=10)

    # Antes de recalcular no hay estadísticas: la lista sale en cero, sin romper.
    inicial = client.get("/api/v1/operarios").json()
    assert {o["capturas_totales"] for o in inicial} == {0}
    assert all(o["precision"] is None and o["ajuste"] == 0 for o in inicial)

    tras = client.post("/api/v1/operarios/recalcular").json()
    op1 = next(o for o in tras if o["id"] == seed.op1)
    assert op1["capturas_totales"] == 35
    assert op1["precision"] < 0.9
    assert op1["ajuste"] < 0  # se le penaliza la confianza
    assert op1["perfil_activo"] is True  # 35 >= minimo_muestras (20)


def test_alta_y_edicion_desde_el_panel_del_lider(client, seed):  # noqa: F811
    nuevo = client.post(
        "/api/v1/operarios", json={"nombre": "Carmen", "pin": "2468", "rol": "operario"}
    )
    assert nuevo.status_code == 201
    assert nuevo.json()["capturas_totales"] == 0

    # El PIN es único: reutilizarlo choca contra el índice, no crea un gemelo.
    repetido = client.post(
        "/api/v1/operarios", json={"nombre": "Otro", "pin": "2468", "rol": "operario"}
    )
    assert repetido.status_code == 409

    editado = client.patch(
        f"/api/v1/operarios/{nuevo.json()['id']}", json={"pin": "1357", "rol": "lider"}
    )
    assert editado.status_code == 200
    assert editado.json()["rol"] == "lider"
    assert client.post("/api/v1/operarios/login", json={"pin": "1357"}).status_code == 200
    assert client.post("/api/v1/operarios/login", json={"pin": "2468"}).status_code == 404

    assert client.post("/api/v1/operarios", json={"nombre": "X", "pin": "12"}).status_code == 422


def test_cambiar_el_pin_conserva_el_historial(client, seed):  # noqa: F811
    """El id no cambia al reasignar el PIN, así que la precisión acumulada sigue
    siendo del mismo operario. Es justo lo que el find-or-create rompía."""
    _capturas(seed, seed.op1, n=25, corregidas=10)
    recalcular_estadisticas(engine)
    antes = next(o for o in client.get("/api/v1/operarios").json() if o["id"] == seed.op1)

    client.patch(f"/api/v1/operarios/{seed.op1}", json={"pin": "9876"}).raise_for_status()

    login = client.post("/api/v1/operarios/login", json={"pin": "9876"}).json()
    assert login["id"] == seed.op1
    despues = next(o for o in client.get("/api/v1/operarios").json() if o["id"] == seed.op1)
    assert despues["capturas_totales"] == antes["capturas_totales"]
    assert despues["ajuste"] == antes["ajuste"]


def test_cerrar_sesion_recalcula_solo(client, seed):  # noqa: F811
    _capturas(seed, seed.op1, n=25, corregidas=10)
    sesion = client.post(
        "/api/v1/sesiones",
        json={"bodega_id": seed.bodega_id, "operario_id": seed.op1, "tipo": "primario"},
    ).json()["sesion_id"]

    client.post(f"/api/v1/sesiones/{sesion}/cerrar").raise_for_status()

    op1 = next(o for o in client.get("/api/v1/operarios").json() if o["id"] == seed.op1)
    assert op1["capturas_totales"] == 35  # el cierre disparó el job, sin botón
