"""Modo replay para la demo (tarea A10).

Con GEMINI_API_KEY vacía y replay activo, el pipeline responde los casos del
guion sin tocar la red — la doble mitigación para cuota agotada o wifi caído.
"""

from pathlib import Path
from uuid import uuid4

import pytest

from app.pipeline import servicios
from app.pipeline.core import ContextoBodega, PayloadConteo, procesar_conteo

REPLAY_DEMO = Path(__file__).resolve().parents[3] / "data" / "replay" / "nlu"


@pytest.fixture
def entorno_replay(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("PIPELINE_MODE", "auto")  # auto → replay si no hay key
    monkeypatch.setenv("PIPELINE_DATA", "csv")
    monkeypatch.setenv("REPLAY_DIR", str(REPLAY_DEMO))
    servicios.reset_pipeline()
    yield
    servicios.reset_pipeline()


def test_auto_sin_key_resuelve_replay(entorno_replay):
    assert servicios._modo() == "replay"
    pipeline = servicios.get_pipeline()
    from app.pipeline.matching.embeddings import EmbedderLexico
    from app.pipeline.nlu.cliente import ClienteReplay

    assert isinstance(pipeline.nlu, ClienteReplay)
    assert isinstance(pipeline.embedder, EmbedderLexico)


async def test_guion_responde_sin_red(entorno_replay):
    payload = PayloadConteo(
        sesion_id=uuid4(), bodega_id=3, operario_id=uuid4(),
        fuente="voz-tablet", payload_texto="noventa cajas de cazuelas",
    )
    r = await procesar_conteo(payload, ContextoBodega(bodega_id=3))
    assert r.status == "requiere_confirmacion"
    assert r.motivo == "anomalia"
