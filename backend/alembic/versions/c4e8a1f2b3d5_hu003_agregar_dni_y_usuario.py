"""HU-003: agregar dni y usuario a usuarios; correo pasa a opcional

Revision ID: c4e8a1f2b3d5
Revises: 9b9f04eb67f6
Create Date: 2026-09-29

Nota: en la base compartida, la columna `correo` había sido renombrada a
`usuario` directamente en Supabase (sin migración). Esta migración detecta
ese caso y lo devuelve al esquema registrado antes de aplicar los cambios.
"""
from alembic import op
import sqlalchemy as sa

revision = "c4e8a1f2b3d5"
down_revision = "9b9f04eb67f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conexion = op.get_bind()

    total = conexion.execute(sa.text("SELECT COUNT(*) FROM usuarios")).scalar()
    if total:
        raise RuntimeError(
            f"La tabla usuarios tiene {total} registro(s) sin DNI. "
            "Elimínalos o complétalos antes de aplicar esta migración."
        )

    columnas = {c["name"] for c in sa.inspect(conexion).get_columns("usuarios")}
    if "usuario" in columnas and "correo" not in columnas:
        # Corrige el cambio manual: `correo` fue renombrada a `usuario` fuera de Alembic.
        op.alter_column("usuarios", "usuario", new_column_name="correo")

    op.add_column("usuarios", sa.Column("dni", sa.String(length=8), nullable=False))
    op.add_column("usuarios", sa.Column("usuario", sa.String(length=9), nullable=False))
    op.create_unique_constraint("usuarios_dni_key", "usuarios", ["dni"])
    op.create_unique_constraint("usuarios_usuario_key", "usuarios", ["usuario"])
    op.alter_column("usuarios", "correo", existing_type=sa.String(length=150), nullable=True)


def downgrade() -> None:
    op.alter_column("usuarios", "correo", existing_type=sa.String(length=150), nullable=False)
    op.drop_constraint("usuarios_usuario_key", "usuarios", type_="unique")
    op.drop_constraint("usuarios_dni_key", "usuarios", type_="unique")
    op.drop_column("usuarios", "usuario")
    op.drop_column("usuarios", "dni")
