"""Fixtures compartidas de las pruebas del pipeline (Persona 1).

Dos modos, como pide la tarea A2:
- por defecto (CI, sin red): las pruebas usan `cliente_replay`, que lee
  respuestas grabadas de `tests/fixtures/nlu/`.
- con `--record`: las pruebas marcadas `integration` llaman a Gemini real y
  reescriben esos fixtures.
"""

import os
from pathlib import Path

import pytest

from app.pipeline.nlu.cliente import ClienteGemini, ClienteReplay

DIR_FIXTURES_NLU = Path(__file__).parent.parent / "fixtures" / "nlu"


def pytest_addoption(parser):
    parser.addoption(
        "--record",
        action="store_true",
        default=False,
        help="Llama a Gemini real y regraba los fixtures de NLU (tarea A2).",
    )


@pytest.fixture(scope="session")
def modo_record(pytestconfig) -> bool:
    return bool(pytestconfig.getoption("--record"))


@pytest.fixture
def cliente_replay() -> ClienteReplay:
    return ClienteReplay(DIR_FIXTURES_NLU)


@pytest.fixture
def cliente_gemini() -> ClienteGemini:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        pytest.skip("GEMINI_API_KEY no configurada; prueba de integración omitida")
    return ClienteGemini(api_key=key)
