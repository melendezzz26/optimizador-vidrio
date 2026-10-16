"""Real HTTP -> PostgreSQL -> FF -> live NDJSON -> canonical GET; no UI mocks."""
import asyncio
import json
from decimal import Decimal
from functools import partial

import pytest
from pydantic import TypeAdapter
from sqlalchemy import select, func, delete

from app.models import (Pedido, Plancha, Retazo, Pieza, MovimientoInventario, Optimizacion,
                        RolPermiso, Permiso, Configuracion)
from app.shared.security import create_access_token
from app.modules.optimization.application.calculation import CalculateRun
from app.modules.optimization.application.runs import AcceptRun
from app.modules.optimization.infrastructure.stock_adapter import InventoryStockAdapter
from app.modules.inventory.infrastructure.repository import SqlAlchemyInventoryRepository
from app.modules.optimization.presentation.run_routes import get_run_unit_of_work, get_run_calculator
from app.modules.optimization.presentation.run_schemas import OptimizationEventV1, RunResponseV1, ErrorResponseV1
from app.modules.optimization.presentation.run_stream import LiveRunStream
from main import app
from tests.integration.optimization.test_runs import prepared  # noqa: F401

BASE = '/api/optimization/runs'
EVENT = TypeAdapter(OptimizationEventV1)


@pytest.fixture
def run_api(client, session_factory, prepared):
    actor, ids, uow = prepared
    calculator = CalculateRun(uow, InventoryStockAdapter(SqlAlchemyInventoryRepository(session_factory)))
    app.dependency_overrides[get_run_unit_of_work] = lambda: uow
    app.dependency_overrides[get_run_calculator] = lambda: calculator
    headers = {'Authorization': 'Bearer ' + create_access_token(actor, 'O73000001', 'Operario')}
    yield client, ids, headers, uow, calculator
    app.dependency_overrides.pop(get_run_unit_of_work, None)
    app.dependency_overrides.pop(get_run_calculator, None)


def parse(response):
    assert response.status_code == 201, response.text
    assert response.headers['content-type'].startswith('application/x-ndjson')
    assert response.headers['cache-control'] == 'no-cache'
    assert response.content.endswith(b'\n')
    events = [EVENT.validate_json(line).model_dump(mode='json') for line in response.iter_lines()]
    assert [e['sequence'] for e in events] == list(range(1,len(events)+1))
    assert len({e['id_optimizacion'] for e in events}) == 1
    assert events[0]['event'] == 'optimization_started'
    return events


@pytest.mark.parametrize('quantity,expected',[(2,'COMPLETADA'),(1,'SIN_SOLUCION'),(0,'SIN_SOLUCION')])
def test_stream_real_ff_canonical_decimal_and_inventory_intact(run_api, session_factory, quantity, expected, monkeypatch):
    client, ids, headers, uow, _ = run_api
    with session_factory() as s:
        s.get(Plancha, 5).cantidad = quantity
        s.commit()
    response = client.post(BASE, json={'order_ids':ids}, headers=headers)
    events = parse(response)
    placed = [e['data'] for e in events if e['event'] == 'piece_placed']
    assert len(placed) == quantity * 2
    assert [p['placed_units'] for p in placed] == list(range(1,len(placed)+1))
    assert all(p['total_units'] == 4 and p['unit_index'] >= 1 and p['stock_unit_index'] >= 1 for p in placed)
    assert all(p['material_source'] == 'PLANCHA' and isinstance(p['x_mm'],str) for p in placed)
    assert events[-1]['data']['estado'] == expected
    assert events[-1]['event'] == 'optimization_completed'
    assert events[-1]['data']['result_url'] == response.headers['location']
    monkeypatch.setattr('app.modules.optimization.domain.first_fit.FirstFitOptimizer.optimize',lambda *a,**k:pytest.fail('GET must not run FF'))
    result = client.get(response.headers['location'], headers=headers)
    assert result.status_code == 200, result.text
    dto = RunResponseV1.model_validate(result.json())
    assert dto.estado.value == expected and dto.total_units == 4
    assert dto.confirmable is (expected == 'COMPLETADA')
    assert dto.metrics_available is bool(placed)
    with session_factory() as s:
        assert s.get(Plancha, 5).cantidad == quantity
        assert s.scalar(select(func.count()).select_from(Retazo)) == 0
        assert s.scalar(select(func.count()).select_from(MovimientoInventario)) == 0


@pytest.mark.parametrize('path,method',[('/runs','post'),('/runs/1','get')])
def test_new_routes_401_t1_error(run_api,path,method):
    client,*_ = run_api
    response = getattr(client,method)('/api/optimization'+path)
    assert response.status_code == 401
    assert ErrorResponseV1.model_validate(response.json()).detail.code == 'UNAUTHENTICATED'
    assert response.headers['www-authenticate'] == 'Bearer'


