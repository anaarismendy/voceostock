"""Puebla articulos.familia con la heurística de primera palabra significativa.

La columna existe desde 0001; esto solo la llena (ver
scripts/populate_familia.py — misma función, rerunnable tras nuevas ingestas).

Revision ID: 0003
Revises: 0002
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from scripts.populate_familia import poblar

    poblar(op.get_bind())


def downgrade() -> None:
    op.get_bind().exec_driver_sql("UPDATE articulos SET familia = NULL")
