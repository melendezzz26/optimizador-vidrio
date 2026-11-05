"""TA-043/B02: widen the method CHECK; no historical data transformations."""
from alembic import op
import sqlalchemy as sa

revision = "s2cmp02d4e6f8"
down_revision = "s2cmp01a1b2c"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("ck_ejecuciones_metodo", "ejecuciones_optimizacion", type_="check")
    op.create_check_constraint("ck_ejecuciones_metodo", "ejecuciones_optimizacion",
                               "metodo IN ('FF', 'BF', 'WF', 'HF', 'M5', 'M6-BS')")


def downgrade():
    # Serialize the guard with writers. Locks are not DDL and do not delete data.
    op.execute("LOCK TABLE optimizaciones, ejecuciones_optimizacion IN ACCESS EXCLUSIVE MODE")
    incompatible = op.get_bind().scalar(sa.text("""
        SELECT EXISTS (
          SELECT 1 FROM optimizaciones
          WHERE criterio_seleccion_version = 'CMP-v2'
             OR comparison_snapshot->>'profile' = 'comparison-v2'
             OR (comparison_snapshot->>'comparison_snapshot_version' IS NOT NULL
                 AND comparison_snapshot->>'comparison_snapshot_version' <> '1')
          UNION ALL
          SELECT 1 FROM ejecuciones_optimizacion
          WHERE metodo NOT IN ('FF', 'BF', 'WF')
             OR patron_resultado->>'profile' = 'comparison-v2'
             OR (patron_resultado->'snapshot'->>'snapshot_version' IS NOT NULL
                 AND patron_resultado->'snapshot'->>'snapshot_version' NOT IN ('1', '2'))
             OR (patron_resultado->>'snapshot_version' IS NOT NULL
                 AND patron_resultado->>'snapshot_version' NOT IN ('1', '2'))
        )
    """))
    if incompatible:
        raise RuntimeError("Downgrade rechazado antes de DDL: existen datos comparison-v2 incompatibles.")
    op.drop_constraint("ck_ejecuciones_metodo", "ejecuciones_optimizacion", type_="check")
    op.create_check_constraint("ck_ejecuciones_metodo", "ejecuciones_optimizacion",
                               "metodo IN ('FF', 'BF', 'WF')")
