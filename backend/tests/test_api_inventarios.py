"""Ciclos de conteo por bodega: numeración, apertura/cierre y —lo que motivó
la tabla— que el cierre de un inventario NO arrastre lo contado en el anterior.
"""
# ruff: noqa: F811 — las fixtures importadas se "redefinen" como parámetros

from tests.test_api_conteos import _bootstrap_db, client, seed  # noqa: F401


def _contar(client, seed, sesion_id, texto):
    r = client.post(
        "/api/v1/conteos",
        json={
            "sesion_id": sesion_id, "bodega_id": seed.bodega_id, "operario_id": seed.op1,
            "fuente": "manual", "payload_texto": texto,
        },
    )
    assert r.status_code == 200, r.text
    return r.json()


def _sesion(client, seed, operario=None):
    r = client.post(
        "/api/v1/sesiones",
        json={
            "bodega_id": seed.bodega_id,
            "operario_id": operario or seed.op1,
            "tipo": "primario",
        },
    )
    return r


def test_listar_devuelve_el_ciclo_sembrado(client, seed):
    filas = client.get("/api/v1/inventarios", params={"bodega_id": seed.bodega_id}).json()
    assert [f["numero"] for f in filas] == [1]
    assert filas[0]["estado"] == "abierto"


def test_no_se_puede_abrir_un_segundo_ciclo_a_la_vez(client, seed):
    r = client.post("/api/v1/inventarios", json={"bodega_id": seed.bodega_id})
    assert r.status_code == 409


def test_cerrar_y_abrir_numera_consecutivo_por_bodega(client, seed):
    assert client.post(f"/api/v1/inventarios/{seed.inventario_id}/cerrar").status_code == 200
    nuevo = client.post("/api/v1/inventarios", json={"bodega_id": seed.bodega_id})
    assert nuevo.status_code == 201
    assert nuevo.json()["numero"] == 2
    assert nuevo.json()["estado"] == "abierto"
    # El primero queda cerrado y fechado.
    filas = client.get("/api/v1/inventarios", params={"bodega_id": seed.bodega_id}).json()
    cerrado = next(f for f in filas if f["numero"] == 1)
    assert cerrado["estado"] == "cerrado" and cerrado["cerrado_en"] is not None


def test_cerrar_dos_veces_da_409(client, seed):
    client.post(f"/api/v1/inventarios/{seed.inventario_id}/cerrar")
    assert client.post(f"/api/v1/inventarios/{seed.inventario_id}/cerrar").status_code == 409


def test_sin_ciclo_abierto_no_se_puede_contar(client, seed):
    client.post(f"/api/v1/inventarios/{seed.inventario_id}/cerrar")
    r = _sesion(client, seed)
    assert r.status_code == 409
    assert "líder" in r.json()["detail"]


def test_el_cierre_no_arrastra_lo_contado_en_el_ciclo_anterior(client, seed):
    """La razón de ser de la tabla: antes /cierre agregaba por bodega_id y el
    conteo de agosto sumaba el de julio, para siempre."""
    sesion1 = _sesion(client, seed).json()["sesion_id"]
    _contar(client, seed, sesion1, "treinta litros de aceite")

    cierre1 = client.get("/api/v1/cierre", params={"bodega_id": seed.bodega_id}).json()
    aceite1 = next(f for f in cierre1 if f["articulo_id"] == seed.aceite_id)
    assert aceite1["contado"] == 30.0

    # Ciclo 2: se vuelve a contar el MISMO artículo, con otra cantidad.
    client.post(f"/api/v1/inventarios/{seed.inventario_id}/cerrar")
    inv2 = client.post("/api/v1/inventarios", json={"bodega_id": seed.bodega_id}).json()
    sesion2 = _sesion(client, seed).json()["sesion_id"]
    _contar(client, seed, sesion2, "treinta litros de aceite")

    # El cierre por defecto (ciclo vigente) muestra 30, no 60.
    cierre2 = client.get("/api/v1/cierre", params={"bodega_id": seed.bodega_id}).json()
    aceite2 = next(f for f in cierre2 if f["articulo_id"] == seed.aceite_id)
    assert aceite2["contado"] == 30.0, "el ciclo 2 está sumando lo contado en el 1"

    # Y el ciclo 1 sigue consultable tal como quedó.
    cierre_viejo = client.get(
        "/api/v1/cierre",
        params={"bodega_id": seed.bodega_id, "inventario_id": seed.inventario_id},
    ).json()
    assert next(f for f in cierre_viejo if f["articulo_id"] == seed.aceite_id)["contado"] == 30.0
    assert inv2["numero"] == 2


def test_dashboard_acotado_al_ciclo(client, seed):
    sesion1 = _sesion(client, seed).json()["sesion_id"]
    _contar(client, seed, sesion1, "treinta litros de aceite")
    assert client.get("/api/v1/dashboard", params={"bodega_id": seed.bodega_id}).json()[
        "total_conteos"
    ] == 1

    client.post(f"/api/v1/inventarios/{seed.inventario_id}/cerrar")
    client.post("/api/v1/inventarios", json={"bodega_id": seed.bodega_id})
    # Ciclo nuevo: el "en vivo" arranca de cero, no hereda el feed anterior.
    assert client.get("/api/v1/dashboard", params={"bodega_id": seed.bodega_id}).json()[
        "total_conteos"
    ] == 0


def test_cerrar_el_ciclo_cierra_sus_sesiones(client, seed):
    sesion_id = _sesion(client, seed).json()["sesion_id"]
    client.post(f"/api/v1/inventarios/{seed.inventario_id}/cerrar")
    # La sesión ya no admite cierre propio: el ciclo se la llevó.
    assert client.post(f"/api/v1/sesiones/{sesion_id}/cerrar").status_code == 409


def test_el_cierre_no_filtra_sd_de_otro_corte(client, seed):
    """`_sd_bodega` toma el corte más reciente; con un solo corte el SD del
    seed debe salir intacto (antes el valor dependía del orden de las filas)."""
    sesion_id = _sesion(client, seed).json()["sesion_id"]
    _contar(client, seed, sesion_id, "treinta litros de aceite")
    fila = next(
        f
        for f in client.get("/api/v1/cierre", params={"bodega_id": seed.bodega_id}).json()
        if f["articulo_id"] == seed.aceite_id
    )
    assert fila["sd"] == 33.0
    assert fila["diferencia"] == -3.0
