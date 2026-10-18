"""S1-RBAC: permisos configurables por rol (PERMISO y ROL_PERMISO).

Crea el catálogo de permisos y la tabla que asigna permisos a roles.
Los datos van literales a propósito: una migración es una foto fija y no debe
cambiar si mañana cambia app/core/permissions.py.

La asignación inicial se une a roles por nombre. En una base vacía los roles
aún no existen (los crea seed.py), así que no se asigna nada aquí y seed.py
completa la asignación después. En una base con roles (Supabase), la
asignación queda lista con el upgrade.
"""
from alembic import op
import sqlalchemy as sa

revision = "s1rbac01a2b3"
down_revision = "ta036a1b2c3d"
branch_labels = None
depends_on = None

PERMISOS = (
    ("users.view", "users", "Ver usuarios y roles disponibles"),
    ("users.manage", "users", "Crear, editar, activar y desactivar usuarios"),
    ("roles.view", "roles", "Ver roles y sus permisos"),
    ("roles.manage", "roles", "Cambiar los permisos de un rol"),
    ("inventory.view", "inventory", "Ver catálogo de vidrio, planchas, retazos e historial"),
    ("inventory.manage", "inventory", "Registrar, editar y dar de baja tipos, planchas y retazos"),
    ("orders.view", "orders", "Ver pedidos y clientes"),
    ("orders.create", "orders", "Registrar pedidos y clientes"),
    ("orders.update", "orders", "Editar pedidos pendientes"),
    ("orders.cancel", "orders", "Cancelar pedidos pendientes"),
    ("optimization.view", "optimization", "Ver resultados de optimización"),
    ("optimization.execute", "optimization", "Ejecutar la optimización y la rasterización"),
    ("optimization.confirm", "optimization", "Confirmar una solución (descuenta stock)"),
)

ASIGNACION_INICIAL = {
    "Administrador": [codigo for codigo, _, _ in PERMISOS],
    "Almacenero": ["inventory.view", "inventory.manage", "optimization.view"],
    "Operario": [
        "inventory.view",
        "orders.view", "orders.create", "orders.update", "orders.cancel",
        "optimization.view", "optimization.execute", "optimization.confirm",
    ],
}


def upgrade():
    permisos = op.create_table(
        "permisos",
        sa.Column("id_permiso", sa.Integer(), primary_key=True),
        sa.Column("codigo", sa.String(50), nullable=False),
        sa.Column("modulo", sa.String(30), nullable=False),
        sa.Column("descripcion", sa.String(150), nullable=False),
        sa.UniqueConstraint("codigo", name="permisos_codigo_key"),
        sa.CheckConstraint("codigo ~ '^[a-z]+\\.[a-z]+$'", name="ck_permisos_codigo_formato"),
        sa.CheckConstraint("codigo LIKE modulo || '.%'", name="ck_permisos_modulo_coincide"),
    )
    op.create_table(
        "rol_permisos",
        sa.Column("id_rol", sa.Integer(), nullable=False),
        sa.Column("id_permiso", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id_rol", "id_permiso", name="rol_permisos_pkey"),
        sa.ForeignKeyConstraint(["id_rol"], ["roles.id_rol"], ondelete="CASCADE",
                                name="fk_rol_permisos_rol"),
        sa.ForeignKeyConstraint(["id_permiso"], ["permisos.id_permiso"], ondelete="CASCADE",
                                name="fk_rol_permisos_permiso"),
    )

    op.bulk_insert(permisos, [
        {"codigo": codigo, "modulo": modulo, "descripcion": descripcion}
        for codigo, modulo, descripcion in PERMISOS
    ])

    # Une por nombre de rol y código de permiso: si un rol no existe, no se inserta nada para él.
    pares = [(rol, codigo) for rol, codigos in ASIGNACION_INICIAL.items() for codigo in codigos]
    valores = ", ".join(f"(:rol{i}, :codigo{i})" for i in range(len(pares)))
    parametros = {}
    for i, (rol, codigo) in enumerate(pares):
        parametros[f"rol{i}"] = rol
        parametros[f"codigo{i}"] = codigo
    op.get_bind().execute(sa.text(
        "INSERT INTO rol_permisos (id_rol, id_permiso) "
        "SELECT r.id_rol, p.id_permiso "
        f"FROM (VALUES {valores}) AS asignacion(nombre_rol, codigo) "
        "JOIN roles r ON r.nombre = asignacion.nombre_rol "
        "JOIN permisos p ON p.codigo = asignacion.codigo"
    ), parametros)


def downgrade():
    op.drop_table("rol_permisos")
    op.drop_table("permisos")