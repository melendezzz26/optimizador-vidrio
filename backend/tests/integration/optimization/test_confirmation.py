"""Confirmation runs on real local PostgreSQL and the existing Inventory schema."""
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select, func, event

from app.models import (Pedido, Pieza, Plancha, Retazo, MovimientoInventario, Optimizacion,
    OptimizacionPedido, EjecucionOptimizacion, MaterialUtilizado, MetricaEjecucion, Configuracion)
from app.modules.optimization.application.runs import AcceptRun
from app.modules.optimization.application.calculation import CalculateRun
from app.modules.optimization.application.confirmation import ConfirmRun
from app.modules.optimization.application.errors import RunError
from app.modules.inventory.infrastructure.repository import SqlAlchemyInventoryRepository
from app.modules.optimization.infrastructure.stock_adapter import InventoryStockAdapter
from .test_runs import prepared  # noqa: F401

TABLES = (Pedido,Pieza,Plancha,Retazo,MovimientoInventario,Optimizacion,OptimizacionPedido,
          EjecucionOptimizacion,MaterialUtilizado,MetricaEjecucion)


def snapshot(factory, models=TABLES):
    with factory() as s:
        return {m.__tablename__:deepcopy([tuple(r) for r in s.execute(
            select(m.__table__).order_by(*m.__table__.primary_key.columns))]) for m in models}


def invariant(factory):
    with factory() as s:
        assert all(p.cantidad>=0 for p in s.scalars(select(Plancha)))
        duplicates=s.execute(select(MovimientoInventario.id_retazo,func.count()).where(
            MovimientoInventario.id_retazo.is_not(None),MovimientoInventario.tipo_evento=='CONSUMO_OPTIMIZACION')
            .group_by(MovimientoInventario.id_retazo).having(func.count()>1)).all()
        assert duplicates==[]
        for row in s.scalars(select(Optimizacion)):
            ids=list(s.scalars(select(OptimizacionPedido.id_pedido).where(OptimizacionPedido.id_optimizacion==row.id_optimizacion)))
            states=[s.get(Pedido,i).estado for i in ids]
            assert 'CONFIRMADO' not in states or all(v=='CONFIRMADO' for v in states)
        for movement in s.scalars(select(MovimientoInventario).where(MovimientoInventario.tipo_evento=='CONSUMO_OPTIMIZACION')):
            assert movement.id_optimizacion is not None and movement.id_usuario is not None
            assert movement.cantidad_afectada>0
            if movement.id_retazo is not None: assert movement.cantidad_afectada==1


def calculate(factory,uow,ids,actor):
    before=snapshot(factory,(Plancha,Retazo,MovimientoInventario))
    accepted=AcceptRun(uow).execute(ids,actor)
    final=CalculateRun(uow,InventoryStockAdapter(SqlAlchemyInventoryRepository(factory))).execute(accepted.optimization_id)
    assert snapshot(factory,(Plancha,Retazo,MovimientoInventario))==before
    return final


@pytest.mark.parametrize('n',[1,2])
def test_confirm_counts_distinct_physical_sheets_single_write_commit(session_factory,prepared,n,monkeypatch):
    actor,ids,uow=prepared
    with session_factory() as s:
        s.get(Plancha,5).cantidad=4
        s.commit()
    run=calculate(session_factory,uow,ids[:n],actor)
    assert run.confirmable and not run.confirmed
    monkeypatch.setattr('app.modules.optimization.domain.first_fit.FirstFitOptimizer.optimize',lambda *a,**k:pytest.fail('Confirmation reran FF'))
    commits=[]
    def committed(s): commits.append(True)
    event.listen(session_factory.class_,'after_commit',committed)
    try:
        receipt=ConfirmRun(uow).execute(run.optimization_id,actor)
    finally:
        event.remove(session_factory.class_,'after_commit',committed)
    assert commits==[True]
    assert len(receipt.materials_consumed)==n
    assert receipt.remnants_created==()
    with uow() as tx:
        canonical=tx.runs.get(run.optimization_id)
    assert canonical.confirmed and not canonical.confirmable and canonical.status.value=='COMPLETADA'
    with session_factory() as s:
        sheet=s.get(Plancha,5)
        assert sheet.cantidad==4-n and sheet.estado
        assert [s.get(Pedido,i).estado for i in ids[:n]]==['CONFIRMADO']*n
        movements=s.scalars(select(MovimientoInventario)).all()
        assert len(movements)==1
        m=movements[0]
        assert (m.id_plancha,m.id_retazo,m.cantidad_afectada,m.id_optimizacion,m.id_usuario)==(5,None,n,run.optimization_id,actor)
        assert m.tipo_evento=='CONSUMO_OPTIMIZACION' and m.fecha.tzinfo is not None
        assert s.get(Optimizacion,run.optimization_id).estado=='COMPLETADA'
    before=snapshot(session_factory)
    with pytest.raises(RunError) as error:
        ConfirmRun(uow).execute(run.optimization_id,actor)
    assert error.value.code=='ALREADY_CONFIRMED'
    assert snapshot(session_factory)==before
    invariant(session_factory)


