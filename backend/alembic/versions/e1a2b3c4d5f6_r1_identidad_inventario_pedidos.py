"""R1: alinear identidad, inventario y pedidos con el modelo v1.1.

Revision ID: e1a2b3c4d5f6
Revises: c4e8a1f2b3d5

Requiere respaldo externo antes de retirar correo. No aplicar sobre Supabase
como parte de la preparación de R1. Consultar docs/database/convergencia-v1-1.md.
"""

from alembic import op
import sqlalchemy as sa

revision = "e1a2b3c4d5f6"
down_revision = "c4e8a1f2b3d5"
branch_labels = None
depends_on = None


def _reject_if(connection, query, message):
    # Solo se consulta existencia; nunca se incluyen datos personales en errores.
    if connection.execute(sa.text(query)).scalar():
        raise RuntimeError(f"R1 abortada: {message}")


def _validate_numeric(connection, table, column, precision, scale, domain):
    # Los identificadores proceden exclusivamente de constantes de esta revisión.
    _reject_if(
        connection,
        f"SELECT EXISTS (SELECT 1 FROM {table} WHERE {column} IS NULL "
        f"OR {column}::text IN ('NaN', 'Infinity', '-Infinity'))",
        f"{table}.{column} contiene nulos o valores no finitos.",
    )
    _reject_if(
        connection,
        f"SELECT EXISTS (SELECT 1 FROM {table} WHERE NOT ({domain}) "
        f"OR abs({column}::numeric) >= power(10::numeric, {precision - scale}) "
        f"OR {column}::numeric <> round({column}::numeric, {scale}))",
        f"{table}.{column} incumple dominio, rango o escala NUMERIC({precision},{scale}).",
    )
    # El cast float -> numeric también puede perder dígitos significativos.
    _reject_if(
        connection,
        f"SELECT EXISTS (SELECT 1 FROM {table} WHERE "
        f"({column}::numeric({precision},{scale}))::double precision <> {column})",
        f"{table}.{column} perdería precisión al convertirse a NUMERIC.",
    )


def _preflight(connection):
    # Mantener las precondiciones hasta el commit: ninguna escritura concurrente
    # puede insertar datos entre la validación y el ALTER TABLE.
    connection.execute(sa.text(
        "LOCK TABLE roles, usuarios, tipos_vidrio, planchas, retazos, pedidos, piezas "
        "IN ACCESS EXCLUSIVE MODE"
    ))
    for table, column, length in (
        ("roles", "nombre", 30), ("roles", "descripcion", 150),
        ("usuarios", "dni", 8), ("usuarios", "usuario", 9),
        ("retazos", "codigo", 40), ("pedidos", "estado", 20),
        ("piezas", "tipo_forma", 30),
    ):
        _reject_if(
            connection,
            f"SELECT EXISTS (SELECT 1 FROM {table} WHERE char_length({column}) > {length})",
            f"{table}.{column} excede la longitud {length}; no se permite truncamiento.",
        )

    for column, pattern in (("dni", "^[0-9]{8}$"), ("usuario", "^[A-Za-z][0-9]{8}$")):
        _reject_if(
            connection,
            f"SELECT EXISTS (SELECT 1 FROM usuarios WHERE {column} IS NULL "
            f"OR {column} !~ '{pattern}')",
            f"usuarios.{column} incumple el patrón aprobado.",
        )
    _reject_if(
        connection,
        "SELECT EXISTS (SELECT 1 FROM tipos_vidrio GROUP BY nombre HAVING count(*) > 1)",
        "tipos_vidrio.nombre contiene duplicados; no se fusionan registros automáticamente.",
    )
    _reject_if(
        connection,
        "SELECT EXISTS (SELECT 1 FROM piezas WHERE geometria IS NULL OR area_mm2 IS NULL)",
        "piezas contiene geometria o area_mm2 NULL; no se fabrican valores.",
    )
    for table, condition in (
        ("planchas", "cantidad >= 0"),
        ("pedidos", "estado IN ('PENDIENTE', 'EN_OPTIMIZACION', 'OPTIMIZADO', 'CONFIRMADO', 'CANCELADO')"),
        ("piezas", "cantidad > 0 AND tipo_forma IN ('RECTANGULO', 'CIRCUNFERENCIA', 'POLIGONO_CONVEXO')"),
    ):
        _reject_if(
            connection, f"SELECT EXISTS (SELECT 1 FROM {table} WHERE NOT ({condition}))",
            f"{table} incumple el dominio v1.1.",
        )
    for table, column, precision, scale, domain in (
        ("planchas", "ancho_mm", 10, 2, "ancho_mm > 0"),
        ("planchas", "alto_mm", 10, 2, "alto_mm > 0"),
        ("planchas", "espesor_mm", 4, 1, "espesor_mm IN (3, 4, 5.5, 6, 8)"),
        ("retazos", "espesor_mm", 4, 1, "espesor_mm IN (3, 4, 5.5, 6, 8)"),
        ("retazos", "area_mm2", 18, 2, "area_mm2 > 0"),
        ("pedidos", "espesor_mm", 4, 1, "espesor_mm IN (3, 4, 5.5, 6, 8)"),
        ("piezas", "area_mm2", 18, 2, "area_mm2 > 0"),
    ):
        _validate_numeric(connection, table, column, precision, scale, domain)

    for table in ("planchas", "retazos", "pedidos"):
        _reject_if(
            connection, f"SELECT EXISTS (SELECT 1 FROM {table})",
            f"{table} debe estar vacía; falta una política aprobada para fechas históricas.",
        )


