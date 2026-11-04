"""B05 real PostgreSQL + Linux spawn; no v2 HTTP route or algorithm substitutes."""
from concurrent.futures import ThreadPoolExecutor
import asyncio
from dataclasses import replace
from functools import partial
import json
import os
from pathlib import Path
from threading import Barrier, Event
from uuid import uuid4

import pytest
from sqlalchemy import event, func, select

from app.models import (Configuracion, EjecucionOptimizacion, MetricaEjecucion,
    MovimientoInventario, Optimizacion, Pedido, Plancha, Retazo)
from app.modules.optimization.application.admission import OptimizerBusy
from app.modules.optimization.application.comparison_acceptance_v2 import AcceptComparisonV2
from app.modules.optimization.application.comparison_catalog import METHODS_V2
from app.modules.optimization.application.comparison_limits import ComparisonBudget
from app.modules.optimization.application.errors import RunError
from app.modules.optimization.application.sequential_policy import SequentialPolicy
from app.modules.optimization.domain.beam_search import BeamSearchLimits
from app.modules.optimization.infrastructure.comparison_v2_uow import SqlComparisonPersistenceUnitOfWork
from app.modules.optimization.infrastructure.in_process_admission import InProcessRunAdmission
from app.modules.optimization.infrastructure.process_lifecycle import process_identity
from app.modules.optimization.infrastructure.sequential_runner import SequentialProcessRunner
from app.modules.optimization.infrastructure.comparison_snapshot import encode_problem
from app.modules.optimization.presentation.comparison_supervision_v2 import ComparisonV2Coordinator, authorize_actor
from tests.unit.optimization.test_sequential_runner import crash_hf, oversize_hf, limited_beam, started_then_blocked
from .test_runs import prepared  # noqa: F401


@pytest.fixture
def setup(session_factory, prepared):
    actor, ids, _ = prepared
    return actor, ids, partial(SqlComparisonPersistenceUnitOfWork,session_factory)


def inventory(factory):
    with factory() as session:
        return dict(sheets=[(p.id_plancha,p.cantidad) for p in session.scalars(select(Plancha))],
            remnants=session.scalar(select(func.count()).select_from(Retazo)),
            movements=session.scalar(select(func.count()).select_from(MovimientoInventario)))


def wait_closed(coordinator):
    job=coordinator.job
    assert job.closed.wait(35), (job.error_type,job.unsafe,job.runner.last_report)
    job.thread.join(1); job.reaper.join(1)
    assert not job.thread.is_alive() and not job.reaper.is_alive()
    assert coordinator.admission.active()==0
    assert job.runner.last_report['all_workers_stopped']
    assert job.runner.last_report['maximum_active_workers']==1
    for state in job.runner.last_report['executions'].values():
        if state['identity'] is not None:
            assert process_identity(state['identity']['pid']) != state['identity']
        assert not state.get('descendants_after')
    with coordinator.uow() as tx:
        current=tx.comparisons_v2.get(job.comparison.comparison_id)
    assert current.terminal and current.supervisor_stopped
    return current


def evidence(name, coordinator, current, **extra):
    destination=os.environ.get('NEWGLASS_B05_EVIDENCE_DIR')
    if not destination: return
    report=dict(comparison_id=current.comparison_id,input_sha256=current.input_sha256,
        problem=encode_problem(current.problem),methods=current.methods,configuration_id=current.configuration_id,
        configuration_version=current.configuration_version,angular_step_deg=str(current.problem.config.angular_step_deg),
        states=[dict(execution_id=e.execution_id,method=e.method,status=e.status,dispatch=e.dispatch_state,
            complete=bool(e.result and e.result.complete),diagnostic=e.diagnostic.public(),
            placed_units=e.result.placed_units if e.result else None) for e in current.executions],
        timeline=coordinator.job.timeline,processes=coordinator.job.runner.last_report,
        retained_event_bytes=coordinator.job.event_bytes,
        retained_visual_bytes=sum(s.charged_bytes for s in coordinator.job.sessions.values()),**extra)
    (Path(destination)/f'{name}.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')