def add_remnant(factory,identifier=9,geometry=None,area=8,glass=7,thickness=6):
    with factory() as s:
        s.add(Retazo(id_retazo=identifier,codigo=f'TEST-{identifier}',id_tipo_vidrio=glass,espesor_mm=thickness,
            geometria=geometry or {'type':'RECTANGULO','width_mm':4,'height_mm':2},area_mm2=area,estado=True,
            fecha_registro=datetime.now(timezone.utc)))
        s.commit()


def test_one_remnant_multiple_placements_consumed_once(session_factory,prepared):
    actor,ids,uow=prepared
    add_remnant(session_factory)
    run=calculate(session_factory,uow,ids[:1],actor)
    assert all(p.stock.source.value=='RETAZO' for p in run.result.placements)
    receipt=ConfirmRun(uow).execute(run.optimization_id,actor)
    assert len(receipt.materials_consumed)==1 and receipt.remnants_created==()
    with session_factory() as s:
        assert s.get(Retazo,9).estado is False
        assert s.get(Plancha,5).cantidad==2
        m=s.scalar(select(MovimientoInventario))
        assert m.id_retazo==9 and m.cantidad_afectada==1 and m.id_plancha is None
    invariant(session_factory)


def test_multimaterial_multiorder_trace_and_empty_sheet_becomes_inactive(session_factory,prepared):
    actor,ids,uow=prepared
    with session_factory() as s:
        p=s.scalar(select(Pieza).where(Pieza.id_pedido==ids[1]))
        p.id_tipo_vidrio,p.espesor_mm=8,Decimal(4)
        s.get(Plancha,5).cantidad=1
        s.commit()
    add_remnant(session_factory,glass=8,thickness=4)
    run=calculate(session_factory,uow,ids,actor)
    receipt=ConfirmRun(uow).execute(run.optimization_id,actor)
    assert {s.source.value for s in receipt.materials_consumed}=={'RETAZO','PLANCHA'}
    with session_factory() as s:
        assert s.get(Plancha,5).cantidad==0 and not s.get(Plancha,5).estado
        assert not s.get(Retazo,9).estado
        assert [s.get(Pedido,i).estado for i in ids]==['CONFIRMADO']*2
        assert s.scalar(select(func.count()).select_from(MovimientoInventario))==2
    invariant(session_factory)


@pytest.mark.parametrize('mutation',['quantity','inactive','dimensions','type','thickness','order','proposals'])
def test_stale_stock_or_state_rejects_everything(session_factory,prepared,mutation):
    actor,ids,uow=prepared
    run=calculate(session_factory,uow,ids,actor)
    with session_factory() as s:
        row=s.get(Plancha,5)
        if mutation=='quantity': row.cantidad=1
        if mutation=='inactive': row.estado=False
        if mutation=='dimensions': row.ancho_mm=5
        if mutation=='type': row.id_tipo_vidrio,row.espesor_mm=8,Decimal(4)
        if mutation=='thickness': row.espesor_mm=Decimal('5.5')
        if mutation=='order': s.get(Pedido,ids[-1]).estado='CANCELADO'
        if mutation=='proposals': s.scalar(select(MaterialUtilizado)).cantidad_utilizada=1
        s.commit()
    before=snapshot(session_factory)
    with pytest.raises(RunError) as error:
        ConfirmRun(uow).execute(run.optimization_id,actor)
    expected='STATE_CONFLICT' if mutation=='order' else 'NOT_CONFIRMABLE' if mutation=='proposals' else 'STOCK_CONFLICT'
    assert error.value.code==expected
    assert snapshot(session_factory)==before
    invariant(session_factory)


