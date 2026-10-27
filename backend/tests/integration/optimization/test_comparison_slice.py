"""Real read adapters -> one captured input -> comparison, on isolated SQLite.

This slice makes no PostgreSQL locking/constraint claims and runs no migrations.
"""
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import event

from app.models import Plancha, Retazo
from app.modules.inventory.infrastructure.repository import SqlAlchemyInventoryRepository
from app.modules.optimization.application import comparison
from app.modules.optimization.application.comparison import ComparisonFailed, compare_methods
from app.modules.optimization.application.preparation import prepare_persisted_problem
from app.modules.optimization.application.stock import with_compatible_stock
from app.modules.optimization.domain.problem import OptimizationConfig
from app.modules.optimization.domain.worst_fit import WorstFitOptimizer
from app.modules.optimization.infrastructure.stock_adapter import InventoryStockAdapter
from app.modules.orders.infrastructure.repositories import SQLAlchemyOrderRepository
from tests.integration.optimization.test_worst_fit_slice import database_snapshot, sqlite_slice
from tests.unit.optimization.test_comparison import METHODS, direct, functional


def captured_input(factory):
    pieces = [dict(tipo_forma="RECTANGULO", cantidad=2, dimensiones={"width_mm": 2, "height_mm": 2},
                   geometria={"type": "RECTANGULO", "width_mm": 2, "height_mm": 2},
                   id_tipo_vidrio=glass, espesor_mm=6, area_mm2=4) for glass in (7, 8)]
    now = datetime.now(timezone.utc)
    with factory() as session:
        orders = SQLAlchemyOrderRepository(session)
        ids = [orders.create_order(1, pieces, id_cliente=41) for _ in range(2)]
        session.add_all([Plancha(id_plancha=identifier, id_tipo_vidrio=glass, ancho_mm=4, alto_mm=4,
                                espesor_mm=6, cantidad=2, estado=True, fecha_registro=now)
                         for identifier, glass in ((5, 7), (6, 8))])
        session.add(Retazo(id_retazo=9, codigo="TA021-TEST-9", id_tipo_vidrio=7, espesor_mm=6,
                           geometria={"type": "RECTANGULO", "width_mm": 3, "height_mm": 3},
                           area_mm2=9, estado=True, fecha_registro=now, id_ejecucion_origen=None))
        session.commit()
        snapshots = [p for identifier in ids for p in orders.get_order(identifier)["piezas"]]
    cfg = OptimizationConfig(resolution_mm=1, margin_mm=0, separation_mm=0, angular_step_deg=5)
    prepared = prepare_persisted_problem(ids[::-1], snapshots[::-1], cfg)
    provider = InventoryStockAdapter(SqlAlchemyInventoryRepository(factory))
    with patch.object(provider, "list_compatible", wraps=provider.list_compatible) as reads:
        prepared = with_compatible_stock(prepared, provider)
        assert reads.call_count == len(prepared.groups) == 2
    return prepared


@pytest.mark.parametrize("failure", [None, "optimization", "metrics"])
def test_comparison_uses_no_sql_and_leaves_every_table_unchanged_even_on_failure(sqlite_slice, monkeypatch, failure):
    factory = sqlite_slice
    prepared = captured_input(factory)
    before, input_before = database_snapshot(factory), repr(prepared)
    methods = METHODS
    original = RuntimeError("synthetic comparison failure")

    if failure == "optimization":
        class FailingWorstFit(WorstFitOptimizer):
            def optimize(self, value):
                super().optimize(value)  # Fails after doing real local work.
                raise original
        methods = (("FF", METHODS[0][1]), ("WF", FailingWorstFit))
    elif failure == "metrics":
        metrics = comparison.calculate_metrics
        def failing_metrics(result, *args):
            measured = metrics(result, *args)
            if result.method == "WF":
                raise original
            return measured
        monkeypatch.setattr(comparison, "calculate_metrics", failing_metrics)

    queries = []
    engine = factory.kw["bind"]
    def record_sql(*args):
        queries.append(args[2])
    event.listen(engine, "before_cursor_execute", record_sql)
    try:
        if failure:
            with pytest.raises(ComparisonFailed) as error:
                compare_methods(prepared, methods, minimum_width_mm=1, minimum_height_mm=1)
            assert error.value.method == "WF" and error.value.__cause__ is original
        else:
            entries = compare_methods(prepared, methods, minimum_width_mm=1, minimum_height_mm=1)
            assert functional(entries) == direct(prepared, methods)
            assert all(e.result.complete and e.result.total_units == 8 for e in entries)
        assert queries == []
    finally:
        event.remove(engine, "before_cursor_execute", record_sql)
    assert repr(prepared) == input_before
    assert database_snapshot(factory) == before
