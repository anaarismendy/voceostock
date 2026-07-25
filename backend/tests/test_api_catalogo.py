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


def test_login_por_pin_find_or_create(client, seed):
    r1 = client.post("/api/v1/operarios/login", json={"pin": "4321"}).json()
    r2 = client.post("/api/v1/operarios/login", json={"pin": "4321"}).json()
    assert r1["id"] == r2["id"]  # mismo PIN → mismo operario
    assert client.post("/api/v1/operarios/login", json={"pin": "abc"}).status_code == 422
