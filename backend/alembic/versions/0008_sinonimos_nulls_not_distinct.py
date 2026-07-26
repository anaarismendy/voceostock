"""Índice único de sinónimos con NULLS NOT DISTINCT.

Sin esto, Postgres trata cada NULL como distinto y los sinónimos GLOBALES
(sede_id NULL, el caso por defecto de POST /config/sinonimos) se duplicaban en
vez de devolver 409.

Revision ID: 0008
Revises: 0007
"""

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

_IX = "ux_sinonimos_sede_texto"
_COLS = "(sede_id, texto_normalizado)"


def upgrade() -> None:
    op.execute(
        "DELETE FROM sinonimos_articulo a USING sinonimos_articulo b "
        "WHERE a.id > b.id AND a.sede_id IS NULL AND b.sede_id IS NULL "
        "AND a.texto_normalizado = b.texto_normalizado"
    )
    op.execute(f"DROP INDEX IF EXISTS {_IX}")
    op.execute(f"CREATE UNIQUE INDEX {_IX} ON sinonimos_articulo {_COLS} NULLS NOT DISTINCT")


def downgrade() -> None:
    op.execute(f"DROP INDEX IF EXISTS {_IX}")
    op.execute(f"CREATE UNIQUE INDEX {_IX} ON sinonimos_articulo {_COLS}")
