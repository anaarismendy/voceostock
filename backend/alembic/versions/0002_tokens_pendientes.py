"""Tabla tokens_pendientes (capturas en espera de confirmación).

Revision ID: 0002
Revises: 0001
"""

from alembic import op
from app.models import TokenPendiente

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # checkfirst: la 0001 hace create_all de los modelos, así que en una BD
    # recién migrada la tabla ya existe.
    TokenPendiente.__table__.create(bind=op.get_bind(), checkfirst=True)


def downgrade() -> None:
    TokenPendiente.__table__.drop(bind=op.get_bind(), checkfirst=True)
