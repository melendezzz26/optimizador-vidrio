"""Flujo HTTP comparativo real. Autor: Fabricio Melendez Quezada. Revisor: Andro Quispe."""
import json
import time
from decimal import Decimal
from functools import partial

import pytest
from sqlalchemy import delete, func, select
from app.models import Configuracion, MovimientoInventario, Optimizacion, Pedido, Permiso, Plancha, Retazo, RolPermiso
from app.shared.security import create_access_token
from app.modules.optimization.infrastructure.comparison_uow import SqlComparisonUnitOfWork
from app.modules.optimization.presentation.comparison_routes import get_comparison_uow, get_comparison_runtime
from app.modules.optimization.presentation.comparison_runtime import ComparisonRuntime
from app.modules.optimization.presentation.comparison_schemas import ComparisonSummary, ComparisonEvent, ExecutionResponse
from main import app
from app.modules.inventory.presentation.dependencies import get_inventory_service
from app.modules.inventory.application.service import InventoryService
from app.modules.inventory.infrastructure.repository import SqlAlchemyInventoryRepository
from tests.integration.optimization.test_runs import prepared  # noqa: F401

BASE = "/api/optimization/comparisons"


@pytest.fixture
def api(client, session_factory, prepared):
    actor, ids, _ = prepared
    uow, runtime = partial(SqlComparisonUnitOfWork, session_factory), ComparisonRuntime()
    app.dependency_overrides[get_comparison_uow] = lambda: uow
    app.dependency_overrides[get_comparison_runtime] = lambda: runtime
    app.dependency_overrides[get_inventory_service] = lambda: InventoryService(SqlAlchemyInventoryRepository(session_factory))
    headers = {"Authorization": "Bearer " + create_access_token(actor, "O73000001", "Operario")}
    try:
        yield client, ids, headers, runtime, uow
    finally:
        runtime.shutdown()
        app.dependency_overrides.pop(get_comparison_uow, None)
        app.dependency_overrides.pop(get_comparison_runtime, None)
        app.dependency_overrides.pop(get_inventory_service, None)


def start(api, key="comparison-api-key"):
    client, ids, headers, *_ = api
    response = client.post(BASE, json={"order_ids": ids}, headers={**headers, "Idempotency-Key": key})
    assert response.status_code == 201, response.text
    current = ComparisonSummary.model_validate(response.json())
    return response.headers["location"], current


def completed(api, path):
    client, _, headers, *_ = api
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        response = client.get(path, headers=headers)
        assert response.status_code == 200, response.text
        current = response.json()
        if current["terminal"]:
            return current
        time.sleep(.02)
    pytest.fail("Comparison did not finish")


