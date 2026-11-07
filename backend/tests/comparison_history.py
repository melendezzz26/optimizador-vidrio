"""Read-only fingerprints of optimization history, independent of application startup."""
import sqlalchemy as sa


def revision(engine):
    with engine.connect() as connection:
        return connection.scalar(sa.text("SELECT version_num FROM alembic_version"))


def history_bytes(engine):
    tables = {"optimizaciones": "id_optimizacion", "ejecuciones_optimizacion": "id_ejecucion",
        "optimizacion_pedidos": "id_optimizacion,id_pedido", "metricas_ejecucion": "id_metrica",
        "materiales_utilizados": "id_material_utilizado"}
    # Fixed internal identifiers, never supplied by HTTP or a test fixture.
    with engine.connect() as connection:
        return {table: connection.exec_driver_sql(
            f"SELECT coalesce(jsonb_agg(to_jsonb(t) ORDER BY {key})::text, '[]') FROM {table} t"
        ).scalar_one() for table, key in tables.items()}