@pytest.mark.parametrize('mutation',['inactive','geometry','area','type','thickness','consumed_reactivated'])
def test_stale_remnant_never_consumes_other_material(session_factory,prepared,mutation):
    actor,ids,uow=prepared
    add_remnant(session_factory)
    run=calculate(session_factory,uow,ids[:1],actor)
    with session_factory() as s:
        row=s.get(Retazo,9)
        if mutation=='inactive': row.estado=False
        if mutation=='geometry': row.geometria={'type':'RECTANGULO','width_mm':2,'height_mm':4}
        if mutation=='area': row.area_mm2=7
        if mutation=='type': row.id_tipo_vidrio,row.espesor_mm=8,Decimal(4)
        if mutation=='thickness': row.espesor_mm=Decimal('5.5')
        if mutation=='consumed_reactivated':
            # A previous run already consumed this concrete remnant; even a raw
            # reactivation cannot grant another consumption.
            s.add(MovimientoInventario(id_retazo=9,tipo_evento='CONSUMO_OPTIMIZACION',motivo='synthetic prior consumption',
                id_usuario=actor,id_optimizacion=None,cantidad_afectada=1))
        s.commit()
    before=snapshot(session_factory)
    with pytest.raises(RunError) as error:
        ConfirmRun(uow).execute(run.optimization_id,actor)
    assert error.value.code=='STOCK_CONFLICT'
    assert snapshot(session_factory)==before
    # This test's synthetic historical movement can lack a run, unlike new writes.
    if mutation!='consumed_reactivated': invariant(session_factory)


@pytest.mark.parametrize('state',['EN_EJECUCION','SIN_SOLUCION','FALLIDA'])
def test_nonconfirmable_runs_no_writes(session_factory,prepared,state):
    actor,ids,uow=prepared
    accepted=AcceptRun(uow).execute(ids,actor)
    if state=='SIN_SOLUCION':
        with session_factory() as s:
            s.get(Plancha,5).cantidad=0
            s.commit()
        CalculateRun(uow,InventoryStockAdapter(SqlAlchemyInventoryRepository(session_factory))).execute(accepted.optimization_id)
    elif state=='FALLIDA':
        with uow() as tx: tx.runs.fail(accepted.optimization_id,'CALCULATION_FAILED')
    before=snapshot(session_factory)
    with pytest.raises(RunError) as error:
        ConfirmRun(uow).execute(accepted.optimization_id,actor)
    assert error.value.code=='NOT_CONFIRMABLE'
    assert snapshot(session_factory)==before
    invariant(session_factory)


def test_residual_created_from_oriented_contours_and_reproducible_free_cells(session_factory,prepared):
    actor,ids,uow=prepared
    with session_factory() as s:
        p=s.scalar(select(Pieza).where(Pieza.id_pedido==ids[0]))
        p.geometria={'type':'RECTANGULO','width_mm':3,'height_mm':1}
        p.area_mm2=3
        sheet=s.get(Plancha,5)
        sheet.ancho_mm,sheet.alto_mm=2,4
        s.commit()
    run=calculate(session_factory,uow,ids[:1],actor)
    assert all(p.rotation_deg==90 for p in run.result.placements)
    receipt=ConfirmRun(uow).execute(run.optimization_id,actor)
    new,=receipt.remnants_created
    assert (new.x_mm,new.y_mm,new.exact_area_mm2)==(0,3,2)
    assert new.geometry=={'type':'RECTANGULO','width_mm':2.0,'height_mm':1.0}
    with session_factory() as s:
        row=s.get(Retazo,new.remnant_id)
        execution=s.scalar(select(EjecucionOptimizacion))
        assert row.estado and row.id_ejecucion_origen==execution.id_ejecucion
        assert row.area_mm2==2 and row.id_tipo_vidrio==7 and row.espesor_mm==6
        assert row.codigo.startswith('FF-') and len(row.codigo)<=40
        assert execution.patron_resultado['confirmation']['receipt']['remnants_created'][0]['remnant_id']==new.remnant_id
    invariant(session_factory)