def test_full_http_three_engines_masks_order_selection_confirmation_and_reload(api, session_factory, record_property):
    client, ids, headers, runtime, _ = api
    path, accepted = start(api)
    assert accepted.selected_execution_id is None
    stream = client.get(path + "/events", headers=headers)
    assert stream.status_code == 200, stream.text
    events = [ComparisonEvent.model_validate_json(line).model_dump(mode="json") for line in stream.iter_lines()]
    assert [e["sequence"] for e in events] == list(range(1, len(events) + 1))
    assert events[0]["event"] == "comparison_accepted" and events[-1]["event"] == "comparison_finished"
    for execution in accepted.executions:
        facts = [e for e in events if e["method"] == execution.method]
        assert [e["execution_sequence"] for e in facts] == list(range(1, len(facts) + 1))
        names = [e["event"] for e in facts]
        assert names.index("piece_ready") < names.index("ordering_ready") < names.index("piece_placed") < names.index("result_persisted")
        assert {e["execution_id"] for e in facts} == {execution.execution_id}
        result = client.get(f"{path}/executions/{execution.execution_id}", headers=headers)
        assert result.status_code == 200, result.text
        dto = ExecutionResponse.model_validate(result.json())
        assert dto.result.metodo == execution.method and dto.result.completo
        assert "confirmable" not in result.json()["result"]
        manifest = client.get(f"{path}/executions/{execution.execution_id}/visual", headers=headers)
        assert manifest.status_code == 200, manifest.text
        mask = next(m for m in manifest.json()["items"] if m["kind"] == "PIECE")
        assert mask["execution_id"] == execution.execution_id and mask["method"] == execution.method
        response = client.get(f"{path}/executions/{execution.execution_id}/visual/masks/{mask['mask_ref']}", headers=headers)
        assert response.status_code == 200, response.text
        assert response.json()["spans_by_row"] == [{"row": 0, "runs": [[0, 2]]}, {"row": 1, "runs": [[0, 2]]}]
        other = next(e for e in accepted.executions if e.execution_id != execution.execution_id)
        assert client.get(f"{path}/executions/{other.execution_id}/visual/masks/{mask['mask_ref']}", headers=headers).status_code == 404
    current = completed(api, path)
    assert current["selected_execution_id"] is None and not current["confirmable"]
    assert current["requested_pieces"][0]["dimensiones"] == {"width_mm": 2, "height_mm": 2}
    wf = next(e for e in current["executions"] if e["method"] == "WF")
    selected = client.put(path + "/selection", json={"execution_id": wf["execution_id"], "expected_version": current["version"]}, headers=headers)
    assert selected.status_code == 200, selected.text
    with session_factory() as s:
        assert s.get(Plancha, 5).cantidad == 2
        assert s.scalar(select(func.count()).select_from(MovimientoInventario)) == 0
    body = {"execution_id": wf["execution_id"], "expected_version": selected.json()["version"]}
    confirm_headers = {**headers, "Idempotency-Key": "confirmation-api-key"}
    left = client.post(path + "/confirm", json=body, headers=confirm_headers)
    assert left.status_code == 200, left.text
    assert client.post(path + "/confirm", json=body, headers=confirm_headers).json() == left.json()
    assert client.get(path, headers=headers).json()["confirmed"]
    assert runtime.job.finished and runtime.job.observers == 0
    record_property("comparison_resources", json.dumps({"runner": runtime.job.runner.last_report,
        "retained_visual_bytes": sum(s.charged_bytes for s in runtime.job.sessions.values()),
        "retained_event_bytes": runtime.job.record_bytes, "event_count": len(runtime.job.records)}))


def test_idempotency_and_request_lookup_do_not_recalculate(api, session_factory):
    client, ids, headers, *_ = api
    path, accepted = start(api)
    repeated_path, repeated = start(api)
    assert path == repeated_path and repeated.comparison_id == accepted.comparison_id
    assert client.get(BASE + "/requests/comparison-api-key", headers=headers).json()["comparison_id"] == accepted.comparison_id
    completed(api, path)
    with session_factory() as s:
        assert s.scalar(select(func.count()).select_from(Optimizacion)) == 1
    conflict = client.post(BASE, json={"order_ids": ids[:1]}, headers={**headers, "Idempotency-Key": "comparison-api-key"})
    assert conflict.status_code == 409


def test_release_preserves_history_and_cursor_recovery(api, session_factory):
    client, ids, headers, runtime, _ = api
    path, accepted = start(api)
    current = completed(api, path)
    job = runtime.job
    with job.condition:
        while len(job.records) > 1:
            _, removed = job.records.popleft()
            job.record_bytes -= len(removed)
    expired = client.get(path + "/events?after_sequence=0", headers=headers)
    assert expired.status_code == 409 and expired.json()["detail"]["code"] == "EVENT_CURSOR_EXPIRED"
    result = client.get(path + f"/executions/{accepted.executions[0].execution_id}", headers=headers)
    assert result.status_code == 200
    released = client.post(path + "/release", json={"expected_version": current["version"]}, headers=headers)
    assert released.status_code == 200 and released.json()["released"]
    with session_factory() as s:
        assert [s.get(Pedido, i).estado for i in ids] == ["PENDIENTE"] * 2


