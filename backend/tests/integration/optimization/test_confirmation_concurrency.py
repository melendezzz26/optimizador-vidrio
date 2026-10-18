"""No fake locks: separate PostgreSQL connections, real wait and committed outcomes."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier,Event,Lock
from time import monotonic,sleep
import json

import pytest
from sqlalchemy import event,select,text,func

from app.models import Pedido,Plancha,Retazo,MovimientoInventario
from app.modules.optimization.application.confirmation import ConfirmRun
from app.modules.optimization.application.errors import RunError
from .test_runs import prepared  # noqa: F401
from .test_confirmation import calculate,add_remnant,invariant,snapshot


def observe_blocking(factory,table):
    deadline=monotonic()+8
    while monotonic()<deadline:
        with factory() as s:
            rows=s.execute(text("SELECT pid,wait_event_type,wait_event,pg_blocking_pids(pid) AS blockers,query "
                "FROM pg_stat_activity WHERE datname=current_database() AND wait_event_type='Lock' "
                "AND pid<>pg_backend_pid()" )).mappings().all()
        for row in rows:
            if f'from {table}' in row['query'].lower() and 'for update' in row['query'].lower() and row['blockers']:
                return dict(row)
        sleep(0.01)
    pytest.fail(f'No real PostgreSQL wait observed on {table}')


def race(factory,table,operations,tmp_path):
    barrier=Barrier(2)
    acquired,release=Event(),Event()
    guard=Lock()
    winner={}
    def hold_after_real_lock(conn,cursor,statement,parameters,context,executemany):
        sql=statement.lower()
        if f'from {table}' not in sql or 'for update' not in sql:
            return
        with guard:
            first=not acquired.is_set()
            if first:
                winner['pid']=conn.scalar(text('SELECT pg_backend_pid()'))
                acquired.set()
        if first:
            assert release.wait(timeout=15),'Timed out releasing winner'
    def attempt(operation):
        barrier.wait(timeout=10)
        try:
            result=operation()
            return {'status':200,'optimization_id':result.optimization_id}
        except RunError as error:
            assert error.code in ('ALREADY_CONFIRMED','STOCK_CONFLICT','STATE_CONFLICT')
            return {'status':409,'code':error.code}
    engine=factory.kw['bind']
    event.listen(engine,'after_cursor_execute',hold_after_real_lock)
    observed=None
    try:
        with ThreadPoolExecutor(max_workers=2,thread_name_prefix='confirmation-race') as pool:
            futures=[pool.submit(attempt,op) for op in operations]
            try:
                assert acquired.wait(timeout=10)
                observed=observe_blocking(factory,table)
                assert winner['pid'] in observed['blockers']
                assert all(not f.done() for f in futures)
            finally:
                release.set()
            outcomes=[f.result(timeout=20) for f in futures]
    finally:
        release.set()
        event.remove(engine,'after_cursor_execute',hold_after_real_lock)
    assert sorted(r['status'] for r in outcomes)==[200,409],outcomes
    proof={'lock_table':table,'winner_pid':winner['pid'],'waiting':observed,'outcomes':outcomes}
    (tmp_path/'postgres-lock-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    invariant(factory)
    return outcomes


def test_same_optimization_two_concurrent_confirms_exactly_one_consumption(session_factory,prepared,tmp_path):
    actor,ids,uow=prepared
    run=calculate(session_factory,uow,ids,actor)
    outcome=race(session_factory,'optimizaciones',[
        lambda:ConfirmRun(uow).execute(run.optimization_id,actor),
        lambda:ConfirmRun(uow).execute(run.optimization_id,actor)],tmp_path)
    assert next(r for r in outcome if r['status']==409)['code']=='ALREADY_CONFIRMED'
    with session_factory() as s:
        assert s.get(Plancha,5).cantidad==0
        assert s.scalar(select(func.count()).select_from(MovimientoInventario))==1
        assert s.scalar(select(MovimientoInventario.cantidad_afectada))==2
        assert [s.get(Pedido,i).estado for i in ids]==['CONFIRMADO']*2


def test_two_optimizations_race_for_same_concrete_remnant(session_factory,prepared,tmp_path):
    actor,ids,uow=prepared
    add_remnant(session_factory)
    first=calculate(session_factory,uow,ids[:1],actor)
    second=calculate(session_factory,uow,ids[1:],actor)
    assert first.result.materials_used==second.result.materials_used
    outcomes=race(session_factory,'retazos',[
        lambda:ConfirmRun(uow).execute(first.optimization_id,actor),
        lambda:ConfirmRun(uow).execute(second.optimization_id,actor)],tmp_path)
    assert next(r for r in outcomes if r['status']==409)['code']=='STOCK_CONFLICT'
    with session_factory() as s:
        assert not s.get(Retazo,9).estado
        assert s.get(Plancha,5).cantidad==2
        movements=s.scalars(select(MovimientoInventario)).all()
        assert len(movements)==1 and movements[0].cantidad_afectada==1
        assert sorted(s.get(Pedido,i).estado for i in ids)==['CONFIRMADO','OPTIMIZADO']
    for run in (first,second):
        with uow() as tx:
            loaded=tx.runs.get(run.optimization_id)
        assert loaded.confirmed is (run.optimization_id==next(r for r in outcomes if r['status']==200)['optimization_id'])


def test_two_optimizations_race_for_last_sheet_unit(session_factory,prepared,tmp_path):
    actor,ids,uow=prepared
    with session_factory() as s:
        s.get(Plancha,5).cantidad=1
        s.commit()
    first=calculate(session_factory,uow,ids[:1],actor)
    second=calculate(session_factory,uow,ids[1:],actor)
    assert first.result.complete and second.result.complete
    outcomes=race(session_factory,'planchas',[
        lambda:ConfirmRun(uow).execute(first.optimization_id,actor),
        lambda:ConfirmRun(uow).execute(second.optimization_id,actor)],tmp_path)
    assert next(r for r in outcomes if r['status']==409)['code']=='STOCK_CONFLICT'
    with session_factory() as s:
        assert s.get(Plancha,5).cantidad==0 and not s.get(Plancha,5).estado
        assert s.scalar(select(func.count()).select_from(MovimientoInventario))==1
        assert sorted(s.get(Pedido,i).estado for i in ids)==['CONFIRMADO','OPTIMIZADO']


def test_inventory_update_lock_wins_and_confirm_revalidates_new_quantity(session_factory,prepared,tmp_path):
    actor,ids,uow=prepared
    run=calculate(session_factory,uow,ids,actor)
    acquired,release=Event(),Event()
    def mutate_stock():
        with session_factory() as s:
            row=s.scalar(select(Plancha).where(Plancha.id_plancha==5).with_for_update())
            row.cantidad=1
            s.flush()
            acquired.set()
            assert release.wait(timeout=15)
            s.commit()
    def confirm():
        assert acquired.wait(timeout=10)
        try:
            ConfirmRun(uow).execute(run.optimization_id,actor)
        except RunError as error:
            return error.code
        pytest.fail('Stale quantity must conflict')
    with ThreadPoolExecutor(max_workers=2) as pool:
        changed=pool.submit(mutate_stock)
        attempt=pool.submit(confirm)
        try:
            assert acquired.wait(timeout=10)
            observed=observe_blocking(session_factory,'planchas')
            assert not attempt.done()
        finally:
            release.set()
        changed.result(timeout=20)
        assert attempt.result(timeout=20)=='STOCK_CONFLICT'
    (tmp_path/'postgres-lock-proof.json').write_text(json.dumps({'case':'external_stock_change','waiting':observed,'outcome':409},indent=2)+'\n')
    with session_factory() as s:
        assert s.get(Plancha,5).cantidad==1
        assert [s.get(Pedido,i).estado for i in ids]==['OPTIMIZADO']*2
        assert s.scalar(select(func.count()).select_from(MovimientoInventario))==0
    invariant(session_factory)
