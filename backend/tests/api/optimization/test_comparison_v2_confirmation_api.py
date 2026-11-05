"""B08 HTTP -> native engines -> PostgreSQL confirmation, using B06 lifecycle."""
from sqlalchemy import select, delete
from app.models import MovimientoInventario, Pedido, Plancha, Permiso, RolPermiso
from app.shared.security import create_access_token
from app.modules.optimization.presentation.comparison_v2_schemas import ComparisonConfirmationV2
from .test_comparisons_v2_api import api, start, completed  # noqa: F401
from tests.integration.optimization.test_runs import prepared  # noqa: F401


def test_real_http_selection_confirmation_and_recovery(api, session_factory, monkeypatch):
    client, actor, ids, headers, coordinator, uow = api
    path, accepted = start(api, 'b08-real-api-request')
    current = completed(api, path)
    original = {e.execution_id: client.get(f'{path}/executions/{e.execution_id}', headers=headers).json()
                for e in current.executions}
    for execution in current.executions:
        response = client.put(path + '/selection', headers=headers,
            json={'execution_id': execution.execution_id, 'expected_version': current.version})
        assert response.status_code == 200, response.text
        current = type(current).model_validate(response.json())
        assert current.selected_execution_id == execution.execution_id and current.confirmable
    with session_factory() as s:
        assert s.get(Plancha, 5).cantidad == 2
        assert not s.scalars(select(MovimientoInventario)).all()
    body = dict(execution_id=current.selected_execution_id, expected_version=current.version)
    key_headers = {**headers, 'Idempotency-Key': 'b08-real-confirm-key'}
    response = client.post(path + '/confirm', headers=key_headers, json=body)
    assert response.status_code == 200, response.text
    receipt = ComparisonConfirmationV2.model_validate(response.json())
    assert receipt.execution_id == current.selected_execution_id
    confirmed = client.get(path, headers=headers).json()
    assert confirmed['confirmed'] and not confirmed['confirmable'] and not confirmed['selection_allowed']
    assert all(not e['eligible'] for e in confirmed['executions'])
    assert client.post(path + '/confirm', headers=key_headers, json=body).json() == response.json()
    assert client.post(path + '/confirm', headers={**headers, 'Idempotency-Key': 'b08-other-confirm-key'}, json=body).status_code == 409
    assert client.put(path + '/selection', headers=headers, json=body).status_code == 409
    coordinator.shutdown()
    def forbidden(*args, **kwargs):
        raise AssertionError('Historical query must never execute engines')
    monkeypatch.setattr(coordinator, 'start', forbidden)
    assert client.get(path, headers=headers).json() == confirmed
    assert client.get('/api/optimization/comparisons-v2/requests/b08-real-api-request', headers=headers).json() == confirmed
    for execution in current.executions:
        restored = client.get(f'{path}/executions/{execution.execution_id}', headers=headers)
        assert restored.status_code == 200, restored.text
        assert restored.json()['result']['placements'] == original[execution.execution_id]['result']['placements']
        assert restored.json()['execution']['diagnostic'] == original[execution.execution_id]['execution']['diagnostic']
    with session_factory() as s:
        assert s.get(Plancha, 5).cantidad == 0
        movements = s.scalars(select(MovimientoInventario)).all()
        assert len(movements) == 1 and movements[0].cantidad_afectada == 2
        assert all(s.get(Pedido, identifier).estado == 'CONFIRMADO' for identifier in ids)
    assert coordinator.admission.active() == 0


def test_confirmation_permissions_ownership_and_strict_input(api, session_factory, create_user):
    client, _, _, headers, _, _ = api
    path, _ = start(api, 'b08-security-request')
    current = completed(api, path)
    body = dict(execution_id=current.executions[0].execution_id, expected_version=current.version)
    assert client.put(path + '/selection', json=body).status_code == 401
    other = create_user('O73000999')
    theirs = {'Authorization': 'Bearer ' + create_access_token(other, 'O73000999', 'Operario'), 'Idempotency-Key': 'b08-owner-check'}
    assert client.put(path + '/selection', headers=theirs, json=body).status_code == 404
    assert client.post(path + '/confirm', headers=theirs, json=body).status_code == 404
    assert client.put(path + '/selection', headers=headers, json={**body, 'execution_id': '1'}).status_code == 422
    assert client.put(path + '/selection', headers=headers, json={**body, 'execution_id': 2147483647}).status_code == 422
    with session_factory() as s:
        permission = s.scalar(select(Permiso).where(Permiso.codigo == 'optimization.confirm'))
        s.execute(delete(RolPermiso).where(RolPermiso.id_permiso == permission.id_permiso))
        s.commit()
    assert client.post(path + '/confirm', headers={**headers, 'Idempotency-Key': 'b08-permission-check'}, json=body).status_code == 403
