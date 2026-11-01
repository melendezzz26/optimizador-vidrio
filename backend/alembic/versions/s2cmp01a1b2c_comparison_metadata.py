"""Metadatos comparativos aditivos; sin reinterpretar corridas históricas.

Autor: Fabricio Melendez Quezada. Revisor asignado: Andro Quispe.
Revision ID: s2cmp01a1b2c
Revises: s1opt02b4c6d
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "s2cmp01a1b2c"
down_revision = "s1opt02b4c6d"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("optimizaciones", sa.Column("comparison_key", sa.String(64), nullable=True))
    op.add_column("optimizaciones", sa.Column("comparison_snapshot", JSONB(), nullable=True))
    op.add_column("optimizaciones", sa.Column("comparison_version", sa.Integer(), nullable=False, server_default="1"))
    op.create_unique_constraint("uq_optimizaciones_comparison_key", "optimizaciones",
                                ["id_usuario_ejecutor", "comparison_key"])
    op.create_check_constraint("ck_optimizaciones_comparison_version", "optimizaciones", "comparison_version > 0")
    op.create_check_constraint("ck_optimizaciones_comparison_metadata", "optimizaciones",
                               "(comparison_key IS NULL) = (comparison_snapshot IS NULL)")


def downgrade():
    if op.get_bind().scalar(sa.text("SELECT count(*) FROM optimizaciones WHERE comparison_snapshot IS NOT NULL")):
        raise RuntimeError("Downgrade perdería snapshots comparativos; operación rechazada.")
    op.drop_constraint("ck_optimizaciones_comparison_metadata", "optimizaciones", type_="check")
    op.drop_constraint("ck_optimizaciones_comparison_version", "optimizaciones", type_="check")
    op.drop_constraint("uq_optimizaciones_comparison_key", "optimizaciones", type_="unique")
    for name in ("comparison_version", "comparison_snapshot", "comparison_key"):
        op.drop_column("optimizaciones", name)
