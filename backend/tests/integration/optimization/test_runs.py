"""Real PostgreSQL acceptance/atomicity; inventory is only observed."""
from datetime import datetime, timezone
from decimal import Decimal
from functools import partial

import pytest
from sqlalchemy import select, func, event

from app.models import (Configuracion, Pedido, Pieza, Optimizacion, OptimizacionPedido,
                        EjecucionOptimizacion, Plancha, MovimientoInventario)
from app.modules.orders.infrastructure.repositories import SQLAlchemyOrderRepository
from app.modules.optimization.application.runs import AcceptRun
from app.modules.optimization.application.errors import RunError
from app.modules.optimization.infrastructure.run_uow import SqlRunUnitOfWork


@pytest.fixture
def prepared(session_factory, create_user):
    actor = create_user("O73000001")
    now = datetime.now(timezone.utc)
    with session_factory() as s:
        s.add(Configuracion(version=1, separacion_mm=0, margen_mm=0, resolucion_raster_mm=1,
            paso_angular_grados=90, ancho_min_retazo_mm=1, alto_min_retazo_mm=1, vigente=True,
            id_usuario_creacion=actor, fecha_creacion=now))
        s.add(Plancha(id_plancha=5, ancho_mm=4, alto_mm=2, espesor_mm=6, cantidad=2, estado=True,
                      fecha_registro=now, id_tipo_vidrio=7))
        s.commit()
        repo = SQLAlchemyOrderRepository(s)
        piece = dict(tipo_forma="RECTANGULO", cantidad=2, dimensiones={"width_mm": 2, "height_mm": 2},
            geometria={"type": "RECTANGULO", "width_mm": 2, "height_mm": 2}, id_tipo_vidrio=7,
            espesor_mm=6, area_mm2=4)
        ids = [repo.create_order(actor, [piece], id_cliente=41) for _ in range(2)]
    return actor, ids, partial(SqlRunUnitOfWork, session_factory)


@pytest.mark.parametrize("n", [1, 2])
def test_accept_batch_one_commit_snapshot_and_links(session_factory, prepared, n):
    actor, ids, uow = prepared
    commits = []
    def committed(session):
        commits.append(True)
    event.listen(session_factory.class_, "after_commit", committed)
    try:
        run = AcceptRun(uow).execute(ids[:n][::-1], actor)
    finally:
        event.remove(session_factory.class_, "after_commit", committed)
    assert len(commits) == 1
    assert run.result.problem.order_ids == tuple(ids[:n])
    assert run.result.total_units == n * 2
    with uow() as tx:
        assert tx.runs.get(run.optimization_id) == run
    with session_factory() as s:
        assert list(s.scalars(select(OptimizacionPedido.id_pedido).order_by(OptimizacionPedido.id_pedido))) == ids[:n]
        assert [s.get(Pedido, i).estado for i in ids[:n]] == ["EN_OPTIMIZACION"] * n
        assert s.get(Plancha, 5).cantidad == 2
        assert s.scalar(select(func.count()).select_from(MovimientoInventario)) == 0


@pytest.mark.parametrize("invalid", ["missing", "state", "geometry", "no_pieces", "duplicate", "empty", "config", "multi_config"])
def test_invalid_batch_rolls_back_everything(session_factory, prepared, invalid):
    actor, ids, uow = prepared
    submitted = ids[:]
    with session_factory() as s:
        if invalid == "missing": submitted.append(99999)
        if invalid == "state": s.get(Pedido, ids[-1]).estado = "OPTIMIZADO"
        if invalid == "geometry":
            p = s.scalar(select(Pieza).where(Pieza.id_pedido == ids[-1]))
            p.geometria = {"type": "RECTANGULO", "width_mm": -2, "height_mm": 2}
        if invalid == "no_pieces":
            for p in s.scalars(select(Pieza).where(Pieza.id_pedido == ids[-1])): s.delete(p)
        if invalid == "duplicate": submitted.append(ids[0])
        if invalid == "empty": submitted = []
        if invalid == "config": s.scalar(select(Configuracion)).paso_angular_grados = None
        if invalid == "multi_config":
            s.add(Configuracion(version=2, separacion_mm=0, margen_mm=0, resolucion_raster_mm=1,
                paso_angular_grados=90, ancho_min_retazo_mm=1, alto_min_retazo_mm=1, vigente=True,
                id_usuario_creacion=actor, fecha_creacion=datetime.now(timezone.utc)))
        s.commit()
    with pytest.raises(RunError):
        AcceptRun(uow).execute(submitted, actor)
    with session_factory() as s:
        assert s.get(Pedido, ids[0]).estado == "PENDIENTE"
        assert s.get(Pedido, ids[-1]).estado == ("OPTIMIZADO" if invalid == "state" else "PENDIENTE")
        for model in (Optimizacion, OptimizacionPedido, EjecucionOptimizacion):
            assert s.scalar(select(func.count()).select_from(model)) == 0


