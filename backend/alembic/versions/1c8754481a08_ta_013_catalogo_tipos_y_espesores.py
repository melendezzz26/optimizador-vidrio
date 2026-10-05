"""TA-013 catalogo tipos y espesores

Revision ID: 1c8754481a08
Revises: b4d5e6f7a8c9
Create Date: 2026-10-05 10:53:43.838895

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1c8754481a08"
down_revision: Union[str, Sequence[str], None] = "b4d5e6f7a8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _validate_existing_combinations(bind) -> None:
    """Abortar si existen registros incompatibles con el catálogo TA-013."""
    tables = (
        ("planchas", "id_plancha"),
        ("retazos", "id_retazo"),
        ("pedidos", "id_pedido"),
    )

    for table, pk in tables:
        invalid_rows = bind.execute(
            sa.text(
                f"""
                SELECT
                    src.{pk},
                    src.id_tipo_vidrio,
                    src.espesor_mm
                FROM {table} AS src
                LEFT JOIN tipos_vidrio_espesores AS tve
                    ON tve.id_tipo_vidrio = src.id_tipo_vidrio
                   AND tve.espesor_mm = src.espesor_mm
                WHERE tve.id_tipo_vidrio IS NULL
                LIMIT 5
                """
            )
        ).fetchall()

        if invalid_rows:
            sample = ", ".join(
                f"{pk}={row[0]}, tipo={row[1]}, espesor={row[2]}"
                for row in invalid_rows
            )
            raise RuntimeError(
                f"TA-013 no puede migrar '{table}': existen combinaciones "
                f"tipo-espesor fuera del catálogo SP-005. Ejemplos: {sample}"
            )


def _validate_old_domain_for_downgrade(bind) -> None:
    """Impedir un downgrade que deje datos incompatibles con v1.1."""
    tables = (
        ("planchas", "id_plancha"),
        ("retazos", "id_retazo"),
        ("pedidos", "id_pedido"),
    )

    for table, pk in tables:
        invalid_rows = bind.execute(
            sa.text(
                f"""
                SELECT {pk}, id_tipo_vidrio, espesor_mm
                FROM {table}
                WHERE espesor_mm NOT IN (3, 4, 5.5, 6, 8)
                LIMIT 5
                """
            )
        ).fetchall()

        if invalid_rows:
            sample = ", ".join(
                f"{pk}={row[0]}, tipo={row[1]}, espesor={row[2]}"
                for row in invalid_rows
            )
            raise RuntimeError(
                f"No se puede volver a v1.1 porque '{table}' contiene "
                f"espesores que v1.1 no admite. Ejemplos: {sample}"
            )


def _seed_catalog(bind) -> None:
    # 2. Asegurar los seis tipos definidos por SP-005.
    #
    # Si un tipo ya existe, preservar ID, descripción y estado (incluso NULL
    # en descripción o estado inactivo). El catálogo no reactiva datos del usuario.
    bind.execute(
        sa.text(
            """
            INSERT INTO tipos_vidrio (nombre, descripcion, estado)
            VALUES
                (
                    'Incoloro',
                    'Vidrio plano de uso general.',
                    TRUE
                ),
                (
                    'Bronce',
                    'Vidrio plano diferenciado por tonalidad bronce.',
                    TRUE
                ),
                (
                    'Gris',
                    'Vidrio plano diferenciado por tonalidad gris.',
                    TRUE
                ),
                (
                    'Catedral',
                    'Vidrio impreso o texturizado.',
                    TRUE
                ),
                (
                    'Reflejante',
                    'Vidrio con recubrimiento para control solar.',
                    TRUE
                ),
                (
                    'Espejo',
                    'Vidrio comercializado como espejo para corte.',
                    TRUE
                )
            ON CONFLICT (nombre)
            DO NOTHING
            """
        )
    )

    # 3. Cargar las combinaciones aprobadas por SP-005.
    bind.execute(
        sa.text(
            """
            WITH catalogo(nombre, espesor_mm) AS (
                VALUES
                    ('Incoloro', CAST(3 AS NUMERIC(4,1))),
                    ('Incoloro', CAST(4 AS NUMERIC(4,1))),
                    ('Incoloro', CAST(5.5 AS NUMERIC(4,1))),
                    ('Incoloro', CAST(6 AS NUMERIC(4,1))),
                    ('Incoloro', CAST(8 AS NUMERIC(4,1))),
                    ('Incoloro', CAST(10 AS NUMERIC(4,1))),
                    ('Incoloro', CAST(12 AS NUMERIC(4,1))),

                    ('Bronce', CAST(4 AS NUMERIC(4,1))),
                    ('Bronce', CAST(5.5 AS NUMERIC(4,1))),
                    ('Bronce', CAST(6 AS NUMERIC(4,1))),
                    ('Bronce', CAST(8 AS NUMERIC(4,1))),
                    ('Bronce', CAST(10 AS NUMERIC(4,1))),

                    ('Gris', CAST(4 AS NUMERIC(4,1))),
                    ('Gris', CAST(5.5 AS NUMERIC(4,1))),
                    ('Gris', CAST(6 AS NUMERIC(4,1))),
                    ('Gris', CAST(8 AS NUMERIC(4,1))),
                    ('Gris', CAST(10 AS NUMERIC(4,1))),

                    ('Catedral', CAST(3 AS NUMERIC(4,1))),
                    ('Catedral', CAST(3.5 AS NUMERIC(4,1))),
                    ('Catedral', CAST(5 AS NUMERIC(4,1))),

                    ('Reflejante', CAST(4 AS NUMERIC(4,1))),
                    ('Reflejante', CAST(5.5 AS NUMERIC(4,1))),
                    ('Reflejante', CAST(6 AS NUMERIC(4,1))),
                    ('Reflejante', CAST(8 AS NUMERIC(4,1))),

                    ('Espejo', CAST(2 AS NUMERIC(4,1))),
                    ('Espejo', CAST(3 AS NUMERIC(4,1))),
                    ('Espejo', CAST(4 AS NUMERIC(4,1))),
                    ('Espejo', CAST(6 AS NUMERIC(4,1)))
            )
            INSERT INTO tipos_vidrio_espesores (
                id_tipo_vidrio,
                espesor_mm
            )
            SELECT
                tv.id_tipo_vidrio,
                catalogo.espesor_mm
            FROM catalogo
            JOIN tipos_vidrio AS tv
                ON tv.nombre = catalogo.nombre
            ON CONFLICT (id_tipo_vidrio, espesor_mm)
            DO NOTHING
            """
        )
    )

    # 4. Comprobar que se cargaron las 28 combinaciones del SP-005.
    catalog_count = bind.execute(
        sa.text(
            """
            SELECT COUNT(*)
            FROM tipos_vidrio_espesores AS tve
            JOIN tipos_vidrio AS tv
                ON tv.id_tipo_vidrio = tve.id_tipo_vidrio
            WHERE tv.nombre IN (
                'Incoloro',
                'Bronce',
                'Gris',
                'Catedral',
                'Reflejante',
                'Espejo'
            )
            """
        )
    ).scalar_one()

    if catalog_count != 28:
        raise RuntimeError(
            "TA-013 esperaba cargar exactamente 28 combinaciones "
            f"tipo-espesor, pero encontró {catalog_count}."
        )


def upgrade() -> None:
    """Crear y aplicar el catálogo reutilizable tipo-espesor de TA-013."""
    bind = op.get_bind()

    # 1. Crear relación tipo de vidrio <-> espesor permitido.
    op.create_table(
        "tipos_vidrio_espesores",
        sa.Column("id_tipo_vidrio", sa.Integer(), nullable=False),
        sa.Column("espesor_mm", sa.Numeric(4, 1), nullable=False),
        sa.CheckConstraint(
            "espesor_mm > 0",
            name="ck_tipos_vidrio_espesores_espesor_positivo",
        ),
        sa.ForeignKeyConstraint(
            ["id_tipo_vidrio"],
            ["tipos_vidrio.id_tipo_vidrio"],
            name="fk_tipos_vidrio_espesores_tipo_vidrio",
        ),
        sa.PrimaryKeyConstraint(
            "id_tipo_vidrio",
            "espesor_mm",
            name="pk_tipos_vidrio_espesores",
        ),
    )

    _seed_catalog(bind)

    # 5. Antes de cambiar restricciones, comprobar datos históricos.
    _validate_existing_combinations(bind)

    # 6. Eliminar la validación global de espesores de v1.1.
    op.drop_constraint(
        "ck_planchas_espesor",
        "planchas",
        type_="check",
    )
    op.drop_constraint(
        "ck_retazos_espesor",
        "retazos",
        type_="check",
    )
    op.drop_constraint(
        "ck_pedidos_espesor",
        "pedidos",
        type_="check",
    )

    # 7. Proteger la combinación tipo-espesor desde PostgreSQL.
    op.create_foreign_key(
        "fk_planchas_tipo_espesor",
        "planchas",
        "tipos_vidrio_espesores",
        ["id_tipo_vidrio", "espesor_mm"],
        ["id_tipo_vidrio", "espesor_mm"],
    )

    op.create_foreign_key(
        "fk_retazos_tipo_espesor",
        "retazos",
        "tipos_vidrio_espesores",
        ["id_tipo_vidrio", "espesor_mm"],
        ["id_tipo_vidrio", "espesor_mm"],
    )

    op.create_foreign_key(
        "fk_pedidos_tipo_espesor",
        "pedidos",
        "tipos_vidrio_espesores",
        ["id_tipo_vidrio", "espesor_mm"],
        ["id_tipo_vidrio", "espesor_mm"],
    )


def downgrade() -> None:
    """Volver al dominio global de espesores definido en BD v1.1."""
    bind = op.get_bind()

    # Un downgrade no debe borrar datos creados con los nuevos espesores.
    _validate_old_domain_for_downgrade(bind)

    # 1. Retirar las FK compuestas.
    op.drop_constraint(
        "fk_pedidos_tipo_espesor",
        "pedidos",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_retazos_tipo_espesor",
        "retazos",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_planchas_tipo_espesor",
        "planchas",
        type_="foreignkey",
    )

    # 2. Restaurar las restricciones globales de v1.1.
    op.create_check_constraint(
        "ck_planchas_espesor",
        "planchas",
        "espesor_mm IN (3, 4, 5.5, 6, 8)",
    )

    op.create_check_constraint(
        "ck_retazos_espesor",
        "retazos",
        "espesor_mm IN (3, 4, 5.5, 6, 8)",
    )

    op.create_check_constraint(
        "ck_pedidos_espesor",
        "pedidos",
        "espesor_mm IN (3, 4, 5.5, 6, 8)",
    )

    # 3. Eliminar la relación introducida por TA-013.
    #
    # No se eliminan los seis tipos de tipos_vidrio porque algunos pudieron
    # existir antes de esta migración o estar referenciados por otros datos.
    op.drop_table("tipos_vidrio_espesores")