def test_common_capture_independent_commits_external_join_and_no_consumption(session_factory,setup):
    actor,ids,uow=setup
    admission=InProcessRunAdmission()
    coordinator=ComparisonV2Coordinator(uow,admission)
    before=inventory(session_factory)
    hashes,commits,dispatch,reads=[],[],[],[]
    def sql(conn,cursor,statement,params,context,many):
        if 'UNION ALL' in statement and 'planchas' in statement: reads.append(statement)
    def sink(signal):
        if signal.kind=='dispatching': dispatch.append(signal.method)
        if signal.kind=='ready': hashes.append(signal.payload['input_sha256'])
        if signal.kind=='result_persisted':
            with uow() as tx: loaded=tx.comparisons_v2.get(signal.comparison_id)
            own=next(e for e in loaded.executions if e.execution_id==signal.execution_id)
            assert own.result==signal.payload.result and not loaded.supervisor_stopped
            assert admission.active()==1 and coordinator.job.thread.is_alive()
            commits.append(signal.method)
    engine=session_factory.kw['bind']
    event.listen(engine,'before_cursor_execute',sql)
    try:
        accepted=coordinator.start(ids,actor,'b05-six-real-0001',sink=sink)
        repeated=coordinator.start(ids,actor,'b05-six-real-0001')
        assert repeated.comparison_id==accepted.comparison_id
        with pytest.raises(OptimizerBusy): admission.acquire(actor+1)
        with pytest.raises(OptimizerBusy): admission.acquire_comparison(actor+1)
        current=wait_closed(coordinator)
    finally:
        coordinator.shutdown()
        event.remove(engine,'before_cursor_execute',sql)
    assert dispatch==commits==list(METHODS_V2)
    assert hashes==[accepted.input_sha256]*6 and len(reads)==1
    assert len({e.execution_id for e in current.executions})==6
    assert all(e.eligible and e.result.problem==accepted.problem for e in current.executions)
    assert all(e.diagnostic.termination_reason=='COMPLETED' for e in current.executions)
    assert current.selected_execution_id is None and inventory(session_factory)==before
    assert coordinator.start(ids,actor,'b05-six-real-0001')==current
    with session_factory() as s:
        assert all(s.get(Pedido,i).estado=='OPTIMIZADO' for i in ids)
        assert s.scalar(select(func.count()).select_from(EjecucionOptimizacion))==6
    kinds=[entry['kind'] for entry in coordinator.job.timeline]
    assert kinds.index('supervisor_returning')<kinds.index('supervisor_joined')<kinds.index('processes_verified')<kinds.index('safe_close_committed')<kinds.index('admission_released')
    assert coordinator.job.runner.retention.bytes=={'visual':0,'event':0}
    refs=[r for e in current.executions for r in e.visual_references]
    assert refs and len({r.mask_ref for r in refs})==len(refs)
    with uow() as tx, pytest.raises(RunError):
        tx.comparisons_v2.get_visual_reference(current.comparison_id,current.executions[-1].execution_id,refs[0].mask_ref)
    evidence('six-real',coordinator,current,inventory_before=before,inventory_after=inventory(session_factory),committed_methods=commits)


def test_concurrent_acceptance_freezes_once_and_rolls_back_invalid_requests(session_factory,setup):
    actor,ids,uow=setup
    gate=Barrier(2)
    def accept():
        gate.wait(5)
        return AcceptComparisonV2(uow,authorize_actor).execute(ids,actor,'b05-concurrent-0001')
    with ThreadPoolExecutor(2) as pool:
        futures=[pool.submit(accept) for _ in range(2)]
        left,right=[f.result(15) for f in futures]
    assert left==right
    with session_factory() as s:
        s.get(Plancha,5).cantidad=0
        s.scalar(select(Configuracion)).margen_mm=1
        s.commit()
    assert AcceptComparisonV2(uow,authorize_actor).execute(ids,actor,'b05-concurrent-0001')==left
    with pytest.raises(RunError): AcceptComparisonV2(uow,authorize_actor).execute(ids[:1],actor,'b05-concurrent-0001')
    with uow() as tx: assert tx.comparisons_v2.get(left.comparison_id)==left
    with session_factory() as s: assert s.scalar(select(func.count()).select_from(Optimizacion))==1


@pytest.mark.parametrize('target',[crash_hf,oversize_hf])
def test_local_process_and_ipc_failure_preserve_other_five(setup,target):
    actor,ids,uow=setup
    coordinator=ComparisonV2Coordinator(uow,InProcessRunAdmission(),runner_factory=partial(SequentialProcessRunner,worker_target=target))
    try:
        coordinator.start(ids,actor,'b05-local-failure-0001')
        current=wait_closed(coordinator)
    finally: coordinator.shutdown()
    assert [e.eligible for e in current.executions]==[True,True,True,False,True,True]
    assert current.executions[3].result is None
    assert current.executions[3].diagnostic.origin=='SUPERVISOR'
    evidence(target.__name__,coordinator,current)


