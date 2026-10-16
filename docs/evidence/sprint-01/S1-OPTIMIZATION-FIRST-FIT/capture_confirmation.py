"""Real local PostgreSQL + HTTP acceptance/calculation/confirmation/repeat/GET.

Run from backend with the installed test PostgreSQL runtime. No Supabase/UI.
"""
import os,sys,secrets,json,tempfile
from pathlib import Path
from datetime import datetime,timezone
from functools import partial
sys.path.insert(0,str(Path.cwd()))
os.environ['PYTHON_DOTENV_DISABLED']='1'
os.environ['DATABASE_URL']='sqlite://'
os.environ['SECRET_KEY']=secrets.token_urlsafe(48)
os.environ['TOKEN_MINUTOS']='480'
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select,text
from fastapi.testclient import TestClient
from tests.integration.postgres_support import temporary_postgres,new_database,upgrade
from app.models import (Rol,Usuario,TipoVidrio,TipoVidrioEspesor,Cliente,Configuracion,Plancha,Retazo,
                        Pedido,MovimientoInventario,EjecucionOptimizacion)
from app.modules.authentication.infrastructure.permission_seed import seed_permissions
from app.modules.authentication.presentation.dependencies import get_database_session
from app.modules.orders.infrastructure.repositories import SQLAlchemyOrderRepository
from app.modules.inventory.infrastructure.repository import SqlAlchemyInventoryRepository
from app.modules.optimization.infrastructure.stock_adapter import InventoryStockAdapter
from app.modules.optimization.infrastructure.run_uow import SqlRunUnitOfWork
from app.modules.optimization.application.calculation import CalculateRun
from app.modules.optimization.presentation.run_routes import get_run_unit_of_work,get_run_calculator
from app.shared.security import create_access_token
from main import app
out=Path('../docs/evidence/sprint-01/S1-OPTIMIZATION-FIRST-FIT')

def save(name,value):
    (out/('confirmation-example-'+name+'.json')).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

