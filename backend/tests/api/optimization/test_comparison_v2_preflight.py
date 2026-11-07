"""TA-047: real HTTP/PostgreSQL rejection before the first business write."""
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import event, select

from app.models import Base, Configuracion, Pieza, Plancha, Retazo
from app.modules.optimization.infrastructure.sequential_runner import SequentialProcessRunner
from tests.api.optimization.test_comparisons_v2_api import api, start, completed  # noqa: F401
from tests.integration.optimization.test_runs import prepared  # noqa: F401


def database_state(factory):
    """Include links, executions, metrics, inventory and every persisted reservation."""
    with factory() as session:
        return {table.name: sorted((repr(tuple(row)) for row in session.execute(select(table))))
                for table in Base.metadata.sorted_tables}


def remnant(session, geometry):
    session.add(Retazo(codigo='TA047-preflight', id_tipo_vidrio=7, espesor_mm=6,
        geometria=geometry, area_mm2=4, estado=True, fecha_registro=datetime.now(timezone.utc)))


@pytest.mark.parametrize('invalid,code,status', [
    ('stock_extent', 'INVALID_INPUT', 422),
    ('stock_cells', 'INVALID_INPUT', 422),
    ('stock_concave', 'INVALID_INPUT', 422),
    ('stock_crossed', 'INVALID_INPUT', 422),
    ('stock_degenerate', 'INVALID_INPUT', 422),
    ('stock_vertices', 'INVALID_INPUT', 422),
    ('piece_extent', 'INVALID_INPUT', 422),
    ('piece_dimensions', 'INVALID_INPUT', 422),
    ('piece_contour', 'INVALID_INPUT', 422),
    ('empty_order', 'INVALID_INPUT', 422),
    ('units', 'LOAD_LIMIT_EXCEEDED', 422),
    ('stock_units', 'LOAD_LIMIT_EXCEEDED', 422),
    ('angle', 'CONFIG_CONFLICT', 409),
    ('missing_angle', 'CONFIG_CONFLICT', 409),
])
def test_rejection_has_no_writes_workers_or_leaked_reservations(
        api, session_factory, monkeypatch, invalid, code, status):
    client, _, ids, headers, coordinator, _ = api
    with session_factory() as session:
        config = session.scalar(select(Configuracion))
        piece = session.scalar(select(Pieza).where(Pieza.id_pedido == ids[-1]))
        if invalid == 'stock_extent': session.get(Plancha, 5).ancho_mm = 4001
        if invalid == 'stock_cells':
            config.resolucion_raster_mm = Decimal('0.5')
            session.get(Plancha, 5).ancho_mm = Decimal('2000.5')
        if invalid == 'stock_concave':
            remnant(session, dict(type='POLIGONO_CONVEXO', vertices_mm=[[0, 0], [4, 0], [1, 1], [0, 4]]))
        if invalid == 'stock_crossed':
            remnant(session, dict(type='POLIGONO_CONVEXO', vertices_mm=[[0, 0], [4, 4], [0, 4], [4, 0]]))
        if invalid == 'stock_degenerate':
            remnant(session, dict(type='POLIGONO_CONVEXO', vertices_mm=[[0, 0], [1, 0], [2, 0]]))
        if invalid == 'stock_vertices':
            from tests.unit.optimization.test_load_budget import polygon
            remnant(session, polygon(129))
        if invalid == 'piece_extent':
            piece.geometria = dict(type='RECTANGULO', width_mm=4001, height_mm=2)
        if invalid == 'piece_dimensions':
            piece.geometria = dict(type='RECTANGULO', width_mm=-2, height_mm=2)
        if invalid == 'piece_contour':
            piece.tipo_forma = 'POLIGONO_CONVEXO'
            piece.geometria = dict(type='POLIGONO_CONVEXO', vertices_mm=[[0, 0], [4, 4], [0, 4], [4, 0]])
        if invalid == 'empty_order':
            for row in session.scalars(select(Pieza).where(Pieza.id_pedido == ids[-1])): session.delete(row)
        if invalid == 'units': piece.cantidad = 151
        if invalid == 'stock_units': session.get(Plancha, 5).cantidad = 51
        if invalid == 'angle': config.paso_angular_grados = 10
        if invalid == 'missing_angle': config.paso_angular_grados = None
        session.commit()
    before = database_state(session_factory)
    writes = []
    def sql(connection, cursor, statement, parameters, context, many):
        if statement.lstrip().split()[0].upper() in ('INSERT', 'UPDATE', 'DELETE'):
            writes.append(statement)
    def forbidden(*args, **kwargs): raise AssertionError('Rejected input started engine execution')
    monkeypatch.setattr(SequentialProcessRunner, 'events', forbidden)
    engine = session_factory.kw['bind']
    event.listen(engine, 'before_cursor_execute', sql)
    try:
        response = client.post('/api/optimization/comparisons-v2', json={'order_ids': ids},
            headers={**headers, 'Idempotency-Key': 'ta047-invalid-0001'})
    finally:
        event.remove(engine, 'before_cursor_execute', sql)
    assert response.status_code == status, response.text
    assert response.json()['detail']['code'] == code
    assert 'location' not in response.headers
    assert writes == []
    assert database_state(session_factory) == before
    assert coordinator.job is None and coordinator.recovery_lease is None
    assert coordinator.admission.active() == 0
    # The exclusive comparison token must also have been released.
    lease = coordinator.admission.acquire_comparison(api[1]); lease.release()


