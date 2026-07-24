"""Config global de pruebas.

Fija DATABASE_URL a la BD de prueba ANTES de que cualquier test importe la
app (app.db crea el engine al importar) y manda el storage a un dir temporal.
Local: Postgres del contenedor colsubsidiohackaton-db-1 en el puerto 5433
(mismo puerto que el service de CI).
"""

import os
import tempfile

os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://voceo:voceo@localhost:5433/voceostock_test"
)
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("STORAGE_DIR", tempfile.mkdtemp(prefix="voceo_storage_"))
