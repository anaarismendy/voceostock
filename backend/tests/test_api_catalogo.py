"""I2: bodegas, artículos (sin SD — conteo ciego) y login por PIN."""
# ruff: noqa: F811 — las fixtures importadas se "redefinen" como parámetros

from tests.test_api_conteos import (  # noqa: F401 — fixtures reutilizadas
    SD_PROHIBIDO,
    _bootstrap_db,
    client,
    seed,
)


def test_bodegas_y_articulos_sin_sd(client, seed):
    bodegas = client.get("/api/v1/bodegas").json()
    assert [b["nombre"] for b in bodegas] == ["bodega demo"]

    articulos = client.get(f"/api/v1/articulos?bodega_id={seed.bodega_id}").json()
    assert len(articulos) == 4
    # E5 añadió `riesgo` al payload (nivel histórico, no SD).
    assert {"articulo_id", "articulo_nombre", "unidad", "riesgo"} == set(articulos[0])
    # conteo ciego: ni claves ni valores de SD en el buscador de artículos
    for a in articulos:
        assert "sd" not in {k.lower() for k in a}
        assert SD_PROHIBIDO not in a.values()


def test_login_identifica_no_crea(client, seed):
    """El login ya NO hace find-or-create: un PIN desconocido es un 404, no un
    operario nuevo. Antes, un dígito mal tecleado creaba una identidad fantasma
    y el operario real perdía su historial de precisión (D5)."""
    assert client.post("/api/v1/operarios/login", json={"pin": "4321"}).status_code == 404

    alta = client.post(
        "/api/v1/operarios", json={"nombre": "Ana", "pin": "4321", "rol": "operario"}
    ).json()
    r1 = client.post("/api/v1/operarios/login", json={"pin": "4321"}).json()
    r2 = client.post("/api/v1/operarios/login", json={"pin": "4321"}).json()
    assert r1["id"] == r2["id"] == alta["id"]  # mismo PIN → siempre el mismo operario
    assert client.post("/api/v1/operarios/login", json={"pin": "abc"}).status_code == 422


def test_login_devuelve_el_rol_del_backend(client, seed):
    """El rol ya no lo elige el cliente: lo define el líder al dar de alta."""
    client.post("/api/v1/operarios", json={"nombre": "Jefa", "pin": "7777", "rol": "lider"})
    assert client.post("/api/v1/operarios/login", json={"pin": "7777"}).json()["rol"] == "lider"
