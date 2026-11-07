"""Strict ownership reader and one retained window, not proofs of OS capacity."""
from copy import deepcopy
from types import SimpleNamespace

import pytest

from app.modules.optimization.application.supervision_contracts import runtime_metadata
from app.modules.optimization.application.errors import WorkersNotStopped
from app.modules.optimization.presentation.comparison_retention import ComparisonRetention


def valid():
    return dict(runtime_version=1,supervisor_stopped_at=None,
        supervisor=dict(token='a'*32,identity=dict(pid=43,start_ticks='100')),
        workers={'4301':dict(pid=44,start_ticks='101')})


@pytest.mark.parametrize('change',[
    lambda r:r.update(runtime_version=True),lambda r:r.update(runtime_version=2),
    lambda r:r.update(extra=1),lambda r:r.update(supervisor=None),
    lambda r:r['supervisor'].update(token='x'),lambda r:r['supervisor']['identity'].update(pid=True),
    lambda r:r['supervisor']['identity'].update(start_ticks=None),
    lambda r:r['workers'].update({'999':dict(pid=99,start_ticks='3')}),
    lambda r:r['workers']['4301'].update(start_ticks='-1'),
    lambda r:r.update(workers=[]),
])
def test_reject_corrupted_or_foreign_ownership(change):
    value=deepcopy(valid()); change(value)
    with pytest.raises(ValueError): runtime_metadata(value,[4301])


def test_old_reader_and_unresolved_spawn_remain_explicit():
    legacy={'supervisor_stopped_at':None}
    assert runtime_metadata(legacy,[4301])==legacy
    current=valid(); current['workers']['4301']=None
    assert runtime_metadata(current,[4301])['workers']['4301'] is None


def test_retention_handoff_clears_both_windows_and_rejects_live_owner():
    retention=ComparisonRetention(); disposed=[]
    old=SimpleNamespace(thread=None,finished=False,dispose=lambda:disposed.append('old'))
    new=SimpleNamespace(thread=None,finished=False,dispose=lambda:disposed.append('new'))
    retention.replace(old)
    with pytest.raises(WorkersNotStopped): retention.replace(new)
    assert disposed==[] and retention.owner is old
    old.finished=True
    retention.replace(new)
    assert disposed==['old'] and retention.owner is new
    retention.clear(old)
    assert retention.owner is new
    retention.clear(new)
    assert retention.owner is None
