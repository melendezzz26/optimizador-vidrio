"""The confirmation endpoint uses real PostgreSQL, real FF and dynamic RBAC."""
import pytest
from sqlalchemy import select,delete
import json

from app.models import Pedido,Plancha,MovimientoInventario,RolPermiso,Permiso
from app.modules.optimization.presentation.run_schemas import ConfirmResponseV1,RunResponseV1,ErrorResponseV1
from app.modules.optimization.infrastructure.confirmation_adapter import SqlConfirmationRepository
from .test_runs_api import run_api,prepared  # noqa: F401
from tests.integration.optimization.test_confirmation import snapshot,invariant

BASE='/api/optimization/runs'


def completed(api):
    client,ids,headers,*_=api
    response=client.post(BASE,json={'order_ids':ids},headers=headers)
    assert response.status_code==201,response.text
    return response.headers['location'],headers


def test_confirm_success_t1_and_get_confirmed_with_real_history(run_api,session_factory,monkeypatch):
    client,ids,headers,*_=run_api
    url,headers=completed(run_api)
    monkeypatch.setattr('app.modules.optimization.domain.first_fit.FirstFitOptimizer.optimize',lambda *a,**k:pytest.fail('No FF search during POST confirm or GET'))
    response=client.post(url+'/confirm',headers=headers)
    assert response.status_code==200,response.text
    receipt=ConfirmResponseV1.model_validate(response.json())
    assert receipt.confirmed and len(receipt.materials_consumed)==2
    assert {s.stock_unit_index for s in receipt.materials_consumed}=={1,2}
    assert [o.id_pedido for o in receipt.orders]==ids and all(o.estado=='CONFIRMADO' for o in receipt.orders)
    canonical=client.get(url,headers=headers)
    assert canonical.status_code==200
    dto=RunResponseV1.model_validate(canonical.json())
    assert dto.confirmed and not dto.confirmable and dto.completo and dto.estado.value=='COMPLETADA'
    with session_factory() as s:
        assert s.get(Plancha,5).cantidad==0 and not s.get(Plancha,5).estado
        movement=s.scalar(select(MovimientoInventario))
        assert movement.cantidad_afectada==2 and movement.id_optimizacion==receipt.id_optimizacion
    # Inventory's public read API exposes this same persisted trace.
    from main import app
    from app.modules.inventory.presentation.dependencies import get_inventory_service
    from app.modules.inventory.application.service import InventoryService
    from app.modules.inventory.infrastructure.repository import SqlAlchemyInventoryRepository
    app.dependency_overrides[get_inventory_service]=lambda:InventoryService(SqlAlchemyInventoryRepository(session_factory))
    try:
        history=client.get('/api/inventory/planchas/5/movimientos',headers=headers)
    finally:
        app.dependency_overrides.pop(get_inventory_service,None)
    assert history.status_code==200,history.text
    assert any(m['id_optimizacion']==receipt.id_optimizacion and m['cantidad_afectada']==2 for m in history.json())
    before=snapshot(session_factory)
    repeat=client.post(url+'/confirm',headers=headers)
    assert repeat.status_code==409
    assert ErrorResponseV1.model_validate(repeat.json()).detail.code=='ALREADY_CONFIRMED'
    assert snapshot(session_factory)==before
    invariant(session_factory)


def test_confirm_401(run_api):
    client,*_=run_api
    response=client.post(BASE+'/1/confirm')
    assert response.status_code==401
    assert ErrorResponseV1.model_validate(response.json()).detail.code=='UNAUTHENTICATED'


def test_confirm_requires_own_dynamic_capability_and_revocation(run_api,session_factory):
    client,ids,headers,*_=run_api
    url,headers=completed(run_api)
    with session_factory() as s:
        pid=s.scalar(select(Permiso.id_permiso).where(Permiso.codigo=='optimization.confirm'))
        s.execute(delete(RolPermiso).where(RolPermiso.id_rol==3,RolPermiso.id_permiso==pid))
        s.commit()
    before=snapshot(session_factory)
    denied=client.post(url+'/confirm',headers=headers)
    assert denied.status_code==403
    assert ErrorResponseV1.model_validate(denied.json()).detail.code=='FORBIDDEN'
    assert snapshot(session_factory)==before


