"""Tabla umbrales_confianza + fila global por defecto (Fase 2 — D1).

Mueve el umbral de confianza (antes 0.8 hardcodeado en el motor de anomalías) a
configuración editable. La fila con sede_id NULL es la config global.

Revision ID: 0004
Revises: 0003
"""

from alembic import op
from app.models import UmbralConfianza

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    # checkfirst: la 0001 hace create_all de los modelos, así que en una BD
    # recién migrada la tabla ya existe (mismo patrón que 0002).
    UmbralConfianza.__table__.create(bind=bind, checkfirst=True)
    # Fila global por defecto (idempotente: no duplica si ya está).
    existe = bind.exec_driver_sql(
        "SELECT 1 FROM umbrales_confianza WHERE sede_id IS NULL LIMIT 1"
    ).first()
    if not existe:
        bind.exec_driver_sql(
            "INSERT INTO umbrales_confianza (sede_id, auto, rapida, aclaracion) "
            "VALUES (NULL, 0.95, 0.90, 0.70)"
        )


def downgrade() -> None:
    UmbralConfianza.__table__.drop(bind=op.get_bind(), checkfirst=True)
