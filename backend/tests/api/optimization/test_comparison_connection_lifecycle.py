"""A single connection must suffice: authentication ends before the run UoW."""
from threading import Lock
from concurrent.futures import ThreadPoolExecutor
import json
import pytest

from sqlalchemy import create_engine, event, select, func
from sqlalchemy import text

from app.models import MovimientoInventario, Pedido, Pieza, Plancha
from tests.api.optimization.test_comparisons_api import api, prepared, start, completed  # noqa: F401
from tests.api.optimization.test_runs_api import run_api  # noqa: F401
from app.modules.optimization.infrastructure.comparison_runner import ComparisonProcessRunner
from app.modules.optimization.presentation.comparison_routes import get_comparison_runtime
from app.modules.optimization.presentation.comparison_runtime import ComparisonRuntime
from main import app


def prepare_sixteen(session_factory, ids):
    with session_factory() as session:
        for piece in session.scalars(select(Pieza).where(Pieza.id_pedido.in_(ids))):
            piece.cantidad = 8
            piece.dimensiones = {"width_mm": 1, "height_mm": 1}
            piece.geometria = {"type": "RECTANGULO", "width_mm": 1, "height_mm": 1}
            piece.area_mm2 = 1
        sheet = session.get(Plancha, 5)
        sheet.ancho_mm = sheet.alto_mm = 4
        sheet.cantidad = 10
        session.commit()


@pytest.mark.parametrize("capacity,readers", [(1, 0), (5, 8)])
def test_sixteen_pieces_persist_all_engines_with_bounded_connections(api, session_factory, record_property, monkeypatch, capacity, readers):
    client, ids, headers, runtime, _ = api
    prepare_sixteen(session_factory, ids)
    original = session_factory.kw["bind"]
    assert original.url.host == "127.0.0.1" and original.url.username == "r1_test"
    probe = 'newglass-worker-connection-probe'
    monkeypatch.setenv('DATABASE_URL', original.url.set(query={'application_name': probe}).render_as_string(hide_password=False))
    worker_connections = []
    class ObservedRunner(ComparisonProcessRunner):
        def calculate(self, *args, **kwargs):
            stream = super().calculate(*args, **kwargs)
            try:
                for packet in stream:
                    if packet['kind'] == 'ready':
                        with session_factory() as session:
                            count = session.scalar(text('SELECT COUNT(*) FROM pg_stat_activity WHERE application_name=:name'), {'name': probe})
                        worker_connections.append(count)
                    yield packet
            finally:
                stream.close()
    runtime.runner_factory = ObservedRunner
    engine = create_engine(original.url, pool_size=capacity, max_overflow=0, pool_timeout=1)
    checked_out = peak = 0
    lock = Lock()
    def checkout(*args):
        nonlocal checked_out, peak
        with lock:
            checked_out += 1
            peak = max(peak, checked_out)
    def checkin(*args):
        nonlocal checked_out
        with lock:
            checked_out -= 1
    event.listen(engine, "checkout", checkout)
    event.listen(engine, "checkin", checkin)
    session_factory.configure(bind=engine)
    try:
        path, accepted = start(api, key="single-connection-sixteen")
        def read_progress(index):
            for iteration in range(8):
                url = path if iteration % 2 else f"{path}/executions/{accepted.executions[index % 3].execution_id}/visual"
                response = client.get(url, headers=headers)
                assert response.status_code == 200, response.text
        if readers:
            with ThreadPoolExecutor(max_workers=readers + 2) as executor:
                views = [executor.submit(client.get, path + "/events", headers=headers) for _ in range(2)]
                requests = [executor.submit(read_progress, index) for index in range(readers)]
                for future in requests:
                    future.result(timeout=20)
                assert all(future.result(timeout=20).status_code == 200 for future in views)
        current = completed(api, path)
        runtime.job.thread.join(timeout=5)
        assert current["status"] == "COMPLETADA" and not current["incomplete"]
        results = {}
        for execution in accepted.executions:
            response = client.get(f"{path}/executions/{execution.execution_id}", headers=headers)
            assert response.status_code == 200, response.text
            result = response.json()["result"]
            assert result["metodo"] == execution.method and result["placed_units"] == 16 and result["completo"]
            results[execution.method] = result
        assert results["FF"]["metrics"]["planchas_nuevas_usadas"] == 1
        assert results["BF"]["metrics"]["planchas_nuevas_usadas"] == 1
        assert results["WF"]["metrics"]["planchas_nuevas_usadas"] == 10
        with session_factory() as session:
            assert session.get(Plancha, 5).cantidad == 10
            assert session.scalar(select(func.count()).select_from(MovimientoInventario)) == 0
        assert checked_out == 0 and 1 <= peak <= capacity
        assert runtime.job.runner.last_report["all_workers_stopped"]
        assert worker_connections == [0, 0, 0]
        record_property("bounded_connection_case", json.dumps({"capacity": capacity, "peak_checked_out": peak,
            "returned_to_pool": checked_out == 0, "pieces": 16, "worker_database_connections": worker_connections,
            "sheets": {method: result["metrics"]["planchas_nuevas_usadas"] for method, result in results.items()}}))
    finally:
        runtime.shutdown()
        session_factory.configure(bind=original)
        engine.dispose()


