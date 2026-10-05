"""R3: trazabilidad de optimizaciones, ejecuciones y material propuesto.

Revision ID: a3c4d5e6f7b8
Revises: f2b3c4d5e6a7

Requiere ejecuciones y métricas vacías. Conserva la tabla/PK de ejecuciones y
el contrato de métricas. No interpreta datos heredados ni modifica inventario.
"""

from alembic import op
import sqlalchemy as sa

revision = "a3c4d5e6f7b8"
down_revision = "f2b3c4d5e6a7"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    if connection.dialect.name != "postgresql":
        raise RuntimeError("R3 requiere PostgreSQL y comprobaciones de datos en línea.")
    connection.execute(sa.text(
        "LOCK TABLE ejecuciones_optimizacion, metricas_ejecucion IN ACCESS EXCLUSIVE MODE"
    ))
    executions = connection.execute(sa.text("SELECT COUNT(*) FROM ejecuciones_optimizacion")).scalar_one()
    metrics = connection.execute(sa.text("SELECT COUNT(*) FROM metricas_ejecucion")).scalar_one()
    if executions or metrics:
        raise RuntimeError(
            "R3 abortada: ejecuciones_optimizacion y metricas_ejecucion deben estar vacías. "
            "No se transforman datos heredados ni se ejecutó DDL."
        )

    # Primera mitad del ciclo: la selección existe como columna, aún sin FK.
    op.create_table(
        "optimizaciones",
        sa.Column("id_optimizacion", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("fecha_inicio", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fecha_fin", sa.DateTime(timezone=True), nullable=True),
        sa.Column("estado", sa.String(20), nullable=False),
        sa.Column("id_pedido", sa.Integer(), sa.ForeignKey("pedidos.id_pedido"), nullable=False),
        sa.Column("id_configuracion", sa.Integer(), sa.ForeignKey("configuraciones.id_configuracion"), nullable=False),
        sa.Column("id_usuario_ejecutor", sa.Integer(), sa.ForeignKey("usuarios.id_usuario"), nullable=False),
        sa.Column("criterio_seleccion_version", sa.String(20), nullable=False),
        sa.Column("id_ejecucion_seleccionada", sa.Integer(), nullable=True),
        sa.CheckConstraint(
            "estado IN ('EN_EJECUCION', 'COMPLETADA', 'SIN_SOLUCION', 'FALLIDA')",
            name="ck_optimizaciones_estado",
        ),
    )

    # ALTER conserva el objeto tabla, su PK y la FK entrante desde métricas.
    op.drop_constraint("ejecuciones_optimizacion_id_pedido_fkey", "ejecuciones_optimizacion", type_="foreignkey")
    op.drop_constraint("ejecuciones_optimizacion_id_configuracion_fkey", "ejecuciones_optimizacion", type_="foreignkey")
    for name in ("id_pedido", "id_configuracion", "tiempo_computacional", "seleccionada"):
        op.drop_column("ejecuciones_optimizacion", name)
    op.alter_column("ejecuciones_optimizacion", "fecha_ejecucion", new_column_name="fecha_inicio")
    # Ambas tablas están vacías: no se interpretan timestamps históricos.
    op.alter_column("ejecuciones_optimizacion", "fecha_inicio", existing_type=sa.DateTime(), type_=sa.DateTime(timezone=True))
    op.alter_column("ejecuciones_optimizacion", "metodo", existing_type=sa.String(30), type_=sa.String(10))
    op.add_column("ejecuciones_optimizacion", sa.Column("id_optimizacion", sa.Integer(), nullable=False))
    op.add_column("ejecuciones_optimizacion", sa.Column("fecha_fin", sa.DateTime(timezone=True), nullable=True))
    op.add_column("ejecuciones_optimizacion", sa.Column("estado", sa.String(20), nullable=False))
    op.add_column("ejecuciones_optimizacion", sa.Column("completo", sa.Boolean(), nullable=False))
    op.create_foreign_key(
        "ejecuciones_optimizacion_id_optimizacion_fkey", "ejecuciones_optimizacion", "optimizaciones",
        ["id_optimizacion"], ["id_optimizacion"],
    )
    op.create_check_constraint("ck_ejecuciones_metodo", "ejecuciones_optimizacion", "metodo IN ('FF', 'BF', 'WF')")
    op.create_check_constraint("ck_ejecuciones_estado", "ejecuciones_optimizacion", "estado IN ('EN_EJECUCION', 'COMPLETADA', 'FALLIDA')")
    op.create_unique_constraint("ejecuciones_optimizacion_metodo_key", "ejecuciones_optimizacion", ["id_optimizacion", "metodo"])
    # Cerrar el ciclo una vez alineada EJECUCION. Sin FK diferibles ni cascadas.
    op.create_foreign_key(
        "fk_optimizaciones_ejecucion_seleccionada", "optimizaciones", "ejecuciones_optimizacion",
        ["id_ejecucion_seleccionada"], ["id_ejecucion"],
    )

    op.add_column("retazos", sa.Column("id_ejecucion_origen", sa.Integer(), nullable=True))
    op.create_foreign_key("retazos_id_ejecucion_origen_fkey", "retazos", "ejecuciones_optimizacion", ["id_ejecucion_origen"], ["id_ejecucion"])
    op.create_table(
        "materiales_utilizados",
        sa.Column("id_material_utilizado", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("id_ejecucion", sa.Integer(), sa.ForeignKey("ejecuciones_optimizacion.id_ejecucion"), nullable=False),
        sa.Column("id_plancha", sa.Integer(), sa.ForeignKey("planchas.id_plancha"), nullable=True),
        sa.Column("id_retazo", sa.Integer(), sa.ForeignKey("retazos.id_retazo"), nullable=True),
        sa.Column("cantidad_utilizada", sa.Integer(), nullable=False, server_default="1"),
        sa.CheckConstraint("cantidad_utilizada > 0", name="ck_materiales_cantidad"),
        sa.CheckConstraint("(id_plancha IS NOT NULL) <> (id_retazo IS NOT NULL)", name="ck_materiales_fuente"),
    )
    op.create_index("ix_optimizaciones_pedido_fecha", "optimizaciones", ["id_pedido", "fecha_inicio"])
    op.create_index("ix_materiales_ejecucion", "materiales_utilizados", ["id_ejecucion"])


def downgrade():
    raise RuntimeError(
        "R3 no admite reversión automática: no se pueden reconstruir de forma segura "
        "las agrupaciones, selección, fechas y tiempos del esquema anterior. "
        "Requiere un procedimiento de recuperación revisado."
    )