@pytest.mark.parametrize('code,path,method',[('optimization.execute','/runs','post'),('optimization.view','/runs/1','get')])
def test_revoked_dynamic_permission_403(run_api,session_factory,code,path,method):
    client,ids,headers,*_ = run_api
    with session_factory() as s:
        pid = s.scalar(select(Permiso.id_permiso).where(Permiso.codigo == code))
        s.execute(delete(RolPermiso).where(RolPermiso.id_rol==3,RolPermiso.id_permiso==pid))
        s.commit()
    response = client.request(method,'/api/optimization'+path,headers=headers,json={'order_ids':ids} if method=='post' else None)
    assert response.status_code == 403
    assert ErrorResponseV1.model_validate(response.json()).detail.code == 'FORBIDDEN'


@pytest.mark.parametrize('body,status,code', [({'order_ids':[]},422,'INVALID_INPUT'),({'order_ids':[1,1]},422,'INVALID_INPUT'),
    ({'order_ids':[1,99999]},404,'NOT_FOUND'),({'orders':[1]},422,'INVALID_INPUT'),({'order_ids':[True]},422,'INVALID_INPUT')])
def test_preflight_error_no_partial_start(run_api,session_factory,body,status,code):
    client,ids,headers,*_ = run_api
    response = client.post(BASE,json=body,headers=headers)
    assert response.status_code == status,response.text
    assert ErrorResponseV1.model_validate(response.json()).detail.code == code
    with session_factory() as s:
        assert [s.get(Pedido,i).estado for i in ids] == ['PENDIENTE']*2
        assert s.scalar(select(func.count()).select_from(Optimizacion)) == 0


def test_config_conflict_and_canonical_404(run_api,session_factory):
    client,ids,headers,*_ = run_api
    with session_factory() as s:
        s.scalar(select(Configuracion)).paso_angular_grados = None
        s.commit()
    assert client.post(BASE,json={'order_ids':ids},headers=headers).status_code == 409
    response = client.get(BASE+'/99999',headers=headers)
    assert response.status_code == 404
    assert ErrorResponseV1.model_validate(response.json()).detail.code == 'NOT_FOUND'


def test_unexpected_failure_has_safe_event_durable_failed_not_no_solution(run_api,session_factory,monkeypatch):
    from app.modules.optimization.domain.first_fit import FirstFitOptimizer
    client,ids,headers,*_ = run_api
    original = FirstFitOptimizer.optimize
    def broken(self,problem,on_event=None):
        def callback(e):
            on_event(e)
            if e.kind == 'piece_placed':
                raise RuntimeError('SQL PASSWORD PRIVATE INTERNAL synthetic crash')
        return original(self,problem,callback)
    monkeypatch.setattr(FirstFitOptimizer,'optimize',broken)
    response = client.post(BASE,json={'order_ids':ids},headers=headers)
    events = parse(response)
    assert events[-1]['event'] == 'optimization_failed'
    assert events[-1]['data']['code'] == 'CALCULATION_FAILED'
    assert 'PRIVATE' not in response.text
    canonical = client.get(response.headers['location'],headers=headers).json()
    assert canonical['estado'] == 'FALLIDA' and not canonical['confirmable']
    assert canonical['placed_units'] == 1  # Retains the real diagnostic placement.
    with session_factory() as s:
        assert [s.get(Pedido,i).estado for i in ids] == ['EN_OPTIMIZACION']*2
        assert s.get(Plancha,5).cantidad == 2


def test_live_event_observable_before_calculation_and_db_completion(run_api):
    client,ids,headers,uow,calculator = run_api
    accepted = AcceptRun(uow).execute(ids, 1)
    async def inspect():
        stream = LiveRunStream(uow,calculator).lines(accepted)
        seen = []
        async for raw in stream:
            e = json.loads(raw)
            seen.append(e)
            if e['event'] == 'piece_placed':
                with uow() as tx:
                    durable = tx.runs.get(accepted.optimization_id)
                assert durable.status.value == 'EN_EJECUCION'
                assert durable.result.placed_units == 0
        assert seen[-1]['event'] == 'optimization_completed'
    asyncio.run(inspect())


def test_disconnect_marks_failed_without_resetting_orders(run_api,session_factory):
    client,ids,headers,uow,calculator = run_api
    accepted = AcceptRun(uow).execute(ids, 1)
    async def disconnect():
        stream = LiveRunStream(uow,calculator).lines(accepted)
        while True:
            event = json.loads(await anext(stream))
            if event['event']=='piece_placed':
                break
        await stream.aclose()
    asyncio.run(disconnect())
    with uow() as tx:
        run = tx.runs.get(accepted.optimization_id)
    assert run.status.value == 'FALLIDA' and run.result.placed_units == 1
    with session_factory() as s:
        assert [s.get(Pedido,i).estado for i in ids] == ['EN_OPTIMIZACION']*2
        assert s.get(Plancha,5).cantidad == 2


