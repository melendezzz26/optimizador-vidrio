"""Read-only, owner-scoped history over the existing comparison tables."""
from sqlalchemy import func, select

from app.models import Optimizacion
from app.shared.security import create_access_token
from .test_comparisons_v2_api import api, start, completed, BASE  # noqa: F401
from tests.integration.optimization.test_runs import prepared  # noqa: F401


def test_history_is_paginated_owned_and_never_reexecutes(api, monkeypatch, create_user):
    client, actor, _, headers, coordinator, uow = api
    path, accepted = start(api)
    completed(api, path)
    def forbidden(*args, **kwargs):
        raise AssertionError("history must not start or reconcile calculations")
    monkeypatch.setattr(coordinator, 'start', forbidden)
    monkeypatch.setattr(coordinator, 'reconcile', forbidden)
    with uow() as tx:
        before = tx.session.scalar(select(func.count()).select_from(Optimizacion))
    response = client.get(BASE+'/history?limit=1', headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert len(data['items']) == 1
    assert data['items'][0]['comparison_id'] == accepted.comparison_id
    assert data['items'][0]['order_ids'] == list(accepted.order_ids)
    assert data['items'][0]['profile'] == 'comparison-v2'
    assert not data['items'][0]['confirmed']
    assert data['next_before_id'] == accepted.comparison_id
    assert client.get(BASE+f'/history?before_id={accepted.comparison_id}', headers=headers).json()['items'] == []
    assert client.get(BASE+'/history?limit=21', headers=headers).status_code == 422
    assert client.get(BASE+'/history?before_id=0', headers=headers).status_code == 422
    assert client.get(BASE+'/history').status_code == 401
    # The fixture's second real user has view permission but owns no comparisons.
    other_id = create_user('O73000002')
    other_headers = {'Authorization': 'Bearer '+create_access_token(other_id, 'O73000002', 'Operario')}
    response = client.get(BASE+'/history', headers=other_headers)
    assert response.status_code == 200, response.text
    assert response.json()['items'] == []
    with uow() as tx:
        assert tx.session.scalar(select(func.count()).select_from(Optimizacion)) == before
