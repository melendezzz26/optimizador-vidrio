"""R3: migración y trazabilidad en PostgreSQL temporal, sin Supabase."""

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
import pytest
import sqlalchemy as sa

from tests.model_contracts import current_metadata
from .postgres_support import new_database, schema_snapshot, upgrade

R2 = "f2b3c4d5e6a7"
R3 = "a3c4d5e6f7b8"


def insert_context(connection):
    """Datos sintéticos compatibles con R2 y R3; no crea ejecuciones."""
    statements = [
        "INSERT INTO roles(id_rol,nombre) VALUES (1,'Operario')",
        "INSERT INTO usuarios(id_usuario,dni,nombres,apellidos,usuario,password_hash,id_rol,fecha_creacion) VALUES (1,'00000001','Prueba','Sintetica','p00000001','hash-sintetico',1,CURRENT_TIMESTAMP)",
        "INSERT INTO tipos_vidrio(id_tipo_vidrio,nombre) VALUES (1,'Sintetico')",
        "INSERT INTO planchas(id_plancha,ancho_mm,alto_mm,espesor_mm,cantidad,id_tipo_vidrio,fecha_registro) VALUES (1,100,200,3,10,1,CURRENT_TIMESTAMP)",
        "INSERT INTO retazos(id_retazo,codigo,espesor_mm,geometria,area_mm2,id_tipo_vidrio,fecha_registro) VALUES (1,'R-SINTETICO',3,'{}',100,1,CURRENT_TIMESTAMP)",
        "INSERT INTO pedidos(id_pedido,fecha_registro,estado,espesor_mm,id_tipo_vidrio,id_usuario_registro) VALUES (1,CURRENT_TIMESTAMP,'PENDIENTE',3,1,1)",
        "INSERT INTO configuraciones(id_configuracion,version,separacion_mm,margen_mm,resolucion_raster_mm,ancho_min_retazo_mm,alto_min_retazo_mm,id_usuario_creacion,fecha_creacion) VALUES (1,1,0,0,0.5,0,0,1,CURRENT_TIMESTAMP)",
    ]
    for statement in statements:
        connection.exec_driver_sql(statement)


@pytest.fixture
def previous_db(isolated_postgres):
    with new_database(isolated_postgres) as engine:
        result = upgrade(engine, R2)
        assert result.returncode == 0, result.stderr
        with engine.begin() as connection:
            insert_context(connection)
        yield engine


@pytest.fixture(scope="module")
def r3_db(isolated_postgres):
    with new_database(isolated_postgres) as engine:
        result = upgrade(engine, "head")
        assert result.returncode == 0, result.stderr
        yield engine


def test_clean_chain_matches_r3_orm_and_expected_counts(r3_db):
    with r3_db.connect() as connection:
        assert connection.scalar(sa.text("SELECT version_num FROM alembic_version")) == R3
        context = MigrationContext.configure(connection, opts={"compare_type": True, "compare_server_default": True})
        assert compare_metadata(context, current_metadata()) == []
        assert connection.scalar(sa.text("""SELECT count(*) FROM pg_trigger t
            JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname='public' AND NOT t.tgisinternal""")) == 0
    inspector = sa.inspect(r3_db)
    tables = set(inspector.get_table_names()) - {"alembic_version"}
    assert len(tables) == 12
    assert sum(len(inspector.get_columns(t)) for t in tables) == 86
    for table, size, checks in (("optimizaciones", 9, 1), ("ejecuciones_optimizacion", 8, 2), ("materiales_utilizados", 5, 2), ("retazos", 9, 2)):
        assert len(inspector.get_columns(table)) == size
        assert len(inspector.get_check_constraints(table)) == checks


def protected_oids(connection):
    return connection.execute(sa.text("""SELECT 'table' AS kind, relname AS name, oid
        FROM pg_class WHERE oid IN ('ejecuciones_optimizacion'::regclass,'metricas_ejecucion'::regclass)
        UNION ALL SELECT 'constraint',conname,oid FROM pg_constraint
        WHERE (conrelid='ejecuciones_optimizacion'::regclass AND contype='p')
           OR (conrelid='metricas_ejecucion'::regclass AND contype IN ('p','f','u'))
        ORDER BY kind,name""")).all()