def test_multimaterial_groups_and_live_materials(run_api,session_factory):
    from datetime import datetime, timezone
    client,ids,headers,*_ = run_api
    with session_factory() as s:
        piece = s.scalar(select(Pieza).where(Pieza.id_pedido==ids[1]))
        piece.id_tipo_vidrio, piece.espesor_mm = 8, Decimal(4)
        s.add(Retazo(id_retazo=9,codigo='MATERIAL-B',geometria={'type':'RECTANGULO','width_mm':4,'height_mm':2},
            area_mm2=8,espesor_mm=4,id_tipo_vidrio=8,estado=True,fecha_registro=datetime.now(timezone.utc)))
        s.commit()
    response = client.post(BASE,json={'order_ids':ids},headers=headers)
    events = parse(response)
    groups = [e['data'] for e in events if e['event']=='group_completed']
    assert [g['total_units'] for g in groups] == [2,2]
    assert [g['placed_units'] for g in groups] == [2,2]
    assert {e['data']['material_source'] for e in events if e['event']=='piece_placed'} == {'PLANCHA','RETAZO'}
    canonical = client.get(response.headers['location'],headers=headers).json()
    assert canonical['estado']=='COMPLETADA' and len(canonical['groups'])==2
    with session_factory() as s:
        assert s.get(Retazo,9).estado is True
        assert s.get(Retazo,9).area_mm2==8
        assert s.get(Plancha,5).cantidad==2
        assert s.scalar(select(func.count()).select_from(MovimientoInventario))==0


@pytest.mark.parametrize('capability',['optimization.view','optimization.execute'])
def test_capabilities_are_independent_without_role_shortcuts(run_api,session_factory,capability):
    client,ids,headers,uow,_ = run_api
    if capability == 'optimization.view':
        accepted = AcceptRun(uow).execute(ids,1)
    with session_factory() as s:
        keep = s.scalar(select(Permiso.id_permiso).where(Permiso.codigo==capability))
        s.execute(delete(RolPermiso).where(RolPermiso.id_rol==3,RolPermiso.id_permiso!=keep))
        s.commit()
    response = client.post(BASE,json={'order_ids':ids},headers=headers)
    if capability == 'optimization.execute':
        assert response.status_code==201,response.text
        url = response.headers['location']
        assert client.get(url,headers=headers).status_code==403
    else:
        assert response.status_code==403
        assert client.get(BASE+f'/{accepted.optimization_id}',headers=headers).status_code==200


def test_result_save_failure_has_distinct_event_and_durable_failed(run_api,session_factory,monkeypatch):
    from app.modules.optimization.infrastructure.run_uow import SqlRunRepository
    client,ids,headers,*_ = run_api
    def fail_save(*args,**kwargs):
        raise RuntimeError('PRIVATE SQL commit synthetic error')
    monkeypatch.setattr(SqlRunRepository,'save_result',fail_save)
    response=client.post(BASE,json={'order_ids':ids},headers=headers)
    events=parse(response)
    assert events[-1]['event']=='optimization_failed'
    assert events[-1]['data']['code']=='RESULT_SAVE_FAILED'
    assert 'PRIVATE' not in response.text
    result=client.get(response.headers['location'],headers=headers).json()
    assert result['estado']=='FALLIDA' and not result['confirmable']
    with session_factory() as s:
        assert [s.get(Pedido,i).estado for i in ids]==['EN_OPTIMIZACION']*2
        assert s.get(Plancha,5).cantidad==2
        assert s.scalar(select(func.count()).select_from(MovimientoInventario))==0


def test_preflight_internal_error_is_sanitized(run_api,monkeypatch):
    from app.modules.optimization.infrastructure.run_uow import SqlRunUnitOfWork
    client,ids,headers,*_=run_api
    monkeypatch.setattr(SqlRunUnitOfWork,'configuration',lambda _: (_ for _ in ()).throw(RuntimeError('PRIVATE SQL')))
    response=client.post(BASE,json={'order_ids':ids},headers=headers)
    assert response.status_code==500
    assert ErrorResponseV1.model_validate(response.json()).detail.code=='INTERNAL_ERROR'
    assert 'PRIVATE' not in response.text


