"""Confirmar solo el elegido, idempotencia, carreras y rollback en PostgreSQL.

Autor: Fabricio Melendez Quezada. Revisor asignado: Andro Quispe.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal
from threading import Barrier

import pytest
from sqlalchemy import event, func, select

from app.models import Configuracion, MovimientoInventario, Pedido, Pieza, Plancha, Retazo
from app.modules.optimization.application.comparisons import AcceptComparison
from app.modules.optimization.application.comparison_confirmation import ConfirmComparison
from app.modules.optimization.application.errors import RunError
from .test_comparison_persistence import comparison_setup, accept, save, finish, ENGINES  # noqa: F401
from .test_runs import prepared  # noqa: F401


@pytest.fixture
def completed(session_factory, comparison_setup):
    # FF llena 6; BF llena las dos unidades de 5; WF (SPEC-TA-019 v2) también llena 6.
    with session_factory() as s:
        s.add(Plancha(id_plancha=6, ancho_mm=8, alto_mm=2, espesor_mm=6, cantidad=1, estado=True,
            fecha_registro=datetime.now(timezone.utc), id_tipo_vidrio=7))
        s.commit()
    current = accept(comparison_setup)
    _, _, uow = comparison_setup
    for method in ENGINES:
        current = save(uow, current, method)
    return finish(uow, current)


@pytest.fixture
def completed_split(session_factory, comparison_setup):
    # Escenario propio para rollback y concurrencia: la confirmación de WF debe consumir
    # más de una fuente y crear un retazo. Cuatro piezas 2x2; plancha 6 de 6x2 (más
    # reciente, se ofrece primero) y plancha 5 de 4x2 x2. WF v2 llena la 6 con tres
    # piezas y abre la 5 (unidad 1) para la cuarta: queda libre 2x2 en la 5 -> un retazo.
    with session_factory() as s:
        s.add(Plancha(id_plancha=6, ancho_mm=6, alto_mm=2, espesor_mm=6, cantidad=1, estado=True,
            fecha_registro=datetime.now(timezone.utc), id_tipo_vidrio=7))
        s.commit()
    current = accept(comparison_setup)
    _, _, uow = comparison_setup
    for method in ENGINES:
        current = save(uow, current, method)
    return finish(uow, current)


def choose(uow, current, method):
    identifier = next(e.execution_id for e in current.executions if e.method == method)
    with uow() as tx:
        return tx.comparisons.select(current.comparison_id, identifier, current.version)


def confirm(uow, current, actor, key="confirm-comparison-key"):
    return ConfirmComparison(uow).execute(current.comparison_id, current.selected_execution_id,
                                         current.version, key, actor)


@pytest.mark.parametrize("method,remaining,rows", [("FF", (2, 0), 1), ("BF", (0, 1), 1), ("WF", (2, 0), 1)])
def test_confirmation_consumes_only_the_selected_engine(session_factory, comparison_setup, completed, method, remaining, rows):
    actor, ids, uow = comparison_setup
    current = choose(uow, completed, method)
    receipt = confirm(uow, current, actor)
    with uow() as tx:
        loaded = tx.comparisons.get(current.comparison_id)
    assert loaded.confirmation["execution_id"] == current.selected_execution_id
    assert loaded.confirmation["method"] == method and loaded.version == current.version + 1
    assert receipt.optimization_id == current.comparison_id
    assert confirm(uow, current, actor) == receipt  # Mismo key/version original: mismo recibo.
    with session_factory() as s:
        assert (s.get(Plancha, 5).cantidad, s.get(Plancha, 6).cantidad) == remaining
        movements = s.scalars(select(MovimientoInventario)).all()
        assert len(movements) == rows
        assert all({"FF": "First Fit", "BF": "Best Fit", "WF": "Worst Fit"}[method] in m.motivo for m in movements)
        assert [s.get(Pedido, i).estado for i in ids] == ["CONFIRMADO"] * 2
        remnants = s.scalars(select(Retazo)).all()
        assert all(r.id_ejecucion_origen == current.selected_execution_id and r.codigo.startswith(method + "-") for r in remnants)
        if method == "WF":
            assert len(remnants) == 0  # la plancha 8x2 queda llena: no hay retazo
    with pytest.raises(RunError), uow() as tx:
        tx.comparisons.release(loaded.comparison_id, loaded.version, actor)
    with pytest.raises(RunError), uow() as tx:
        tx.comparisons.select(loaded.comparison_id, loaded.executions[0].execution_id, loaded.version)
    with pytest.raises(RunError) as error:
        confirm(uow, current, actor, "confirm-different-key")
    assert error.value.code == "ALREADY_CONFIRMED"


def test_no_selection_and_stale_selection_cannot_consume(session_factory, comparison_setup, completed):
    actor, _, uow = comparison_setup
    bf = next(e.execution_id for e in completed.executions if e.method == "BF")
    with pytest.raises(RunError) as error:
        ConfirmComparison(uow).execute(completed.comparison_id, bf, completed.version, "confirm-comparison-key", actor)
    assert error.value.code == "NOT_CONFIRMABLE"
    selected = choose(uow, completed, "BF")
    choose(uow, selected, "WF")
    with pytest.raises(RunError) as error:
        confirm(uow, selected, actor)
    assert error.value.code == "STATE_CONFLICT"
    with session_factory() as s:
        assert (s.get(Plancha, 5).cantidad, s.get(Plancha, 6).cantidad) == (2, 1)
        assert s.scalar(select(func.count()).select_from(MovimientoInventario)) == 0


def test_stock_conflict_can_release_without_destroying_history(session_factory, comparison_setup, completed):
    actor, ids, uow = comparison_setup
    current = choose(uow, completed, "BF")
    with session_factory() as s:
        s.get(Plancha, 5).cantidad = 1
        s.commit()
    with pytest.raises(RunError) as error:
        confirm(uow, current, actor)
    assert error.value.code == "STOCK_CONFLICT"
    with uow() as tx:
        assert tx.comparisons.get(current.comparison_id) == current
        released = tx.comparisons.release(current.comparison_id, current.version, actor)
    assert released.released and released.executions == current.executions
    with session_factory() as s:
        assert [s.get(Pedido, i).estado for i in ids] == ["PENDIENTE"] * 2
        assert s.scalar(select(func.count()).select_from(MovimientoInventario)) == 0


def test_failure_creating_residual_rolls_back_all_consumption(session_factory, comparison_setup, completed_split):
    actor, ids, uow = comparison_setup
    current = choose(uow, completed_split, "WF")
    def fail(session, flush_context, instances):
        if any(isinstance(o, Retazo) for o in session.new):
            raise RuntimeError("synthetic remnant write failure")
    event.listen(session_factory.class_, "before_flush", fail)
    try:
        with pytest.raises(RuntimeError):
            confirm(uow, current, actor)
    finally:
        event.remove(session_factory.class_, "before_flush", fail)
    with uow() as tx:
        assert tx.comparisons.get(current.comparison_id) == current
    with session_factory() as s:
        assert (s.get(Plancha, 5).cantidad, s.get(Plancha, 6).cantidad) == (2, 1)
        assert [s.get(Pedido, i).estado for i in ids] == ["OPTIMIZADO"] * 2
        assert s.scalar(select(func.count()).select_from(Retazo)) == 0
        assert s.scalar(select(func.count()).select_from(MovimientoInventario)) == 0


def test_concurrent_repeated_confirmation_returns_same_receipt_once(session_factory, comparison_setup, completed_split):
    actor, _, uow = comparison_setup
    current = choose(uow, completed_split, "WF")
    gate = Barrier(2)
    def submitted():
        gate.wait(timeout=5)
        return confirm(uow, current, actor)
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs = [pool.submit(submitted), pool.submit(submitted)]
        left, right = [f.result(timeout=15) for f in jobs]
    assert left == right
    with session_factory() as s:
        # Consumo una sola vez: una unidad de la 6 y una de la 5 (un movimiento por plancha).
        assert (s.get(Plancha, 5).cantidad, s.get(Plancha, 6).cantidad) == (1, 0)
        assert s.scalar(select(func.count()).select_from(MovimientoInventario)) == 2
        assert s.scalar(select(func.count()).select_from(Retazo)) == 1


@pytest.mark.parametrize("competing", ["selection", "release"])
def test_selection_or_release_race_with_confirmation_is_atomic(session_factory, comparison_setup, completed, competing):
    actor, ids, uow = comparison_setup
    current = choose(uow, completed, "BF")
    gate = Barrier(2)
    def confirm_now():
        gate.wait(timeout=5)
        try:
            confirm(uow, current, actor)
            return "confirmed"
        except RunError as error:
            return error.code
    def mutate():
        gate.wait(timeout=5)
        try:
            if competing == "selection":
                choose(uow, current, "WF")
            else:
                with uow() as tx:
                    tx.comparisons.release(current.comparison_id, current.version, actor)
            return "changed"
        except RunError as error:
            return error.code
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs = [pool.submit(confirm_now), pool.submit(mutate)]
        outcomes = [f.result(timeout=15) for f in jobs]
    assert outcomes in (["confirmed", "STATE_CONFLICT"], ["STATE_CONFLICT", "changed"])
    with session_factory() as s:
        if outcomes[0] == "confirmed":
            assert (s.get(Plancha, 5).cantidad, s.get(Plancha, 6).cantidad) == (0, 1)
            assert [s.get(Pedido, i).estado for i in ids] == ["CONFIRMADO"] * 2
        else:
            assert (s.get(Plancha, 5).cantidad, s.get(Plancha, 6).cantidad) == (2, 1)
            assert s.scalar(select(func.count()).select_from(MovimientoInventario)) == 0


def test_unpersistable_residual_is_not_shown_as_reusable_after_confirmation(session_factory, comparison_setup):
    actor, ids, uow = comparison_setup
    with session_factory() as s:
        config = s.scalar(select(Configuracion))
        config.resolucion_raster_mm = Decimal("0.001")
        config.ancho_min_retazo_mm = config.alto_min_retazo_mm = 0
        p = s.scalar(select(Pieza).where(Pieza.id_pedido == ids[0]))
        p.cantidad, p.area_mm2 = 1, Decimal("0.01")
        p.geometria = {"type": "RECTANGULO", "width_mm": 0.1, "height_mm": 0.1}
        p.dimensiones = {"width_mm": 0.1, "height_mm": 0.1}
        s.get(Plancha, 5).ancho_mm = Decimal("0.11")
        s.get(Plancha, 5).alto_mm = Decimal("0.10")
        s.commit()
    current = AcceptComparison(uow).execute(ids[:1], actor, "comparison-tiny-residual")
    for method in ENGINES:
        current = save(uow, current, method)
    current = choose(uow, finish(uow, current), "BF")
    assert current.executions[1].result.metrics.recoverable_remnant_mm2 == Decimal("0.001")
    assert confirm(uow, current, actor).remnants_created == ()
    with uow() as tx:
        loaded = tx.comparisons.get(current.comparison_id)
    assert loaded.executions[1].result.metrics.recoverable_remnant_mm2 == 0
    assert loaded.executions[1].residuals == ()
