"""TA-049: timeout HTTP boundaries for three/six engines and safe subsequent work."""
from dataclasses import replace
from functools import partial

import pytest
from sqlalchemy import select

from app.models import Pedido
from app.modules.optimization.application.comparison_limits import ComparisonBudget
from app.modules.optimization.application.run_recovery import RecoverStoppedRun
from app.modules.optimization.application.errors import RunError
from app.modules.optimization.application.sequential_policy import SequentialPolicy
from app.modules.optimization.infrastructure.comparison_runner import ComparisonProcessRunner
from app.modules.optimization.infrastructure.sequential_runner import SequentialProcessRunner
from app.modules.optimization.infrastructure.run_uow import SqlRunUnitOfWork
from tests.api.optimization.test_comparisons_api import (
    api as comparison_v1, start as start_v1, completed as completed_v1)  # noqa: F401
from tests.api.optimization.test_comparisons_v2_api import (
    api as comparison_v2, start as start_v2, completed as completed_v2)  # noqa: F401
from tests.integration.optimization.test_runs import prepared  # noqa: F401
from tests.integration.optimization.test_run_states import inventory


@pytest.mark.parametrize('deadline', ['calculation', 'global'])
@pytest.mark.parametrize('profile', ['v1', 'v2'])
def test_comparison_deadline_releases_only_after_stop_and_allows_new_work(
        request, session_factory, run_admission, profile, deadline):
    api = request.getfixturevalue('comparison_' + profile)
    budget = replace(ComparisonBudget(), **{deadline + '_seconds': 1e-9})
    before = inventory(session_factory)
    if profile == 'v1':
        client, ids, headers, owner, _ = api
        owner.runner_factory = partial(ComparisonProcessRunner, budget)
        start, completed = start_v1, completed_v1
    else:
        client, _, ids, headers, owner, _ = api
        owner.runner_factory = partial(SequentialProcessRunner, policy=SequentialPolicy(budget=budget))
        start, completed = start_v2, completed_v2
    path, accepted = start(api, 'ta049-deadline-first')
    final = completed(api, path)
    data = final if isinstance(final, dict) else final.model_dump(mode='json')
    assert data['status'] == 'FALLIDA' and data['terminal']
    assert len(data['executions']) == (3 if profile == 'v1' else 6)
    if profile == 'v1':
        assert all(e['failure_code'] == 'TIME_BUDGET_EXCEEDED' for e in data['executions'])
    else:
        expected = 'GLOBAL_TIME_LIMIT' if deadline == 'global' else 'TIME_BUDGET_EXCEEDED'
        assert all(e['diagnostic']['termination_reason'] == expected for e in data['executions'])
    assert owner.job.runner.last_report['all_workers_stopped']
    assert run_admission.active() == 0
    assert inventory(session_factory) == before
    with session_factory() as db:
        assert list(db.scalars(select(Pedido.estado).order_by(Pedido.id_pedido))) == ['PENDIENTE'] * len(ids)
    # FF reconciliation must never reinterpret a comparison's FF execution.
    with pytest.raises(RunError) as mismatch:
        RecoverStoppedRun(partial(SqlRunUnitOfWork, session_factory)).execute(
            accepted.comparison_id, service_stopped=True)
    assert mismatch.value.code == 'NOT_FOUND'
    owner.runner_factory = ComparisonProcessRunner if profile == 'v1' else SequentialProcessRunner
    second_path, _ = start(api, 'ta049-deadline-second')
    second = completed(api, second_path)
    second_data = second if isinstance(second, dict) else second.model_dump(mode='json')
    assert second_data['status'] == 'COMPLETADA'
    assert all(e['complete'] for e in second_data['executions'])
    assert client.get(path, headers=headers).json() == data
    with session_factory() as db:
        assert list(db.scalars(select(Pedido.estado).order_by(Pedido.id_pedido))) == ['OPTIMIZADO'] * len(ids)
    assert inventory(session_factory) == before
