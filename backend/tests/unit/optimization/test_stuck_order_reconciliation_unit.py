"""S2 F6: clasificación de pedidos atascados y orquestación del caso de uso, sin base de datos."""
import io
import json

import pytest

from app.modules.optimization.application.errors import RunError
from app.modules.optimization.application.order_reconciliation import (
    LinkedOptimization as L, ReconcileStuckOrders, StuckCase, classify,
)
from scripts.reconcile_stuck_orders import main


@pytest.mark.parametrize("links, expected", [
    ((), StuckCase.NO_OPTIMIZATION),
    ((L(1, "FALLIDA"), L(2, "SIN_SOLUCION")), StuckCase.ALL_TERMINAL),
    ((L(1, "COMPLETADA", released=True), L(2, "FALLIDA")), StuckCase.ALL_TERMINAL),
    ((L(1, "FALLIDA"), L(2, "EN_EJECUCION")), StuckCase.OPEN_OPTIMIZATION),
    ((L(1, "COMPLETADA"),), StuckCase.ELIGIBLE_RESULT),
    ((L(1, "FALLIDA", consumed=True),), StuckCase.CONSUMED),
    ((L(1, "COMPLETADA", released=True, confirmed=True),), StuckCase.CONSUMED),
    # Prioridad: consumo antes que corrida abierta; corrida abierta antes que resultado vigente.
    ((L(1, "EN_EJECUCION"), L(2, "FALLIDA", consumed=True)), StuckCase.CONSUMED),
    ((L(1, "COMPLETADA"), L(2, "EN_EJECUCION")), StuckCase.OPEN_OPTIMIZATION),
], ids=["A", "B", "B-released", "C", "D", "E-consumed", "E-confirmed", "E-over-C", "C-over-D"])
def test_classify(links, expected):
    assert classify(links) is expected


class FakeStore:
    def __init__(self, orders, links):
        self.orders, self.links, self.locks, self.writes = dict(orders), dict(links), [], []


class FakeUnitOfWork:
    def __init__(self, store):
        self.store = store
        self.stuck_orders = self
        self.orders = self

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def stuck_order_ids(self, order_ids=None):
        return tuple(i for i, state in sorted(self.store.orders.items())
                     if state == "EN_OPTIMIZACION" and (not order_ids or i in order_ids))

    def order_state(self, order_id, *, lock):
        if lock:
            self.store.locks.append(order_id)
        return self.store.orders[order_id]

    def linked_optimizations(self, order_id):
        return self.store.links.get(order_id, ())

    def transition(self, ids, expected, target):
        if any(self.store.orders[i] != expected for i in ids):
            raise RunError("STATE_CONFLICT", "El estado del lote ha cambiado.")
        for i in ids:
            self.store.orders[i] = target
            self.store.writes.append((i, expected, target))


def store():
    return FakeStore(
        {1: "EN_OPTIMIZACION", 2: "EN_OPTIMIZACION", 3: "EN_OPTIMIZACION", 4: "EN_OPTIMIZACION",
         5: "EN_OPTIMIZACION", 6: "PENDIENTE"},
        {2: (L(20, "FALLIDA"),), 3: (L(30, "EN_EJECUCION"),), 4: (L(40, "COMPLETADA"),),
         5: (L(50, "FALLIDA", consumed=True),)})


def test_dry_run_reports_without_writes_or_locks():
    data = store()
    entries = ReconcileStuckOrders(lambda: FakeUnitOfWork(data)).execute()
    assert [(e.order_id, e.case.value, e.after, e.applied) for e in entries] == [
        (1, "A", "PENDIENTE", False), (2, "B", "PENDIENTE", False), (3, "C", "EN_OPTIMIZACION", False),
        (4, "D", "EN_OPTIMIZACION", False), (5, "E", "EN_OPTIMIZACION", False)]
    assert data.writes == [] and data.locks == []


def test_apply_changes_only_a_and_b_and_logs_each_change(caplog):
    data = store()
    with caplog.at_level("INFO", logger="app.modules.optimization.application.order_reconciliation"):
        entries = ReconcileStuckOrders(lambda: FakeUnitOfWork(data)).execute(apply=True)
    assert data.writes == [(1, "EN_OPTIMIZACION", "PENDIENTE"), (2, "EN_OPTIMIZACION", "PENDIENTE")]
    assert [e.order_id for e in entries if e.applied] == [1, 2]
    assert data.orders == {1: "PENDIENTE", 2: "PENDIENTE", 3: "EN_OPTIMIZACION", 4: "EN_OPTIMIZACION",
                           5: "EN_OPTIMIZACION", 6: "PENDIENTE"}
    assert [r.getMessage() for r in caplog.records] == [
        "Pedido 1 reconciliado: EN_OPTIMIZACION -> PENDIENTE (caso A, optimizaciones ninguna)",
        "Pedido 2 reconciliado: EN_OPTIMIZACION -> PENDIENTE (caso B, optimizaciones [20])"]


def test_order_filter_and_state_changed_since_listing():
    data = store()

    class Racing(FakeUnitOfWork):
        def order_state(self, order_id, *, lock):
            self.store.orders[order_id] = "PENDIENTE"  # otro proceso lo liberó entre la lista y el bloqueo
            return super().order_state(order_id, lock=lock)

    entries = ReconcileStuckOrders(lambda: Racing(data)).execute(apply=True, order_ids=[2])
    assert [(e.order_id, e.applied, e.before) for e in entries] == [(2, False, "PENDIENTE")]
    assert data.writes == []


def test_script_is_dry_run_by_default_and_prints_json_report():
    data, out = store(), io.StringIO()
    assert main(["--report", "-"], unit_of_work=lambda: FakeUnitOfWork(data), out=out) == 0
    text = out.getvalue()
    assert text.startswith("Modo: DRY-RUN (no escribe)")
    report = json.loads(text[text.index("{"):])
    assert report["mode"] == "dry-run"
    assert report["summary"] == {"stuck_orders": 5, "recoverable": 2, "changed": 0,
                                 "by_case": {"A": 1, "B": 1, "C": 1, "D": 1, "E": 1}}
    assert report["entries"][1]["optimizations"] == [
        {"optimization_id": 20, "status": "FALLIDA", "released": False, "confirmed": False, "consumed": False}]
    assert data.writes == []
