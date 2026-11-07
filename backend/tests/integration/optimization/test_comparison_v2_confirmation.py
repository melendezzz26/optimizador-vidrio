"""B08: real isolated PostgreSQL selection, exclusive consumption and atomic retries."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal
from threading import Barrier

import pytest
from sqlalchemy import event, select

from app.models import Configuracion, EjecucionOptimizacion, MovimientoInventario, Pedido, Pieza, Plancha, Retazo
from app.modules.optimization.application.comparison_catalog import METHODS_V2
from app.modules.optimization.application.comparison_confirmation import ConfirmComparisonV2
from app.modules.optimization.application.errors import RunError
from .test_comparison_v2_persistence import setup_v2, create, save  # noqa: F401
from .test_runs import prepared  # noqa: F401


def inventory(factory):
    with factory() as s:
        return dict(sheets=[(p.id_plancha, p.cantidad, p.estado) for p in s.scalars(select(Plancha).order_by(Plancha.id_plancha))],
            movements=[(m.id_movimiento, m.id_optimizacion, m.cantidad_afectada) for m in s.scalars(select(MovimientoInventario))],
            remnants=[(r.id_retazo, r.id_ejecucion_origen) for r in s.scalars(select(Retazo))],
            orders=[(p.id_pedido, p.estado) for p in s.scalars(select(Pedido).order_by(Pedido.id_pedido))])


@pytest.fixture
def completed(setup_v2, session_factory):
    current = create(setup_v2)
    for method in METHODS_V2:
        current = save(setup_v2, current, method)
    with setup_v2[2]() as tx:
        current = tx.comparisons_v2.record_supervisor_stopped(current.comparison_id, datetime.now(timezone.utc), current.version)
        for identifier in current.problem.order_ids:
            tx.session.get(Pedido, identifier).estado = "OPTIMIZADO"
    return current


def choose(setup, current, method="M6-BS"):
    execution = next(e for e in current.executions if e.method == method)
    with setup[2]() as tx:
        return tx.comparisons_v2.select(current.comparison_id, execution.execution_id, current.version, setup[0])


def confirm(setup, current, key="b08-confirm-key"):
    return ConfirmComparisonV2(setup[2]).execute(current.comparison_id, current.selected_execution_id,
        current.version, key, setup[0])


@pytest.mark.parametrize("method", METHODS_V2)
def test_each_selected_engine_consumes_once_and_preserves_other_snapshots(setup_v2, session_factory, completed, method):
    before = inventory(session_factory)
    with session_factory() as s:
        snapshots = {e.id_ejecucion: e.patron_resultado for e in s.scalars(select(EjecucionOptimizacion))}
    selected = choose(setup_v2, completed, method)
    assert inventory(session_factory) == before
    receipt = confirm(setup_v2, selected)
    after = inventory(session_factory)
    assert after["sheets"] == [(5, 0, False)]
    assert len(after["movements"]) == 1 and after["movements"][0][2] == 2
    assert all(state == "CONFIRMADO" for _, state in after["orders"])
    assert confirm(setup_v2, selected) == receipt
    assert inventory(session_factory) == after
    with setup_v2[2]() as tx:
        loaded = tx.comparisons_v2.get_owned(selected.comparison_id, setup_v2[0])
        assert loaded.confirmation["method"] == method
        assert loaded.selected_execution_id == selected.selected_execution_id
        assert loaded.version == selected.version + 1
        assert [e.diagnostic for e in loaded.executions] == [e.diagnostic for e in selected.executions]
        for execution in loaded.executions:
            row = tx.session.get(EjecucionOptimizacion, execution.execution_id)
            assert row.patron_resultado["snapshot"]["snapshot_version"] == 3
            if execution.execution_id != selected.selected_execution_id:
                assert row.patron_resultado == snapshots[execution.execution_id]
    with pytest.raises(RunError, match="confirmada"):
        confirm(setup_v2, selected, "different-confirm-key")
    with pytest.raises(RunError):
        choose(setup_v2, loaded, "FF")


def test_selection_version_ownership_and_release(setup_v2, session_factory, completed):
    before = inventory(session_factory)
    selected = choose(setup_v2, completed, "HF")
    with pytest.raises(RunError) as failure:
        choose(setup_v2, completed, "BF")
    assert failure.value.code == "STATE_CONFLICT"
    selected = choose(setup_v2, selected, "M5")
    with pytest.raises(RunError), setup_v2[2]() as tx:
        tx.comparisons_v2.select(selected.comparison_id, selected.selected_execution_id, selected.version, setup_v2[0] + 1)
    with pytest.raises(RunError), setup_v2[2]() as tx:
        tx.comparisons_v2.select(selected.comparison_id, 2147483647, selected.version, setup_v2[0])
    assert inventory(session_factory) == before
    with setup_v2[2]() as tx:
        released = tx.comparisons_v2.release(selected.comparison_id, setup_v2[0], selected.version)
    assert released.released and released.selected_execution_id is None
    assert inventory(session_factory)["sheets"] == before["sheets"]


@pytest.mark.parametrize("stage", ["movimientos_inventario", "pedidos"])
def test_failure_rolls_back_every_write(setup_v2, session_factory, completed, stage):
    selected = choose(setup_v2, completed)
    before = inventory(session_factory)
    engine = session_factory.kw["bind"]
    def fail(conn, cursor, statement, parameters, context, executemany):
        if statement.lower().startswith(("insert into " + stage, "update " + stage)):
            raise RuntimeError("B08 induced write failure")
    event.listen(engine, "before_cursor_execute", fail)
    try:
        with pytest.raises(RuntimeError, match="induced"):
            confirm(setup_v2, selected)
    finally:
        event.remove(engine, "before_cursor_execute", fail)
    assert inventory(session_factory) == before
    with setup_v2[2]() as tx:
        assert tx.comparisons_v2.get(selected.comparison_id) == selected
    assert confirm(setup_v2, selected).optimization_id == selected.comparison_id


@pytest.mark.parametrize("same_key", [True, False])
def test_concurrent_confirmation_has_one_effect(setup_v2, session_factory, completed, same_key):
    selected = choose(setup_v2, completed)
    barrier = Barrier(2)
    def submit(index):
        barrier.wait(timeout=10)
        try:
            return confirm(setup_v2, selected, "b08-concurrent-key" if same_key else f"b08-concurrent-{index}")
        except RunError as error:
            return error.code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(submit, range(2)))
    if same_key:
        assert results[0] == results[1]
    else:
        assert sum(value == "ALREADY_CONFIRMED" for value in results) == 1
    after = inventory(session_factory)
    assert after["sheets"] == [(5, 0, False)] and len(after["movements"]) == 1


def test_changed_stock_rejects_without_partial_effect(setup_v2, session_factory, completed):
    selected = choose(setup_v2, completed)
    with session_factory() as s:
        s.get(Plancha, 5).cantidad = 1
        s.commit()
    before = inventory(session_factory)
    with pytest.raises(RunError) as failure:
        confirm(setup_v2, selected)
    assert failure.value.code == "STOCK_CONFLICT"
    assert inventory(session_factory) == before


def test_active_and_unselected_results_cannot_confirm(setup_v2, completed):
    with pytest.raises(RunError) as failure:
        ConfirmComparisonV2(setup_v2[2]).execute(completed.comparison_id, completed.executions[0].execution_id,
            completed.version, "b08-unselected-key", setup_v2[0])
    assert failure.value.code == "NOT_CONFIRMABLE"


def test_two_comparisons_compete_for_same_physical_stock(setup_v2, session_factory):
    with session_factory() as s:
        s.get(Plancha, 5).cantidad = 1
        s.commit()
    candidates = []
    for index, order in enumerate(setup_v2[1]):
        current = create(setup_v2, key=f'b08-stock-race-{index}', ids=[order])
        for method in METHODS_V2:
            current = save(setup_v2, current, method)
        with setup_v2[2]() as tx:
            current = tx.comparisons_v2.record_supervisor_stopped(current.comparison_id, datetime.now(timezone.utc), current.version)
            tx.session.get(Pedido, order).estado = 'OPTIMIZADO'
        candidates.append(choose(setup_v2, current))
    barrier = Barrier(2)
    def submit(current):
        barrier.wait(timeout=10)
        try:
            return confirm(setup_v2, current)
        except RunError as error:
            return error.code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(submit, candidates))
    assert sum(value == 'STOCK_CONFLICT' for value in results) == 1
    after = inventory(session_factory)
    assert after['sheets'] == [(5, 0, False)] and len(after['movements']) == 1
    assert sorted(state for _, state in after['orders']) == ['CONFIRMADO', 'OPTIMIZADO']


def test_partial_failed_and_uncertain_closure_are_not_selectable(setup_v2):
    current = create(setup_v2)
    for method in METHODS_V2:
        current = save(setup_v2, current, method, failed=method == 'HF', partial_result=method == 'M6-BS')
    with pytest.raises(RunError), setup_v2[2]() as tx:
        tx.comparisons_v2.select(current.comparison_id, current.executions[0].execution_id, current.version, setup_v2[0])
    with pytest.raises(RunError):
        ConfirmComparisonV2(setup_v2[2]).execute(current.comparison_id, current.executions[0].execution_id,
            current.version, 'b08-uncertain-key', setup_v2[0])
    with setup_v2[2]() as tx:
        current = tx.comparisons_v2.record_supervisor_stopped(current.comparison_id, datetime.now(timezone.utc), current.version)
    for method in ('HF', 'M6-BS'):
        with pytest.raises(RunError) as failure:
            choose(setup_v2, current, method)
        assert failure.value.code == 'NOT_CONFIRMABLE'


def test_distinct_alternative_sources_are_not_consumed(setup_v2, session_factory):
    with session_factory() as s:
        s.add(Plancha(id_plancha=6, ancho_mm=8, alto_mm=2, espesor_mm=6, cantidad=1, estado=True,
            fecha_registro=datetime.now(timezone.utc), id_tipo_vidrio=7))
        s.commit()
    current = create(setup_v2)
    for method in METHODS_V2:
        current = save(setup_v2, current, method)
    source_sets = {tuple((s.material_id, s.physical_unit_index) for s in e.result.materials_used) for e in current.executions}
    assert len(source_sets) >= 2
    with setup_v2[2]() as tx:
        current = tx.comparisons_v2.record_supervisor_stopped(current.comparison_id, datetime.now(timezone.utc), current.version)
        for identifier in current.problem.order_ids:
            tx.session.get(Pedido, identifier).estado = 'OPTIMIZADO'
    selected = choose(setup_v2, current, 'BF')
    confirm(setup_v2, selected)
    with session_factory() as s:
        assert s.get(Plancha, 5).cantidad == 0
        assert s.get(Plancha, 6).cantidad == 1
        assert all(m.id_plancha == 5 for m in s.scalars(select(MovimientoInventario)))


def test_selected_remnant_consumed_once_without_touching_sheets(setup_v2, session_factory):
    with session_factory() as s:
        remnant = Retazo(codigo='B08-OWNED-REMNANT', id_tipo_vidrio=7, espesor_mm=6,
            geometria={'type': 'RECTANGULO', 'width_mm': 8, 'height_mm': 2}, area_mm2=16,
            estado=True, fecha_registro=datetime.now(timezone.utc))
        s.add(remnant); s.commit(); identifier = remnant.id_retazo
    current = create(setup_v2)
    for method in METHODS_V2:
        current = save(setup_v2, current, method)
    with setup_v2[2]() as tx:
        current = tx.comparisons_v2.record_supervisor_stopped(current.comparison_id, datetime.now(timezone.utc), current.version)
        for order in current.problem.order_ids:
            tx.session.get(Pedido, order).estado = 'OPTIMIZADO'
    selected = choose(setup_v2, current, 'HF')
    receipt = confirm(setup_v2, selected)
    assert len(receipt.materials_consumed) == 1 and receipt.materials_consumed[0].material_id == identifier
    assert confirm(setup_v2, selected) == receipt
    with session_factory() as s:
        assert not s.get(Retazo, identifier).estado and s.get(Plancha, 5).cantidad == 2
        movements = s.scalars(select(MovimientoInventario)).all()
        assert len(movements) == 1 and movements[0].id_retazo == identifier and movements[0].cantidad_afectada == 1


def test_unpersistable_residual_matches_actual_inventory_after_confirmation(setup_v2, session_factory):
    identifier = setup_v2[1][0]
    with session_factory() as s:
        config = s.scalar(select(Configuracion))
        config.resolucion_raster_mm = Decimal('0.001')
        config.ancho_min_retazo_mm = config.alto_min_retazo_mm = 0
        piece = s.scalar(select(Pieza).where(Pieza.id_pedido == identifier))
        piece.cantidad, piece.area_mm2 = 1, Decimal('0.01')
        piece.geometria = {'type': 'RECTANGULO', 'width_mm': 0.1, 'height_mm': 0.1}
        piece.dimensiones = {'width_mm': 0.1, 'height_mm': 0.1}
        s.get(Plancha, 5).ancho_mm = Decimal('0.11')
        s.get(Plancha, 5).alto_mm = Decimal('0.10')
        s.commit()
    current = create(setup_v2, ids=[identifier])
    from app.modules.optimization.application.engine_execution import EngineExecutionAdapter, ExecutionScope
    execution = current.executions[0]
    for state in ('STARTING', 'RUNNING'):
        with setup_v2[2]() as tx:
            current = tx.comparisons_v2.set_dispatch_state(current.comparison_id, execution.execution_id, state, current.version)
    adapted = EngineExecutionAdapter('FF').execute(ExecutionScope(comparison_id=current.comparison_id,
        execution_id=execution.execution_id, method='FF'), current.problem,
        minimum_width_mm=Decimal(0), minimum_height_mm=Decimal(0))
    assert adapted.payload.result.metrics.recoverable_remnant_mm2 == Decimal('0.001')
    with setup_v2[2]() as tx:
        current = tx.comparisons_v2.save_execution(current.comparison_id, execution.execution_id,
            adapted.payload, adapted.residuals, current.version)
    for method in METHODS_V2[1:]:
        current = save(setup_v2, current, method, failed=True)
    with setup_v2[2]() as tx:
        current = tx.comparisons_v2.record_supervisor_stopped(current.comparison_id, datetime.now(timezone.utc), current.version)
        tx.session.get(Pedido, identifier).estado = 'OPTIMIZADO'
    selected = choose(setup_v2, current, 'FF')
    assert confirm(setup_v2, selected).remnants_created == ()
    with setup_v2[2]() as tx:
        result = tx.comparisons_v2.get(current.comparison_id).executions[0]
        assert result.result.metrics.recoverable_remnant_mm2 == 0
        assert result.residuals == ()


@pytest.mark.parametrize('phase', ['before_commit', 'after_commit'])
def test_connection_loss_boundary_recovers_durable_operation(setup_v2, session_factory, completed, phase):
    from functools import partial
    from app.modules.optimization.infrastructure.comparison_v2_uow import SqlComparisonPersistenceUnitOfWork
    selected = choose(setup_v2, completed)
    before = inventory(session_factory)
    class LostConnection(SqlComparisonPersistenceUnitOfWork):
        def __exit__(self, exc_type, exc, traceback):
            if exc_type is not None:
                return super().__exit__(exc_type, exc, traceback)
            error = ConnectionError('B08 controlled acknowledgement loss')
            if phase == 'before_commit':
                super().__exit__(ConnectionError, error, None)
            else:
                super().__exit__(None, None, None)
            raise error
    with pytest.raises(ConnectionError, match='acknowledgement'):
        ConfirmComparisonV2(partial(LostConnection, session_factory)).execute(selected.comparison_id,
            selected.selected_execution_id, selected.version, 'b08-lost-connection', setup_v2[0])
    after_loss = inventory(session_factory)
    if phase == 'before_commit':
        assert after_loss == before
    else:
        assert len(after_loss['movements']) == 1
    receipt = confirm(setup_v2, selected, 'b08-lost-connection')
    final = inventory(session_factory)
    assert len(final['movements']) == 1
    if phase == 'after_commit':
        assert final == after_loss
    assert confirm(setup_v2, selected, 'b08-lost-connection') == receipt
    assert inventory(session_factory) == final
