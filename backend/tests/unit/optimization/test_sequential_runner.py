"""T-04/T-05 B04 primitives, real Linux spawn and bounded negative scenarios."""
from dataclasses import asdict, replace
from decimal import Decimal
from functools import partial
import json
import multiprocessing as mp
import os
import signal
from pathlib import Path
import time

import pytest

from app.modules.optimization.application.comparison_limits import ComparisonBudget, MIB
from app.modules.optimization.application.comparison_catalog import METHODS_V2
from app.modules.optimization.application.engine_execution import ExecutionScope
from app.modules.optimization.application.sequential_policy import SequentialPolicy, ObservationRetention
from app.modules.optimization.infrastructure import sequential_runner as runner
from app.modules.optimization.infrastructure.sequential_worker import calculation_worker_v2
from app.modules.optimization.infrastructure.process_lifecycle import process_identity, protect_against_parent_exit
from app.modules.optimization.infrastructure.comparison_snapshot import decode_problem

ROOT = Path(__file__).resolve().parents[4]


def inputs():
    frozen = json.loads((ROOT/'docs/evidence/sprint-02/TA-043/B03/adapter-validation.json').read_text())["problem"]
    return tuple(ExecutionScope(comparison_id=43, execution_id=4301+i, method=m) for i,m in enumerate(METHODS_V2)), decode_problem(frozen), (Decimal(1),Decimal(1))


def never_ready(*args):
    protect_against_parent_exit(args[-2])
    time.sleep(10)


def started_then_blocked(*args):
    scope,payload,minimums,connection,gate,clock,budget,checkpoint_cancel,parent,observed=args
    protect_against_parent_exit(parent)
    from app.modules.optimization.infrastructure.comparison_snapshot import problem_fingerprint
    connection.send_bytes(json.dumps(dict(scope=scope,kind="ready",data=dict(
        identity=process_identity(os.getpid()),input_sha256=problem_fingerprint(decode_problem(json.loads(payload)))))).encode())
    gate.wait(5); clock.value=time.monotonic()
    connection.send_bytes(json.dumps(dict(scope=scope,kind="started",data=dict(monotonic=clock.value))).encode())
    time.sleep(10)


def crash_hf(*args):
    if args[0]["method"]=="HF": os._exit(7)
    calculation_worker_v2(*args)


def oversize_hf(*args):
    if args[0]["method"]=="HF":
        protect_against_parent_exit(args[-2])
        args[3].send_bytes(b'x'*(args[6].packet_bytes+1))
    else: calculation_worker_v2(*args)


def excessive_memory_hf(*args):
    if args[0]["method"]=="HF":
        from app.modules.optimization.application import engine_execution
        def allocate(*a,**k): return bytearray(512*MIB)
        engine_execution.BY_METHOD["HF"].optimizer_type.optimize=allocate
    calculation_worker_v2(*args)


def limited_beam(*args,limits):
    if args[0]["method"]=="M6-BS":
        from app.modules.optimization.application import engine_execution
        original=engine_execution.EngineExecutionAdapter.__init__
        def init(self,method,**kwargs): original(self,method,beam_limits=limits)
        engine_execution.EngineExecutionAdapter.__init__=init
    calculation_worker_v2(*args)


def cooperative_cancel(*args):
    args[7].set()
    calculation_worker_v2(*args)


def blocked_observer_worker(*args):
    from app.modules.optimization.application import engine_execution
    original=engine_execution.EngineExecutionAdapter.execute
    def execute(self,*values,**kwargs):
        callback=kwargs['on_observation']
        def blocked(fact):
            callback(fact)
            time.sleep(10)
        kwargs['on_observation']=blocked
        return original(self,*values,**kwargs)
    engine_execution.EngineExecutionAdapter.execute=execute
    calculation_worker_v2(*args)


def dependent_sleep(parent):
    protect_against_parent_exit(parent)
    time.sleep(10)


def with_descendant(*args):
    child=mp.get_context('spawn').Process(target=dependent_sleep,args=(process_identity(os.getpid()),))
    child.start()
    time.sleep(.15)
    try: started_then_blocked(*args)
    finally:
        if child.is_alive(): child.terminate()
        child.join(2)


def test_checkpoint_cancel_runs_without_observation_and_exits_cleanly():
    service=runner.SequentialProcessRunner(worker_target=cooperative_cancel)
    values=service.calculate(*inputs(),observed=False)
    assert all(v.payload.result is None and v.payload.diagnostic.termination_reason=='CANCELLED' for v in values)
    assert all(s['exitcode']==0 and s['worker_report']['error_type']=='ExecutionInterrupted'
               for s in service.last_report['executions'].values())


def test_owned_descendant_is_accounted_and_stopped_on_close():
    service=runner.SequentialProcessRunner(worker_target=with_descendant)
    stream=service.events(*inputs())
    assert next(stream)['kind']=='ready'
    children=service.last_report['executions']['FF'].get('descendants',[])
    assert children
    stream.close()
    assert service.last_report['all_workers_stopped']
    assert not service.last_report['executions']['FF']['descendants_after']


