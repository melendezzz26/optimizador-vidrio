"""TA-036: cantidades auditables y bajas parciales de plancha.

Historia de planchas: NULL significa cantidad desconocida, sin imputación.
Solo bajas manuales de retazos (unidades concretas) admiten backfill de 1.
Downgrade bloqueado si perdería cantidades o múltiples bajas de una plancha.
"""
from alembic import op
import sqlalchemy as sa

revision = "ta036a1b2c3d"
down_revision = "fa014e1a2b3c"
branch_labels = None
depends_on = None

MANUAL = "'BAJA_ROTURA', 'BAJA_MERMA', 'BAJA_ERROR_REGISTRO', 'BAJA_RETIRO'"


def upgrade():
    op.add_column("movimientos_inventario", sa.Column("cantidad_afectada", sa.Integer(), nullable=True))
    op.execute(sa.text(
        f"UPDATE movimientos_inventario SET cantidad_afectada=1 "
        f"WHERE id_retazo IS NOT NULL AND tipo_evento IN ({MANUAL})"
    ))
    op.create_check_constraint("ck_movimientos_cantidad_positiva", "movimientos_inventario",
                               "cantidad_afectada IS NULL OR cantidad_afectada > 0")
    op.create_check_constraint("ck_movimientos_retazo_unitario", "movimientos_inventario",
                               "id_retazo IS NULL OR cantidad_afectada IS NULL OR cantidad_afectada = 1")
    op.drop_index("uq_movimientos_baja_manual_plancha", table_name="movimientos_inventario")


def downgrade():
    connection = op.get_bind()
    # Lock excludes concurrent inserts between the guard and restoration of uniqueness.
    connection.execute(sa.text("LOCK TABLE movimientos_inventario IN ACCESS EXCLUSIVE MODE"))
    unsafe = connection.scalar(sa.text(
        "SELECT EXISTS (SELECT 1 FROM movimientos_inventario WHERE cantidad_afectada IS NOT NULL) "
        f"OR EXISTS (SELECT id_plancha FROM movimientos_inventario WHERE tipo_evento IN ({MANUAL}) "
        "AND id_plancha IS NOT NULL GROUP BY id_plancha HAVING count(*) > 1)"
    ))
    if unsafe:
        raise RuntimeError("Downgrade TA-036 bloqueado: perdería cantidades o bajas parciales históricas.")
    op.create_index("uq_movimientos_baja_manual_plancha", "movimientos_inventario", ["id_plancha"],
                    unique=True, postgresql_where=sa.text(f"tipo_evento IN ({MANUAL})"))
    op.drop_constraint("ck_movimientos_retazo_unitario", "movimientos_inventario", type_="check")
    op.drop_constraint("ck_movimientos_cantidad_positiva", "movimientos_inventario", type_="check")
    op.drop_column("movimientos_inventario", "cantidad_afectada")
