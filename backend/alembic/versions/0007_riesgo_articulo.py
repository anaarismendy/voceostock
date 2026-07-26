"""Tabla riesgo_articulo (Fase 2 — E5).

Persiste el nivel de riesgo histórico por artículo (alto/medio/bajo) que calcula
el job a partir de D6. Se expone en el payload del catálogo. No toca `articulos`.

Revision ID: 0007
Revises: 0006
"""

from alembic import op
from app.models import RiesgoArticulo

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # checkfirst: la 0001 hace create_all de los modelos (mismo patrón que 0002).
    RiesgoArticulo.__table__.create(bind=op.get_bind(), checkfirst=True)


def downgrade() -> None:
    RiesgoArticulo.__table__.drop(bind=op.get_bind(), checkfirst=True)
