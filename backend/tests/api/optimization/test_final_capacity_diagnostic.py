"""Characterize existing capacity boundaries without allocating oversized rasters."""
from datetime import datetime, timezone
from decimal import Decimal as D
import json
import pytest
from sqlalchemy import func, select

from app.models import MovimientoInventario, Optimizacion, Pedido, Pieza, Plancha
from tests.api.optimization.test_comparisons_api import api, prepared, completed  # noqa: F401


@pytest.mark.parametrize('scenario', ['no-fit','oversized-piece','stock-count','oversized-stock-with-usable-source','raster-estimate'])
def test_capacity_rejections_and_order_lifecycle_are_explicit(api, session_factory, run_admission, record_property, scenario):
    client, ids, headers, runtime, _ = api
    with session_factory() as session:
        piece = session.scalar(select(Pieza).where(Pieza.id_pedido==ids[0]))
        if scenario in ('no-fit','oversized-piece'):
            width,height = (5,5) if scenario=='no-fit' else (4001,1)
            piece.dimensiones = {'width_mm':width,'height_mm':height}
            piece.geometria = dict(type='RECTANGULO',width_mm=width,height_mm=height)
            piece.area_mm2 = width * height
        if scenario=='stock-count': session.get(Plancha,5).cantidad = 51
        if scenario=='oversized-stock-with-usable-source':
            session.add(Plancha(id_plancha=6,ancho_mm=4001,alto_mm=1,cantidad=1,estado=True,
                fecha_registro=datetime.now(timezone.utc),id_tipo_vidrio=7,espesor_mm=6))
        if scenario=='raster-estimate':
            for i in range(12):
                session.add(Pieza(id_pedido=ids[0],id_tipo_vidrio=7,espesor_mm=6,tipo_forma='RECTANGULO',cantidad=1,
                    geometria=dict(type='RECTANGULO',width_mm=2000+i,height_mm=2000),area_mm2=(2000+i)*2000))
        before_stock = [(p.id_plancha,p.cantidad,p.estado) for p in session.scalars(select(Plancha).order_by(Plancha.id_plancha))]
        session.commit()
    response = client.post('/api/optimization/comparisons',headers={**headers,'Idempotency-Key':'capacity-'+scenario},json={'order_ids':ids})
    detail, final = None, None
    if scenario in ('oversized-piece','stock-count','raster-estimate'):
        assert response.status_code == 422, response.text
        detail = response.json()['detail']
        assert detail['code'] == ('INVALID_INPUT' if scenario=='oversized-piece' else 'LOAD_LIMIT_EXCEEDED')
        assert runtime.job is None
    else:
        assert response.status_code == 201, response.text
        final = completed(api,response.headers['location'])
        runtime.job.thread.join(timeout=5)
        assert runtime.job.runner.last_report['all_workers_stopped']
        if scenario=='oversized-stock-with-usable-source':
            assert final['status']=='FALLIDA'
            assert all(e['failure_code']=='EXECUTION_FAILED' for e in final['executions'])
        else:
            assert final['status']=='SIN_SOLUCION' and not final['incomplete']
            assert all(e['status']=='COMPLETADA' and not e['complete'] for e in final['executions'])
    with session_factory() as session:
        assert [session.get(Pedido,i).estado for i in ids] == ['PENDIENTE']*len(ids)
        assert [(p.id_plancha,p.cantidad,p.estado) for p in session.scalars(select(Plancha).order_by(Plancha.id_plancha))] == before_stock
        assert session.scalar(select(func.count()).select_from(MovimientoInventario)) == 0
        assert session.scalar(select(func.count()).select_from(Optimizacion)) == (1 if final else 0)
    assert run_admission.active() == 0
    record_property('capacity_diagnostic',json.dumps(dict(scenario=scenario,http=response.status_code,detail=detail,
        final_status=final['status'] if final else None,orders_pending=True,inventory_unchanged=True,
        accepted_before_failure=bool(final),workers_started=bool(final))))