def test_productive_six_are_sequential_isolated_and_stopped():
    service=runner.SequentialProcessRunner()
    values=service.calculate(*inputs())
    assert tuple(v.scope.method for v in values)==METHODS_V2
    assert all(v.payload.result and v.payload.result.complete for v in values)
    report=service.last_report
    assert report["maximum_active_workers"]==1 and report["all_workers_stopped"]
    assert report["maximum_queued_packets"]<=1 and report["maximum_packet_bytes"]<=12*MIB
    previous=None
    identities=[]
    for method,state in report["executions"].items():
        assert state["identity_after"] is None and state["exitcode"]==0
        identities.append(tuple(state["identity"].items()))
        if previous is not None: assert state["launched_monotonic"]>=previous["stopped_monotonic"]
        previous=state
    assert len(set(identities))==6
    scopes,_,_=inputs()
    assert service.retention.get('visual',scopes[0])
    assert not service.retention.get('visual',replace(scopes[0],comparison_id=999))


@pytest.mark.parametrize("change", [dict(max_active_workers=2),dict(max_active_workers=True),
    dict(methods=METHODS_V2[::-1]),dict(budget=replace(ComparisonBudget(),global_seconds=181))])
def test_policy_rejects_unapproved_concurrency_order_or_budget(change):
    with pytest.raises(ValueError): SequentialPolicy(**change)


def test_first_effective_deadline_and_queue_not_in_calculation_clock():
    policy=SequentialPolicy()
    assert policy.expired(179,0,170,175) is None
    assert policy.expired(181,0,170,175)=='GLOBAL_TIME_LIMIT'
    assert policy.expired(140,0,1,2)=='TIME_BUDGET_EXCEEDED'
    assert policy.expired(35,0,1,0)=='PROCESS_START_FAILED'


def test_individual_startup_is_bounded_without_dispatching_simultaneously():
    policy=SequentialPolicy(budget=replace(ComparisonBudget(),startup_seconds=.1,global_seconds=15))
    service=runner.SequentialProcessRunner(policy,worker_target=never_ready)
    values=service.calculate(*inputs())
    assert len(values)==6 and all(v.never_started and v.dispatched for v in values)
    assert all(v.payload.diagnostic.termination_reason=='PROCESS_START_FAILED' for v in values)
    assert service.last_report['all_workers_stopped']


def test_individual_calculation_includes_blocked_observer_wall_time():
    policy=SequentialPolicy(budget=replace(ComparisonBudget(),calculation_seconds=.1,global_seconds=30))
    service=runner.SequentialProcessRunner(policy,worker_target=blocked_observer_worker)
    values=service.calculate(*inputs())
    assert all(v.engine_started and v.payload.result is None for v in values)
    assert all(v.payload.diagnostic.termination_reason=='TIME_BUDGET_EXCEEDED' for v in values)


def test_global_deadline_marks_queued_never_dispatched_and_stops_while_consumer_is_paused():
    policy=SequentialPolicy(budget=replace(ComparisonBudget(),global_seconds=5))
    service=runner.SequentialProcessRunner(policy,worker_target=started_then_blocked)
    stream=service.events(*inputs())
    first=next(stream)
    assert first['kind']=='ready'
    identity=service.last_report['executions']['FF']['identity']
    time.sleep(5.2)
    # Independent watchdog already stopped the worker; no consumer progress needed.
    assert process_identity(identity['pid']) != identity or Path(f"/proc/{identity['pid']}/stat").read_text().split(') ')[1].startswith('Z ')
    values=[p['data'] for p in stream if p['kind']=='result']
    assert len(values)==6 and sum(v.dispatched for v in values)==1
    assert all(v.never_started and not v.dispatched for v in values[1:])
    assert all(v.payload.diagnostic.termination_reason=='GLOBAL_TIME_LIMIT' for v in values)


@pytest.mark.parametrize("target,reason", [(crash_hf,'EXECUTION_FAILED'),(oversize_hf,'EXECUTION_FAILED'),
                                        (excessive_memory_hf,'MEMORY_BUDGET_EXCEEDED')])
def test_fault_isolation_and_real_address_space_limit(target,reason):
    service=runner.SequentialProcessRunner(worker_target=target)
    values=service.calculate(*inputs(),observed=False)
    hole=next(v for v in values if v.scope.method=='HF')
    assert hole.payload.result is None and hole.payload.diagnostic.termination_reason==reason
    assert all(v.payload.result.complete for v in values if v.scope.method!='HF')
    assert service.last_report['all_workers_stopped']


