"""HU-012: incorporar clientes y asociarlos a pedidos.

Revision ID: ef6564220e70
Revises: d6e7f8a9b0c1
"""

from alembic import op
import sqlalchemy as sa


revision = "ef6564220e70"
down_revision = "d6e7f8a9b0c1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "clientes",
        sa.Column("id_cliente", sa.Integer(), primary_key=True),
        sa.Column("tipo_documento", sa.String(), nullable=True),
        sa.Column("numero_documento", sa.String(), nullable=True),
        sa.Column("nombre_razon_social", sa.String(), nullable=False),
        sa.Column("telefono", sa.String(), nullable=True),
        sa.Column(
            "estado",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "fecha_registro",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "tipo_documento",
            "numero_documento",
            name="uq_clientes_tipo_numero_documento",
        ),
    )

    # Se mantiene nullable durante la transición para no inventar clientes
    # asociados a pedidos históricos.
    op.add_column(
        "pedidos",
        sa.Column("id_cliente", sa.Integer(), nullable=True),
    )

    op.create_foreign_key(
        "fk_pedidos_cliente",
        "pedidos",
        "clientes",
        ["id_cliente"],
        ["id_cliente"],
    )


def downgrade():
    op.drop_constraint(
        "fk_pedidos_cliente",
        "pedidos",
        type_="foreignkey",
    )

    op.drop_column("pedidos", "id_cliente")

    op.drop_table("clientes")