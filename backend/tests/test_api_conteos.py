"""B8: flujo de estados, supersede, concurrencia sin bloqueo, WS y la prueba
guardiana del conteo ciego. Corre contra la BD de prueba (ver conftest.py)."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.db import DATABASE_URL, engine
from app.main import app
from app.models import Articulo, Base, Bodega, Conteo, Operario, StockTeorico, TokenPendiente

# Valor centinela de SD: si aparece en una respuesta o evento se filtró stock
# teórico y la prueba guardiana revienta. ÚNICA excepción sancionada: el campo
# `pregunta` de una anomalía de orden de magnitud sí cita el saldo anterior.
SD_PROHIBIDO = 9137.25
SD_PROHIBIDO_STR = ("9137.25", "9137,25")  # _num() formatea con coma decimal


@pytest.fixture(scope="session", autouse=True)
def _bootstrap_db():
    admin_url, nombre_db = DATABASE_URL.rsplit("/", 1)
    admin = create_engine(admin_url + "/voceostock", isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        existe = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": nombre_db}
        ).scalar()
        if not existe:
            conn.execute(text(f'CREATE DATABASE "{nombre_db}"'))
    admin.dispose()
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()


@pytest.fixture(scope="session")
def client():
    # Un solo TestClient (un solo event loop) para toda la sesión de pruebas:
    # el pub/sub WS en memoria usa primitivas asyncio atadas al loop.
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def seed(_bootstrap_db):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        bodega = Bodega(nombre="bodega demo", nombre_normalizado="bodega demo")
        op1 = Operario(nombre="Ana", pin="hash", rol="operario")
        op2 = Operario(nombre="Luis", pin="hash", rol="operario")
        # Catálogo mínimo para el pipeline real en replay: "cazuela" es ambigua
        # (CAZUELA vs TAPA CAZUELA), "cazuelas"=90 dispara ratio_sd contra el
        # centinela, y el aceite (SD 33 ≈ conteo 30) pasa sin anomalía.
        cazuela = Articulo(
            nombre="CAZUELA 16 ONZ", nombre_normalizado="cazuela 16 onz", unidad_base="Unidad"
        )
        tapa = Articulo(
            nombre="TAPA CAZUELA 16 ONZ",
            nombre_normalizado="tapa cazuela 16 onz",
            unidad_base="Unidad",
        )
        caldero = Articulo(
            nombre="CALDERO RECORT TAPA 50X60 CM",
            nombre_normalizado="caldero recort tapa 50x60 cm",
            unidad_base="Unidad",
        )
        aceite = Articulo(
            nr_articulo=7290,
            nombre="ACEITE DE OLIVA",
            nombre_normalizado="aceite de oliva",
            unidad_base="Liter",
        )
        s.add_all([bodega, op1, op2, cazuela, tapa, caldero, aceite])
        s.flush()
        for art, sd in ((cazuela, SD_PROHIBIDO), (tapa, SD_PROHIBIDO),
                        (caldero, SD_PROHIBIDO), (aceite, 33.0)):
            s.add(
                StockTeorico(bodega_id=bodega.id, articulo_id=art.id, sd=sd, orden_original=1)
            )
        s.commit()
        return SimpleNamespace(
            bodega_id=bodega.id,
            op1=str(op1.id),
            op2=str(op2.id),
            cazuela_id=cazuela.id,
            aceite_id=aceite.id,
        )


def _sesion(client, seed, operario: str) -> tuple[str, dict]:
    resp = client.post(
        "/api/v1/sesiones",
        json={"bodega_id": seed.bodega_id, "operario_id": operario, "tipo": "primario"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["sesion_id"], resp.json()


def _conteo(client, seed, sesion_id: str, texto: str, operario: str | None = None) -> dict:
    resp = client.post(
        "/api/v1/conteos",
        json={
            "sesion_id": sesion_id,
            "bodega_id": seed.bodega_id,
            "operario_id": operario or seed.op1,
            "fuente": "voz-tablet",
            "payload_texto": texto,
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_flujo_tres_estados_y_resolver(client, seed):
    sesion_id, sesion = _sesion(client, seed, seed.op1)
    assert sesion["bodega"]["nombre"] == "bodega demo"
    assert sesion["total_articulos"] == 4

    confirmado = _conteo(client, seed, sesion_id, "treinta litros de aceite")
    assert confirmado["status"] == "confirmado"
    assert confirmado["conteo"]["articulo_nombre"] == "ACEITE DE OLIVA"
    assert confirmado["conteo"]["articulo_id"] == seed.aceite_id
    assert confirmado["conteo"]["cantidad"] == 30

    anomalia = _conteo(client, seed, sesion_id, "noventa cajas de cazuelas")
    assert anomalia["status"] == "requiere_confirmacion"
    assert anomalia["motivo"] == "anomalia"
    resuelto = client.post(
        f"/api/v1/conteos/{anomalia['token_pendiente']}/resolver", json={"respuesta": "si"}
    ).json()
    assert resuelto["status"] == "confirmado"
    assert resuelto["conteo"]["cantidad"] == 90
    with Session(engine) as s:
        anomalos = s.scalars(select(Conteo).where(Conteo.anomalia_flag.is_(True))).all()
    assert len(anomalos) == 1
    assert anomalos[0].anomalia_tipo == "anomalia"
    assert anomalos[0].anomalia_resuelta is True

    progreso = client.get(f"/api/v1/sesiones/{sesion_id}/progreso").json()
    assert progreso["contados"] == 2
    assert progreso["total"] == 4
    assert progreso["colisiones"] == 0

    ambiguo = _conteo(client, seed, sesion_id, "cazuela")
    assert ambiguo["status"] == "requiere_confirmacion"
    assert ambiguo["motivo"] == "ambiguedad"
    assert {c["articulo_nombre"] for c in ambiguo["candidatos"]} == {
        "CAZUELA 16 ONZ", "TAPA CAZUELA 16 ONZ",
    }
    elegido = client.post(
        f"/api/v1/conteos/{ambiguo['token_pendiente']}/resolver",
        json={"respuesta": f"articulo_id:{seed.cazuela_id}"},
    ).json()
    assert elegido["status"] == "confirmado"
    assert elegido["conteo"]["articulo_nombre"] == "CAZUELA 16 ONZ"
    # la cantidad dictada sobrevive a la ambigüedad (no se persiste 0)
    assert elegido["conteo"]["cantidad"] == 1

    descartable = _conteo(client, seed, sesion_id, "otra cazuela")
    descarte = client.post(
        f"/api/v1/conteos/{descartable['token_pendiente']}/resolver", json={"respuesta": "no"}
    ).json()
    assert descarte == {"status": "descartado"}

    no_cat = _conteo(client, seed, sesion_id, "producto xyz")
    assert no_cat["status"] == "no_catalogado"
    assert no_cat["texto_capturado"] == "producto xyz"
    assert no_cat["cantidad"] == 4

    otra_anomalia = _conteo(client, seed, sesion_id, "noventa unidades")
    ajustado = client.post(
        f"/api/v1/conteos/{otra_anomalia['token_pendiente']}/resolver",
        json={"respuesta": "cantidad:12"},
    ).json()
    assert ajustado["conteo"]["cantidad"] == 12.0


def test_resolver_si_persiste_valores_del_pipeline(client, seed):
    """El bug corregido: "si" debe guardar lo que el pipeline determinó ANTES
    de preguntar (cantidad 90), no 0 con el texto crudo como artículo."""
    sesion_id, _ = _sesion(client, seed, seed.op1)
    anomalia = _conteo(client, seed, sesion_id, "noventa cajas de cazuelas")
    resp = client.post(
        f"/api/v1/conteos/{anomalia['token_pendiente']}/resolver", json={"respuesta": "si"}
    ).json()
    assert resp["status"] == "confirmado"
    assert resp["conteo"]["cantidad"] == 90
    assert resp["conteo"]["articulo_nombre"] == "CAZUELA 16 ONZ"
    assert resp["conteo"]["unidad"] == "Unidad"
    with Session(engine) as s:
        conteo = s.scalar(select(Conteo).where(Conteo.activo.is_(True)))
        assert conteo.cantidad == 90
        assert conteo.unidad == "Unidad"
        assert conteo.articulo_id == seed.cazuela_id
        assert conteo.anomalia_flag is True


def test_supersede_append_only(client, seed):
    sesion_id, _ = _sesion(client, seed, seed.op1)
    primero = _conteo(client, seed, sesion_id, "treinta litros de aceite")
    segundo = _conteo(client, seed, sesion_id, "treinta litros de aceite")
    with Session(engine) as s:
        conteos = s.scalars(select(Conteo).order_by(Conteo.creado_en)).all()
    assert len(conteos) == 2
    viejo = next(c for c in conteos if str(c.id) == primero["conteo"]["id"])
    nuevo = next(c for c in conteos if str(c.id) == segundo["conteo"]["id"])
    assert viejo.activo is False
    assert nuevo.activo is True
    assert nuevo.supersede_id == viejo.id


def test_concurrencia_sin_bloqueo_y_colision(client, seed):
    sesion1, _ = _sesion(client, seed, seed.op1)
    sesion2, _ = _sesion(client, seed, seed.op2)
    _conteo(client, seed, sesion1, "treinta litros de aceite")

    with client.websocket_connect(f"/ws/bodegas/{seed.bodega_id}") as ws:
        _conteo(client, seed, sesion2, "treinta litros de aceite", operario=seed.op2)
        eventos = [ws.receive_json() for _ in range(3)]

    # Ningún conteo se rechazó: ambos persisten activos en sesiones distintas.
    with Session(engine) as s:
        activos = s.scalars(
            select(Conteo).where(Conteo.articulo_id == seed.aceite_id, Conteo.activo.is_(True))
        ).all()
    assert {str(c.sesion_id) for c in activos} == {sesion1, sesion2}

    colision = next(e for e in eventos if e["tipo"] == "colision")
    assert sorted(colision["data"]["sesiones"]) == sorted([sesion1, sesion2])

    progreso = client.get(f"/api/v1/sesiones/{sesion1}/progreso").json()
    assert progreso["colisiones"] == 1


def test_ws_dos_clientes_reciben_conteo_nuevo(client, seed):
    sesion_id, _ = _sesion(client, seed, seed.op1)
    url = f"/ws/bodegas/{seed.bodega_id}"
    with client.websocket_connect(url) as ws1, client.websocket_connect(url) as ws2:
        _conteo(client, seed, sesion_id, "treinta litros de aceite")
        for ws in (ws1, ws2):
            evento = ws.receive_json()
            assert evento["tipo"] == "conteo_nuevo"
            assert evento["data"]["articulo_nombre"] == "ACEITE DE OLIVA"
            assert ws.receive_json()["tipo"] == "progreso"


def test_token_expirado_y_ya_resuelto(client, seed):
    sesion_id, _ = _sesion(client, seed, seed.op1)

    expirado = _conteo(client, seed, sesion_id, "noventa cajas")["token_pendiente"]
    with Session(engine) as s:
        token = s.get(TokenPendiente, UUID(expirado))
        token.expira_en = datetime.now(UTC) - timedelta(minutes=1)
        s.commit()
    resp = client.post(f"/api/v1/conteos/{expirado}/resolver", json={"respuesta": "si"})
    assert resp.status_code == 410

    vigente = _conteo(client, seed, sesion_id, "noventa cajas")["token_pendiente"]
    assert client.post(
        f"/api/v1/conteos/{vigente}/resolver", json={"respuesta": "si"}
    ).status_code == 200
    resp = client.post(f"/api/v1/conteos/{vigente}/resolver", json={"respuesta": "si"})
    assert resp.status_code == 409


def _sin_rastro_de_sd(obj, ruta="$"):
    """La guardia del conteo ciego: ni claves de stock ni el valor de SD.

    ÚNICA excepción (decisión de producto): el campo `pregunta` de una anomalía
    de orden de magnitud (motivo="anomalia") sí puede citar el saldo anterior.
    Todo lo demás sigue blindado, incluidas las claves."""
    if isinstance(obj, dict):
        es_anomalia = obj.get("motivo") == "anomalia"
        for k, v in obj.items():
            k_norm = k.lower()
            assert k_norm != "sd" and "stock" not in k_norm, f"clave prohibida {k!r} en {ruta}"
            if es_anomalia and k == "pregunta":
                continue  # la pregunta de la anomalía puede traer el saldo
            _sin_rastro_de_sd(v, f"{ruta}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _sin_rastro_de_sd(v, f"{ruta}[{i}]")
    else:
        assert obj != SD_PROHIBIDO, f"valor de SD filtrado en {ruta}"
        if isinstance(obj, str):
            for forma in SD_PROHIBIDO_STR:
                assert forma not in obj, f"valor de SD filtrado en {ruta}"


def test_conteo_ciego_guardian(client, seed):
    """Recorre TODAS las respuestas de los endpoints de captura y TODOS los
    eventos WS de un flujo completo: nada puede oler a stock teórico."""
    respuestas = []

    resp = client.post(
        "/api/v1/sesiones",
        json={"bodega_id": seed.bodega_id, "operario_id": seed.op1, "tipo": "primario"},
    ).json()
    respuestas.append(resp)
    sesion_id = resp["sesion_id"]
    sesion2 = client.post(
        "/api/v1/sesiones",
        json={"bodega_id": seed.bodega_id, "operario_id": seed.op2, "tipo": "primario"},
    ).json()
    respuestas.append(sesion2)

    with client.websocket_connect(f"/ws/bodegas/{seed.bodega_id}") as ws:
        respuestas.append(_conteo(client, seed, sesion_id, "treinta litros de aceite"))
        anomalia = _conteo(client, seed, sesion_id, "noventa cajas de cazuelas")
        # la excepción se ejercita de verdad: la pregunta SÍ trae el saldo
        assert "9137,25" in anomalia["pregunta"]
        respuestas.append(anomalia)
        respuestas.append(
            client.post(
                f"/api/v1/conteos/{anomalia['token_pendiente']}/resolver",
                json={"respuesta": "si"},
            ).json()
        )
        respuestas.append(_conteo(client, seed, sesion_id, "producto xyz"))
        # colisión: la otra sesión cuenta el mismo artículo
        respuestas.append(
            _conteo(client, seed, sesion2["sesion_id"], "treinta litros de aceite",
                    operario=seed.op2)
        )
        # conteo_nuevo+progreso, anomalia, anomalia+conteo_nuevo+progreso,
        # conteo_nuevo+progreso, conteo_nuevo+progreso+colision = 11 eventos
        eventos = [ws.receive_json() for _ in range(11)]

    respuestas.append(client.get(f"/api/v1/sesiones/{sesion_id}/progreso").json())
    respuestas.append(client.post(f"/api/v1/sesiones/{sesion_id}/cerrar").json())

    assert {e["tipo"] for e in eventos} == {"conteo_nuevo", "progreso", "anomalia", "colision"}
    for r in respuestas + eventos:
        _sin_rastro_de_sd(r)
