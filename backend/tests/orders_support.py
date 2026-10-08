"""Orders tests use canonical tables in an exclusively owned local database."""
import pytest
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

from tests.integration.postgres_support import new_database, upgrade


@pytest.fixture(scope="module")
def orders_database(isolated_postgres):
    with new_database(isolated_postgres) as engine:
        result = upgrade(engine, "head")
        assert result.returncode == 0, result.stderr
        yield engine


@pytest.fixture
def session_factory(orders_database):
    from app.models import Rol, TipoVidrio, TipoVidrioEspesor

    assert orders_database.url.host == "127.0.0.1"
    assert orders_database.url.username == "r1_test"
    with orders_database.begin() as connection:
        connection.exec_driver_sql("TRUNCATE roles, tipos_vidrio RESTART IDENTITY CASCADE")
    factory = sessionmaker(bind=orders_database, expire_on_commit=True)
    with factory() as session:
        session.add_all([Rol(id_rol=i, nombre=name) for i, name in
                         [(1, "Administrador"), (2, "Almacenero"), (3, "Operario")]])
        session.add(TipoVidrio(id_tipo_vidrio=7, nombre="Material de prueba", estado=True))
        session.flush()
        session.add_all([TipoVidrioEspesor(id_tipo_vidrio=7, espesor_mm=value) for value in (5.5, 6)])
        session.commit()
    return factory