def test_database_write_failure_does_not_emit_false_persistence(session_factory,setup):
    actor,ids,uow=setup
    signals=[]
    def fail(session,context,instances):
        for obj in session.new:
            if isinstance(obj,MetricaEjecucion):
                execution=session.get(EjecucionOptimizacion,obj.id_ejecucion)
                if execution.metodo=='HF': raise RuntimeError('controlled B05 metric transaction failure')
    event.listen(session_factory.class_,'before_flush',fail)
    coordinator=ComparisonV2Coordinator(uow,InProcessRunAdmission())
    try:
        coordinator.start(ids,actor,'b05-write-failure-0001',sink=signals.append)
        current=wait_closed(coordinator)
    finally:
        coordinator.shutdown(); event.remove(session_factory.class_,'before_flush',fail)
    assert [e.eligible for e in current.executions]==[True,True,True,False,True,True]
    assert current.executions[3].diagnostic.termination_reason=='RESULT_SAVE_FAILED'
    assert not any(s.method=='HF' and s.kind=='result_persisted' for s in signals)
    assert any(s.method=='HF' and s.kind=='execution_failed' for s in signals)
    evidence('write-failure',coordinator,current)


@pytest.mark.parametrize('mode',['disconnected','blocked'])
def test_observer_cannot_release_admission_while_supervisor_alive(setup,mode):
    actor,ids,uow=setup
    arrived,resume=Event(),Event()
    def observer(signal):
        if mode=='disconnected': raise ConnectionError('controlled disconnected observer')
        if signal.kind=='result_persisted' and signal.method=='FF':
            arrived.set(); assert resume.wait(10)
    admission=InProcessRunAdmission(); coordinator=ComparisonV2Coordinator(uow,admission)
    try:
        coordinator.start(ids,actor,'b05-observer-test-0001',sink=observer)
        if mode=='blocked':
            assert arrived.wait(10)
            assert coordinator.job.thread.is_alive() and admission.active()==1
            assert not coordinator._close(coordinator.job)
            with pytest.raises(OptimizerBusy): admission.acquire(actor+1)
            resume.set()
        current=wait_closed(coordinator)
    finally: resume.set(); coordinator.shutdown()
    assert all(e.eligible for e in current.executions)
    evidence(mode,coordinator,current)


@pytest.mark.parametrize('reason,limits',[
    ('EXPANSION_LIMIT',BeamSearchLimits(max_expansions=1)),
    ('GEOMETRY_PROBE_LIMIT',BeamSearchLimits(max_geometry_probes=1)),
    ('STATE_MEMORY_LIMIT',BeamSearchLimits(max_state_bytes=1)),
    ('TIME_LIMIT',BeamSearchLimits(seconds=0.000001)),
])
def test_native_m6_diagnostic_survives_process_and_database(setup,reason,limits):
    actor,ids,uow=setup
    factory=partial(SequentialProcessRunner,worker_target=partial(limited_beam,limits=limits))
    coordinator=ComparisonV2Coordinator(uow,InProcessRunAdmission(),runner_factory=factory)
    try:
        coordinator.start(ids,actor,'b05-native-beam-0001'); current=wait_closed(coordinator)
    finally: coordinator.shutdown()
    beam=current.executions[-1]
    assert beam.diagnostic.origin=='ENGINE' and beam.diagnostic.termination_reason==reason
    assert beam.result is not None and not beam.result.complete and not beam.eligible
    assert all(e.eligible for e in current.executions[:-1])
    evidence(reason.lower(),coordinator,current)


@pytest.mark.parametrize('mode',['deadline','shutdown'])
def test_global_abort_and_shutdown_close_never_started_workers(session_factory,setup,mode):
    actor,ids,uow=setup
    started=Event()
    budget=replace(ComparisonBudget(),global_seconds=2)
    coordinator=ComparisonV2Coordinator(uow,InProcessRunAdmission(),runner_factory=partial(SequentialProcessRunner,
        policy=SequentialPolicy(budget=budget),worker_target=started_then_blocked))
    try:
        coordinator.start(ids,actor,'b05-global-abort-0001',sink=lambda s:started.set() if s.kind=='started' else None)
        if mode=='shutdown':
            assert started.wait(5); coordinator.shutdown()
        current=wait_closed(coordinator)
    finally: coordinator.shutdown()
    assert not any(e.eligible for e in current.executions)
    assert all(e.diagnostic.termination_reason==('GLOBAL_TIME_LIMIT' if mode=='deadline' else 'CANCELLED') for e in current.executions)
    assert all(e.diagnostic.statistics['runtime_dispatched']==0 for e in current.executions[1:])
    with session_factory() as s: assert all(s.get(Pedido,i).estado=='PENDIENTE' for i in ids)
    evidence(mode,coordinator,current)