def test_transaction_failure_after_transitions_is_total_rollback(session_factory, prepared):
    actor, ids, factory = prepared
    class BrokenUow(SqlRunUnitOfWork):
        def __exit__(self, exc_type, exc, traceback):
            if exc_type is None:
                self.session.flush()
                self.session.rollback()
                self.session.close()
                raise RuntimeError("synthetic commit failure")
            return super().__exit__(exc_type, exc, traceback)
    with pytest.raises(RuntimeError):
        AcceptRun(partial(BrokenUow, session_factory)).execute(ids, actor)
    with session_factory() as s:
        assert all(s.get(Pedido, i).estado == "PENDIENTE" for i in ids)
        assert s.scalar(select(func.count()).select_from(Optimizacion)) == 0


def test_multimaterial_snapshot_is_detached(session_factory, prepared):
    actor, ids, uow = prepared
    with session_factory() as s:
        p = s.scalar(select(Pieza).where(Pieza.id_pedido == ids[1]))
        p.id_tipo_vidrio, p.espesor_mm = 8, Decimal('4')
        s.commit()
    run = AcceptRun(uow).execute(ids, actor)
    assert [g.key for g in run.result.problem.groups] == [(7, Decimal(6)), (8, Decimal(4))]
    with session_factory() as s:
        s.scalar(select(Pieza).where(Pieza.id_pedido == ids[1])).cantidad = 3
        s.commit()
    with uow() as tx:
        assert tx.runs.get(run.optimization_id).result.total_units == 4


@pytest.mark.parametrize('availability,placed,complete', [(2, 4, True), (1, 2, False), (0, 0, False)])
def test_durable_results_metrics_physical_stock_and_no_consumption(session_factory, prepared, availability, placed, complete, monkeypatch):
    from app.models import MaterialUtilizado, MetricaEjecucion, Retazo
    from app.modules.optimization.application.calculation import CalculateRun
    from app.modules.inventory.infrastructure.repository import SqlAlchemyInventoryRepository
    from app.modules.optimization.infrastructure.stock_adapter import InventoryStockAdapter
    from app.modules.optimization.presentation.run_serialization import run_response
    actor, ids, uow = prepared
    with session_factory() as s:
        s.get(Plancha, 5).cantidad = availability
        s.commit()
    accepted = AcceptRun(uow).execute(ids, actor)
    provider = InventoryStockAdapter(SqlAlchemyInventoryRepository(session_factory))
    run = CalculateRun(uow, provider).execute(accepted.optimization_id)
    assert run.result.placed_units == placed and run.result.complete is complete
    assert run.confirmable is complete
    assert run.result.computation_time_ms >= 0
    # Canonical load must work with both algorithm and live source data unavailable.
    monkeypatch.setattr('app.modules.optimization.domain.first_fit.FirstFitOptimizer.optimize', lambda *a, **k: pytest.fail('GET reran FF'))
    with uow() as tx:
        loaded = tx.runs.get(run.optimization_id)
    assert loaded == run
    wire = run_response(loaded).model_dump(mode='json')
    assert wire['metrics_available'] is bool(placed)
    if placed:
        assert wire['metrics']['aprovechamiento_pct'] == '100.000'
        assert Decimal(wire['metrics']['merma_mm2']) == Decimal('0')
        assert wire['metrics']['planchas_nuevas_usadas'] == availability
    else:
        assert wire['metrics'] is None
    with session_factory() as s:
        assert s.get(Plancha, 5).cantidad == availability
        assert s.scalar(select(func.count()).select_from(MovimientoInventario)) == 0
        assert s.scalar(select(func.count()).select_from(Retazo)) == 0
        assert [s.get(Pedido, i).estado for i in ids] == ['OPTIMIZADO' if complete else 'PENDIENTE'] * 2
        assert s.scalar(select(func.count()).select_from(MetricaEjecucion)) == bool(placed)
        materials = s.scalars(select(MaterialUtilizado)).all()
        assert len(materials) == bool(placed)
        if materials:
            assert materials[0].cantidad_utilizada == availability
        row = s.get(Optimizacion, run.optimization_id)
        assert (row.id_ejecucion_seleccionada is not None) is complete


