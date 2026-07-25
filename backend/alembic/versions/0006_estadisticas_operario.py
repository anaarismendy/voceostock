"""Tabla estadisticas_operario (Fase 2 — D5).

Estadísticas agregadas por operario (totales/correctas). Su precisión histórica
ajusta la sensibilidad de confirmación del pipeline. No modifica `operarios`.

Revision ID: 0006
Revises: 0005
"""

from alembic import op
from app.models import EstadisticaOperario

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # checkfirst: la 0001 hace create_all de los modelos (mismo patrón que 0002).
    EstadisticaOperario.__table__.create(bind=op.get_bind(), checkfirst=True)


def downgrade() -> None:
    EstadisticaOperario.__table__.drop(bind=op.get_bind(), checkfirst=True)