@pytest.mark.parametrize("asgi_version",["2.0","2.4"])
def test_real_asgi_disconnect_is_cooperative_and_durable(run_api,session_factory,asgi_version):
    client,ids,headers,uow,_=run_api
    async def disconnect_request():
        disconnected=asyncio.Event()
        body_sent=False
        async def receive():
            nonlocal body_sent
            if not body_sent:
                body_sent=True
                return {'type':'http.request','body':json.dumps({'order_ids':ids}).encode(),'more_body':False}
            await disconnected.wait()
            return {'type':'http.disconnect'}
        async def send(message):
            if message['type']=='http.response.body' and b'"event":"piece_placed"' in message.get('body',b''):
                if asgi_version=='2.4':
                    raise OSError('Client closed connection')
                disconnected.set()
                await asyncio.sleep(0)  # Allow the ASGI disconnect listener to cancel delivery.
        scope={'type':'http','asgi':{'version':'3.0','spec_version':asgi_version},'http_version':'1.1',
            'method':'POST','scheme':'http','path':BASE,'raw_path':BASE.encode(),'query_string':b'',
            'headers':[(b'content-type',b'application/json'),(b'authorization',headers['Authorization'].encode())],
            'client':('127.0.0.1',10000),'server':('testserver',80),'root_path':''}
        if asgi_version=='2.4':
            from starlette.requests import ClientDisconnect
            with pytest.raises(ClientDisconnect):
                await asyncio.wait_for(app(scope,receive,send),timeout=10)
        else:
            await asyncio.wait_for(app(scope,receive,send),timeout=10)
        # Cancellation may return before the producer's independent failure commit.
        for _ in range(100):
            with session_factory() as s:
                parent=s.scalar(select(Optimizacion))
                if parent.estado=='FALLIDA':
                    return parent.id_optimizacion
            await asyncio.sleep(0.02)
        pytest.fail('Disconnect did not record durable failure')
    identifier=asyncio.run(disconnect_request())
    with uow() as tx:
        failed=tx.runs.get(identifier)
    assert failed.status.value=='FALLIDA'
    assert not failed.confirmable
    with session_factory() as s:
        assert [s.get(Pedido,i).estado for i in ids]==['EN_OPTIMIZACION']*2
        assert s.get(Plancha,5).cantidad==2
        assert s.scalar(select(func.count()).select_from(MovimientoInventario))==0


def test_browser_can_read_location_for_canonical_result(run_api):
    client,ids,headers,*_=run_api
    response=client.post(BASE,json={'order_ids':ids},headers={**headers,'Origin':'http://localhost:5173'})
    assert response.status_code==201
    assert response.headers['access-control-allow-origin']=='http://localhost:5173'
    assert 'Location' in response.headers['access-control-expose-headers']
    assert response.headers['location'].startswith(BASE+'/')


def test_rotated_placement_geometry_is_durable_and_used_without_second_rotation(run_api,session_factory):
    client,ids,headers,*_=run_api
    with session_factory() as s:
        piece=s.scalar(select(Pieza).where(Pieza.id_pedido==ids[0]))
        piece.geometria={'type':'RECTANGULO','width_mm':3,'height_mm':1}
        piece.area_mm2=3
        sheet=s.get(Plancha,5)
        sheet.ancho_mm,sheet.alto_mm=2,4
        s.commit()
    response=client.post(BASE,json={'order_ids':ids[:1]},headers=headers)
    events=parse(response)
    live=[e['data'] for e in events if e['event']=='piece_placed']
    assert len(live)==2
    assert all(Decimal(p['rotation_deg'])==90 for p in live)
    assert all(p['geometria']=={'type':'RECTANGULO','width_mm':1.0,'height_mm':3.0} for p in live)
    assert [Decimal(p['x_mm']) for p in live]==[0,1]
    final=client.get(response.headers['location'],headers=headers).json()
    assert final['estado']=='COMPLETADA' and final['metrics_available']
    assert final['placements'][0]['geometria']==live[0]['geometria']
    assert Decimal(final['metrics']['area_piezas_colocadas_mm2'])==6
    assert Decimal(final['metrics']['retazo_recuperable_mm2'])==2


def test_authorization_db_session_ends_before_stream_calculation(run_api,session_factory,monkeypatch):
    from app.modules.authentication.presentation.dependencies import get_database_session
    client,ids,headers,uow,calculator=run_api
    opened=[]
    closed=[]
    original_override=app.dependency_overrides[get_database_session]
    def tracked_session():
        with session_factory() as s:
            opened.append(s)
            try:
                yield s
            finally:
                s.close()
                closed.append(s)
    original_calculate=calculator.execute
    observed=[]
    def calculate(*args,**kwargs):
        assert opened and closed==opened
        assert all(not s.in_transaction() for s in opened)
        observed.append(True)
        return original_calculate(*args,**kwargs)
    app.dependency_overrides[get_database_session]=tracked_session
    monkeypatch.setattr(calculator,'execute',calculate)
    try:
        response=client.post(BASE,json={'order_ids':ids},headers=headers)
        assert parse(response)[-1]['event']=='optimization_completed'
        assert observed==[True]
    finally:
        app.dependency_overrides[get_database_session]=original_override