def test_decimal_coordinates_and_residual_proposal_are_lossless(session_factory, prepared):
    from app.models import Retazo
    from app.modules.optimization.application.calculation import CalculateRun
    from app.modules.inventory.infrastructure.repository import SqlAlchemyInventoryRepository
    from app.modules.optimization.infrastructure.stock_adapter import InventoryStockAdapter
    actor, ids, uow = prepared
    with session_factory() as s:
        config = s.scalar(select(Configuracion))
        config.resolucion_raster_mm = Decimal('0.125')
        config.ancho_min_retazo_mm = config.alto_min_retazo_mm = Decimal('0.125')
        piece = s.scalar(select(Pieza).where(Pieza.id_pedido == ids[0]))
        piece.geometria = {'type': 'RECTANGULO', 'width_mm': 0.25, 'height_mm': 2}
        piece.area_mm2 = Decimal('0.50')
        s.commit()
    accepted = AcceptRun(uow).execute(ids[:1], actor)
    run = CalculateRun(uow, InventoryStockAdapter(SqlAlchemyInventoryRepository(session_factory))).execute(accepted.optimization_id)
    assert [p.x_mm for p in run.result.placements] == [Decimal(0), Decimal('0.250')]
    with uow() as tx:
        assert tx.runs.get(run.optimization_id) == run
    with session_factory() as s:
        stored = s.scalar(select(EjecucionOptimizacion)).patron_resultado
        residuals = stored['residual_rectangles']
        assert len(residuals) == 1
        assert Decimal(residuals[0]['x_mm']) == Decimal('0.500')
        assert Decimal(residuals[0]['area_mm2']) == Decimal('7')
        assert run.result.metrics.recoverable_remnant_mm2 == Decimal('7')
        assert run.result.metrics.waste_mm2 == 0
        assert s.scalar(select(func.count()).select_from(Retazo)) == 0


def test_final_save_failure_rolls_back_result_and_all_states(session_factory, prepared):
    from app.modules.optimization.application.calculation import CalculateRun
    from app.modules.inventory.infrastructure.repository import SqlAlchemyInventoryRepository
    from app.modules.optimization.infrastructure.stock_adapter import InventoryStockAdapter
    actor, ids, uow = prepared
    run = AcceptRun(uow).execute(ids, actor)
    def fail(session, flush_context, instances):
        if any(isinstance(o, Optimizacion) and o.estado == 'COMPLETADA' for o in session.dirty):
            raise RuntimeError('synthetic save error')
    event.listen(session_factory.class_, 'before_flush', fail)
    try:
        with pytest.raises(RuntimeError):
            CalculateRun(uow, InventoryStockAdapter(SqlAlchemyInventoryRepository(session_factory))).execute(run.optimization_id)
    finally:
        event.remove(session_factory.class_, 'before_flush', fail)
    with uow() as tx:
        assert tx.runs.get(run.optimization_id) == run
    with session_factory() as s:
        assert [s.get(Pedido, i).estado for i in ids] == ['EN_OPTIMIZACION'] * 2
        assert s.scalar(select(func.count()).select_from(MovimientoInventario)) == 0
