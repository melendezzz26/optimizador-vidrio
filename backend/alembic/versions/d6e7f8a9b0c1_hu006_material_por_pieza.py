"""HU-006: trasladar material y espesor del pedido a cada pieza.

Revision ID: d6e7f8a9b0c1
Revises: 1c8754481a08
"""
from alembic import op
import sqlalchemy as sa

revision = "d6e7f8a9b0c1"
down_revision = "1c8754481a08"
branch_labels = None
depends_on = None


def _reject(bind, query, message):
    rows = bind.execute(sa.text(query + " LIMIT 5")).fetchall()
    if rows:
        raise RuntimeError(f"HU-006: {message}. IDs de ejemplo: {rows}")


def _counts(bind):
    return tuple(bind.scalar(sa.text(f"SELECT COUNT(*) FROM {table}"))
                 for table in ("pedidos", "piezas"))


def _preflight(bind):
    # Se mantiene hasta el commit/rollback de Alembic; no hay ventana de escritura
    # entre validación, backfill y retirada de las columnas antiguas.
    bind.execute(sa.text("LOCK TABLE pedidos, piezas IN ACCESS EXCLUSIVE MODE"))
    bind.execute(sa.text("LOCK TABLE tipos_vidrio_espesores IN SHARE MODE"))
    _reject(bind, "SELECT p.id_pieza FROM piezas p LEFT JOIN pedidos o USING (id_pedido) "
            "WHERE o.id_pedido IS NULL", "piezas huérfanas; revisar integridad antes de migrar")
    _reject(bind, "SELECT o.id_pedido FROM pedidos o WHERE NOT EXISTS "
            "(SELECT 1 FROM piezas p WHERE p.id_pedido = o.id_pedido)",
            "pedidos históricos sin piezas; decidir tratamiento sin borrar su material")
    return _counts(bind)


def _validate_pairs(bind, table, identifier):
    _reject(bind, f"SELECT {identifier} FROM {table} "
            "WHERE id_tipo_vidrio IS NULL OR espesor_mm IS NULL", "material o espesor NULL")
    _reject(bind, f"SELECT src.{identifier} FROM {table} src LEFT JOIN tipos_vidrio_espesores c "
            "ON c.id_tipo_vidrio = src.id_tipo_vidrio AND c.espesor_mm = src.espesor_mm "
            "WHERE c.id_tipo_vidrio IS NULL", "parejas inexistentes en el catálogo TA-013")


def _assert_counts(bind, before):
    if _counts(bind) != before:
        raise RuntimeError("HU-006: cambiaron los conteos de pedidos/piezas; se aborta la migración")


def upgrade():
    bind = op.get_bind()
    before = _preflight(bind)
    _validate_pairs(bind, "pedidos", "id_pedido")
    # Descubrir nombres del destino, no asumir nombres generados por PostgreSQL.
    material_fks = [fk for fk in sa.inspect(bind).get_foreign_keys("pedidos")
                    if set(fk["constrained_columns"]) & {"id_tipo_vidrio", "espesor_mm"}]
    for fk in material_fks:
        if not set(fk["constrained_columns"]) <= {"id_tipo_vidrio", "espesor_mm"}:
            raise RuntimeError("HU-006: FK de material inesperada; revisar dependencias de pedidos")

    op.add_column("piezas", sa.Column("id_tipo_vidrio", sa.Integer(), nullable=True))
    op.add_column("piezas", sa.Column("espesor_mm", sa.Numeric(4, 1), nullable=True))
    bind.execute(sa.text(
        "UPDATE piezas SET id_tipo_vidrio = pedidos.id_tipo_vidrio, "
        "espesor_mm = pedidos.espesor_mm FROM pedidos "
        "WHERE piezas.id_pedido = pedidos.id_pedido"))
    _validate_pairs(bind, "piezas", "id_pieza")
    _reject(bind, "SELECT p.id_pieza FROM piezas p JOIN pedidos o USING (id_pedido) "
            "WHERE p.id_tipo_vidrio IS DISTINCT FROM o.id_tipo_vidrio "
            "OR p.espesor_mm IS DISTINCT FROM o.espesor_mm", "backfill distinto del material histórico")
    _assert_counts(bind, before)
    op.alter_column("piezas", "id_tipo_vidrio", nullable=False)
    op.alter_column("piezas", "espesor_mm", nullable=False)
    op.create_foreign_key("fk_piezas_tipo_espesor", "piezas", "tipos_vidrio_espesores",
                          ["id_tipo_vidrio", "espesor_mm"], ["id_tipo_vidrio", "espesor_mm"])
    for fk in material_fks:
        op.drop_constraint(fk["name"], "pedidos", type_="foreignkey")
    # Sin CASCADE: dependencias externas imprevistas abortan toda la transacción.
    op.drop_column("pedidos", "id_tipo_vidrio")
    op.drop_column("pedidos", "espesor_mm")
    _assert_counts(bind, before)


def downgrade():
    bind = op.get_bind()
    before = _preflight(bind)
    _validate_pairs(bind, "piezas", "id_pieza")
    _reject(bind, "SELECT id_pedido FROM piezas GROUP BY id_pedido "
            "HAVING COUNT(DISTINCT (id_tipo_vidrio, espesor_mm)) > 1",
            "downgrade bloqueado: pedidos multimaterial no tienen cabecera monomaterial equivalente")

    op.add_column("pedidos", sa.Column("id_tipo_vidrio", sa.Integer(), nullable=True))
    op.add_column("pedidos", sa.Column("espesor_mm", sa.Numeric(4, 1), nullable=True))
    # DISTINCT produce exactamente una pareja por pedido, demostrado arriba.
    # No se selecciona arbitrariamente la primera pieza ni se redondean valores.
    bind.execute(sa.text(
        "UPDATE pedidos o SET id_tipo_vidrio = p.id_tipo_vidrio, espesor_mm = p.espesor_mm "
        "FROM (SELECT DISTINCT id_pedido, id_tipo_vidrio, espesor_mm FROM piezas) p "
        "WHERE p.id_pedido = o.id_pedido"))
    _validate_pairs(bind, "pedidos", "id_pedido")
    op.alter_column("pedidos", "id_tipo_vidrio", nullable=False)
    op.alter_column("pedidos", "espesor_mm", nullable=False)
    op.create_foreign_key("pedidos_id_tipo_vidrio_fkey", "pedidos", "tipos_vidrio",
                          ["id_tipo_vidrio"], ["id_tipo_vidrio"])
    op.create_foreign_key("fk_pedidos_tipo_espesor", "pedidos", "tipos_vidrio_espesores",
                          ["id_tipo_vidrio", "espesor_mm"], ["id_tipo_vidrio", "espesor_mm"])
    op.drop_constraint("fk_piezas_tipo_espesor", "piezas", type_="foreignkey")
    op.drop_column("piezas", "id_tipo_vidrio")
    op.drop_column("piezas", "espesor_mm")
    _assert_counts(bind, before)
