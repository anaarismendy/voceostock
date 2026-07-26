"""PIN único por operario.

El login hacía find-or-create sin restricción: dos operarios podían quedar con
el mismo PIN y `SELECT ... WHERE pin = :pin` devolvía uno al azar. Peor para D5:
las estadísticas se repartían entre dos filas y ninguna reflejaba al operario
real. El PIN identifica — tiene que ser único.

Revision ID: 0009
Revises: 0008
"""

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

_IX = "ux_operarios_pin"


def upgrade() -> None:
    # Duplicados heredados del find-or-create: al de PIN repetido se le asigna
    # uno libre en vez de borrarlo — puede tener conteos colgando (FK).
    # Los window functions no se permiten en el SET de un UPDATE: el PIN nuevo
    # se calcula dentro de la subconsulta. Si el 9001+ ya estuviera tomado, el
    # índice de abajo falla — ruidoso a propósito, mejor que pisar un PIN vivo.
    op.execute(
        """
        UPDATE operarios o SET pin = d.pin_nuevo
        FROM (
            SELECT id,
                   LPAD((9000 + ROW_NUMBER() OVER (ORDER BY id))::text, 4, '0') AS pin_nuevo
            FROM (
                SELECT id, ROW_NUMBER() OVER (PARTITION BY pin ORDER BY id) AS n
                FROM operarios
            ) t WHERE t.n > 1
        ) d WHERE o.id = d.id
        """
    )
    op.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS {_IX} ON operarios (pin)")


def downgrade() -> None:
    op.execute(f"DROP INDEX IF EXISTS {_IX}")
