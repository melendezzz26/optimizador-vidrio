"""Resource diagnostics, bounded deployment configuration and lossless IPC reuse."""
from dataclasses import replace
import json
from pathlib import Path

import pytest

from app.modules.optimization.application.comparison_limits import ComparisonBudget, MIB
from app.modules.optimization.application.errors import RunError
from app.modules.optimization.domain.raster_mask import RasterMask
from app.modules.optimization.domain.visual_events import VisualEvent
from app.modules.optimization.infrastructure.comparison_transport import VisualEncoder, VisualDecoder
from app.modules.optimization.infrastructure import resource_runtime
from app.modules.optimization.infrastructure import comparison_runner
from app.modules.optimization.infrastructure.sequential_runner import failed, with_resources
from tests.unit.optimization.test_sequential_runner import inputs


def test_material_reuse_is_lossless_smaller_and_scoped_to_one_execution():
    _, problem, _ = inputs()
    stock = problem.groups[0].stock_candidates[0]
    mask = RasterMask(1, 1000, tuple([(1 << 1000)-1]*1000))
    fact = VisualEvent(kind='source_selected',unit=problem.units[0],stock=stock,material_mask=mask)
    encoder, decoder = VisualEncoder(), VisualDecoder(problem)
    first, repeated = [json.loads(json.dumps(encoder.pack(fact))) for _ in range(2)]
    assert len(json.dumps(repeated)) < len(json.dumps(first))/10
    a, b = decoder.unpack(first), decoder.unpack(repeated)
    assert a == b == fact and a.material_mask is b.material_mask
    with pytest.raises(ValueError, match='not declared'):
        VisualDecoder(problem).unpack(repeated)
    foreign = {**repeated, 'material_mask_ref':['REMNANT',999]}
    with pytest.raises(ValueError, match='another source'):
        decoder.unpack(foreign)


def test_material_cache_replaces_one_entry_and_does_not_reuse_changed_masks():
    _, problem, _ = inputs()
    stock = problem.groups[0].stock_candidates[0]
    fact = VisualEvent(kind='source_selected',stock=stock,material_mask=RasterMask(1,2,(3,)))
    encoder, decoder = VisualEncoder(), VisualDecoder(problem)
    assert decoder.unpack(encoder.pack(fact)) == fact
    changed = replace(fact, material_mask=RasterMask(1,2,(1,)))
    packet = encoder.pack(changed)
    assert packet['material_mask'] is not None
    assert decoder.unpack(packet) == changed


def test_durable_diagnostic_distinguishes_parent_cut_and_global_non_execution():
    scopes, _, _ = inputs()
    report = dict(supervisor_peak_rss=300*MIB, maximum_aggregate_rss=400*MIB,
        limit_supervisor_rss=True,global_reason='MEMORY_BUDGET_EXCEEDED')
    result = with_resources(failed(scopes[1],'MEMORY_BUDGET_EXCEEDED'),report,{},ComparisonBudget())
    statistics = result.payload.diagnostic.statistics
    assert statistics['runtime_limit_supervisor_rss']==1
    assert statistics['runtime_limit_aggregate_rss']==statistics['runtime_worker_allocation_failed']==0
    assert statistics['runtime_not_started_global']==1
    assert statistics['runtime_supervisor_peak_rss_bytes'] > statistics['runtime_supervisor_limit_bytes']
    worker = with_resources(failed(scopes[0],'MEMORY_BUDGET_EXCEEDED',engine_started=True),
        {**report,'global_reason':None,'limit_supervisor_rss':False},
        dict(allocation_failed=True,engine_started=True),ComparisonBudget())
    assert worker.payload.diagnostic.statistics['runtime_worker_allocation_failed']==1
    assert worker.payload.diagnostic.statistics['runtime_not_started_global']==0


def test_v1_nested_parent_and_v2_cgroup_limits_are_detected(tmp_path):
    root = tmp_path/'cgroup'
    root.mkdir()
    (root/'memory.max').write_text(str(2*1024*MIB))
    (root/'memory.current').write_text(str(200*MIB))
    nested = root/'memory'/'dyno'/'web'
    nested.mkdir(parents=True)
    for path,limit,used in ((nested,512,100),(nested.parent,400,90)):
        (path/'memory.limit_in_bytes').write_text(str(limit*MIB))
        (path/'memory.usage_in_bytes').write_text(str(used*MIB))
    membership=tmp_path/'membership'
    membership.write_text('0::/\n5:memory:/dyno/web\n')
    values=resource_runtime.cgroup_memory(root,membership)
    assert (512*MIB,100*MIB) in values and (400*MIB,90*MIB) in values
    assert min(limit-used for limit,used in values)==310*MIB


def test_memory_overrides_are_explicit_and_leave_dyno_headroom(monkeypatch):
    monkeypatch.setattr(resource_runtime,'cgroup_memory',lambda:[(1024*MIB,100*MIB)])
    assert resource_runtime.configured_policy({}).budget==ComparisonBudget()
    values=dict(NEWGLASS_COMPARISON_SUPERVISOR_MIB='320',NEWGLASS_COMPARISON_WORKER_MIB='384',
        NEWGLASS_COMPARISON_AGGREGATE_MIB='800')
    policy=resource_runtime.configured_policy(values)
    assert policy.budget.supervisor_rss_bytes==320*MIB
    assert policy.budget.calculation_seconds==120 and policy.max_active_workers==1
    for changed in ({'NEWGLASS_COMPARISON_SUPERVISOR_MIB':'321'},
                    {**values,'NEWGLASS_COMPARISON_WORKER_MIB':'-1'},
                    {**values,'NEWGLASS_COMPARISON_AGGREGATE_MIB':'1024'},
                    {**values,'NEWGLASS_COMPARISON_AGGREGATE_MIB':'128'},
                    {**values,'NEWGLASS_DYNO_MEMORY_MIB':'512'}):
        with pytest.raises(RunError): resource_runtime.configured_policy(changed)


def test_sequential_preflight_does_not_reserve_the_live_supervisor_twice(monkeypatch):
    budget=replace(ComparisonBudget(),aggregate_rss_bytes=448*MIB,supervisor_rss_bytes=280*MIB)
    monkeypatch.setattr(comparison_runner,'resident_bytes',lambda pid:100*MIB)
    monkeypatch.setattr(comparison_runner,'available_memory',lambda:400*MIB)
    comparison_runner.check_environment(budget,inclusive_supervisor=True)
    with pytest.raises(RunError): comparison_runner.check_environment(budget)
    monkeypatch.setattr(comparison_runner,'available_memory',lambda:300*MIB)
    with pytest.raises(RunError): comparison_runner.check_environment(budget,inclusive_supervisor=True)