def test_only_confirm_capability_suffices_without_role_shortcuts(run_api,session_factory):
    client,ids,headers,*_=run_api
    url,headers=completed(run_api)
    with session_factory() as s:
        pid=s.scalar(select(Permiso.id_permiso).where(Permiso.codigo=='optimization.confirm'))
        s.execute(delete(RolPermiso).where(RolPermiso.id_rol==3,RolPermiso.id_permiso!=pid))
        s.commit()
    response=client.post(url+'/confirm',headers=headers)
    assert response.status_code==200,response.text
    assert client.get(url,headers=headers).status_code==403
    assert client.post(BASE,json={'order_ids':ids},headers=headers).status_code==403


def test_confirm_404(run_api):
    client,ids,headers,*_=run_api
    response=client.post(BASE+'/999999/confirm',headers=headers)
    assert response.status_code==404
    assert ErrorResponseV1.model_validate(response.json()).detail.code=='NOT_FOUND'


@pytest.mark.parametrize('body',[{}, {'placements':[]}, {'material_id':99}, None])
def test_no_client_body_can_change_the_solution(run_api,session_factory,body):
    client,ids,headers,*_=run_api
    url,headers=completed(run_api)
    before=snapshot(session_factory)
    # json=None in httpx sends no body, so explicit null tests a non-empty body.
    response=client.post(url+'/confirm',headers=headers,content='null' if body is None else json.dumps(body))
    assert response.status_code==422,response.text
    assert ErrorResponseV1.model_validate(response.json()).detail.code=='INVALID_INPUT'
    assert snapshot(session_factory)==before


def test_no_solution_422_and_no_inventory_mutation(run_api,session_factory):
    client,ids,headers,*_=run_api
    with session_factory() as s:
        s.get(Plancha,5).cantidad=0
        s.commit()
    url,headers=completed(run_api)
    before=snapshot(session_factory)
    response=client.post(url+'/confirm',headers=headers)
    assert response.status_code==422
    assert ErrorResponseV1.model_validate(response.json()).detail.code=='NOT_CONFIRMABLE'
    assert snapshot(session_factory)==before
    canonical=client.get(url,headers=headers).json()
    assert canonical['estado']=='SIN_SOLUCION' and not canonical['confirmable'] and not canonical['confirmed']


@pytest.mark.parametrize('change',['quantity','state','geometry'])
def test_stock_changed_after_calculation_409_no_partial_confirmation(run_api,session_factory,change):
    client,ids,headers,*_=run_api
    url,headers=completed(run_api)
    with session_factory() as s:
        row=s.get(Plancha,5)
        if change=='quantity': row.cantidad=1
        if change=='state': row.estado=False
        if change=='geometry': row.ancho_mm=9
        s.commit()
    before=snapshot(session_factory)
    response=client.post(url+'/confirm',headers=headers)
    assert response.status_code==409,response.text
    assert ErrorResponseV1.model_validate(response.json()).detail.code=='STOCK_CONFLICT'
    assert snapshot(session_factory)==before
    with session_factory() as s:
        assert [s.get(Pedido,i).estado for i in ids]==['OPTIMIZADO']*2
    invariant(session_factory)


def test_internal_error_is_500_safe_and_rollback_is_total(run_api,session_factory,monkeypatch):
    client,ids,headers,*_=run_api
    url,headers=completed(run_api)
    before=snapshot(session_factory)
    original=SqlConfirmationRepository.record_movements
    def fail(self,*args,**kwargs):
        original(self,*args,**kwargs)
        raise RuntimeError('PRIVATE SQL secret stack synthetic failure')
    monkeypatch.setattr(SqlConfirmationRepository,'record_movements',fail)
    response=client.post(url+'/confirm',headers=headers)
    assert response.status_code==500
    assert ErrorResponseV1.model_validate(response.json()).detail.code=='INTERNAL_ERROR'
    assert 'PRIVATE' not in response.text and 'SQL' not in response.text
    assert snapshot(session_factory)==before
    invariant(session_factory)