@pytest.mark.parametrize("missing", ["key", "permission", "auth"])
def test_rejections_have_no_accepted_work(api, session_factory, missing):
    client, ids, headers, *_ = api
    if missing == "permission":
        with session_factory() as s:
            pid = s.scalar(select(Permiso.id_permiso).where(Permiso.codigo == "optimization.execute"))
            s.execute(delete(RolPermiso).where(RolPermiso.id_rol == 3, RolPermiso.id_permiso == pid))
            s.commit()
    actual = {} if missing == "auth" else dict(headers)
    if missing != "key":
        actual["Idempotency-Key"] = "comparison-api-key"
    response = client.post(BASE, json={"order_ids": ids}, headers=actual)
    assert response.status_code == {"key": 422, "permission": 403, "auth": 401}[missing]
    with session_factory() as s:
        assert s.scalar(select(func.count()).select_from(Optimizacion)) == 0


def test_disconnected_observation_keeps_calculation_and_releases_view_slot(api):
    client, _, headers, runtime, _ = api
    path, _ = start(api)
    job = runtime.job
    observer = job.observe()
    stream = job.lines(0, observer)
    assert json.loads(next(stream))["event"] == "comparison_accepted"
    observer.release()
    stream.close()
    assert completed(api, path)["status"] == "COMPLETADA"
    assert job.observers == 0


def test_orphaned_supervisor_is_reconciled_from_process_identity(api, session_factory):
    from app.modules.optimization.application.comparisons import AcceptComparison
    client, ids, headers, _, uow = api
    # prepared crea el actor; se obtiene desde la configuración de prueba.
    from app.models import Configuracion
    with session_factory() as s:
        actor = s.scalar(select(Configuracion.id_usuario_creacion))
    current = AcceptComparison(uow).execute(ids, actor, "orphan-comparison-key")
    with uow() as tx:
        tx.comparisons.claim_supervisor(current.comparison_id, "old-supervisor", {"pid": 2147483647, "start_ticks": "1"})
    response = client.get(f"{BASE}/{current.comparison_id}", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["terminal"] and response.json()["status"] == "FALLIDA"
    with session_factory() as s:
        assert [s.get(Pedido, i).estado for i in ids] == ["PENDIENTE"] * 2


def test_visual_budget_exhaustion_keeps_results_and_memory_is_aggregate(api):
    from dataclasses import replace
    from app.modules.optimization.application.comparison_limits import ComparisonBudget
    from app.modules.optimization.infrastructure.comparison_runner import ComparisonProcessRunner
    client, _, headers, runtime, _ = api
    budget = replace(ComparisonBudget(), retained_visual_bytes=1)
    runtime.runner_factory = lambda: ComparisonProcessRunner(budget)
    path, current = start(api)
    assert completed(api, path)["status"] == "COMPLETADA"
    assert sum(s.charged_bytes for s in runtime.job.sessions.values()) <= 1
    for execution in current.executions:
        manifest = client.get(f"{path}/executions/{execution.execution_id}/visual", headers=headers)
        assert manifest.json()["items"] == []


def test_browser_can_send_idempotency_header(api):
    client, *_ = api
    response = client.options(BASE, headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "authorization,content-type,idempotency-key"})
    assert response.status_code == 200
    assert "idempotency-key" in response.headers["access-control-allow-headers"].lower()


def test_memory_preflight_rejects_before_acceptance_and_frees_admission(api, session_factory, run_admission, monkeypatch):
    from app.modules.optimization.infrastructure import comparison_runner
    monkeypatch.setattr(comparison_runner, "available_memory", lambda: 0)
    client, ids, headers, *_ = api
    response = client.post(BASE, json={"order_ids": ids}, headers={**headers, "Idempotency-Key": "memory-preflight-key"})
    assert response.status_code == 503 and response.json()["detail"]["code"] == "RESOURCE_UNAVAILABLE"
    assert run_admission.active() == 0
    with session_factory() as s:
        assert s.scalar(select(func.count()).select_from(Optimizacion)) == 0
        assert [s.get(Pedido, i).estado for i in ids] == ["PENDIENTE"] * 2


