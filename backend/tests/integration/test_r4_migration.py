"""R4: alineación final de métricas en PostgreSQL temporal, sin Supabase."""

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
import pytest
import sqlalchemy as sa

from tests.model_contracts import historical_metadata
from .postgres_support import new_database, schema_snapshot, upgrade


R3 = "a3c4d5e6f7b8"
R4 = "b4d5e6f7a8c9"


def insert_r3_context(connection, *, with_catalog=False):
    """Contexto sintético válido para crear una ejecución R3."""

    statements = [
        "INSERT INTO roles(id_rol,nombre) VALUES (1,'Operario')",

        """
        INSERT INTO usuarios(
            id_usuario,dni,nombres,apellidos,usuario,password_hash,
            id_rol,fecha_creacion
        )
        VALUES (
            1,'00000001','Prueba','Sintetica','p00000001',
            'hash-sintetico',1,CURRENT_TIMESTAMP
        )
        """,

        """
        INSERT INTO tipos_vidrio(id_tipo_vidrio,nombre)
        VALUES (1,'Sintetico')
        """,

        """
        INSERT INTO pedidos(
            id_pedido,fecha_registro,estado,espesor_mm,
            id_tipo_vidrio,id_usuario_registro
        )
        VALUES (
            1,CURRENT_TIMESTAMP,'PENDIENTE',3,1,1
        )
        """,

        """
        INSERT INTO configuraciones(
            id_configuracion,version,separacion_mm,margen_mm,
            resolucion_raster_mm,ancho_min_retazo_mm,
            alto_min_retazo_mm,id_usuario_creacion,fecha_creacion
        )
        VALUES (
            1,1,0,0,0.5,0,0,1,CURRENT_TIMESTAMP
        )
        """,

        """
        INSERT INTO optimizaciones(
            id_optimizacion,fecha_inicio,estado,id_pedido,
            id_configuracion,id_usuario_ejecutor,
            criterio_seleccion_version
        )
        VALUES (
            1,CURRENT_TIMESTAMP,'EN_EJECUCION',1,1,1,'LEX-V1'
        )
        """,

        """
        INSERT INTO ejecuciones_optimizacion(
            id_ejecucion,id_optimizacion,metodo,
            fecha_inicio,estado,completo
        )
        VALUES (
            1,1,'FF',CURRENT_TIMESTAMP,'COMPLETADA',TRUE
        )
        """,
    ]

    if with_catalog:
        statements.insert(3, "INSERT INTO tipos_vidrio_espesores VALUES (1,3),(1,4)")

    for statement in statements:
        connection.exec_driver_sql(statement)


@pytest.fixture
def previous_db(isolated_postgres):
    with new_database(isolated_postgres) as engine:
        result = upgrade(engine, R3)
        assert result.returncode == 0, result.stderr

        with engine.begin() as connection:
            insert_r3_context(connection)

        yield engine


@pytest.fixture(scope="module")
def r4_db(isolated_postgres):
    with new_database(isolated_postgres) as engine:
        result = upgrade(engine, R4)
        assert result.returncode == 0, result.stderr
        yield engine


@pytest.fixture
def metric_context(r4_db):
    with r4_db.connect() as connection:
        transaction = connection.begin()

        try:
            insert_r3_context(connection)
            yield connection
        finally:
            transaction.rollback()


def metric_constraints(connection):
    return connection.execute(
        sa.text(
            """
            SELECT conname, contype, pg_get_constraintdef(oid)
            FROM pg_constraint
            WHERE conrelid = 'metricas_ejecucion'::regclass
              AND contype IN ('p', 'f', 'u')
            ORDER BY conname
            """
        )
    ).all()


def test_clean_chain_matches_r4_orm_and_v11_counts(r4_db):
    with r4_db.connect() as connection:
        assert connection.scalar(
            sa.text("SELECT version_num FROM alembic_version")
        ) == R4

        context = MigrationContext.configure(
            connection,
            opts={
                "compare_type": True,
                "compare_server_default": True,
            },
        )

        assert compare_metadata(
            context,
            historical_metadata(R4),
        ) == []

    inspector = sa.inspect(r4_db)

    tables = set(inspector.get_table_names()) - {"alembic_version"}

    assert len(tables) == 12

    assert sum(
        len(inspector.get_columns(table))
        for table in tables
    ) == 90

    assert len(
        inspector.get_columns("metricas_ejecucion")
    ) == 11

    assert len(
        inspector.get_check_constraints("metricas_ejecucion")
    ) == 9


