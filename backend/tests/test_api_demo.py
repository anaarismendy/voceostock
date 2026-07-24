"""C9–C11 reales: cierre del líder, dashboard (sin SD) y semilla de demo."""
# ruff: noqa: F811 — las fixtures importadas se "redefinen" como parámetros

from tests.test_api_conteos import (  # noqa: F401 — fixtures reutilizadas
    SD_PROHIBIDO,
    _bootstrap_db,
    _sin_rastro_de_sd,
    client,
    seed,
)


def test_seed_y_cierre_cuadra_sobra_falta(client, seed):
    r = client.post(f"/api/v1/demo/seed?bodega_id={seed.bodega_id}").json()
    assert r == {"ok": True, "total": 2}  # COSTILLA DE RES no está en la BD de prueba

    filas = client.get(f"/api/v1/cierre?bodega_id={seed.bodega_id}&ids=7290").json()
    por_nombre = {f["articulo_nombre"]: f for f in filas}
    assert por_nombre["CAZUELA 16 ONZ"]["diferencia"] == 2.0  # sobra
    assert por_nombre["ACEITE DE OLIVA"]["diferencia"] == 0.0  # cuadra
    # ids=7290 es nr_articulo (checklist): aparece como "sin contar"
    assert por_nombre["ACEITE DE OLIVA"]["contado"] > 0

    reset = client.post(f"/api/v1/demo/reset?bodega_id={seed.bodega_id}").json()
    assert reset["ok"] is True
    assert client.get(f"/api/v1/cierre?bodega_id={seed.bodega_id}").json() == []


def test_dashboard_sin_sd(client, seed):
    client.post(f"/api/v1/demo/seed?bodega_id={seed.bodega_id}")
    r = client.get(f"/api/v1/dashboard?bodega_id={seed.bodega_id}").json()
    assert r["total_conteos"] == 2
    assert r["articulos_unicos"] == 2
    assert len(r["recientes"]) == 2
    for fila in r["recientes"]:
        assert "sd" not in {k.lower() for k in fila}