def test_r2_to_r3_preserves_metrics_table_identity_other_tables_and_retazos(previous_db):
    tables = set(sa.inspect(previous_db).get_table_names()) - {"alembic_version", "ejecuciones_optimizacion", "retazos"}
    before = schema_snapshot(previous_db, tables)
    retazo_before = schema_snapshot(previous_db, ["retazos"])["retazos"]
    retazo_columns = [c["name"] for c in sa.inspect(previous_db).get_columns("retazos")]
    with previous_db.connect() as connection:
        identities = protected_oids(connection)
        retazo_rows = connection.exec_driver_sql("SELECT * FROM retazos ORDER BY id_retazo").all()
        data_before = {t: connection.exec_driver_sql(f'SELECT * FROM "{t}" ORDER BY 1').all() for t in tables}
    result = upgrade(previous_db, R3)
    assert result.returncode == 0, result.stderr
    assert schema_snapshot(previous_db, tables) == before
    retazo_after = schema_snapshot(previous_db, ["retazos"])["retazos"]
    retazo_after["columns"] = [c for c in retazo_after["columns"] if c[0] != "id_ejecucion_origen"]
    retazo_after["fk"] = [f for f in retazo_after["fk"] if f["constrained_columns"] != ["id_ejecucion_origen"]]
    assert retazo_after == retazo_before
    with previous_db.connect() as connection:
        assert protected_oids(connection) == identities
        assert connection.exec_driver_sql(f"SELECT {','.join(retazo_columns)} FROM retazos ORDER BY id_retazo").all() == retazo_rows
        assert connection.scalar(sa.text("SELECT id_ejecucion_origen FROM retazos WHERE id_retazo=1")) is None
        assert {t: connection.exec_driver_sql(f'SELECT * FROM "{t}" ORDER BY 1').all() for t in tables} == data_before
        assert connection.scalar(sa.text("SELECT version_num FROM alembic_version")) == R3


@pytest.mark.parametrize("scenario", ["execution", "execution-and-metric", "dependent-view"])
def test_r3_failure_preserves_r2_schema_data_and_revision(previous_db, scenario):
    with previous_db.begin() as connection:
        if scenario == "dependent-view":
            # El DROP de seleccionada falla tras crear OPTIMIZACION y otros DDL.
            connection.exec_driver_sql("CREATE VIEW seleccion_historica AS SELECT seleccionada FROM ejecuciones_optimizacion")
        else:
            connection.exec_driver_sql("""INSERT INTO ejecuciones_optimizacion
                (id_ejecucion,metodo,fecha_ejecucion,seleccionada,id_pedido,id_configuracion)
                VALUES (1,'HISTORICO','2000-01-01',true,1,1)""")
            if scenario == "execution-and-metric":
                connection.exec_driver_sql("INSERT INTO metricas_ejecucion(id_metrica,id_ejecucion) VALUES (1,1)")
    tables = sa.inspect(previous_db).get_table_names()
    before = schema_snapshot(previous_db, tables)
    with previous_db.connect() as connection:
        identities = protected_oids(connection)
        data = {t: connection.exec_driver_sql(f'SELECT * FROM "{t}" ORDER BY 1').all() for t in tables}
    result = upgrade(previous_db, R3)
    assert result.returncode != 0
    assert ("DependentObjectsStillExist" if scenario == "dependent-view" else "RuntimeError: R3 abortada") in result.stderr
    assert sa.inspect(previous_db).get_table_names() == tables
    assert schema_snapshot(previous_db, tables) == before
    with previous_db.connect() as connection:
        assert protected_oids(connection) == identities
        assert connection.scalar(sa.text("SELECT version_num FROM alembic_version")) == R2
        assert {t: connection.exec_driver_sql(f'SELECT * FROM "{t}" ORDER BY 1').all() for t in tables} == data


@pytest.fixture
def trace_rows(r3_db):
    with r3_db.connect() as connection:
        transaction = connection.begin()
        try:
            insert_context(connection)
            for optimization in (1, 2):
                connection.execute(sa.text("""INSERT INTO optimizaciones
                    (id_optimizacion,fecha_inicio,estado,id_pedido,id_configuracion,id_usuario_ejecutor,criterio_seleccion_version)
                    VALUES (:id,CURRENT_TIMESTAMP,'EN_EJECUCION',1,1,1,'LEX-V1')"""), {"id": optimization})
            connection.exec_driver_sql("""INSERT INTO ejecuciones_optimizacion
                (id_ejecucion,id_optimizacion,metodo,fecha_inicio,estado,completo)
                VALUES (1,1,'FF',CURRENT_TIMESTAMP,'COMPLETADA',true),
                       (2,2,'FF',CURRENT_TIMESTAMP,'COMPLETADA',true),
                       (3,1,'BF',CURRENT_TIMESTAMP,'FALLIDA',false),
                       (4,1,'WF',CURRENT_TIMESTAMP,'EN_EJECUCION',false)""")
            yield connection
        finally:
            transaction.rollback()


def test_both_cycle_fks_retazo_origin_and_metrics_fk_work(trace_rows):
    trace_rows.exec_driver_sql("UPDATE optimizaciones SET id_ejecucion_seleccionada=1 WHERE id_optimizacion=1")
    trace_rows.exec_driver_sql("UPDATE retazos SET id_ejecucion_origen=1 WHERE id_retazo=1")
    trace_rows.exec_driver_sql("INSERT INTO metricas_ejecucion(id_metrica,id_ejecucion) VALUES (1,1)")
    row = trace_rows.execute(sa.text("""SELECT o.id_ejecucion_seleccionada,e.id_optimizacion,r.id_ejecucion_origen,m.id_ejecucion
        FROM optimizaciones o JOIN ejecuciones_optimizacion e ON e.id_ejecucion=o.id_ejecucion_seleccionada
        JOIN retazos r ON r.id_ejecucion_origen=e.id_ejecucion JOIN metricas_ejecucion m ON m.id_ejecucion=e.id_ejecucion
        WHERE o.id_optimizacion=1""")).one()
    assert tuple(row) == (1, 1, 1, 1)
    assert trace_rows.scalar(sa.text("SELECT count(*) FROM ejecuciones_optimizacion WHERE id_optimizacion=1")) == 3


