"""S1: asociación multipedido, preservando la referencia histórica escalar.

Revision ID: s1opt02b4c6d
Revises: s1rbac01a2b3
"""
from alembic import op
import sqlalchemy as sa

revision = "s1opt02b4c6d"
down_revision = "s1rbac01a2b3"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "optimizacion_pedidos",
        sa.Column("id_optimizacion", sa.Integer(), nullable=False),
        sa.Column("id_pedido", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id_optimizacion", "id_pedido", name="pk_optimizacion_pedidos"),
        sa.ForeignKeyConstraint(["id_optimizacion"], ["optimizaciones.id_optimizacion"],
                                name="fk_optimizacion_pedidos_optimizacion"),
        sa.ForeignKeyConstraint(["id_pedido"], ["pedidos.id_pedido"], name="fk_optimizacion_pedidos_pedido"),
    )
    op.create_index("ix_optimizacion_pedidos_pedido", "optimizacion_pedidos", ["id_pedido", "id_optimizacion"])
    op.execute("INSERT INTO optimizacion_pedidos(id_optimizacion,id_pedido) SELECT id_optimizacion,id_pedido FROM optimizaciones")
    missing = op.get_bind().scalar(sa.text(
        "SELECT count(*) FROM optimizaciones o LEFT JOIN optimizacion_pedidos p "
        "ON p.id_optimizacion=o.id_optimizacion AND p.id_pedido=o.id_pedido WHERE p.id_pedido IS NULL"
    ))
    if missing:
        raise RuntimeError("Backfill incompleto; no se puede preservar la trazabilidad histórica.")


def downgrade():
    # Check BEFORE DDL; rollback must never discard an unrepresentable batch.
    unsafe = op.get_bind().scalar(sa.text(
        "SELECT count(*) FROM optimizaciones o WHERE "
        "(SELECT count(*) FROM optimizacion_pedidos p WHERE p.id_optimizacion=o.id_optimizacion) <> 1 "
        "OR NOT EXISTS (SELECT 1 FROM optimizacion_pedidos p "
        "WHERE p.id_optimizacion=o.id_optimizacion AND p.id_pedido=o.id_pedido)"
    ))
    if unsafe:
        raise RuntimeError("Downgrade perdería asociaciones multipedido o trazabilidad; operación rechazada.")
    op.drop_index("ix_optimizacion_pedidos_pedido", table_name="optimizacion_pedidos")
    op.drop_table("optimizacion_pedidos")
