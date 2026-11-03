"""Real SQL filtering on an isolated in-memory inventory, without PostgreSQL."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.models import Plancha, Retazo
from app.modules.inventory.infrastructure.repository import SqlAlchemyInventoryRepository
from app.modules.optimization.infrastructure.stock_adapter import InventoryStockAdapter
from app.modules.optimization.application.stock import with_compatible_stock
from app.modules.optimization.domain.first_fit import FirstFitOptimizer
from tests.unit.optimization.test_first_fit import problem


@pytest.fixture
def inventory():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE planchas (id_plancha INTEGER PRIMARY KEY, ancho_mm NUMERIC, alto_mm NUMERIC, espesor_mm NUMERIC, cantidad INTEGER, estado BOOLEAN, fecha_registro DATETIME, id_tipo_vidrio INTEGER)")
        connection.exec_driver_sql("CREATE TABLE retazos (id_retazo INTEGER PRIMARY KEY, codigo VARCHAR, espesor_mm NUMERIC, geometria JSON, area_mm2 NUMERIC, estado BOOLEAN, fecha_registro DATETIME, id_ejecucion_origen INTEGER, id_tipo_vidrio INTEGER)")
    factory = sessionmaker(engine)
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    with factory.begin() as session:
        for i, glass, thickness, active in [(1, 1, 6, True), (2, 2, 6, True),
                                              (3, 1, 8, True), (4, 2, 8, True),
                                              (5, 1, 6, False), (6, 1, 6, True)]:
            when = now + timedelta(days=i)
            session.add(Plancha(id_plancha=i, id_tipo_vidrio=glass, espesor_mm=thickness,
                                ancho_mm=10, alto_mm=8, cantidad=0 if i == 6 else 1,
                                estado=active, fecha_registro=when))
            session.add(Retazo(id_retazo=i, codigo=f"R{i}", id_tipo_vidrio=glass,
                               espesor_mm=thickness, geometria={"type": "RECTANGULO", "width_mm": 10, "height_mm": 8},
                               area_mm2=80, estado=active, fecha_registro=when))
    yield engine, factory
    engine.dispose()


def test_queries_filter_at_database_and_preserve_order(inventory):
    engine, factory = inventory
    statements = []
    def capture(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)
    event.listen(engine, "before_cursor_execute", capture)
    repo = SqlAlchemyInventoryRepository(factory)
    with repo.read_transaction():
        remnants = repo.list_retazos_compatibles(1, Decimal(6))
        sheets = repo.list_planchas_compatibles(1, Decimal(6))
        assert [r.id_retazo for r in remnants] == [6, 1]
        assert [s.id_plancha for s in sheets] == [1]
        assert repo.list_retazos_compatibles(99, Decimal(6)) == []
        assert repo.list_planchas_compatibles(99, Decimal(6)) == []
    event.remove(engine, "before_cursor_execute", capture)
    assert len(statements) == 4
    assert all("WHERE" in s.upper() and "ESPESOR_MM" in s.upper() and "ID_TIPO_VIDRIO" in s.upper() for s in statements)


def test_adapter_matches_legacy_candidates_and_optimizer(inventory):
    _, factory = inventory
    repo = SqlAlchemyInventoryRepository(factory)
    adapter = InventoryStockAdapter(repo)
    class LegacyInventory:
        def read_transaction(self):
            return repo.read_transaction()
        def list_retazos_compatibles(self, glass, thickness):
            return [r for r in repo.list_retazos() if r.estado and (r.id_tipo_vidrio, r.espesor_mm) == (glass, thickness)]
        def list_planchas_compatibles(self, glass, thickness):
            return [s for s in repo.list_planchas() if s.estado and s.cantidad > 0 and (s.id_tipo_vidrio, s.espesor_mm) == (glass, thickness)]
    legacy = InventoryStockAdapter(LegacyInventory())
    key = (1, Decimal(6))
    actual = adapter.list_compatible(key)
    assert actual == adapter.list_compatible(key) == legacy.list_compatible(key)
    assert adapter.count_compatible(key) == legacy.count_compatible(key) == 3
    assert adapter.list_compatible((99, Decimal(6))) == ()
    p = problem()
    assert FirstFitOptimizer().optimize(with_compatible_stock(p, adapter)) == FirstFitOptimizer().optimize(with_compatible_stock(p, legacy))