@pytest.mark.parametrize("sql", [
    "UPDATE optimizaciones SET estado='OTRO' WHERE id_optimizacion=1",
    "UPDATE optimizaciones SET id_pedido=999 WHERE id_optimizacion=1",
    "UPDATE optimizaciones SET id_configuracion=999 WHERE id_optimizacion=1",
    "UPDATE optimizaciones SET id_usuario_ejecutor=999 WHERE id_optimizacion=1",
    "UPDATE optimizaciones SET id_ejecucion_seleccionada=999 WHERE id_optimizacion=1",
    "UPDATE optimizaciones SET criterio_seleccion_version=NULL WHERE id_optimizacion=1",
    "UPDATE optimizaciones SET fecha_inicio=NULL WHERE id_optimizacion=1",
    "UPDATE ejecuciones_optimizacion SET metodo='OTRO' WHERE id_ejecucion=1",
    "UPDATE ejecuciones_optimizacion SET estado='SIN_SOLUCION' WHERE id_ejecucion=1",
    "UPDATE ejecuciones_optimizacion SET completo=NULL WHERE id_ejecucion=1",
    "UPDATE ejecuciones_optimizacion SET fecha_inicio=NULL WHERE id_ejecucion=1",
    "UPDATE ejecuciones_optimizacion SET id_optimizacion=999 WHERE id_ejecucion=1",
    "UPDATE ejecuciones_optimizacion SET id_optimizacion=1 WHERE id_ejecucion=2",
    "UPDATE retazos SET id_ejecucion_origen=999 WHERE id_retazo=1",
    "INSERT INTO metricas_ejecucion(id_metrica,id_ejecucion) VALUES (1,999)",
])
def test_traceability_rejects_invalid_data(trace_rows, sql):
    with pytest.raises(sa.exc.IntegrityError):
        trace_rows.exec_driver_sql(sql)


@pytest.mark.parametrize("state", ["EN_EJECUCION", "COMPLETADA", "SIN_SOLUCION", "FALLIDA"])
def test_optimization_accepts_exact_state_domain(trace_rows, state):
    trace_rows.execute(sa.text("UPDATE optimizaciones SET estado=:state WHERE id_optimizacion=1"), {"state": state})


@pytest.mark.parametrize("plancha,retazo,valid", [(1, None, True), (None, 1, True), (None, None, False), (1, 1, False)])
def test_material_source_xor(trace_rows, plancha, retazo, valid):
    statement = sa.text("INSERT INTO materiales_utilizados(id_material_utilizado,id_ejecucion,id_plancha,id_retazo) VALUES (1,1,:plancha,:retazo)")
    if valid:
        trace_rows.execute(statement, {"plancha": plancha, "retazo": retazo})
        assert trace_rows.scalar(sa.text("SELECT cantidad_utilizada FROM materiales_utilizados")) == 1
    else:
        with pytest.raises(sa.exc.IntegrityError):
            trace_rows.execute(statement, {"plancha": plancha, "retazo": retazo})


@pytest.mark.parametrize("execution,plancha,retazo,quantity", [
    (999, 1, None, 1), (1, 999, None, 1), (1, None, 999, 1),
    (1, 1, None, 0), (1, 1, None, -1), (1, 1, None, None), (None, 1, None, 1),
])
def test_material_rejects_invalid_fks_and_quantities(trace_rows, execution, plancha, retazo, quantity):
    with pytest.raises(sa.exc.IntegrityError):
        trace_rows.execute(sa.text("""INSERT INTO materiales_utilizados
            (id_material_utilizado,id_ejecucion,id_plancha,id_retazo,cantidad_utilizada)
            VALUES (1,:execution,:plancha,:retazo,:quantity)"""),
            {"execution": execution, "plancha": plancha, "retazo": retazo, "quantity": quantity})


def test_proposed_material_never_changes_inventory(trace_rows):
    before = {t: trace_rows.exec_driver_sql(f"SELECT * FROM {t} ORDER BY 1").all() for t in ("planchas", "retazos")}
    trace_rows.exec_driver_sql("""INSERT INTO materiales_utilizados
        (id_material_utilizado,id_ejecucion,id_plancha,id_retazo,cantidad_utilizada)
        VALUES (1,1,1,NULL,2),(2,1,NULL,1,1)""")
    assert {t: trace_rows.exec_driver_sql(f"SELECT * FROM {t} ORDER BY 1").all() for t in before} == before