def test_windows_rejection_is_actionable_read_only_and_frees_admission(api, session_factory, run_admission, monkeypatch):
    from app.modules.optimization.infrastructure import comparison_runner
    client, ids, headers, runtime, _ = api
    with session_factory() as s:
        stock_before = s.get(Plancha, 5).cantidad
        movements_before = s.scalar(select(func.count()).select_from(MovimientoInventario))
    with monkeypatch.context() as patch:
        patch.setattr(comparison_runner.sys, "platform", "win32")
        response = client.post(BASE, json={"order_ids": ids}, headers={**headers, "Idempotency-Key": "windows-preflight-key"})
    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["code"] == "RESOURCE_UNAVAILABLE" and "WSL2" in detail["message"]
    assert run_admission.active() == 0 and runtime.job is None
    with session_factory() as s:
        assert s.scalar(select(func.count()).select_from(Optimizacion)) == 0
        assert [s.get(Pedido, i).estado for i in ids] == ["PENDIENTE"] * 2
        assert s.get(Plancha, 5).cantidad == stock_before
        assert s.scalar(select(func.count()).select_from(MovimientoInventario)) == movements_before
    # El mismo endpoint vuelve a admitir trabajo con el entorno real de Linux.
    path, _ = start(api, key="linux-after-rejection-key")
    assert completed(api, path)["status"] == "COMPLETADA"


