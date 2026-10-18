"""Rollback is demonstrated by PostgreSQL triggers, not mocked transaction logic."""
from contextlib import contextmanager
from sqlalchemy import select,func
from sqlalchemy.exc import DBAPIError
import pytest

from app.models import Pedido,Pieza,Plancha,Retazo,Configuracion,EjecucionOptimizacion,MovimientoInventario
from app.modules.optimization.application.confirmation import ConfirmRun
from app.modules.optimization.application.errors import RunError
from .test_runs import prepared  # noqa: F401
from .test_confirmation import calculate,add_remnant,snapshot,invariant


@contextmanager
def failing_trigger(factory,table,event,condition,sqlstate="P0001"):
    engine=factory.kw['bind']
    # Fixed identifiers/expressions from this parametrized test only; no user SQL.
    with engine.begin() as c:
        c.exec_driver_sql("CREATE FUNCTION fail_confirmation_test() RETURNS trigger LANGUAGE plpgsql AS $$ "
            f"BEGIN IF {condition} THEN RAISE EXCEPTION 'SYNTHETIC confirmation rollback trigger' USING ERRCODE = '{sqlstate}'; END IF; "
            "RETURN NEW; END; $$")
        c.exec_driver_sql(f'CREATE TRIGGER fail_confirmation_test AFTER {event} ON {table} '
                         'FOR EACH ROW EXECUTE FUNCTION fail_confirmation_test()')
    try:
        yield
    finally:
        with engine.begin() as c:
            c.exec_driver_sql(f'DROP TRIGGER fail_confirmation_test ON {table}')
            c.exec_driver_sql('DROP FUNCTION fail_confirmation_test()')


@pytest.mark.parametrize('stage,table,event,condition',[
    ('after_sheet_update','planchas','UPDATE','NEW.cantidad < OLD.cantidad'),
    ('during_movement','movimientos_inventario','INSERT',"NEW.tipo_evento = 'CONSUMO_OPTIMIZACION'"),
    ('during_residual_insert','retazos','INSERT','NEW.id_ejecucion_origen IS NOT NULL'),
    ('before_final_orders','pedidos','UPDATE',"NEW.estado = 'CONFIRMADO'"),
    ('during_receipt','ejecuciones_optimizacion','UPDATE',"NEW.patron_resultado ? 'confirmation'")])
def test_real_sql_error_rolls_back_every_write(session_factory,prepared,stage,table,event,condition):
    actor,ids,uow=prepared
    # Leave residual on both sheets so residual INSERT/receipt failures happen
    # AFTER earlier stock/movement writes have already been flushed.
    with session_factory() as s:
        s.get(Plancha,5).ancho_mm=6
        s.commit()
    run=calculate(session_factory,uow,ids,actor)
    assert run.result.metrics.recoverable_remnant_mm2>0
    before=snapshot(session_factory)
    with failing_trigger(session_factory,table,event,condition):
        with pytest.raises(DBAPIError):
            ConfirmRun(uow).execute(run.optimization_id,actor)
    assert snapshot(session_factory)==before
    invariant(session_factory)
    # A fresh session can confirm the SAME original solution after trigger removal.
    receipt=ConfirmRun(uow).execute(run.optimization_id,actor)
    assert len(receipt.remnants_created)>0
    invariant(session_factory)


def mixed_run(factory,prepared):
    actor,ids,uow=prepared
    add_remnant(factory)
    run=calculate(factory,uow,ids,actor)
    assert {s.source.value for s in run.result.materials_used}=={'PLANCHA','RETAZO'}
    return actor,ids,uow,run


@pytest.mark.parametrize('conflict',['retazo','quantity'])
def test_mixed_stock_conflict_never_consumes_the_other_resource(session_factory,prepared,conflict):
    actor,ids,uow,run=mixed_run(session_factory,prepared)
    with session_factory() as s:
        if conflict=='retazo': s.get(Retazo,9).estado=False
        else: s.get(Plancha,5).cantidad=0
        s.commit()
    before=snapshot(session_factory)
    with pytest.raises(RunError) as error:
        ConfirmRun(uow).execute(run.optimization_id,actor)
    assert error.value.code=='STOCK_CONFLICT'
    assert snapshot(session_factory)==before
    invariant(session_factory)


def test_retazo_update_error_also_rolls_back_sheet_and_entire_batch(session_factory,prepared):
    actor,ids,uow,run=mixed_run(session_factory,prepared)
    before=snapshot(session_factory)
    with failing_trigger(session_factory,'retazos','UPDATE','OLD.estado AND NOT NEW.estado'):
        with pytest.raises(DBAPIError):
            ConfirmRun(uow).execute(run.optimization_id,actor)
    assert snapshot(session_factory)==before
    invariant(session_factory)


def test_residual_code_conflict_rolls_back_already_flushed_consumption(session_factory,prepared):
    actor,ids,uow=prepared
    with session_factory() as s:
        s.get(Plancha,5).ancho_mm=6
        s.commit()
    run=calculate(session_factory,uow,ids,actor)
    # Code belongs to a pre-existing, unrelated manual retazo; never overwrite it.
    add_remnant(session_factory)
    with session_factory() as s:
        s.get(Retazo,9).codigo=f'FF-{run.optimization_id}-P5-2'
        s.commit()
    before=snapshot(session_factory)
    with pytest.raises(RunError) as error:
        ConfirmRun(uow).execute(run.optimization_id,actor)
    assert error.value.code=='STATE_CONFLICT'
    assert snapshot(session_factory)==before
    invariant(session_factory)
