"""State boundaries A/B/C: one write commit or rollback of the entire batch."""
from functools import partial
from sqlalchemy import event, select, func
import pytest

from app.models import (Pedido, Plancha, Retazo, MovimientoInventario, Optimizacion,
                        EjecucionOptimizacion, MaterialUtilizado, MetricaEjecucion)
from app.modules.optimization.application.runs import AcceptRun
from app.modules.optimization.application.calculation import CalculateRun
from app.modules.optimization.application.errors import RunError, ResultSaveFailed
from app.modules.inventory.infrastructure.repository import SqlAlchemyInventoryRepository
from app.modules.optimization.infrastructure.stock_adapter import InventoryStockAdapter
from .test_runs import prepared  # noqa: F401


def calculator(factory, uow):
    return CalculateRun(uow, InventoryStockAdapter(SqlAlchemyInventoryRepository(factory)))


def inventory(factory):
    with factory() as s:
        return ([(p.id_plancha,p.cantidad,p.estado,p.ancho_mm,p.alto_mm) for p in s.scalars(select(Plancha).order_by(Plancha.id_plancha))],
                [(r.id_retazo,r.estado,r.geometria,r.area_mm2) for r in s.scalars(select(Retazo).order_by(Retazo.id_retazo))],
                s.scalar(select(func.count()).select_from(MovimientoInventario)))


@pytest.mark.parametrize('n',[1,2])
@pytest.mark.parametrize('complete',[True,False])
def test_all_states_and_result_in_single_write_commit(session_factory,prepared,n,complete):
    actor, all_ids,uow=prepared
    ids=all_ids[:n]
    if not complete:
        with session_factory() as s:
            sheet=s.get(Plancha,5)
            sheet.ancho_mm=sheet.alto_mm=2
            sheet.cantidad=1
            s.commit()
    before=inventory(session_factory)
    run=AcceptRun(uow).execute(ids,actor)
    write_commits=[]
    def committing(s):
        if s.new or s.dirty or s.deleted:
            write_commits.append(True)
    event.listen(session_factory.class_,'before_commit',committing)
    try:
        final=calculator(session_factory,uow).execute(run.optimization_id)
    finally:
        event.remove(session_factory.class_,'before_commit',committing)
    assert write_commits==[True]
    assert final.status.value==('COMPLETADA' if complete else 'SIN_SOLUCION')
    assert final.confirmable is complete
    with session_factory() as s:
        assert [s.get(Pedido,i).estado for i in ids]==['OPTIMIZADO' if complete else 'PENDIENTE']*n
        parent=s.get(Optimizacion,run.optimization_id)
        execution=s.scalar(select(EjecucionOptimizacion))
        assert parent.fecha_fin is not None and execution.fecha_fin==parent.fecha_fin
        assert execution.estado=='COMPLETADA' and execution.completo is complete
        assert (parent.id_ejecucion_seleccionada==execution.id_ejecucion) is complete
    assert inventory(session_factory)==before


@pytest.mark.parametrize('complete',[True,False])
def test_failure_after_sql_flush_rolls_back_every_final_write(session_factory,prepared,complete):
    actor,ids,uow=prepared
    if not complete:
        with session_factory() as s:
            s.get(Plancha,5).cantidad=1
            s.commit()
    accepted=AcceptRun(uow).execute(ids,actor)
    before=inventory(session_factory)
    injected=[]
    def after_flush(s,context):
        # SQL for ALL updates/inserts already ran, but transaction has not committed.
        state=s.scalar(select(Optimizacion.estado).where(Optimizacion.id_optimizacion==accepted.optimization_id))
        if state in ('COMPLETADA','SIN_SOLUCION'):
            injected.append(state)
            raise RuntimeError('synthetic failure after SQL writes')
    event.listen(session_factory.class_,'after_flush_postexec',after_flush)
    try:
        with pytest.raises(ResultSaveFailed):
            calculator(session_factory,uow).execute(accepted.optimization_id)
    finally:
        event.remove(session_factory.class_,'after_flush_postexec',after_flush)
    assert len(injected)==1
    with uow() as tx:
        assert tx.runs.get(accepted.optimization_id)==accepted
    with session_factory() as s:
        assert [s.get(Pedido,i).estado for i in ids]==['EN_OPTIMIZACION']*2
        for model in (MaterialUtilizado,MetricaEjecucion):
            assert s.scalar(select(func.count()).select_from(model))==0
    assert inventory(session_factory)==before


