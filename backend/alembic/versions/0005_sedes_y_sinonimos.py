"""Sedes, bodegas.sede_id y sinonimos_articulo (Fase 2 — punto 0 + D3).

- `sedes`: agrupa bodegas del mismo sitio físico.
- `bodegas.sede_id`: a qué sede pertenece cada bodega (nullable).
- `sinonimos_articulo`: capa de sinónimos por sede que el matching consulta
  antes de la cascada. NUNCA toca el catálogo oficial (`articulos`).

Revision ID: 0005
Revises: 0004
"""

from alembic import op
from app.models import Sede, SinonimoArticulo

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    # checkfirst / IF NOT EXISTS: en una BD recién migrada la 0001 hace create_all
    # de los modelos, así que estas estructuras ya existen (mismo patrón que 0002).
    Sede.__table__.create(bind=bind, checkfirst=True)
    op.execute("ALTER TABLE bodegas ADD COLUMN IF NOT EXISTS sede_id INTEGER REFERENCES sedes(id)")
    SinonimoArticulo.__table__.create(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    SinonimoArticulo.__table__.drop(bind=bind, checkfirst=True)
    op.execute("ALTER TABLE bodegas DROP COLUMN IF EXISTS sede_id")
    Sede.__table__.drop(bind=bind, checkfirst=True)