def test_failed_closure_commit_keeps_lease_until_successful_retry(session_factory,setup):
    actor,ids,uow=setup
    attempted=Event()
    def fail(session,context,instances):
        if any(isinstance(o,Optimizacion) and o.fecha_fin is not None for o in session.dirty):
            attempted.set(); raise RuntimeError('controlled close transaction failure')
    event.listen(session_factory.class_,'before_flush',fail)
    coordinator=ComparisonV2Coordinator(uow,InProcessRunAdmission())
    try:
        accepted=coordinator.start(ids,actor,'b05-close-failure-0001')
        assert attempted.wait(30)
        coordinator.job.reaper.join(5)
        assert not coordinator.job.thread.is_alive() and not coordinator.job.closed.is_set()
        assert coordinator.admission.active()==1
        with uow() as tx:
            current=tx.comparisons_v2.get(accepted.comparison_id)
            assert not current.supervisor_stopped and all(e.eligible for e in current.executions)
    finally: event.remove(session_factory.class_,'before_flush',fail)
    try:
        assert coordinator._close(coordinator.job)
        current=wait_closed(coordinator)
    finally: coordinator.shutdown()
    evidence('closure-retry',coordinator,current)


@pytest.mark.parametrize('owner_state',['dead','live','reused_pid','unknown','spawn_intent','dead_worker'])
def test_recovery_requires_process_identity_proof_without_recalculation(session_factory,setup,owner_state):
    actor,ids,uow=setup
    accepted=AcceptComparisonV2(uow,authorize_actor).execute(ids,actor,'b05-recovery-0001')
    own=process_identity(os.getpid()); token=uuid4().hex
    absent=dict(pid=2147483647,start_ticks='1')
    expected=own if owner_state=='live' else dict(pid=own['pid'],start_ticks=str(int(own['start_ticks'])-1)) if owner_state=='reused_pid' else absent
    with uow() as tx:
        if owner_state=='unknown':
            row=tx.session.get(Optimizacion,accepted.comparison_id)
            row.comparison_snapshot={**row.comparison_snapshot,'runtime':{'supervisor_stopped_at':None}}
        else:
            assert tx.comparisons_v2.claim_supervisor(accepted.comparison_id,token,expected)
            if owner_state=='spawn_intent': tx.comparisons_v2.record_worker(accepted.comparison_id,accepted.executions[0].execution_id,token,None)
            if owner_state=='dead_worker': tx.comparisons_v2.record_worker(accepted.comparison_id,accepted.executions[0].execution_id,token,absent)
    coordinator=ComparisonV2Coordinator(uow,InProcessRunAdmission())
    proven=owner_state in ('dead','reused_pid')
    assert coordinator.recover_pending()==proven
    assert coordinator.admission.active()==(0 if proven else 1)
    with uow() as tx:
        current=tx.comparisons_v2.get(accepted.comparison_id)
        assert current.terminal==proven
        assert all(e.result is None for e in current.executions)
    assert process_identity(own['pid'])==own  # No killing a reused PID or another session.


def test_legacy_admission_and_preflight_reject_before_acceptance(session_factory,setup):
    actor,ids,uow=setup
    admission=InProcessRunAdmission(); lease=admission.acquire(actor)
    coordinator=ComparisonV2Coordinator(uow,admission)
    with pytest.raises(OptimizerBusy): coordinator.start(ids,actor,'b05-no-overlap-0001')
    lease.release()
    class RejectedRunner(SequentialProcessRunner):
        def preflight(self): raise RunError('RESOURCE_UNAVAILABLE','controlled unsupported platform')
    coordinator.runner_factory=RejectedRunner
    with pytest.raises(RunError): coordinator.start(ids,actor,'b05-no-overlap-0001')
    assert admission.active()==0
    with session_factory() as s: assert s.scalar(select(func.count()).select_from(Optimizacion))==0


