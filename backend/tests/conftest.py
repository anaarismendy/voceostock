"""Config global de pruebas.

Fija DATABASE_URL a la BD de prueba ANTES de que cualquier test importe la
app (app.db crea el engine al importar) y manda el storage a un dir temporal.
Local: Postgres del contenedor colsubsidiohackaton-db-1 en el puerto 5433
(mismo puerto que el service de CI).
"""

import os
import tempfile
from pathlib import Path

os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://voceo:voceo@localhost:5433/voceostock_test"
)
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("STORAGE_DIR", tempfile.mkdtemp(prefix="voceo_storage_"))
# TTS aislado: las pruebas no deben leer la caché commiteada ni llamar a la API.
os.environ.setdefault("TTS_CACHE_DIR", tempfile.mkdtemp(prefix="voceo_tts_"))
os.environ.pop("ELEVENLABS_API_KEY", None)
# La API de pruebas corre el pipeline real en modo replay (sin red) con sus
# propias respuestas grabadas; PIPELINE_MODE=auto ya resuelve replay sin key.
os.environ.setdefault("REPLAY_DIR", str(Path(__file__).parent / "fixtures" / "replay_api"))
