"""R2 en PostgreSQL temporal, exclusivamente con datos sintéticos."""

from decimal import Decimal

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
import pytest
import sqlalchemy as sa
from tests.model_contracts import historical_metadata

from .postgres_support import new_database, schema_snapshot, upgrade

R1 = "e1a2b3c4d5f6"
R2 = "f2b3c4d5e6a7"


@pytest.fixture
def previous_db(isolated_postgres):
    with new_database(isolated_postgres) as engine:
        result = upgrade(engine, R1)
        assert result.returncode == 0, result.stderr
        yield engine


@pytest.fixture(scope="module")
def r2_db(isolated_postgres):
    with new_database(isolated_postgres) as engine:
        result = upgrade(engine, R2)
        assert result.returncode == 0, result.stderr
        yield engine


def test_clean_chain_reaches_r2_and_matches_historical_contract(r2_db):
    with r2_db.connect() as connection:
        assert connection.scalar(sa.text("SELECT version_num FROM alembic_version")) == R2
        context = MigrationContext.configure(connection, opts={"compare_type": True, "compare_server_default": True})
        assert compare_metadata(context, historical_metadata(R2)) == []
    inspector = sa.inspect(r2_db)
    tables = set(inspector.get_table_names()) - {"alembic_version"}
    assert len(tables) == 10
    assert sum(len(inspector.get_columns(t)) for t in tables) == 71
    assert len(inspector.get_columns("configuraciones")) == 11
    assert len(inspector.get_check_constraints("configuraciones")) == 7
    assert [c["column_names"] for c in inspector.get_unique_constraints("configuraciones")] == [["version"]]
    assert [i["column_names"] for i in inspector.get_indexes("configuraciones")] == [["version"]]


def test_r1_to_r2_changes_only_empty_configuration(previous_db):
    inspector = sa.inspect(previous_db)
    other_tables = set(inspector.get_table_names()) - {"configuraciones", "alembic_version"}
    before = schema_snapshot(previous_db, other_tables)
    sequences = set(inspector.get_sequence_names())
    with previous_db.connect() as connection:
        assert connection.scalar(sa.text("SELECT count(*) FROM configuraciones")) == 0
    result = upgrade(previous_db, R2)
    assert result.returncode == 0, result.stderr
    assert schema_snapshot(previous_db, other_tables) == before
    assert set(sa.inspect(previous_db).get_sequence_names()) == sequences
    with previous_db.connect() as connection:
        assert connection.scalar(sa.text("SELECT count(*) FROM configuraciones")) == 0
        assert connection.scalar(sa.text("SELECT version_num FROM alembic_version")) == R2
        assert connection.scalar(sa.text("""SELECT count(*) FROM pg_trigger
            WHERE tgrelid='configuraciones'::regclass AND NOT tgisinternal""")) == 0


@pytest.mark.parametrize("dependency", [False, True], ids=["populated-table", "dependent-view"])
def test_r2_failure_preserves_schema_rows_and_revision(previous_db, dependency):
    with previous_db.begin() as connection:
        if dependency:
            # Falla al retirar el campo, después de otros DDL: demuestra atomicidad.
            connection.exec_driver_sql("CREATE VIEW configuracion_dependiente AS SELECT area_minima_retazo FROM configuraciones")
        else:
            connection.exec_driver_sql("""INSERT INTO configuraciones
                (separacion_mm,margen_mm,resolucion_raster,paso_angular,
                 area_minima_retazo,dimension_minima_retazo,fecha_actualizacion)
                VALUES (1,2,0.5,45,100,10,'2000-01-01 12:00:00')""")
    tables = sa.inspect(previous_db).get_table_names()
    before = schema_snapshot(previous_db, tables)
    with previous_db.connect() as connection:
        rows_before = {t: connection.exec_driver_sql(f'SELECT * FROM "{t}" ORDER BY 1').all() for t in tables}
    result = upgrade(previous_db, R2)
    assert result.returncode != 0
    expected_error = "DependentObjectsStillExist" if dependency else "RuntimeError: R2 abortada: configuraciones debe estar vacía"
    assert expected_error in result.stderr
    assert schema_snapshot(previous_db, tables) == before
    with previous_db.connect() as connection:
        assert connection.scalar(sa.text("SELECT version_num FROM alembic_version")) == R1
        assert {t: connection.exec_driver_sql(f'SELECT * FROM "{t}" ORDER BY 1').all() for t in tables} == rows_before


