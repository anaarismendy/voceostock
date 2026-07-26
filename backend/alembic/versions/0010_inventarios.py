"""Tabla inventarios: el ciclo de conteo como entidad propia.

Antes de esto, /cierre y /dashboard agregaban por bodega_id sin filtrar nada:
el conteo de agosto sumaba el de julio, para siempre, y no había forma de pedir
"el inventario 1". Ahora las sesiones cuelgan de un inventario numerado y
fechado por bodega.

Backfill: todo lo ya contado en una bodega pasa a ser su Inventario #1, abierto
(nadie lo cerró nunca), para no perder historia ni romper el cierre en curso.

Revision ID: 0010
Revises: 0009
"""

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # IF NOT EXISTS en todo: la 0001 hace create_all de los modelos, así que en
    # una BD desde cero estas tablas ya existen (mismo patrón que 0002 y 0007).
    op.execute("""
        CREATE TABLE IF NOT EXISTS inventarios (
            id          SERIAL PRIMARY KEY,
            bodega_id   INTEGER NOT NULL REFERENCES bodegas(id),
            numero      INTEGER NOT NULL,
            estado      TEXT NOT NULL DEFAULT 'abierto',
            corte_fecha DATE,
            abierto_en  TIMESTAMPTZ NOT NULL DEFAULT now(),
            cerrado_en  TIMESTAMPTZ,
            CONSTRAINT ck_inventarios_estado CHECK (estado IN ('abierto','cerrado'))
        )
    """)
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_inventarios_bodega_abierto ON inventarios (bodega_id) "
        "WHERE estado = 'abierto'"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_inventarios_bodega_numero "
        "ON inventarios (bodega_id, numero)"
    )
    op.execute(
        "ALTER TABLE sesiones_conteo ADD COLUMN IF NOT EXISTS inventario_id "
        "INTEGER REFERENCES inventarios(id)"
    )

    # Backfill: un Inventario #1 por bodega que ya tenga sesiones huérfanas.
    # `abierto_en` toma la fecha de la sesión más antigua para que el rango sea
    # el real. ON CONFLICT: re-ejecutar no duplica ni revienta.
    op.execute("""
        INSERT INTO inventarios (bodega_id, numero, estado, abierto_en)
        SELECT bodega_id, 1, 'abierto', MIN(iniciada_en)
        FROM sesiones_conteo
        WHERE inventario_id IS NULL
        GROUP BY bodega_id
        ON CONFLICT DO NOTHING
    """)
    op.execute("""
        UPDATE sesiones_conteo s
        SET inventario_id = i.id
        FROM inventarios i
        WHERE i.bodega_id = s.bodega_id AND i.numero = 1 AND s.inventario_id IS NULL
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_sesiones_inventario ON sesiones_conteo (inventario_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_sesiones_inventario")
    op.execute("ALTER TABLE sesiones_conteo DROP COLUMN IF EXISTS inventario_id")
    op.execute("DROP TABLE IF EXISTS inventarios")
