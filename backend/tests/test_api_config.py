"""E2: endpoints de configuración (umbrales + sinónimos). Corre contra la BD de
prueba. Reusa las fixtures de test_api_conteos."""
# ruff: noqa: F811 — las fixtures importadas se "redefinen" como parámetros

import pytest

from app.pipeline.confianza import restablecer, umbrales_actuales
from tests.test_api_conteos import _bootstrap_db, client, seed  # noqa: F401


@pytest.fixture(autouse=True)
def _restaura_umbrales():
    # El PUT reconfigura el pipeline vivo; devolver a defaults tras cada test
    # para no alterar el comportamiento de los demás (baja_confianza usa rapida).
    yield
    restablecer()


def test_get_umbrales_devuelve_defaults_sin_fila(client, seed):
    r = client.get("/api/v1/config/umbrales")
    assert r.status_code == 200
    assert r.json() == {"auto": 0.95, "rapida": 0.9, "aclaracion": 0.7}


def test_put_umbral_se_refleja_sin_reiniciar(client, seed):
    r = client.put("/api/v1/config/umbrales", json={"auto": 0.95, "rapida": 0.5, "aclaracion": 0.4})
    assert r.status_code == 200
    # Persiste (GET lo refleja)…
    assert client.get("/api/v1/config/umbrales").json()["rapida"] == 0.5
    # …y el pipeline VIVO ya lo usa, sin reiniciar (J1 / DoD de E2).
    assert umbrales_actuales().rapida == 0.5


def test_put_umbral_inconsistente_422(client, seed):
    # rapida > auto viola el orden del dominio.
    r = client.put("/api/v1/config/umbrales", json={"auto": 0.5, "rapida": 0.9, "aclaracion": 0.4})
    assert r.status_code == 422


def test_crud_sinonimos(client, seed):
    # Crear (articulo del seed → FK válida).
    r = client.post(
        "/api/v1/config/sinonimos",
        json={"articulo_id": seed.cazuela_id, "texto_sinonimo": "olla honda"},
    )
    assert r.status_code == 201
    sid = r.json()["id"]
    assert r.json()["origen"] == "manual"

    # Listar.
    lst = client.get("/api/v1/config/sinonimos").json()
    assert any(x["texto_sinonimo"] == "olla honda" and x["articulo_id"] == seed.cazuela_id for x in lst)

    # Borrar.
    assert client.delete(f"/api/v1/config/sinonimos/{sid}").status_code == 204
    assert all(x["id"] != sid for x in client.get("/api/v1/config/sinonimos").json())


def test_sinonimo_global_duplicado_409(client, seed):
    # sede_id NULL: sin NULLS NOT DISTINCT (migración 0008) el índice único no
    # aplica y esto crearía un duplicado en vez de dar 409.
    body = {"articulo_id": seed.cazuela_id, "texto_sinonimo": "cazuelita"}
    assert client.post("/api/v1/config/sinonimos", json=body).status_code == 201
    assert client.post("/api/v1/config/sinonimos", json=body).status_code == 409


def test_borrar_sinonimo_inexistente_404(client, seed):
    assert client.delete("/api/v1/config/sinonimos/999999").status_code == 404
