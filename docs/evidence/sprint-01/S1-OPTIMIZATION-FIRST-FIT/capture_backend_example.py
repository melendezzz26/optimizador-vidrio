"""Capture a real local HTTP calculation; no external database or frontend."""
import os, sys, secrets, json, tempfile
from pathlib import Path
from datetime import datetime, timezone
from functools import partial
sys.path.insert(0, str(Path.cwd()))
os.environ['PYTHON_DOTENV_DISABLED']='1'
os.environ['DATABASE_URL']='sqlite://'
os.environ['SECRET_KEY']=secrets.token_urlsafe(48)
os.environ['TOKEN_MINUTOS']='480'
from tests.integration.postgres_support import temporary_postgres, new_database, upgrade
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, func, text
from fastapi.testclient import TestClient
from app.models import (Rol,Usuario,TipoVidrio,TipoVidrioEspesor,Cliente,Configuracion,Plancha,
                        Pedido,Retazo,MovimientoInventario)
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
with tempfile.TemporaryDirectory(prefix='newglass-capture-',dir='/tmp') as directory:
    with temporary_postgres(Path(directory)) as cluster, new_database(cluster) as engine:
        result=upgrade(engine,'head')
        assert result.returncode==0,result.stderr
        factory=sessionmaker(bind=engine)
        now=datetime.now(timezone.utc)
        with factory() as s:
            s.add(Rol(id_rol=3,nombre='Operario'))
            s.flush()
            s.add(Usuario(id_usuario=1,dni='73000001',usuario='O73000001',nombres='Ejemplo',apellidos='Local',password_hash='synthetic-unused',id_rol=3,fecha_creacion=now,estado=True))
            s.add(TipoVidrio(id_tipo_vidrio=7,nombre='Ejemplo FF',estado=True))
            s.flush()
            s.add(TipoVidrioEspesor(id_tipo_vidrio=7,espesor_mm=6))
            s.add(Cliente(id_cliente=41,nombre_razon_social='Ejemplo local',estado=True,fecha_registro=now))
            s.add(Configuracion(id_configuracion=1,version=1,separacion_mm=0,margen_mm=0,resolucion_raster_mm=1,paso_angular_grados=90,ancho_min_retazo_mm=1,alto_min_retazo_mm=1,vigente=True,id_usuario_creacion=1,fecha_creacion=now))
            s.flush()
            s.add(Plancha(id_plancha=5,ancho_mm=4,alto_mm=2,espesor_mm=6,cantidad=2,estado=True,fecha_registro=now,id_tipo_vidrio=7))
            s.commit()
            seed_permissions(s)
            repo=SQLAlchemyOrderRepository(s)
            piece=dict(tipo_forma='RECTANGULO',cantidad=2,dimensiones={'width_mm':2,'height_mm':2},geometria={'type':'RECTANGULO','width_mm':2,'height_mm':2},id_tipo_vidrio=7,espesor_mm=6,area_mm2=4)
            ids=[repo.create_order(1,[piece],id_cliente=41) for _ in range(2)]
        def session_override():
            with factory() as s:yield s
        uow=partial(SqlRunUnitOfWork,factory)
        calculator=CalculateRun(uow,InventoryStockAdapter(SqlAlchemyInventoryRepository(factory)))
        app.dependency_overrides[get_database_session]=session_override
        app.dependency_overrides[get_run_unit_of_work]=lambda:uow
        app.dependency_overrides[get_run_calculator]=lambda:calculator
        headers={'Authorization':'Bearer '+create_access_token(1,'O73000001','Operario')}
        with TestClient(app) as client:
            response=client.post('/api/optimization/runs',json={'order_ids':ids},headers=headers)
            assert response.status_code==201,response.text
            canonical=client.get(response.headers['location'],headers=headers)
            assert canonical.status_code==200,canonical.text
            assert canonical.json()['estado']=='COMPLETADA'
            (out/'phase5-example-complete.ndjson').write_text(response.text,encoding='utf-8')
            (out/'phase5-example-complete.json').write_text(json.dumps(canonical.json(),indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        with factory() as s:
            facts={'alembic_head':s.scalar(text('SELECT version_num FROM alembic_version')),
                'stock_before':{'PLANCHA:5':{'cantidad':2,'estado':True}},
                'stock_after':{'PLANCHA:5':{'cantidad':s.get(Plancha,5).cantidad,'estado':s.get(Plancha,5).estado}},
                'orders_after':{str(i):s.get(Pedido,i).estado for i in ids},
                'inventory_movements':s.scalar(select(func.count()).select_from(MovimientoInventario)),
                'created_remnants':s.scalar(select(func.count()).select_from(Retazo)),
                'http_status':response.status_code,'location':response.headers['location'],
                'event_count':len(response.text.splitlines())}
            assert facts['stock_before']==facts['stock_after'] and facts['inventory_movements']==facts['created_remnants']==0
            (out/'phase5-example-db.json').write_text(json.dumps(facts,indent=2)+'\n',encoding='utf-8')
        app.dependency_overrides.clear()
print('Captured real local POST/NDJSON, canonical GET and DB assertions.')