def test_r3_to_r4_preserves_other_tables_and_metric_relation(previous_db):
    inspector = sa.inspect(previous_db)

    tables = (
        set(inspector.get_table_names())
        - {"alembic_version", "metricas_ejecucion"}
    )

    before = schema_snapshot(previous_db, tables)

    with previous_db.connect() as connection:
        constraints_before = metric_constraints(connection)

    result = upgrade(previous_db, R4)

    assert result.returncode == 0, result.stderr

    assert schema_snapshot(previous_db, tables) == before

    with previous_db.connect() as connection:
        assert metric_constraints(connection) == constraints_before

        assert connection.scalar(
            sa.text("SELECT version_num FROM alembic_version")
        ) == R4


def test_r4_aborts_with_historical_metric_and_preserves_everything(previous_db):
    with previous_db.begin() as connection:
        connection.exec_driver_sql(
            """
            INSERT INTO metricas_ejecucion(
                id_metrica,
                aprovechamiento_pct,
                merma_mm2,
                planchas_utilizadas,
                area_recuperable_mm2,
                tiempo_computacional_ms,
                id_ejecucion
            )
            VALUES (
                1,75.5,100,1,50,125.5,1
            )
            """
        )

    tables = sa.inspect(previous_db).get_table_names()
    before = schema_snapshot(previous_db, tables)

    with previous_db.connect() as connection:
        data_before = {
            table: connection.exec_driver_sql(
                f'SELECT * FROM "{table}" ORDER BY 1'
            ).all()
            for table in tables
        }

    result = upgrade(previous_db, R4)

    assert result.returncode != 0
    assert "RuntimeError: R4 abortada" in result.stderr

    assert schema_snapshot(previous_db, tables) == before

    with previous_db.connect() as connection:
        assert connection.scalar(
            sa.text("SELECT version_num FROM alembic_version")
        ) == R3

        assert {
            table: connection.exec_driver_sql(
                f'SELECT * FROM "{table}" ORDER BY 1'
            ).all()
            for table in tables
        } == data_before


def test_r4_failure_after_first_ddl_rolls_back(previous_db):
    with previous_db.begin() as connection:
        connection.exec_driver_sql(
            """
            CREATE VIEW metrica_historica AS
            SELECT aprovechamiento_pct
            FROM metricas_ejecucion
            """
        )

    tables = sa.inspect(previous_db).get_table_names()
    before = schema_snapshot(previous_db, tables)

    result = upgrade(previous_db, R4)

    assert result.returncode != 0

    assert schema_snapshot(previous_db, tables) == before

    with previous_db.connect() as connection:
        assert connection.scalar(
            sa.text("SELECT version_num FROM alembic_version")
        ) == R3

        assert connection.scalar(
            sa.text(
                """
                SELECT COUNT(*)
                FROM information_schema.views
                WHERE table_schema = 'public'
                  AND table_name = 'metrica_historica'
                """
            )
        ) == 1


def insert_valid_metric(connection, metric_id=1, execution_id=1):
    connection.execute(
        sa.text(
            """
            INSERT INTO metricas_ejecucion(
                id_metrica,
                id_ejecucion,
                area_material_total_mm2,
                area_piezas_colocadas_mm2,
                aprovechamiento_pct,
                merma_mm2,
                retazo_recuperable_mm2,
                planchas_nuevas_usadas,
                tiempo_computacional_ms,
                memoria_pico_mb,
                tiempo_cpu_ms
            )
            VALUES (
                :metric_id,
                :execution_id,
                1000.00,
                750.00,
                75.000,
                250.00,
                100.00,
                1,
                1250,
                64.125,
                1000
            )
            """
        ),
        {
            "metric_id": metric_id,
            "execution_id": execution_id,
        },
    )


def test_r4_accepts_complete_valid_metric(metric_context):
    insert_valid_metric(metric_context)

    row = metric_context.execute(
        sa.text(
            """
            SELECT
                area_material_total_mm2,
                area_piezas_colocadas_mm2,
                aprovechamiento_pct,
                merma_mm2,
                retazo_recuperable_mm2,
                planchas_nuevas_usadas,
                tiempo_computacional_ms,
                memoria_pico_mb,
                tiempo_cpu_ms
            FROM metricas_ejecucion
            WHERE id_metrica = 1
            """
        )
    ).one()

    assert tuple(row) == (
        1000,
        750,
        75,
        250,
        100,
        1,
        1250,
        64.125,
        1000,
    )


