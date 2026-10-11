"""HU-014: persistencia base para la trazabilidad de inventario.

Revision ID: fa014e1a2b3c
Revises: ef6564220e70

El downgrade elimina movimientos y, con ellos, los datos de trazabilidad HU-014.
"""

from alembic import op
import sqlalchemy as sa


revision = "fa014e1a2b3c"
down_revision = "ef6564220e70"
branch_labels = None
depends_on = None


MANUAL_EVENTS_SQL = "'BAJA_ROTURA', 'BAJA_MERMA', 'BAJA_ERROR_REGISTRO', 'BAJA_RETIRO'"
ALL_EVENTS_SQL = f"{MANUAL_EVENTS_SQL}, 'CONSUMO_OPTIMIZACION'"


def upgrade():
    op.create_table(
        "movimientos_inventario",
        sa.Column("id_movimiento", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("id_plancha", sa.Integer(), nullable=True),
        sa.Column("id_retazo", sa.Integer(), nullable=True),
        sa.Column("tipo_evento", sa.String(length=30), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=False),
        sa.Column("observacion", sa.Text(), nullable=True),
        sa.Column("id_usuario", sa.Integer(), nullable=False),
        sa.Column(
            "fecha",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("id_optimizacion", sa.Integer(), nullable=True),
        sa.CheckConstraint(
            "(id_plancha IS NOT NULL) <> (id_retazo IS NOT NULL)",
            name="ck_movimientos_inventario_recurso_xor",
        ),
        sa.CheckConstraint(
            f"tipo_evento IN ({ALL_EVENTS_SQL})",
            name="ck_movimientos_inventario_tipo_evento",
        ),
        sa.CheckConstraint(
            "length(trim(motivo)) > 0",
            name="ck_movimientos_inventario_motivo_no_vacio",
        ),
        sa.ForeignKeyConstraint(
            ["id_plancha"], ["planchas.id_plancha"],
            name="fk_movimientos_inventario_plancha",
        ),
        sa.ForeignKeyConstraint(
            ["id_retazo"], ["retazos.id_retazo"],
            name="fk_movimientos_inventario_retazo",
        ),
        sa.ForeignKeyConstraint(
            ["id_usuario"], ["usuarios.id_usuario"],
            name="fk_movimientos_inventario_usuario",
        ),
        sa.ForeignKeyConstraint(
            ["id_optimizacion"], ["optimizaciones.id_optimizacion"],
            name="fk_movimientos_inventario_optimizacion",
        ),
    )

    op.create_index(
        "ix_movimientos_inventario_plancha_fecha",
        "movimientos_inventario",
        ["id_plancha", "fecha", "id_movimiento"],
    )
    op.create_index(
        "ix_movimientos_inventario_retazo_fecha",
        "movimientos_inventario",
        ["id_retazo", "fecha", "id_movimiento"],
    )
    op.create_index(
        "uq_movimientos_baja_manual_plancha",
        "movimientos_inventario",
        ["id_plancha"],
        unique=True,
        postgresql_where=sa.text(f"tipo_evento IN ({MANUAL_EVENTS_SQL})"),
    )
    op.create_index(
        "uq_movimientos_baja_manual_retazo",
        "movimientos_inventario",
        ["id_retazo"],
        unique=True,
        postgresql_where=sa.text(f"tipo_evento IN ({MANUAL_EVENTS_SQL})"),
    )


def downgrade():
    """Elimina la tabla y todos los datos de trazabilidad de HU-014."""
    op.drop_table("movimientos_inventario")
