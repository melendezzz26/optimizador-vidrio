"""R2: alinear CONFIGURACION con snapshots del modelo v1.1.

Revision ID: f2b3c4d5e6a7
Revises: e1a2b3c4d5f6

Solo admite configuraciones vacía. No transforma datos históricos ni implementa
la lógica de creación de versiones o de inmutabilidad de la aplicación.
"""

from alembic import op
import sqlalchemy as sa

revision = "f2b3c4d5e6a7"
down_revision = "e1a2b3c4d5f6"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    if connection.dialect.name != "postgresql":
        raise RuntimeError("R2 requiere PostgreSQL y comprobar CONFIGURACION en línea.")
    # La transacción Alembic conserva este bloqueo hasta finalizar: evita que
    # una escritura invalide el preflight antes de los ALTER TABLE.
    connection.execute(sa.text("LOCK TABLE configuraciones IN ACCESS EXCLUSIVE MODE"))
    total = connection.execute(sa.text("SELECT COUNT(*) FROM configuraciones")).scalar_one()
    if total:
        raise RuntimeError(
            "R2 abortada: configuraciones debe estar vacía. No existe una política "
            "aprobada para transformar configuraciones heredadas; no se modificó el esquema."
        )

    for old, new in (
        ("resolucion_raster", "resolucion_raster_mm"),
        ("paso_angular", "paso_angular_grados"),
        ("fecha_actualizacion", "fecha_creacion"),
    ):
        op.alter_column("configuraciones", old, new_column_name=new)
    for column, precision, scale in (
        ("separacion_mm", 8, 2), ("margen_mm", 8, 2),
        ("resolucion_raster_mm", 8, 3), ("paso_angular_grados", 6, 2),
    ):
        op.alter_column(
            "configuraciones", column, existing_type=sa.Float(),
            type_=sa.Numeric(precision, scale),
            postgresql_using=f"{column}::numeric({precision},{scale})",
        )
    op.alter_column("configuraciones", "paso_angular_grados", nullable=True)
    # No hay fechas heredadas que interpretar ni zonas históricas que asumir.
    op.alter_column(
        "configuraciones", "fecha_creacion", existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
    )
    op.add_column("configuraciones", sa.Column("version", sa.Integer(), nullable=False))
    op.add_column("configuraciones", sa.Column("ancho_min_retazo_mm", sa.Numeric(10, 2), nullable=False))
    op.add_column("configuraciones", sa.Column("alto_min_retazo_mm", sa.Numeric(10, 2), nullable=False))
    op.add_column("configuraciones", sa.Column("vigente", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("configuraciones", sa.Column("id_usuario_creacion", sa.Integer(), nullable=False))
    op.create_unique_constraint("configuraciones_version_key", "configuraciones", ["version"])
    op.create_foreign_key(
        "configuraciones_id_usuario_creacion_fkey", "configuraciones", "usuarios",
        ["id_usuario_creacion"], ["id_usuario"],
    )
    for name, condition in (
        ("ck_configuraciones_version", "version > 0"),
        ("ck_configuraciones_separacion", "separacion_mm >= 0"),
        ("ck_configuraciones_margen", "margen_mm >= 0"),
        ("ck_configuraciones_resolucion", "resolucion_raster_mm > 0"),
        ("ck_configuraciones_paso_angular", "paso_angular_grados > 0 AND paso_angular_grados <= 360"),
        ("ck_configuraciones_ancho_retazo", "ancho_min_retazo_mm >= 0"),
        ("ck_configuraciones_alto_retazo", "alto_min_retazo_mm >= 0"),
    ):
        op.create_check_constraint(name, "configuraciones", condition)
    op.drop_column("configuraciones", "area_minima_retazo")
    op.drop_column("configuraciones", "dimension_minima_retazo")


def downgrade():
    raise RuntimeError(
        "R2 no admite reversión automática: no se pueden reconstruir de forma segura "
        "area_minima_retazo, dimension_minima_retazo ni la semántica histórica de los "
        "campos renombrados. Requiere un procedimiento de recuperación revisado."
    )