def test_real_comparison_preserves_entire_inventory_and_returns_three_owned_results(api, session_factory, run_admission, record_property):
    client, _, headers, runtime, _ = api
    def inventory():
        with session_factory() as s:
            return {model.__tablename__: [dict(row) for row in s.execute(
                select(model.__table__).order_by(*model.__table__.primary_key.columns)).mappings()]
                for model in (Plancha, Retazo, MovimientoInventario)}
    before = inventory()
    path, accepted = start(api)
    current = completed(api, path)
    runtime.job.thread.join(timeout=5)
    assert current["status"] == "COMPLETADA" and not current["confirmed"]
    assert {e.method for e in accepted.executions} == {"FF", "BF", "WF"}
    assert len({e.execution_id for e in accepted.executions}) == 3
    results = []
    for execution in accepted.executions:
        response = client.get(f"{path}/executions/{execution.execution_id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["execution"]["execution_id"] == execution.execution_id
        assert data["result"]["metodo"] == execution.method and data["result"]["completo"]
        results.append({"method": execution.method, "execution_id": execution.execution_id,
                        "placed_units": data["result"]["placed_units"]})
    assert inventory() == before
    assert run_admission.active() == 0 and runtime.job.runner.last_report["all_workers_stopped"]
    record_property("real_comparison", json.dumps({"comparison_id": accepted.comparison_id,
        "results": results, "inventory_unchanged": True, "runner": runtime.job.runner.last_report}))


def test_busy_comparison_has_no_accepted_work_and_runs_after_capacity_is_released(api, session_factory, run_admission):
    client, ids, headers, runtime, _ = api
    lease = run_admission.acquire(9999)
    try:
        response = client.post(BASE, json={"order_ids": ids}, headers={**headers, "Idempotency-Key": "overload-comparison-key"})
        assert response.status_code == 503 and response.json()["detail"]["code"] == "OPTIMIZER_BUSY"
        assert response.headers["Retry-After"] == "15"
        assert runtime.job is None and run_admission.active() == 1
        with session_factory() as s:
            assert s.scalar(select(func.count()).select_from(Optimizacion)) == 0
            assert [s.get(Pedido, i).estado for i in ids] == ["PENDIENTE"] * 2
            assert s.get(Plancha, 5).cantidad == 2
            assert s.scalar(select(func.count()).select_from(MovimientoInventario)) == 0
    finally:
        lease.release()
    path, _ = start(api, key="overload-comparison-key")
    assert completed(api, path)["status"] == "COMPLETADA"
    runtime.job.thread.join(timeout=5)
    assert run_admission.active() == 0 and runtime.job.runner.last_report["all_workers_stopped"]


def test_publishing_angular_version_unblocks_three_engines_without_inventory_changes(api, session_factory, run_admission, record_property):
    from app.modules.optimization.infrastructure.configuration_publication import publish_angular_step_version
    client, ids, headers, runtime, _ = api
    def inventory():
        with session_factory() as s:
            return {model.__tablename__: [dict(row) for row in s.execute(
                select(model.__table__).order_by(*model.__table__.primary_key.columns)).mappings()]
                for model in (Plancha, Retazo, MovimientoInventario)}
    with session_factory() as s:
        old = s.scalar(select(Configuracion).where(Configuracion.vigente.is_(True)))
        old.paso_angular_grados = 90
        s.commit()
        old_id = old.id_configuracion
        before = {c.name: getattr(old, c.name) for c in Configuracion.__table__.columns}
    stock_before = inventory()
    key = "published-angular-key"
    rejected = client.post(BASE, json={"order_ids": ids}, headers={**headers, "Idempotency-Key": key})
    assert rejected.status_code == 409 and rejected.json()["detail"]["code"] == "CONFIG_CONFLICT"
    assert run_admission.active() == 0 and runtime.job is None
    with session_factory() as s:
        assert s.scalar(select(func.count()).select_from(Optimizacion)) == 0
        assert [s.get(Pedido, i).estado for i in ids] == ["PENDIENTE"] * 2
        published = publish_angular_step_version(s, "O73000001")
        assert published.changed and published.current_version == 2
        old = s.get(Configuracion, old_id)
        assert {c.name: getattr(old, c.name) for c in Configuracion.__table__.columns} == {**before, "vigente": False}
        new = s.scalar(select(Configuracion).where(Configuracion.vigente.is_(True)))
        assert new.paso_angular_grados == 5
        assert all(getattr(new, name) == before[name] for name in (
            "separacion_mm", "margen_mm", "resolucion_raster_mm", "ancho_min_retazo_mm", "alto_min_retazo_mm"))
        new_id = new.id_configuracion
    path, accepted = start(api, key=key)
    assert accepted.configuration_id == new_id and accepted.configuration_version == 2
    assert accepted.configuration.paso_angular_grados == 5
    assert completed(api, path)["status"] == "COMPLETADA"
    runtime.job.thread.join(timeout=5)
    for execution in accepted.executions:
        response = client.get(f"{path}/executions/{execution.execution_id}", headers=headers)
        assert response.status_code == 200
        result = response.json()["result"]
        assert result["metodo"] == execution.method and result["completo"]
        assert Decimal(result["configuracion"]["paso_angular_grados"]) == 5
        assert all(Decimal(p["rotation_deg"]) % 5 == 0 for p in result["placements"])
    assert inventory() == stock_before
    assert run_admission.active() == 0 and runtime.job.runner.last_report["all_workers_stopped"]
    record_property("angular_publication_comparison", json.dumps({"rejected_status": rejected.status_code,
        "accepted_status": 201, "configuration_version": accepted.configuration_version,
        "angular_step_deg": str(accepted.configuration.paso_angular_grados),
        "executions": [{"execution_id": e.execution_id, "method": e.method} for e in accepted.executions],
        "inventory_unchanged": True, "all_workers_stopped": True}))


def test_selected_wf_remnant_has_physical_origin_through_inventory_api(api, session_factory):
    client, ids, headers, *_ = api
    with session_factory() as s:
        s.get(Plancha, 5).ancho_mm = 5
        s.commit()
    path, _ = start(api)
    current = completed(api, path)
    execution = next(e for e in current["executions"] if e["method"] == "WF")
    chosen = client.put(path + "/selection", json={"execution_id": execution["execution_id"], "expected_version": current["version"]}, headers=headers).json()
    response = client.post(path + "/confirm", headers={**headers, "Idempotency-Key": "wf-origin-confirm-key"},
        json={"execution_id": execution["execution_id"], "expected_version": chosen["version"]})
    assert response.status_code == 200, response.text
    remnants = response.json()["receipt"]["remnants_created"]
    assert remnants
    for remnant in remnants:
        origin = client.get(f"/api/inventory/retazos/{remnant['id_retazo']}/origen", headers=headers)
        assert origin.status_code == 200, origin.text
        assert origin.json()["source"] == remnant["source"]
        assert origin.json()["id_ejecucion_origen"] == execution["execution_id"]
