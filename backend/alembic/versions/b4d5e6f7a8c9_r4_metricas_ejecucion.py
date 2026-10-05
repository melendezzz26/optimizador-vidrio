"""R4: alinear métricas de ejecución con el modelo v1.1.

Revision ID: b4d5e6f7a8c9
Revises: a3c4d5e6f7b8

Requiere metricas_ejecucion vacía. No reinterpreta métricas históricas,
no rellena valores desconocidos y no modifica otras entidades.
"""

from alembic import op
import sqlalchemy as sa


revision = "b4d5e6f7a8c9"
down_revision = "a3c4d5e6f7b8"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()

    if connection.dialect.name != "postgresql":
        raise RuntimeError(
            "R4 requiere PostgreSQL y comprobaciones de datos en línea."
        )

    connection.execute(
        sa.text(
            "LOCK TABLE metricas_ejecucion "
            "IN ACCESS EXCLUSIVE MODE"
        )
    )

    metrics = connection.execute(
        sa.text("SELECT COUNT(*) FROM metricas_ejecucion")
    ).scalar_one()

    if metrics:
        raise RuntimeError(
            "R4 abortada: metricas_ejecucion debe estar vacía. "
            "No se reinterpretan métricas históricas ni se ejecutó DDL."
        )

    # Nuevas métricas que no existen en R3.
    op.add_column(
        "metricas_ejecucion",
        sa.Column(
            "area_material_total_mm2",
            sa.Numeric(18, 2),
            nullable=False,
        ),
    )

    op.add_column(
        "metricas_ejecucion",
        sa.Column(
            "area_piezas_colocadas_mm2",
            sa.Numeric(18, 2),
            nullable=False,
        ),
    )

    op.add_column(
        "metricas_ejecucion",
        sa.Column(
            "memoria_pico_mb",
            sa.Numeric(12, 3),
            nullable=True,
        ),
    )

    op.add_column(
        "metricas_ejecucion",
        sa.Column(
            "tiempo_cpu_ms",
            sa.BigInteger(),
            nullable=True,
        ),
    )

    # Los renombres son estructurales. La tabla vacía evita atribuir
    # semántica nueva a datos históricos.
    op.alter_column(
        "metricas_ejecucion",
        "planchas_utilizadas",
        existing_type=sa.Integer(),
        new_column_name="planchas_nuevas_usadas",
    )

    op.alter_column(
        "metricas_ejecucion",
        "area_recuperable_mm2",
        existing_type=sa.Float(),
        new_column_name="retazo_recuperable_mm2",
    )

    # Conversiones exactas del contrato final.
    op.alter_column(
        "metricas_ejecucion",
        "aprovechamiento_pct",
        existing_type=sa.Float(),
        type_=sa.Numeric(6, 3),
        nullable=False,
        postgresql_using="aprovechamiento_pct::numeric(6,3)",
    )

    op.alter_column(
        "metricas_ejecucion",
        "merma_mm2",
        existing_type=sa.Float(),
        type_=sa.Numeric(18, 2),
        nullable=False,
        postgresql_using="merma_mm2::numeric(18,2)",
    )

    op.alter_column(
        "metricas_ejecucion",
        "retazo_recuperable_mm2",
        existing_type=sa.Float(),
        type_=sa.Numeric(18, 2),
        nullable=False,
        postgresql_using="retazo_recuperable_mm2::numeric(18,2)",
    )

    op.alter_column(
        "metricas_ejecucion",
        "planchas_nuevas_usadas",
        existing_type=sa.Integer(),
        nullable=False,
    )

    op.alter_column(
        "metricas_ejecucion",
        "tiempo_computacional_ms",
        existing_type=sa.Float(),
        type_=sa.BigInteger(),
        nullable=False,
        postgresql_using="tiempo_computacional_ms::bigint",
    )

    # Restricciones normativas.
    op.create_check_constraint(
        "ck_metricas_area_material_total",
        "metricas_ejecucion",
        "area_material_total_mm2 > 0",
    )

    op.create_check_constraint(
        "ck_metricas_area_piezas_colocadas",
        "metricas_ejecucion",
        "area_piezas_colocadas_mm2 >= 0",
    )

    op.create_check_constraint(
        "ck_metricas_aprovechamiento",
        "metricas_ejecucion",
        "aprovechamiento_pct >= 0 AND aprovechamiento_pct <= 100",
    )

    op.create_check_constraint(
        "ck_metricas_merma",
        "metricas_ejecucion",
        "merma_mm2 >= 0",
    )

    op.create_check_constraint(
        "ck_metricas_retazo_recuperable",
        "metricas_ejecucion",
        "retazo_recuperable_mm2 >= 0",
    )

    op.create_check_constraint(
        "ck_metricas_planchas_nuevas",
        "metricas_ejecucion",
        "planchas_nuevas_usadas >= 0",
    )

    op.create_check_constraint(
        "ck_metricas_tiempo_computacional",
        "metricas_ejecucion",
        "tiempo_computacional_ms >= 0",
    )

    op.create_check_constraint(
        "ck_metricas_memoria_pico",
        "metricas_ejecucion",
        "memoria_pico_mb >= 0",
    )

    op.create_check_constraint(
        "ck_metricas_tiempo_cpu",
        "metricas_ejecucion",
        "tiempo_cpu_ms >= 0",
    )


def downgrade():
    raise RuntimeError(
        "R4 no admite reversión automática: el esquema anterior no puede "
        "reconstruirse sin descartar las métricas añadidas o reinterpretar "
        "su semántica. Requiere un procedimiento de recuperación revisado."
    )