@pytest.mark.parametrize('n',[1,2])
def test_unexpected_failed_keeps_entire_batch_for_reconciliation(session_factory,prepared,n):
    actor,ids,uow=prepared
    ids=ids[:n]
    accepted=AcceptRun(uow).execute(ids,actor)
    before=inventory(session_factory)
    with uow() as tx:
        failed=tx.runs.fail(accepted.optimization_id,'CALCULATION_FAILED')
    assert failed.status.value=='FALLIDA' and not failed.confirmable
    with uow() as tx:
        assert tx.runs.get(accepted.optimization_id)==failed
    with session_factory() as s:
        assert [s.get(Pedido,i).estado for i in ids]==['EN_OPTIMIZACION']*n
        assert s.scalar(select(EjecucionOptimizacion)).estado=='FALLIDA'
    assert inventory(session_factory)==before


def test_failure_recording_rolls_back_without_reset_or_partial_state(session_factory,prepared):
    actor,ids,uow=prepared
    run=AcceptRun(uow).execute(ids,actor)
    def fail(s,context):
        if s.scalar(select(Optimizacion.estado))=='FALLIDA':
            raise RuntimeError('synthetic failure recording exception')
    event.listen(session_factory.class_,'after_flush_postexec',fail)
    try:
        with pytest.raises(RuntimeError):
            with uow() as tx:
                tx.runs.fail(run.optimization_id,'CALCULATION_FAILED')
    finally:
        event.remove(session_factory.class_,'after_flush_postexec',fail)
    with uow() as tx:
        assert tx.runs.get(run.optimization_id)==run
    with session_factory() as s:
        assert [s.get(Pedido,i).estado for i in ids]==['EN_OPTIMIZACION']*2


def test_changed_order_prevents_any_terminal_subset(session_factory,prepared):
    actor,ids,uow=prepared
    run=AcceptRun(uow).execute(ids,actor)
    with session_factory() as s:
        s.get(Pedido,ids[-1]).estado='PENDIENTE'  # Deliberate out-of-band inconsistency.
        s.commit()
    with pytest.raises(ResultSaveFailed):
        calculator(session_factory,uow).execute(run.optimization_id)
    with uow() as tx:
        assert tx.runs.get(run.optimization_id)==run
    with session_factory() as s:
        assert [s.get(Pedido,i).estado for i in ids]==['EN_OPTIMIZACION','PENDIENTE']
        assert s.scalar(select(func.count()).select_from(MaterialUtilizado))==0


def test_terminal_cannot_be_recalculated_or_overwritten_by_late_disconnect(session_factory,prepared):
    actor,ids,uow=prepared
    accepted=AcceptRun(uow).execute(ids,actor)
    final=calculator(session_factory,uow).execute(accepted.optimization_id)
    with pytest.raises(RunError) as error:
        calculator(session_factory,uow).execute(accepted.optimization_id)
    assert error.value.code=='STATE_CONFLICT'
    with uow() as tx:
        assert tx.runs.fail(final.optimization_id,'EXECUTION_INTERRUPTED')==final
    with session_factory() as s:
        assert s.scalar(select(func.count()).select_from(MetricaEjecucion))==1
        assert s.scalar(select(func.count()).select_from(MaterialUtilizado))==1
        assert [s.get(Pedido,i).estado for i in ids]==['OPTIMIZADO']*2
        assert s.get(Plancha,5).cantidad==2


def test_inconsistent_parent_execution_rejected_for_reconciliation(session_factory,prepared):
    actor,ids,uow=prepared
    accepted=AcceptRun(uow).execute(ids,actor)
    with session_factory() as s:
        s.scalar(select(EjecucionOptimizacion)).estado='FALLIDA'
        s.commit()
    with pytest.raises(RunError) as error:
        with uow() as tx:
            tx.runs.get(accepted.optimization_id)
    assert error.value.code=='INTERNAL_ERROR'