@pytest.mark.parametrize('scenario,expected', [
    ('no_stock', 'SIN_SOLUCION'), ('no_fit', 'SIN_SOLUCION'),
    ('margin', 'SIN_SOLUCION'), ('separation', 'SIN_SOLUCION'),
    ('rotation', 'COMPLETADA'), ('fractional', 'COMPLETADA'),
    ('negative_origin', 'COMPLETADA'), ('circle', 'COMPLETADA'),
    ('irregular_no_fit', 'SIN_SOLUCION'),
])
def test_valid_geometry_runs_all_six_engines_including_no_solution(api, session_factory, scenario, expected):
    client, _, ids, headers, coordinator, _ = api
    with session_factory() as session:
        config = session.scalar(select(Configuracion))
        sheet = session.get(Plancha, 5)
        if scenario == 'no_stock': sheet.cantidad = 0
        if scenario == 'no_fit': sheet.ancho_mm = sheet.alto_mm = 1
        if scenario == 'margin': config.margen_mm = Decimal('0.01')
        if scenario == 'separation':
            config.separacion_mm = Decimal('0.01')
        if scenario == 'rotation':
            sheet.ancho_mm, sheet.alto_mm = 2, 4
            for piece in session.scalars(select(Pieza)):
                piece.geometria = dict(type='RECTANGULO', width_mm=3, height_mm=1)
                piece.area_mm2 = 3
        if scenario == 'fractional': config.resolucion_raster_mm = Decimal('0.125')
        if scenario == 'circle':
            for piece in session.scalars(select(Pieza)):
                piece.tipo_forma = 'CIRCUNFERENCIA'
                piece.geometria = dict(type='CIRCUNFERENCIA', radius_mm=1)
                piece.area_mm2 = Decimal('3.14')
        if scenario == 'irregular_no_fit':
            sheet.cantidad = 0
            remnant(session, dict(type='POLIGONO_CONVEXO', vertices_mm=[[0, 0], [4, 0], [0, 4]]))
            session.flush()
            session.scalar(select(Retazo)).area_mm2 = 8
            for piece in session.scalars(select(Pieza)):
                piece.geometria = dict(type='RECTANGULO', width_mm=3, height_mm=3)
                piece.area_mm2 = 9
        if scenario == 'negative_origin':
            for piece in session.scalars(select(Pieza)):
                piece.tipo_forma = 'POLIGONO_CONVEXO'
                piece.geometria = dict(type='POLIGONO_CONVEXO', vertices_mm=[[-2, -2], [0, -2], [-2, 0]])
                piece.area_mm2 = 2
        session.commit()
    before_inventory = database_state(session_factory)
    path, _ = start(api, 'ta047-valid-0001')
    current = completed(api, path)
    assert current.status == expected
    assert current.methods == ['FF', 'BF', 'WF', 'HF', 'M5', 'M6-BS']
    assert all(e.result_available for e in current.executions)
    if scenario == 'rotation':
        for execution in current.executions:
            result = client.get(f'{path}/executions/{execution.execution_id}', headers=headers).json()['result']
            assert any(Decimal(p['rotation_deg']) != 0 for p in result['placements'])
    if expected == 'SIN_SOLUCION':
        assert all(e.diagnostic.termination_reason == 'NO_FIT' and not e.eligible for e in current.executions)
    after = database_state(session_factory)
    for table in ('planchas', 'retazos', 'movimientos_inventario'):
        assert after[table] == before_inventory[table]
    assert coordinator.admission.active() == 0
    # A replay returns the frozen input even after the live source becomes invalid.
    with session_factory() as session:
        session.get(Plancha, 5).ancho_mm = 4001
        session.commit()
    replay = client.post('/api/optimization/comparisons-v2', json={'order_ids': ids},
        headers={**headers, 'Idempotency-Key': 'ta047-valid-0001'})
    assert replay.status_code == 201 and replay.json() == current.model_dump(mode='json')


def test_rejected_request_preserves_previous_comparison_events_and_masks(api, session_factory):
    client, _, ids, headers, coordinator, _ = api
    path, _ = start(api, 'ta047-retained-0001')
    current = completed(api, path)
    job = coordinator.job
    events = tuple(job.events)
    contexts = tuple(job.store.contexts)
    assert events and contexts and not job.disposed
    execution = current.executions[0]
    visual_path = f'{path}/executions/{execution.execution_id}/visual'
    visual = client.get(visual_path, headers=headers).json()
    assert visual['items']
    # A new pending order must be rejected without retiring the completed job.
    with session_factory() as session:
        from app.modules.orders.infrastructure.repositories import SQLAlchemyOrderRepository
        piece = session.scalar(select(Pieza).where(Pieza.id_pedido == ids[0]))
        row = {name: getattr(piece, name) for name in ('tipo_forma', 'cantidad', 'dimensiones',
            'geometria', 'id_tipo_vidrio', 'espesor_mm', 'area_mm2')}
        order_id = SQLAlchemyOrderRepository(session).create_order(api[1], [row], id_cliente=41)
        session.get(Plancha, 5).ancho_mm = 4001
        session.commit()
    before = database_state(session_factory)
    response = client.post('/api/optimization/comparisons-v2', json={'order_ids': [order_id]},
        headers={**headers, 'Idempotency-Key': 'ta047-retained-0002'})
    assert response.status_code == 422, response.text
    assert response.json()['detail']['code'] == 'INVALID_INPUT'
    assert database_state(session_factory) == before
    assert coordinator.admission.active() == 0
    assert coordinator.job is job and not job.disposed
    assert tuple(job.events) == events and tuple(job.store.contexts) == contexts
    assert client.get(visual_path, headers=headers).json() == visual
    assert client.get(path + '/events', headers=headers).status_code == 200
