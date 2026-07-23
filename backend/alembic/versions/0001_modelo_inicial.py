"""Modelo inicial: bodegas, articulos, stock_teorico, operarios,
sesiones_conteo, conteos, alias_articulos.

Revision ID: 0001
Revises:
"""

from alembic import op
from app.models import Base

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    # ponytail: migración inicial atada a los modelos; las siguientes van a mano
    # con op.create_table/op.add_column (si los modelos cambian, esta no se toca).
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
    op.execute("DROP EXTENSION IF EXISTS vector")
