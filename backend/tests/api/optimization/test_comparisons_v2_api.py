"""B06 real FastAPI/RBAC -> isolated PostgreSQL -> native spawn -> typed wire."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from functools import partial
import json
import os
from pathlib import Path
import time
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select,func,delete

from app.models import Optimizacion,EjecucionOptimizacion,Plancha,Permiso,RolPermiso
from app.shared.security import create_access_token
from app.modules.optimization.application.comparison_acceptance_v2 import AcceptComparisonV2
from app.modules.optimization.application.comparison_limits import ComparisonBudget
from app.modules.optimization.application.sequential_policy import SequentialPolicy
from app.modules.optimization.domain.beam_search import BeamSearchLimits
from app.modules.optimization.infrastructure.comparison_v2_uow import SqlComparisonPersistenceUnitOfWork
from app.modules.optimization.infrastructure.comparison_snapshot import problem_fingerprint
from app.modules.optimization.infrastructure.sequential_runner import SequentialProcessRunner
from app.modules.optimization.presentation.comparison_supervision_v2 import ComparisonV2Coordinator,authorize_actor,get_comparison_v2_coordinator
from app.modules.optimization.presentation.comparison_http_runtime_v2 import HttpComparisonJob
from app.modules.optimization.presentation.comparison_v2_schemas import ComparisonSummaryV2,ExecutionResponseV2,ComparisonEventV2,ComparisonMaskV2
from tests.integration.optimization.test_runs import prepared  # noqa: F401
from tests.integration.optimization.test_comparison_supervision_v2 import inventory
from tests.unit.optimization.test_sequential_runner import crash_hf,limited_beam,started_then_blocked
from main import app

BASE='/api/optimization/comparisons-v2'


@pytest.fixture
def api(session_factory,prepared,run_admission,monkeypatch):
    from app.modules.authentication.presentation.dependencies import get_database_session
    from app.modules.optimization.presentation import comparison_supervision_v2 as composition
    actor,ids,_=prepared
    uow=partial(SqlComparisonPersistenceUnitOfWork,session_factory)
    coordinator=ComparisonV2Coordinator(uow,run_admission,job_factory=HttpComparisonJob)
    app.dependency_overrides[get_comparison_v2_coordinator]=lambda:coordinator
    def database():
        with session_factory() as session: yield session
    app.dependency_overrides[get_database_session]=database
    monkeypatch.setattr(composition,'get_comparison_v2_coordinator',lambda:coordinator)
    headers={'Authorization':'Bearer '+create_access_token(actor,'O73000001','Operario')}
    try:
        with TestClient(app,raise_server_exceptions=False) as client:
            yield client,actor,ids,headers,coordinator,uow
    finally:
        coordinator.shutdown()
        app.dependency_overrides.pop(get_comparison_v2_coordinator,None)
        app.dependency_overrides.pop(get_database_session,None)


def start(api,key='b06-real-comparison-0001'):
    client,_,ids,headers,_,_=api
    response=client.post(BASE,json={'order_ids':ids},headers={**headers,'Idempotency-Key':key})
    assert response.status_code==201,response.text
    return response.headers['location'],ComparisonSummaryV2.model_validate(response.json())


def completed(api,path):
    client,_,_,headers,coordinator,_=api
    deadline=time.monotonic()+25
    while time.monotonic()<deadline:
        response=client.get(path,headers=headers)
        assert response.status_code==200,response.text
        current=ComparisonSummaryV2.model_validate(response.json())
        if current.terminal:
            assert coordinator.job.closed.wait(3)
            return current
        time.sleep(.025)
    pytest.fail('v2 did not reach safe terminal state')


def save_evidence(name,data):
    destination=os.environ.get('NEWGLASS_B06_EVIDENCE_DIR')
    if destination:
        path=Path(destination); path.mkdir(parents=True,exist_ok=True)
        (path/f'{name}.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')


def test_real_six_results_events_masks_restart_and_no_inventory_consumption(api,session_factory,monkeypatch):
    client,actor,ids,headers,coordinator,uow=api
    before=inventory(session_factory)
    path,accepted=start(api)
    finished=completed(api,path)
    assert finished.methods==['FF','BF','WF','HF','M5','M6-BS']
    assert all(e.complete and e.result_available for e in finished.executions)
    keyed=client.get(BASE+'/requests/b06-real-comparison-0001',headers=headers)
    assert keyed.json()==finished.model_dump(mode='json')
    results=[]; manifests=[]
    for execution in finished.executions:
        response=client.get(f'{path}/executions/{execution.execution_id}',headers=headers)
        result=ExecutionResponseV2.model_validate(response.json())
        assert result.execution.method==execution.method and result.result.metodo==execution.method
        assert result.result.metrics is not None and result.result.placed_units==4
        results.append(response.json())
        visual=client.get(f'{path}/executions/{execution.execution_id}/visual',headers=headers)
        assert visual.status_code==200,visual.text
        manifests.append(visual.json())
    refs=manifests[0]['items']; assert refs
    descriptor=ComparisonMaskV2.model_validate(refs[0])
    mask_path=f'{path}/executions/{descriptor.execution_id}/visual/masks/{descriptor.mask_ref}'
    assert client.get(mask_path,headers=headers).status_code==200
    assert client.get(f'{path}/executions/{finished.executions[1].execution_id}/visual/masks/{descriptor.mask_ref}',headers=headers).status_code==404
    stream=client.get(path+'/events',headers=headers)
    assert stream.status_code==200,stream.text
    events=[ComparisonEventV2.model_validate_json(line) for line in stream.iter_lines()]
    assert [e.sequence for e in events]==list(range(1,len(events)+1))
    assert events[0].event=='comparison_accepted' and events[-1].event=='comparison_finished'
    assert sum(e.event=='result_persisted' for e in events)==6
    assert all(e.presentation=='PROVISIONAL' for e in events if e.event=='search_progress')
    assert not any(e.method=='M6-BS' and e.event=='piece_placed' for e in events)
    assert coordinator.job.runner.retention.bytes=={'visual':0,'event':0}
    assert coordinator.job.event_bytes==sum(len(raw) for _,raw in coordinator.job.events)
    assert coordinator.job.runner.last_report['all_workers_stopped'] and coordinator.admission.active()==0
    with uow() as tx:
        durable=tx.comparisons_v2.get(finished.comparison_id)
        assert all(problem_fingerprint(e.result.problem)==finished.input_sha256 for e in durable.executions)
    # A new coordinator has no retained events/masks and must never recalculate history.
    fresh=ComparisonV2Coordinator(uow,coordinator.admission,job_factory=HttpComparisonJob)
    def forbidden(*args,**kwargs): pytest.fail('History read restarted a productive engine')
    monkeypatch.setattr(SequentialProcessRunner,'events',forbidden)
    app.dependency_overrides[get_comparison_v2_coordinator]=lambda:fresh
    assert client.get(path,headers=headers).json()==finished.model_dump(mode='json')
    assert client.get(BASE+'/requests/b06-real-comparison-0001',headers=headers).json()==finished.model_dump(mode='json')
    assert client.post(BASE,json={'order_ids':ids},headers={**headers,'Idempotency-Key':'b06-real-comparison-0001'}).json()==finished.model_dump(mode='json')
    for execution,result in zip(finished.executions,results):
        assert client.get(f'{path}/executions/{execution.execution_id}',headers=headers).json()==result
    assert client.get(path+'/events',headers=headers).status_code==410
    assert client.get(mask_path,headers=headers).status_code==410
    assert inventory(session_factory)==before
    with session_factory() as s: assert s.scalar(select(func.count()).select_from(EjecucionOptimizacion))==6
    save_evidence('api-real',dict(summary=finished.model_dump(mode='json'),executions=results,
        events=[e.model_dump(mode='json') for e in events],manifests=manifests,
        inventory_before=before,inventory_after=inventory(session_factory),
        timeline=coordinator.job.timeline,resources=coordinator.job.runner.last_report,restart_without_recalculation=True))


@pytest.mark.parametrize('method,path',[('post',''),('get','/1'),('get','/requests/b06-key-0001'),
    ('get','/1/executions/1'),('get','/1/events'),('get','/1/executions/1/visual'),
    ('get','/1/executions/1/visual/masks/'+'a'*32),('post','/1/release')])
def test_requires_real_bearer(api,method,path):
    client,*_=api
    response=getattr(client,method)(BASE+path,json={'order_ids':[1]} if method=='post' else None) if method=='post' else client.get(BASE+path)
    assert response.status_code==401,response.text


@pytest.mark.parametrize('operation',['execute','view','release'])
def test_rbac_guard_precedes_operation(api,session_factory,operation):
    client,_,ids,headers,_,_=api
    code='optimization.view' if operation=='view' else 'optimization.execute'
    with session_factory() as s:
        permission=s.scalar(select(Permiso.id_permiso).where(Permiso.codigo==code))
        s.execute(delete(RolPermiso).where(RolPermiso.id_rol==3,RolPermiso.id_permiso==permission)); s.commit()
    response=client.get(BASE+'/1',headers=headers) if operation=='view' else client.post(
        BASE+('/1/release' if operation=='release' else ''),headers={**headers,'Idempotency-Key':'b06-denied-0001'},
        json={'expected_version':1} if operation=='release' else {'order_ids':ids})
    assert response.status_code==403,response.text


@pytest.mark.parametrize('data',[{}, {'order_ids':[]},{'order_ids':[True]},{'order_ids':['1']},
    {'order_ids':[1,1]},{'order_ids':[-1]},{'order_ids':[2147483648]}, {'order_ids':[1],'method':'FF'}])
def test_invalid_request_has_no_acceptance(api,session_factory,data):
    client,_,_,headers,_,_=api
    response=client.post(BASE,json=data,headers={**headers,'Idempotency-Key':'b06-invalid-0001'})
    assert response.status_code==422,response.text
    with session_factory() as s: assert s.scalar(select(func.count()).select_from(Optimizacion))==0


def test_concurrent_idempotency_lot_conflict_and_shared_admission(api,session_factory):
    client,actor,ids,headers,coordinator,_=api
    lease=coordinator.admission.acquire(actor)
    response=client.post(BASE,json={'order_ids':ids},headers={**headers,'Idempotency-Key':'b06-idempotent-0001'})
    assert response.status_code==503
    lease.release()
    def posted(): return client.post(BASE,json={'order_ids':ids},headers={**headers,'Idempotency-Key':'b06-idempotent-0001'})
    with ThreadPoolExecutor(2) as pool:
        responses=[f.result(15) for f in [pool.submit(posted),pool.submit(posted)]]
    assert [r.status_code for r in responses]==[201,201]
    assert len({r.json()['comparison_id'] for r in responses})==1
    path=responses[0].headers['location']; completed(api,path)
    assert client.post(BASE,json={'order_ids':ids[:1]},headers={**headers,'Idempotency-Key':'b06-idempotent-0001'}).status_code==409
    with session_factory() as s: assert s.scalar(select(func.count()).select_from(EjecucionOptimizacion))==6


def test_other_actor_cannot_read_events_masks_or_release(api,create_user):
    client,_,_,headers,_,_=api
    path,_=start(api); current=completed(api,path)
    foreign=create_user('O73000002')
    theirs={'Authorization':'Bearer '+create_access_token(foreign,'O73000002','Operario')}
    eid=current.executions[0].execution_id
    for suffix in ('',f'/executions/{eid}','/events',f'/executions/{eid}/visual',f'/executions/{eid}/visual/masks/'+'a'*32):
        assert client.get(path+suffix,headers=theirs).status_code==404
    assert client.get(BASE+'/requests/b06-real-comparison-0001',headers=theirs).status_code==404
    assert client.post(path+'/release',json={'expected_version':current.version},headers=theirs).status_code==404
    assert client.get(path,headers=headers).status_code==200


@pytest.mark.parametrize('reason,limits',[
    ('EXPANSION_LIMIT',BeamSearchLimits(max_expansions=1)),('GEOMETRY_PROBE_LIMIT',BeamSearchLimits(max_geometry_probes=1)),
    ('STATE_MEMORY_LIMIT',BeamSearchLimits(max_state_bytes=1)),('TIME_LIMIT',BeamSearchLimits(seconds=.000001))])
def test_native_m6_partial_diagnostic_http_roundtrip(api,reason,limits):
    client,_,_,headers,coordinator,_=api
    coordinator.runner_factory=partial(SequentialProcessRunner,worker_target=partial(limited_beam,limits=limits))
    path,_=start(api); current=completed(api,path)
    execution=current.executions[-1]
    response=client.get(f'{path}/executions/{execution.execution_id}',headers=headers)
    value=ExecutionResponseV2.model_validate(response.json())
    assert value.execution.outcome=='PARTIAL' and value.execution.diagnostic.termination_reason==reason
    assert value.result.termination_reason==reason and not value.execution.eligible
    assert all(u.reason=='RESOURCE_LIMIT' for u in value.result.unplaced_units)
    save_evidence(reason.lower(),response.json())


def test_failed_engine_does_not_hide_other_five(api):
    client,_,_,headers,coordinator,_=api
    coordinator.runner_factory=partial(SequentialProcessRunner,worker_target=crash_hf)
    path,_=start(api); current=completed(api,path)
    assert [e.complete for e in current.executions]==[True,True,True,False,True,True]
    hf=current.executions[3]
    failure=client.get(f'{path}/executions/{hf.execution_id}',headers=headers).json()
    assert failure['result'] is None and failure['execution']['metrics'] is None
    assert failure['execution']['diagnostic']['origin']=='SUPERVISOR'
    save_evidence('failed-engine',dict(summary=current.model_dump(mode='json'),execution=failure))


def test_global_deadline_identifies_never_started(api):
    client,_,_,headers,coordinator,_=api
    policy=SequentialPolicy(budget=replace(ComparisonBudget(),global_seconds=2))
    coordinator.runner_factory=partial(SequentialProcessRunner,policy=policy,worker_target=started_then_blocked)
    path,_=start(api); current=completed(api,path)
    assert all(e.diagnostic.termination_reason=='GLOBAL_TIME_LIMIT' for e in current.executions)
    assert all(e.diagnostic.statistics['runtime_dispatched']==0 for e in current.executions[1:])
    assert all(client.get(f'{path}/executions/{e.execution_id}',headers=headers).status_code==200 for e in current.executions)
    save_evidence('global-deadline',current.model_dump(mode='json'))


def test_cursor_expiry_snapshot_recovery_and_observer_limit(api):
    client,_,_,headers,coordinator,_=api
    path,_=start(api); finished=completed(api,path); job=coordinator.job
    assert client.get(path+'/events?after_sequence=99999999',headers=headers).status_code==422
    observer=job.observe(); slow=job.lines(0,observer)
    job.event_limit=512  # Lower this test's retention only, to exercise actual eviction.
    for _ in range(5): job.emit(None,'heartbeat',{})
    assert job.event_bytes<=512
    assert ComparisonEventV2.model_validate_json(next(slow)).event=='snapshot_required'
    slow.close(); observer.release()
    expired=client.get(path+'/events?after_sequence=0',headers=headers)
    assert expired.status_code==409 and expired.json()['detail']['code']=='EVENT_CURSOR_EXPIRED'
    assert client.get(path,headers=headers).json()==finished.model_dump(mode='json')
    one,two=job.observe(),job.observe()
    try: assert client.get(path+f'/events?after_sequence={job.sequence}',headers=headers).status_code==503
    finally: one.release(); two.release()
    observer=job.observe(); iterator=job.lines(job.sequence-1,observer)
    next(iterator); iterator.close(); observer.release()
    assert job.observers==0 and not job.cancel.is_set()
    job.finished_at=time.monotonic()-301
    assert client.get(path+'/events',headers=headers).status_code==410
    assert job.event_bytes==0 and not job.store.contexts
    assert client.get(path,headers=headers).status_code==200


def test_release_requires_safe_close_versions_and_preserves_results(api,session_factory):
    client,_,_,headers,_,_=api
    before=inventory(session_factory)
    path,_=start(api); current=completed(api,path)
    assert client.post(path+'/release',json={'expected_version':current.version-1},headers=headers).status_code==409
    response=client.post(path+'/release',json={'expected_version':current.version},headers=headers)
    assert response.status_code==200,response.text
    released=ComparisonSummaryV2.model_validate(response.json())
    assert released.released and not released.selection_allowed and not any(e.eligible for e in released.executions)
    assert client.post(path+'/release',json={'expected_version':current.version},headers=headers).json()==response.json()
    assert all(client.get(f'{path}/executions/{e.execution_id}',headers=headers).status_code==200 for e in current.executions)
    assert inventory(session_factory)==before


def test_uncertain_restart_blocks_aggregate_and_keeps_durable_results_accessible(api):
    from decimal import Decimal
    from app.modules.optimization.application.engine_execution import EngineExecutionAdapter,ExecutionScope
    client,actor,ids,headers,coordinator,uow=api
    accepted=AcceptComparisonV2(uow,authorize_actor).execute(ids,actor,'b06-ambiguous-0001')
    with uow() as tx:
        tx.comparisons_v2.claim_supervisor(accepted.comparison_id,uuid4().hex,{'pid':2147483647,'start_ticks':'1'})
        token=tx.comparisons_v2.get(accepted.comparison_id).runtime['supervisor']['token']
        tx.comparisons_v2.record_worker(accepted.comparison_id,accepted.executions[0].execution_id,token,None)
    first=accepted.executions[0]
    native=EngineExecutionAdapter('FF').execute(ExecutionScope(comparison_id=accepted.comparison_id,
        execution_id=first.execution_id,method='FF'),accepted.problem,
        minimum_width_mm=Decimal(1),minimum_height_mm=Decimal(1))
    with uow() as tx:
        current=tx.comparisons_v2.get(accepted.comparison_id)
        current=tx.comparisons_v2.set_dispatch_state(current.comparison_id,first.execution_id,'STARTING',current.version)
        current=tx.comparisons_v2.set_dispatch_state(current.comparison_id,first.execution_id,'RUNNING',current.version)
        tx.comparisons_v2.save_execution(current.comparison_id,first.execution_id,native.payload,native.residuals,current.version)
    path=BASE+f'/{accepted.comparison_id}'
    blocked=client.get(path,headers=headers)
    assert blocked.status_code==503 and blocked.json()['detail']['code']=='RECOVERY_BLOCKED'
    assert coordinator.admission.active()==1
    response=client.get(path+f'/executions/{accepted.executions[0].execution_id}',headers=headers)
    assert response.status_code==200 and response.headers['X-Comparison-Recovery']=='BLOCKED'
    assert not response.json()['execution']['eligible'] and response.json()['result']['completo']
    assert response.json()['execution']['metrics'] is not None
    assert client.post(path+'/release',json={'expected_version':accepted.version},headers=headers).status_code==503
    assert all(secret not in blocked.text for secret in ('start_ticks','runtime_version','/proc','Traceback'))
    save_evidence('ambiguous-recovery',dict(aggregate=blocked.json(),execution=response.json(),
        recovery_header=response.headers['X-Comparison-Recovery'],admission_active=coordinator.admission.active()))


def test_v1_profile_key_conflicts_and_legacy_read_without_conversion(api):
    from app.modules.optimization.application.comparisons import AcceptComparison
    from app.modules.optimization.infrastructure.comparison_uow import SqlComparisonUnitOfWork
    client,actor,ids,headers,_,uow=api
    legacy_uow=partial(SqlComparisonUnitOfWork,uow.args[0])
    v1=AcceptComparison(legacy_uow).execute(ids,actor,'b06-profile-conflict-0001')
    response=client.post(BASE,json={'order_ids':ids},headers={**headers,'Idempotency-Key':'b06-profile-conflict-0001'})
    assert response.status_code==409
    assert client.get(BASE+f'/{v1.comparison_id}',headers=headers).json()['detail']['code']=='COMPARISON_PROFILE_MISMATCH'


def test_no_selection_confirmation_or_alternative_routes_are_published(api):
    paths=app.openapi()['paths']
    assert BASE in paths
    assert not any(path.startswith(BASE) and path.endswith(('/selection','/confirm')) for path in paths)
    assert BASE+'/{comparison_id}/executions/{execution_id}' in paths


def test_two_comparisons_keep_result_ownership_and_retire_one_visual_window(api):
    client,_,ids,headers,coordinator,_=api
    first=client.post(BASE,json={'order_ids':ids[:1]},headers={**headers,'Idempotency-Key':'b06-scope-first-0001'})
    assert first.status_code==201
    first_path=first.headers['location']; one=completed(api,first_path); old_job=coordinator.job
    second=client.post(BASE,json={'order_ids':ids[1:]},headers={**headers,'Idempotency-Key':'b06-scope-second-0001'})
    assert second.status_code==201
    second_path=second.headers['location']; two=completed(api,second_path)
    assert not old_job.events and not old_job.store.contexts and old_job.disposed
    assert client.get(first_path,headers=headers).json()==one.model_dump(mode='json')
    assert client.get(first_path+'/events',headers=headers).status_code==410
    assert client.get(second_path+f'/executions/{one.executions[0].execution_id}',headers=headers).status_code==404
    assert len({e.execution_id for e in one.executions+two.executions})==12


def test_failed_http_projection_does_not_cancel_or_rewrite_results(api):
    client,_,_,headers,coordinator,_=api
    class FailedProjection(HttpComparisonJob):
        def record(self,signal,data):
            if signal.kind=='observation': raise ConnectionError('controlled HTTP projection failure')
            return super().record(signal,data)
    coordinator.job_factory=FailedProjection
    path,_=start(api); current=completed(api,path)
    assert all(e.complete for e in current.executions)
    assert all(client.get(path+f'/executions/{e.execution_id}',headers=headers).status_code==200 for e in current.executions)
    events=client.get(path+'/events',headers=headers)
    assert events.status_code==200
    values=[ComparisonEventV2.model_validate_json(line) for line in events.iter_lines()]
    assert values[-1].event=='comparison_finished'
    assert sum(e.event=='result_persisted' for e in values)<6  # Missing history is not manufactured.
    assert not coordinator.job.cancel.is_set()


def test_one_connection_suffices_for_auth_capture_observation_and_query(api,session_factory):
    from sqlalchemy import create_engine
    client,_,_,headers,coordinator,_=api
    original=session_factory.kw['bind']
    engine=create_engine(original.url,pool_size=1,max_overflow=0,pool_timeout=1)
    session_factory.configure(bind=engine)
    try:
        path,_=start(api); current=completed(api,path)
        assert all(e.complete for e in current.executions)
        assert client.get(path+'/events',headers=headers).status_code==200
        assert engine.pool.checkedout()==0
    finally:
        coordinator.shutdown()
        session_factory.configure(bind=original); engine.dispose()