def test_v1_external_owner_commits_after_join_and_shared_retention_handoff(setup):
    from app.modules.optimization.application.comparisons import AcceptComparison
    from app.modules.optimization.infrastructure.comparison_uow import SqlComparisonUnitOfWork
    from app.modules.optimization.presentation.comparison_runtime import ComparisonRuntime
    from app.modules.optimization.presentation.comparison_retention import ComparisonRetention
    actor,ids,uow=setup
    legacy_uow=partial(SqlComparisonUnitOfWork,uow.args[0])
    retention=ComparisonRetention(); admission=InProcessRunAdmission()
    runtime=ComparisonRuntime(retention=retention)
    lease=admission.acquire_comparison(actor)
    job=runtime.reserve()
    accepted=AcceptComparison(legacy_uow).execute(ids,actor,'b05-v1-owner-0001')
    releases=[]
    class VerifiedLease:
        def release(self):
            with legacy_uow() as tx: current=tx.comparisons.get(accepted.comparison_id)
            releases.append((job.thread.is_alive(),current.terminal,job.finished))
            lease.release()
    try:
        runtime.start(job,accepted,legacy_uow,VerifiedLease())
        job.thread.join(20); job.reaper.join(5)
        assert releases==[(False,True,True)] and admission.active()==0
        assert job.finished and job.records and any(s.records for s in job.sessions.values())
        following=runtime.reserve()  # Same handoff also used by the v2 composition.
        assert not job.records and not job.store.contexts
        runtime.abort(following)
        assert retention.owner is None
    finally: runtime.shutdown()


def test_fastapi_lifespan_recovers_and_shuts_down_real_v2_without_routes(setup,monkeypatch):
    import main
    from app.modules.optimization.presentation import comparison_supervision_v2 as composition
    actor,ids,uow=setup
    started=Event()
    coordinator=ComparisonV2Coordinator(uow,InProcessRunAdmission(),runner_factory=partial(
        SequentialProcessRunner,worker_target=started_then_blocked))
    monkeypatch.setattr(composition,'get_comparison_v2_coordinator',lambda:coordinator)
    async def lifecycle():
        async with main.lifespan(main.app):
            coordinator.start(ids,actor,'b05-lifespan-0001',sink=lambda s:started.set() if s.kind=='started' else None)
            assert await asyncio.to_thread(started.wait,5)
    asyncio.run(lifecycle())
    assert wait_closed(coordinator).terminal
    assert not any('comparisons-v2' in path for path in main.app.openapi()['paths'])


def test_spawn_failure_keeps_other_engines_and_closes_spawn_intent(setup,monkeypatch):
    from multiprocessing.context import SpawnProcess
    original=SpawnProcess.start
    def fail_first(process):
        if process.name=='comparison-v2-FF': raise OSError('controlled process start failure')
        return original(process)
    monkeypatch.setattr(SpawnProcess,'start',fail_first)
    actor,ids,uow=setup
    coordinator=ComparisonV2Coordinator(uow,InProcessRunAdmission())
    try:
        coordinator.start(ids,actor,'b05-spawn-failure-0001'); current=wait_closed(coordinator)
    finally: coordinator.shutdown()
    assert [e.eligible for e in current.executions]==[False,True,True,True,True,True]
    assert current.executions[0].diagnostic.termination_reason=='PROCESS_START_FAILED'
    assert current.runtime['workers'][str(current.executions[0].execution_id)] is None
    evidence('spawn-failure',coordinator,current)


def test_owner_allocation_failure_after_acceptance_keeps_operational_block(setup,monkeypatch):
    from app.modules.optimization.presentation import comparison_supervision_v2 as composition
    def exhausted(*args,**kwargs): raise MemoryError('controlled owner allocation failure')
    monkeypatch.setattr(composition,'SupervisedJob',exhausted)
    actor,ids,uow=setup
    coordinator=ComparisonV2Coordinator(uow,InProcessRunAdmission())
    with pytest.raises(MemoryError): coordinator.start(ids,actor,'b05-owner-allocation-0001')
    assert coordinator.job is None and coordinator.admission.active()==1
    assert not coordinator.recover_pending()
    with uow() as tx:
        current=tx.comparisons_v2.find_by_key(actor,'b05-owner-allocation-0001')
        assert not current.terminal and len(current.executions)==6
        assert current.runtime['supervisor'] is None and not current.runtime['workers']


def test_recovery_on_unsupported_platform_keeps_block_without_pid_inference(setup):
    actor,ids,uow=setup
    accepted=AcceptComparisonV2(uow,authorize_actor).execute(ids,actor,'b05-recovery-platform-0001')
    with uow() as tx:
        tx.comparisons_v2.claim_supervisor(accepted.comparison_id,uuid4().hex,dict(pid=2147483647,start_ticks='1'))
    class Unsupported(SequentialProcessRunner):
        def preflight(self): raise RunError('RESOURCE_UNAVAILABLE','controlled unsupported process platform')
    coordinator=ComparisonV2Coordinator(uow,InProcessRunAdmission(),runner_factory=Unsupported)
    assert not coordinator.recover_pending() and coordinator.admission.active()==1
    with uow() as tx: assert not tx.comparisons_v2.get(accepted.comparison_id).terminal