def test_legacy_ff_and_comparison_ff_persist_identical_placements_on_the_same_sixteen_piece_input(api, run_api, session_factory, run_admission):
    client, ids, headers, _, _ = api
    prepare_sixteen(session_factory, ids)
    original = client.post('/api/optimization/runs', json={"order_ids": ids}, headers=headers)
    assert original.status_code == 201
    assert json.loads(original.text.strip().splitlines()[-1])["event"] == 'optimization_completed'
    legacy = client.get(original.headers['location'], headers=headers).json()
    assert legacy['placed_units'] == 16 and legacy['estado'] == 'COMPLETADA'
    assert run_admission.active() == 0
    # Fixture reset only: feed the exact same order IDs and stock into the comparator.
    with session_factory() as session:
        for identifier in ids:
            session.get(Pedido, identifier).estado = 'PENDIENTE'
        assert session.get(Plancha, 5).cantidad == 10
        session.commit()
    path, accepted = start(api)
    assert completed(api, path)['status'] == 'COMPLETADA'
    ff = next(execution for execution in accepted.executions if execution.method == 'FF')
    result = client.get(f'{path}/executions/{ff.execution_id}', headers=headers).json()['result']
    for field in ('placements', 'materials_used', 'configuracion', 'placed_units', 'total_units'):
        assert result[field] == legacy[field]
    with session_factory() as session:
        assert session.get(Plancha, 5).cantidad == 10
        assert session.scalar(select(func.count()).select_from(MovimientoInventario)) == 0


def test_runtime_restart_expires_visual_buffers_but_preserves_all_three_results(api):
    client, _, headers, runtime, _ = api
    path, accepted = start(api)
    assert completed(api, path)['status'] == 'COMPLETADA'
    runtime.shutdown()
    fresh = ComparisonRuntime()
    app.dependency_overrides[get_comparison_runtime] = lambda: fresh
    try:
        recovered = client.get(path, headers=headers)
        assert recovered.status_code == 200 and recovered.json()['terminal']
        for execution in accepted.executions:
            own = f'{path}/executions/{execution.execution_id}'
            result = client.get(own, headers=headers)
            assert result.status_code == 200
            assert result.json()['result']['metodo'] == execution.method
            assert result.json()['result']['completo']
            assert client.get(own + '/visual', headers=headers).status_code == 410
        assert client.get(path + '/events', headers=headers).status_code == 410
    finally:
        fresh.shutdown()
        app.dependency_overrides[get_comparison_runtime] = lambda: runtime


@pytest.mark.parametrize('capacity', [1, 5])
def test_dashboard_and_inventory_reads_return_auth_connections_before_repository_queries(api, session_factory, capacity):
    client, _, headers, _, _ = api
    original = session_factory.kw['bind']
    assert original.url.host == '127.0.0.1' and original.url.username == 'r1_test'
    engine = create_engine(original.url, pool_size=capacity, max_overflow=0, pool_timeout=1)
    session_factory.configure(bind=engine)
    paths = ['/api/inventory/planchas', '/api/inventory/retazos', '/api/clients',
        '/api/orders?estado=PENDIENTE', '/api/orders?estado=EN_OPTIMIZACION', '/api/orders']
    try:
        def read(index):
            for offset in range(len(paths)):
                response = client.get(paths[(index + offset) % len(paths)], headers=headers)
                assert response.status_code == 200, response.text
        with ThreadPoolExecutor(max_workers=8) as executor:
            for future in [executor.submit(read, index) for index in range(8)]:
                future.result(timeout=20)
        assert engine.pool.checkedout() == 0
    finally:
        session_factory.configure(bind=original)
        engine.dispose()
