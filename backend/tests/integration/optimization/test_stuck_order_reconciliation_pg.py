"""S2 F6: reconciliación de pedidos atascados sobre PostgreSQL real (casos A–E y dry-run).

Cada caso reproduce el estado que dejaron los caminos antiguos: A, la vista previa
HU-015 (14–21/10) que pasaba el pedido a EN_OPTIMIZACION sin optimización; B, una
corrida FF fallida antes de TA-049, que dejaba los pedidos retenidos.
"""
from datetime import datetime, timezone
from functools import partial

import pytest
from sqlalchemy import select

from app.models import EjecucionOptimizacion, MovimientoInventario, Optimizacion, Pedido
from app.modules.optimization.application.order_reconciliation import ReconcileStuckOrders
from app.modules.optimization.application.runs import AcceptRun
from app.modules.optimization.infrastructure.order_reconciliation_repository import SqlStuckOrdersUnitOfWork
from tests.integration.optimization.test_runs import prepared  # noqa: F401
from tests.integration.optimization.test_worst_fit_slice import database_snapshot


def set_order(factory, order_id, state):
    with factory() as db:
        db.get(Pedido, order_id).estado = state
        db.commit()


def set_optimization(factory, optimization_id, state):
    with factory() as db:
        db.get(Optimizacion, optimization_id).estado = state
        for execution in db.scalars(select(EjecucionOptimizacion).where(
                EjecucionOptimizacion.id_optimizacion == optimization_id)):
            execution.estado = "FALLIDA" if state == "FALLIDA" else "COMPLETADA"
        db.commit()


def order_state(factory, order_id):
    with factory() as db:
        return db.get(Pedido, order_id).estado


def arrange(case, factory, actor, order_id, uow):
    """Deja order_id en EN_OPTIMIZACION con la situación del caso; devuelve la optimización o None."""
    if case == "A":
        set_order(factory, order_id, "EN_OPTIMIZACION")
        return None
    optimization_id = AcceptRun(uow).execute([order_id], actor).optimization_id   # EN_EJECUCION
    if case in ("B", "E"):
        set_optimization(factory, optimization_id, "FALLIDA")
    if case == "D":
        set_optimization(factory, optimization_id, "COMPLETADA")
    if case == "E":
        with factory() as db:
            db.add(MovimientoInventario(id_plancha=5, tipo_evento="CONSUMO_OPTIMIZACION", motivo="Consumo de prueba",
                                        id_usuario=actor, id_optimizacion=optimization_id, cantidad_afectada=1,
                                        fecha=datetime.now(timezone.utc)))
            db.commit()
    return optimization_id


@pytest.mark.parametrize("case, expected_after", [
    ("A", "PENDIENTE"), ("B", "PENDIENTE"),
    ("C", "EN_OPTIMIZACION"), ("D", "EN_OPTIMIZACION"), ("E", "EN_OPTIMIZACION"),
])
def test_apply_releases_only_cases_a_and_b(session_factory, prepared, case, expected_after):
    actor, ids, uow = prepared
    optimization_id = arrange(case, session_factory, actor, ids[0], uow)
    before = database_snapshot(session_factory)

    entries = ReconcileStuckOrders(partial(SqlStuckOrdersUnitOfWork, session_factory)).execute(apply=True)

    # Solo se consideran pedidos en EN_OPTIMIZACION: el otro pedido PENDIENTE no aparece.
    assert [(e.order_id, e.case.value, e.before, e.after) for e in entries] == [
        (ids[0], case, "EN_OPTIMIZACION", expected_after)]
    assert entries[0].applied is (case in ("A", "B"))
    assert [link.optimization_id for link in entries[0].optimizations] == (
        [] if optimization_id is None else [optimization_id])
    assert order_state(session_factory, ids[0]) == expected_after
    assert order_state(session_factory, ids[1]) == "PENDIENTE"
    after = database_snapshot(session_factory)
    if case in ("A", "B"):
        # Cambia únicamente el estado del pedido; optimizaciones, ejecuciones e inventario intactos.
        changed = {name for name in before if before[name] != after[name]}
        assert changed == {"pedidos"}
    else:
        assert after == before


def test_dry_run_reports_a_and_b_without_any_write(session_factory, prepared):
    actor, ids, uow = prepared
    arrange("A", session_factory, actor, ids[0], uow)
    arrange("B", session_factory, actor, ids[1], uow)
    before = database_snapshot(session_factory)

    entries = ReconcileStuckOrders(partial(SqlStuckOrdersUnitOfWork, session_factory)).execute()

    assert [(e.order_id, e.case.value, e.after, e.applied) for e in entries] == [
        (ids[0], "A", "PENDIENTE", False), (ids[1], "B", "PENDIENTE", False)]
    assert database_snapshot(session_factory) == before