with tempfile.TemporaryDirectory(prefix='newglass-confirmation-',dir='/tmp') as directory:
    with temporary_postgres(Path(directory)) as cluster,new_database(cluster) as engine:
        result=upgrade(engine,'head')
        assert result.returncode==0,result.stderr
        factory=sessionmaker(bind=engine)
        now=datetime.now(timezone.utc)
        with factory() as s:
            s.add(Rol(id_rol=3,nombre='Operario'))
            s.flush()
            s.add(Usuario(id_usuario=1,dni='74000001',usuario='O74000001',nombres='Ejemplo',apellidos='Local',password_hash='synthetic-unused',id_rol=3,fecha_creacion=now,estado=True))
            s.add_all([TipoVidrio(id_tipo_vidrio=i,nombre=f'Ejemplo FF {i}',estado=True) for i in (7,8)])
            s.flush()
            s.add_all([TipoVidrioEspesor(id_tipo_vidrio=i,espesor_mm=t) for i,t in ((7,6),(8,4))])
            s.add(Cliente(id_cliente=41,nombre_razon_social='Ejemplo local',estado=True,fecha_registro=now))
            s.add(Configuracion(id_configuracion=1,version=1,separacion_mm=0,margen_mm=0,resolucion_raster_mm=1,paso_angular_grados=90,ancho_min_retazo_mm=1,alto_min_retazo_mm=1,vigente=True,id_usuario_creacion=1,fecha_creacion=now))
            s.flush()
            s.add(Plancha(id_plancha=5,ancho_mm=6,alto_mm=2,espesor_mm=6,cantidad=4,estado=True,fecha_registro=now,id_tipo_vidrio=7))
            s.add(Retazo(id_retazo=9,codigo='EXAMPLE-R9',espesor_mm=4,geometria={'type':'RECTANGULO','width_mm':4,'height_mm':2},area_mm2=8,estado=True,fecha_registro=now,id_tipo_vidrio=8))
            s.commit()
            seed_permissions(s)
            repo=SQLAlchemyOrderRepository(s)
            piece=dict(tipo_forma='RECTANGULO',cantidad=2,dimensiones={'width_mm':2,'height_mm':2},geometria={'type':'RECTANGULO','width_mm':2,'height_mm':2},id_tipo_vidrio=7,espesor_mm=6,area_mm2=4)
            ids=[repo.create_order(1,[piece],id_cliente=41),repo.create_order(1,[piece,piece|{'id_tipo_vidrio':8,'espesor_mm':4}],id_cliente=41)]
        def state():
            with factory() as s:
                return dict(sheets=[dict(id=p.id_plancha,quantity=p.cantidad,active=p.estado) for p in s.scalars(select(Plancha).order_by(Plancha.id_plancha))],
                    remnants=[dict(id=r.id_retazo,code=r.codigo,active=r.estado,geometry=r.geometria,area_mm2=str(r.area_mm2),execution_origin=r.id_ejecucion_origen) for r in s.scalars(select(Retazo).order_by(Retazo.id_retazo))],
                    orders={str(i):s.get(Pedido,i).estado for i in ids},
                    movements=[dict(id=m.id_movimiento,optimization_id=m.id_optimizacion,sheet_id=m.id_plancha,remnant_id=m.id_retazo,quantity=m.cantidad_afectada,event=m.tipo_evento,actor_id=m.id_usuario,at=m.fecha.isoformat(),observation=m.observacion) for m in s.scalars(select(MovimientoInventario).order_by(MovimientoInventario.id_movimiento))])
        def session_override():
            with factory() as s:yield s
        uow=partial(SqlRunUnitOfWork,factory)
        calculator=CalculateRun(uow,InventoryStockAdapter(SqlAlchemyInventoryRepository(factory)))
        app.dependency_overrides[get_database_session]=session_override
        app.dependency_overrides[get_run_unit_of_work]=lambda:uow
        app.dependency_overrides[get_run_calculator]=lambda:calculator
        headers={'Authorization':'Bearer '+create_access_token(1,'O74000001','Operario')}
        before=state()
        with TestClient(app) as client:
            stream=client.post('/api/optimization/runs',json={'order_ids':ids},headers=headers)
            assert stream.status_code==201,stream.text
            (out/'confirmation-example-stream.ndjson').write_text(stream.text,encoding='utf-8')
            url=stream.headers['location']
            before_dto=client.get(url,headers=headers).json()
            after_simulation=state()
            for key in ('sheets','remnants','movements'):assert before[key]==after_simulation[key]
            assert before_dto['completo'] and before_dto['confirmable'] and not before_dto['confirmed']
            response=client.post(url+'/confirm',headers=headers)
            assert response.status_code==200,response.text
            after_dto=client.get(url,headers=headers).json()
            after_confirmation=state()
            repeated=client.post(url+'/confirm',headers=headers)
            assert repeated.status_code==409 and repeated.json()['detail']['code']=='ALREADY_CONFIRMED'
            assert state()==after_confirmation
            assert after_dto['confirmed'] and not after_dto['confirmable']
            assert after_dto['placements']==before_dto['placements'] and after_dto['total_units']==6
            assert len(response.json()['materials_consumed'])==3 and len(response.json()['remnants_created'])==1
            assert after_confirmation['sheets'][0]['quantity']==2
            assert next(r for r in after_confirmation['remnants'] if r['id']==9)['active'] is False
            assert set(after_confirmation['orders'].values())=={'CONFIRMADO'}
            assert sorted(m['quantity'] for m in after_confirmation['movements'])==[1,2]
            save('before',before_dto)
            save('response',response.json())
            save('after',after_dto)
            save('repeat',dict(http_status=repeated.status_code,body=repeated.json()))
        with factory() as s:
            save('stock',dict(alembic_head=s.scalar(text('SELECT version_num FROM alembic_version')),
                order_ids=ids,before=before,after_simulation=after_simulation,after_confirmation=after_confirmation,
                confirmation_receipt=s.scalar(select(EjecucionOptimizacion)).patron_resultado['confirmation']))
        app.dependency_overrides.clear()
print('Real HTTP/PostgreSQL: 2 orders, 6 placements, PLANCHA 4->2, RETAZO consumed once, 1 valid residual, repeat409, canonical confirmed=true.')