def test_residual_minimums_use_effective_snapshot_not_new_defaults(session_factory,prepared):
    actor,ids,uow=prepared
    with session_factory() as s:
        s.scalar(select(Pieza).where(Pieza.id_pedido==ids[0])).cantidad=1
        config=s.scalar(select(Configuracion))
        config.ancho_min_retazo_mm=5
        s.commit()
    run=calculate(session_factory,uow,ids[:1],actor)
    assert run.result.metrics.recoverable_remnant_mm2==0
    with session_factory() as s:
        s.scalar(select(Configuracion)).ancho_min_retazo_mm=0
        s.commit()
    receipt=ConfirmRun(uow).execute(run.optimization_id,actor)
    assert receipt.remnants_created==()
    invariant(session_factory)


def test_nonpersistable_tiny_residual_is_not_invented_and_metric_reflects_it(session_factory,prepared):
    actor,ids,uow=prepared
    with session_factory() as s:
        config=s.scalar(select(Configuracion))
        config.resolucion_raster_mm=Decimal('0.001')
        config.ancho_min_retazo_mm=config.alto_min_retazo_mm=0
        p=s.scalar(select(Pieza).where(Pieza.id_pedido==ids[0]))
        p.geometria={'type':'RECTANGULO','width_mm':0.1,'height_mm':0.1}
        p.area_mm2=Decimal('0.01')
        p.cantidad=1
        sheet=s.get(Plancha,5)
        sheet.ancho_mm,sheet.alto_mm=Decimal('0.11'),Decimal('0.10')
        s.commit()
    run=calculate(session_factory,uow,ids[:1],actor)
    assert run.result.metrics.recoverable_remnant_mm2==Decimal('0.001')
    receipt=ConfirmRun(uow).execute(run.optimization_id,actor)
    assert receipt.remnants_created==()
    with uow() as tx:
        confirmed=tx.runs.get(run.optimization_id)
    assert confirmed.confirmed
    assert confirmed.result.metrics.recoverable_remnant_mm2==0
    assert confirmed.result.metrics.waste_mm2==Decimal('0.001')
    with session_factory() as s:
        assert s.scalar(select(func.count()).select_from(Retazo))==0
        stored=s.scalar(select(EjecucionOptimizacion)).patron_resultado
        assert stored['confirmation']['skipped_residuals'][0]['reason']=='INVENTORY_GEOMETRY_NOT_PERSISTABLE'
    invariant(session_factory)


def test_irregular_residual_is_contained_in_triangle_not_its_bounding_box(session_factory,prepared):
    actor,ids,uow=prepared
    add_remnant(session_factory,geometry={'type':'POLIGONO_CONVEXO','vertices_mm':[[0,0],[8,0],[0,8]]},area=32)
    run=calculate(session_factory,uow,ids[:1],actor)
    receipt=ConfirmRun(uow).execute(run.optimization_id,actor)
    new,=receipt.remnants_created
    # Every corner of an axis-aligned rectangle inside x+y<=8 stays inside.
    assert new.x_mm+new.y_mm+Decimal(str(new.geometry['width_mm']))+Decimal(str(new.geometry['height_mm']))<=8
    assert new.exact_area_mm2<=Decimal(32)-8
    with session_factory() as s:
        assert not s.get(Retazo,9).estado
        assert s.get(Plancha,5).cantidad==2
        assert s.get(Retazo,new.remnant_id).id_ejecucion_origen is not None
    invariant(session_factory)