def upgrade():
    connection = op.get_bind()
    if connection.dialect.name != "postgresql":
        raise RuntimeError("R1 requiere PostgreSQL y validación de datos en línea.")
    _preflight(connection)

    op.alter_column("roles", "nombre", type_=sa.String(30), existing_type=sa.String(50))
    op.alter_column("roles", "descripcion", type_=sa.String(150), existing_type=sa.Text())

    op.alter_column("usuarios", "dni", type_=sa.CHAR(8), existing_type=sa.String(8))
    op.create_check_constraint("ck_usuarios_dni_formato", "usuarios", "dni ~ '^[0-9]{8}$'")
    op.create_check_constraint("ck_usuarios_usuario_formato", "usuarios", "usuario ~ '^[A-Za-z][0-9]{8}$'")
    op.add_column("usuarios", sa.Column("fecha_creacion", sa.DateTime(timezone=True), nullable=True))
    # Fecha técnica de incorporación para cuentas heredadas, no fecha histórica.
    connection.execute(sa.text("UPDATE usuarios SET fecha_creacion = statement_timestamp()"))
    op.alter_column("usuarios", "fecha_creacion", nullable=False)
    op.drop_constraint("usuarios_correo_key", "usuarios", type_="unique")
    op.drop_column("usuarios", "correo")

    op.create_unique_constraint("tipos_vidrio_nombre_key", "tipos_vidrio", ["nombre"])
    for table in ("usuarios", "tipos_vidrio", "planchas", "retazos"):
        op.alter_column(table, "estado", existing_type=sa.Boolean(), server_default=sa.true())

    op.drop_constraint("planchas_codigo_key", "planchas", type_="unique")
    op.drop_column("planchas", "codigo")
    op.alter_column("retazos", "codigo", type_=sa.String(40), existing_type=sa.String(50))
    for table in ("planchas", "retazos"):
        op.add_column(table, sa.Column("fecha_registro", sa.DateTime(timezone=True), nullable=False))
    for table, column, precision, scale in (
        ("planchas", "ancho_mm", 10, 2), ("planchas", "alto_mm", 10, 2),
        ("planchas", "espesor_mm", 4, 1), ("retazos", "espesor_mm", 4, 1),
        ("retazos", "area_mm2", 18, 2), ("pedidos", "espesor_mm", 4, 1),
        ("piezas", "area_mm2", 18, 2),
    ):
        op.alter_column(
            table, column, existing_type=sa.Float(), type_=sa.Numeric(precision, scale),
            postgresql_using=f"{column}::numeric({precision},{scale})",
        )

    # pedidos está vacía: no se interpreta la zona de ninguna fecha heredada.
    op.alter_column("pedidos", "fecha_registro", existing_type=sa.DateTime(), type_=sa.DateTime(timezone=True))
    op.alter_column("pedidos", "estado", existing_type=sa.String(30), type_=sa.String(20))
    op.alter_column("pedidos", "id_usuario", new_column_name="id_usuario_registro", existing_type=sa.Integer())
    op.alter_column("piezas", "tipo_forma", existing_type=sa.String(50), type_=sa.String(30))
    op.alter_column("piezas", "geometria", nullable=False)
    op.alter_column("piezas", "area_mm2", nullable=False)

    for table, name, condition in (
        ("planchas", "ck_planchas_ancho_positivo", "ancho_mm > 0"),
        ("planchas", "ck_planchas_alto_positivo", "alto_mm > 0"),
        ("planchas", "ck_planchas_espesor", "espesor_mm IN (3, 4, 5.5, 6, 8)"),
        ("planchas", "ck_planchas_cantidad", "cantidad >= 0"),
        ("retazos", "ck_retazos_espesor", "espesor_mm IN (3, 4, 5.5, 6, 8)"),
        ("retazos", "ck_retazos_area_positiva", "area_mm2 > 0"),
        ("pedidos", "ck_pedidos_espesor", "espesor_mm IN (3, 4, 5.5, 6, 8)"),
        ("pedidos", "ck_pedidos_estado", "estado IN ('PENDIENTE', 'EN_OPTIMIZACION', 'OPTIMIZADO', 'CONFIRMADO', 'CANCELADO')"),
        ("piezas", "ck_piezas_tipo_forma", "tipo_forma IN ('RECTANGULO', 'CIRCUNFERENCIA', 'POLIGONO_CONVEXO')"),
        ("piezas", "ck_piezas_cantidad", "cantidad > 0"),
        ("piezas", "ck_piezas_area_positiva", "area_mm2 > 0"),
    ):
        op.create_check_constraint(name, table, condition)
    for table in ("planchas", "retazos"):
        op.create_index(f"ix_{table}_stock_compatible", table, ["id_tipo_vidrio", "espesor_mm", "estado"])
    op.create_index("ix_pedidos_estado_fecha", "pedidos", ["estado", "fecha_registro"])


def downgrade():
    raise RuntimeError(
        "R1 no admite reversión automática: correo y codigo de plancha no pueden "
        "reconstruirse. Requiere un procedimiento revisado y el respaldo externo."
    )