def test_r4_accepts_nullable_resource_metrics(metric_context):
    metric_context.exec_driver_sql(
        """
        INSERT INTO metricas_ejecucion(
            id_metrica,
            id_ejecucion,
            area_material_total_mm2,
            area_piezas_colocadas_mm2,
            aprovechamiento_pct,
            merma_mm2,
            retazo_recuperable_mm2,
            planchas_nuevas_usadas,
            tiempo_computacional_ms,
            memoria_pico_mb,
            tiempo_cpu_ms
        )
        VALUES (
            1,1,1000,0,0,1000,0,0,0,NULL,NULL
        )
        """
    )

    row = metric_context.exec_driver_sql(
        """
        SELECT memoria_pico_mb, tiempo_cpu_ms
        FROM metricas_ejecucion
        WHERE id_metrica=1
        """
    ).one()

    assert tuple(row) == (None, None)


@pytest.mark.parametrize(
    "column,value",
    [
        ("area_material_total_mm2", 0),
        ("area_material_total_mm2", -1),
        ("area_piezas_colocadas_mm2", -1),
        ("aprovechamiento_pct", -0.001),
        ("aprovechamiento_pct", 100.001),
        ("merma_mm2", -1),
        ("retazo_recuperable_mm2", -1),
        ("planchas_nuevas_usadas", -1),
        ("tiempo_computacional_ms", -1),
        ("memoria_pico_mb", -0.001),
        ("tiempo_cpu_ms", -1),
    ],
)
def test_r4_rejects_values_outside_metric_domains(
    metric_context,
    column,
    value,
):
    insert_valid_metric(metric_context)

    with pytest.raises(sa.exc.IntegrityError):
        metric_context.execute(
            sa.text(
                f"""
                UPDATE metricas_ejecucion
                SET {column} = :value
                WHERE id_metrica = 1
                """
            ),
            {"value": value},
        )


@pytest.mark.parametrize(
    "column",
    [
        "id_ejecucion",
        "area_material_total_mm2",
        "area_piezas_colocadas_mm2",
        "aprovechamiento_pct",
        "merma_mm2",
        "retazo_recuperable_mm2",
        "planchas_nuevas_usadas",
        "tiempo_computacional_ms",
    ],
)
def test_r4_rejects_null_in_required_metric_columns(
    metric_context,
    column,
):
    insert_valid_metric(metric_context)

    with pytest.raises(sa.exc.IntegrityError):
        metric_context.exec_driver_sql(
            f"""
            UPDATE metricas_ejecucion
            SET {column}=NULL
            WHERE id_metrica=1
            """
        )


def test_r4_rejects_unknown_execution(metric_context):
    with pytest.raises(sa.exc.IntegrityError):
        metric_context.exec_driver_sql(
            """
            INSERT INTO metricas_ejecucion(
                id_metrica,
                id_ejecucion,
                area_material_total_mm2,
                area_piezas_colocadas_mm2,
                aprovechamiento_pct,
                merma_mm2,
                retazo_recuperable_mm2,
                planchas_nuevas_usadas,
                tiempo_computacional_ms
            )
            VALUES (
                1,999,1000,750,75,250,100,1,1250
            )
            """
        )


def test_r4_rejects_second_metric_for_same_execution(metric_context):
    insert_valid_metric(metric_context, metric_id=1)

    with pytest.raises(sa.exc.IntegrityError):
        insert_valid_metric(
            metric_context,
            metric_id=2,
            execution_id=1,
        )


def test_r4_does_not_add_derived_formula_constraints(metric_context):
    metric_context.exec_driver_sql(
        """
        INSERT INTO metricas_ejecucion(
            id_metrica,
            id_ejecucion,
            area_material_total_mm2,
            area_piezas_colocadas_mm2,
            aprovechamiento_pct,
            merma_mm2,
            retazo_recuperable_mm2,
            planchas_nuevas_usadas,
            tiempo_computacional_ms
        )
        VALUES (
            1,1,1000,500,80,100,50,0,0
        )
        """
    )

    assert metric_context.scalar(
        sa.text(
            """
            SELECT aprovechamiento_pct
            FROM metricas_ejecucion
            WHERE id_metrica=1
            """
        )
    ) == 80