def test_two_real_http_confirmations_have_one_200_and_one_409(run_api,session_factory,tmp_path):
    from types import SimpleNamespace
    from app.modules.optimization.application.errors import RunError
    from tests.integration.optimization.test_confirmation_concurrency import race
    client,ids,headers,*_=run_api
    url,headers=completed(run_api)
    responses=[]
    def post():
        response=client.post(url+'/confirm',headers=headers)
        responses.append(response)
        if response.status_code==409:
            detail=ErrorResponseV1.model_validate(response.json()).detail
            raise RunError(detail.code,detail.message)
        assert response.status_code==200,response.text
        result=ConfirmResponseV1.model_validate(response.json())
        return SimpleNamespace(optimization_id=result.id_optimizacion)
    race(session_factory,'optimizaciones',[post,post],tmp_path)
    assert sorted(r.status_code for r in responses)==[200,409]
    assert next(r for r in responses if r.status_code==409).json()['detail']['code']=='ALREADY_CONFIRMED'
    with session_factory() as s:
        assert s.get(Plancha,5).cantidad==0
        assert s.scalar(select(MovimientoInventario.cantidad_afectada))==2
    invariant(session_factory)


@pytest.mark.parametrize('code,status,error_code',[('P0001',500,'INTERNAL_ERROR'),('40001',409,'STATE_CONFLICT')])
def test_real_postgres_error_is_safe_and_rolls_back_http_confirmation(run_api,session_factory,code,status,error_code):
    from tests.integration.optimization.test_confirmation_rollback import failing_trigger
    client,ids,headers,*_=run_api
    url,headers=completed(run_api)
    before=snapshot(session_factory)
    with failing_trigger(session_factory,'movimientos_inventario','INSERT',"NEW.tipo_evento='CONSUMO_OPTIMIZACION'",code):
        response=client.post(url+'/confirm',headers=headers)
    assert response.status_code==status,response.text
    assert ErrorResponseV1.model_validate(response.json()).detail.code==error_code
    assert 'SYNTHETIC' not in response.text and 'SQL' not in response.text
    assert snapshot(session_factory)==before
    invariant(session_factory)


@pytest.mark.parametrize('corruption,status,code',[
    ('execution_complete',422,'NOT_CONFIRMABLE'),('missing_placement',422,'NOT_CONFIRMABLE'),
    ('selected',422,'NOT_CONFIRMABLE'),('residual',422,'NOT_CONFIRMABLE'),
    ('contour',422,'NOT_CONFIRMABLE'),('missing_stock',409,'STOCK_CONFLICT')])
def test_persisted_result_is_revalidated_not_blindly_trusted(run_api,session_factory,corruption,status,code):
    from copy import deepcopy
    from app.models import EjecucionOptimizacion,Optimizacion
    client,ids,headers,*_=run_api
    url,headers=completed(run_api)
    with session_factory() as s:
        execution=s.scalar(select(EjecucionOptimizacion))
        stored=deepcopy(execution.patron_resultado)
        if corruption=='execution_complete': execution.completo=False
        if corruption=='missing_placement': stored['result']['placements'].pop()
        if corruption=='selected': s.scalar(select(Optimizacion)).id_ejecucion_seleccionada=None
        if corruption=='residual': stored['residual_rectangles']=[dict(material_source='PLANCHA',material_id=5,
            stock_unit_index=1,x_mm='0',y_mm='0',width_mm='2',height_mm='2',area_mm2='4')]
        if corruption=='contour': stored['result']['placements'][0]['geometry']={'type':'RECTANGULO','width_mm':1,'height_mm':1}
        if corruption=='missing_stock':
            for group in stored['result']['problem']['groups']:
                for stock in group['stock_candidates']: stock['material_id']=99999
            for p in stored['result']['placements']: p['stock']['material_id']=99999
        execution.patron_resultado=stored
        s.commit()
    before=snapshot(session_factory)
    response=client.post(url+'/confirm',headers=headers)
    assert response.status_code==status,response.text
    assert ErrorResponseV1.model_validate(response.json()).detail.code==code
    assert snapshot(session_factory)==before
    invariant(session_factory)


def test_retazo_conflict_409_leaves_sheet_and_all_orders_unchanged(run_api,session_factory):
    from app.models import Retazo
    from tests.integration.optimization.test_confirmation import add_remnant
    client,ids,headers,*_=run_api
    add_remnant(session_factory)
    url,headers=completed(run_api)
    with session_factory() as s:
        s.get(Retazo,9).estado=False
        s.commit()
    before=snapshot(session_factory)
    response=client.post(url+'/confirm',headers=headers)
    assert response.status_code==409
    assert ErrorResponseV1.model_validate(response.json()).detail.code=='STOCK_CONFLICT'
    assert snapshot(session_factory)==before
    invariant(session_factory)