@pytest.fixture
def configuration_row(r2_db):
    with r2_db.connect() as connection:
        transaction = connection.begin()
        try:
            connection.exec_driver_sql("INSERT INTO roles(id_rol,nombre) VALUES (1,'Operario')")
            connection.exec_driver_sql("""INSERT INTO usuarios
                (id_usuario,dni,nombres,apellidos,usuario,password_hash,id_rol,fecha_creacion)
                VALUES (1,'00000001','Prueba','Sintetica','p00000001','hash-sintetico',1,CURRENT_TIMESTAMP)""")
            connection.exec_driver_sql("""INSERT INTO configuraciones
                (id_configuracion,version,separacion_mm,margen_mm,resolucion_raster_mm,
                 ancho_min_retazo_mm,alto_min_retazo_mm,id_usuario_creacion,fecha_creacion)
                VALUES (1,1,0,0,0.001,0,0,1,CURRENT_TIMESTAMP)""")
            yield connection
        finally:
            transaction.rollback()


@pytest.mark.parametrize("assignment", [
    "version=0", "version=-1", "version=NULL", "separacion_mm=-0.01", "separacion_mm=NULL",
    "margen_mm=-0.01", "margen_mm=NULL", "resolucion_raster_mm=0", "resolucion_raster_mm=NULL",
    "paso_angular_grados=0", "paso_angular_grados=360.01", "paso_angular_grados=-1",
    "ancho_min_retazo_mm=-0.01", "ancho_min_retazo_mm=NULL",
    "alto_min_retazo_mm=-0.01", "alto_min_retazo_mm=NULL", "vigente=NULL",
    "id_usuario_creacion=999", "id_usuario_creacion=NULL", "fecha_creacion=NULL",
])
def test_r2_database_rejects_invalid_configuration(configuration_row, assignment):
    with pytest.raises(sa.exc.IntegrityError):
        configuration_row.exec_driver_sql(f"UPDATE configuraciones SET {assignment}")


def test_r2_rejects_duplicate_version(configuration_row):
    with pytest.raises(sa.exc.IntegrityError):
        configuration_row.exec_driver_sql("""INSERT INTO configuraciones
            (id_configuracion,version,separacion_mm,margen_mm,resolucion_raster_mm,
             ancho_min_retazo_mm,alto_min_retazo_mm,id_usuario_creacion,fecha_creacion)
            SELECT 2,version,separacion_mm,margen_mm,resolucion_raster_mm,
             ancho_min_retazo_mm,alto_min_retazo_mm,id_usuario_creacion,fecha_creacion
            FROM configuraciones WHERE id_configuracion=1""")


def test_r2_nullable_angle_multiple_current_rows_and_exact_boundaries(configuration_row):
    row = configuration_row.execute(sa.text("SELECT paso_angular_grados,vigente,fecha_creacion FROM configuraciones")).one()
    assert row.paso_angular_grados is None and row.vigente is True
    assert row.fecha_creacion.tzinfo is not None
    configuration_row.exec_driver_sql("""INSERT INTO configuraciones
        (id_configuracion,version,separacion_mm,margen_mm,resolucion_raster_mm,paso_angular_grados,
         ancho_min_retazo_mm,alto_min_retazo_mm,id_usuario_creacion,fecha_creacion)
        VALUES (2,2,999999.99,999999.99,99999.999,360,99999999.99,99999999.99,1,CURRENT_TIMESTAMP)""")
    assert configuration_row.scalar(sa.text("SELECT count(*) FROM configuraciones WHERE vigente")) == 2
    row = configuration_row.execute(sa.text("SELECT separacion_mm,resolucion_raster_mm,paso_angular_grados,ancho_min_retazo_mm FROM configuraciones WHERE version=2")).one()
    assert tuple(row) == (Decimal("999999.99"), Decimal("99999.999"), Decimal("360.00"), Decimal("99999999.99"))


@pytest.mark.parametrize("assignment", [
    "separacion_mm=1000000", "margen_mm=1000000", "resolucion_raster_mm=100000",
    "ancho_min_retazo_mm=100000000", "alto_min_retazo_mm=100000000",
])
def test_r2_numeric_range_is_enforced(configuration_row, assignment):
    with pytest.raises(sa.exc.DataError):
        configuration_row.exec_driver_sql(f"UPDATE configuraciones SET {assignment}")