def test_aggregate_rss_aborts_global_queue_with_real_processes(monkeypatch):
    policy=SequentialPolicy(budget=replace(ComparisonBudget(),aggregate_rss_bytes=
        runner.resident_bytes(os.getpid())+ComparisonBudget().helper_reserve_bytes+MIB))
    # Preflight capacity is checked separately; this test reaches the real RSS watchdog.
    service=runner.SequentialProcessRunner(policy,worker_target=never_ready)
    service.preflight=lambda:None
    values=service.calculate(*inputs())
    assert all(v.payload.diagnostic.termination_reason=='MEMORY_BUDGET_EXCEEDED' for v in values)
    assert service.last_report['maximum_aggregate_rss']>policy.budget.aggregate_rss_bytes
    assert service.last_report['all_workers_stopped']


def test_cancel_and_explicit_close_stop_owned_processes():
    cancel=mp.get_context('spawn').Event()
    service=runner.SequentialProcessRunner(worker_target=started_then_blocked)
    stream=service.events(*inputs(),cancel=cancel)
    assert next(stream)['kind']=='ready'
    cancel.set()
    values=[p['data'] for p in stream if p['kind']=='result']
    assert len(values)==6 and all(v.payload.diagnostic.termination_reason=='CANCELLED' for v in values)
    stream=service.events(*inputs())
    next(stream); stream.close()
    assert service.last_report['all_workers_stopped']
    assert all(s.get('identity_after') is None for s in service.last_report['executions'].values())


def test_same_instance_rejects_overlap_and_can_reuse_after_verified_close():
    service=runner.SequentialProcessRunner(worker_target=started_then_blocked)
    stream=service.events(*inputs())
    assert next(stream)['kind']=='ready'
    other=service.events(*inputs())
    with pytest.raises(Exception) as error: next(other)
    assert error.value.code=='OPTIMIZER_BUSY'
    stream.close()
    again=service.events(*inputs())
    assert next(again)['kind']=='ready'
    again.close()
    assert service.last_report['all_workers_stopped']


def test_retention_is_shared_byte_bounded_with_scoped_eviction():
    policy=replace(ComparisonBudget(),retained_event_bytes=8,retained_visual_bytes=12)
    retain=ObservationRetention(policy)
    scopes,_,_=inputs()
    for s in scopes: retain.append('event',s,b'abcd')
    assert retain.bytes['event']==8 and len(retain.records['event'])==2
    assert not retain.get('event',scopes[0]) and retain.get('event',scopes[-1])==(b'abcd',)
    assert not retain.append('visual',scopes[0],b'x'*13)
    assert retain.bytes['visual']==0


def test_retention_handoff_does_not_allocate_a_second_window():
    service=runner.SequentialProcessRunner()
    values=service.calculate(*inputs(),retain_observations=False)
    assert all(v.payload.result.complete for v in values)
    assert service.last_report['retained_bytes']==dict(visual=0,event=0)


def test_observer_transport_failure_is_explicit_and_does_not_change_solution():
    policy=SequentialPolicy(budget=replace(ComparisonBudget(),visual_packet_bytes=1))
    service=runner.SequentialProcessRunner(policy)
    values=service.calculate(*inputs())
    assert all(v.payload.result.complete for v in values)
    assert all(s['worker_report']['observer_error_type']=='ComparisonSnapshotError' for s in service.last_report['executions'].values())


def test_terminating_owned_worker_does_not_erase_other_five():
    service=runner.SequentialProcessRunner()
    stream=service.events(*inputs())
    assert next(stream)['kind']=='ready'
    identity=service.last_report['executions']['FF']['identity']
    assert process_identity(identity['pid'])==identity
    os.kill(identity['pid'],signal.SIGTERM)
    values=[p['data'] for p in stream if p['kind']=='result']
    assert len(values)==6 and values[0].payload.result is None
    assert all(v.payload.result.complete for v in values[1:])


@pytest.mark.parametrize('options,reason',[(dict(max_expansions=1),'EXPANSION_LIMIT'),
    (dict(max_geometry_probes=1),'GEOMETRY_PROBE_LIMIT'),(dict(max_state_bytes=1),'STATE_MEMORY_LIMIT'),
    (dict(seconds=.000000001),'TIME_LIMIT')])
def test_m6_native_resource_reason_survives_process_transport(options,reason):
    from app.modules.optimization.domain.beam_search import BeamSearchLimits
    values=runner.SequentialProcessRunner(worker_target=partial(limited_beam,limits=BeamSearchLimits(**options))).calculate(*inputs(),observed=False)
    assert values[-1].payload.result is not None and not values[-1].payload.result.complete
    assert values[-1].payload.diagnostic.termination_reason==reason
    assert values[-1].payload.diagnostic.origin=='ENGINE'


def test_preflight_rejects_before_process_creation(monkeypatch):
    monkeypatch.setattr('app.modules.optimization.infrastructure.comparison_runner.available_memory',lambda:0)
    with pytest.raises(Exception) as error: runner.SequentialProcessRunner().calculate(*inputs())
    assert error.value.code=='RESOURCE_UNAVAILABLE'
