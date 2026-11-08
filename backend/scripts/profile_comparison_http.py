"""Real HTTP + PostgreSQL + six native spawn engines with disposable synthetic data.

From backend: python -m scripts.profile_comparison_http --units 600 --output /tmp/profile.json
Requires local PostgreSQL binaries (NEWGLASS_TEST_PG_BIN). Never accepts a remote
database/API URL, reads .env, confirms a result, or consumes shared inventory.
Each invocation starts a fresh uvicorn process and its own PostgreSQL cluster.
This is an HTTP load measurement, not a browser rendering benchmark.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
from threading import Event, Thread
import time

os.environ['PYTHON_DOTENV_DISABLED'] = '1'


def seed(engine, count):
    from sqlalchemy.orm import Session
    from app.models import Rol, Usuario, TipoVidrio, TipoVidrioEspesor, Cliente, Configuracion, Plancha
    from app.shared.security import hash_password
    from app.modules.authentication.infrastructure.permission_seed import seed_permissions
    from app.modules.orders.infrastructure.repositories import SQLAlchemyOrderRepository
    now = datetime.now(timezone.utc)
    with Session(engine) as db:
        db.add(Rol(id_rol=1, nombre='Administrador'))
        db.flush()
        actor = Usuario(dni='73000001', usuario='A73000001', nombres='Carga', apellidos='Sintetica',
            password_hash=hash_password('Synthetic-local-only-2026!'), id_rol=1, fecha_creacion=now)
        db.add(actor)
        db.add_all([TipoVidrio(id_tipo_vidrio=i, nombre=f'Perfil sintetico {i}', estado=True) for i in (7, 9)])
        db.add(Cliente(id_cliente=41, nombre_razon_social='Cliente sintetico', estado=True, fecha_registro=now))
        db.flush()
        db.add_all([TipoVidrioEspesor(id_tipo_vidrio=i, espesor_mm=6) for i in (7, 9)])
        db.flush()
        db.add(Configuracion(version=1, separacion_mm=0, margen_mm=0, resolucion_raster_mm=1,
            paso_angular_grados=5, ancho_min_retazo_mm=10, alto_min_retazo_mm=10, vigente=True,
            id_usuario_creacion=actor.id_usuario, fecha_creacion=now))
        db.add_all([Plancha(id_plancha=i, ancho_mm=2440, alto_mm=3300, espesor_mm=6,
            cantidad=2, estado=True, fecha_registro=now, id_tipo_vidrio=i) for i in (7, 9)])
        db.commit()
        seed_permissions(db)
        pieces = []
        # Three actual shapes in each material group, at the deployed 1 mm / 5 degree setting.
        from decimal import Decimal as D
        from scripts.benchmark_academic_800 import case_problem
        for group in case_problem(count).groups:
            frequencies = Counter(unit.piece_id for unit in group.units)
            for piece_id, quantity in frequencies.items():
                unit = next(u for u in group.units if u.piece_id == piece_id)
                geometry = json.loads(json.dumps(dict(unit.geometry), default=lambda v: float(v) if isinstance(v,D) else list(v)))
                shape = geometry['type']
                pieces.append(dict(tipo_forma=shape, cantidad=quantity, dimensiones=geometry,
                    geometria=geometry, id_tipo_vidrio=7 if group.glass_type_id==1 else 9,
                    espesor_mm=6, area_mm2=unit.area_mm2))
        identifier = SQLAlchemyOrderRepository(db).create_order(actor.id_usuario, pieces, id_cliente=41)
        return actor.id_usuario, identifier


def server(args):
    from tests.integration.postgres_support import temporary_postgres, new_database, upgrade
    with tempfile.TemporaryDirectory(prefix='newglass-resource-profile-') as root:
        with temporary_postgres(Path(root)) as cluster, new_database(cluster) as engine:
            os.environ['DATABASE_URL'] = engine.url.render_as_string(hide_password=False)
            os.environ['SECRET_KEY'] = secrets.token_urlsafe(48)
            result = upgrade(engine, 'head')
            if result.returncode:
                raise RuntimeError(result.stderr)
            actor, order = seed(engine, args.units)
            from app.shared.security import create_access_token
            from app.modules.optimization.presentation.comparison_supervision_v2 import get_comparison_v2_coordinator
            from main import app
            from sqlalchemy import select, func
            from sqlalchemy.orm import Session
            from app.models import Plancha, Retazo, MovimientoInventario
            def inventory():
                with Session(engine) as db:
                    return dict(sheets=[list(row) for row in db.execute(select(Plancha.id_plancha,Plancha.cantidad).order_by(Plancha.id_plancha))],
                        remnants=db.scalar(select(func.count()).select_from(Retazo)),
                        movements=db.scalar(select(func.count()).select_from(MovimientoInventario)))
            before = inventory()
            # Fixture-only loopback readiness information; never placed in the output report.
            Path(args.ready).write_text(json.dumps(dict(order_id=order,
                token=create_access_token(actor, 'A73000001', 'Administrador'))))
            import uvicorn
            server = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=args.port, log_level='warning'))
            @app.post('/__profile__/shutdown', include_in_schema=False)
            def shutdown_owned_fixture():
                server.should_exit = True
                return {'stopping':True}
            try:
                server.run()
            finally:
                job = get_comparison_v2_coordinator().job
                report = dict(runner=job.runner.last_report if job is not None else None,
                    inventory_before=before, inventory_after=inventory())
                Path(args.ready+'.resources').write_text(json.dumps(report, default=str))


def profile(args):
    import httpx
    with tempfile.TemporaryDirectory(prefix='newglass-profile-client-') as directory:
        ready = str(Path(directory)/'ready.json')
        with socket.socket() as reservation:
            reservation.bind(('127.0.0.1', 0))
            port = reservation.getsockname()[1]
        logs = Path(directory)/'server.log'
        environment = {**os.environ, 'PYTHON_DOTENV_DISABLED':'1'}
        with logs.open('w') as log:
            process = subprocess.Popen([sys.executable, '-B', '-m', 'scripts.profile_comparison_http',
                '--server', '--units', str(args.units), '--port', str(port), '--ready', ready],
                stdout=log, stderr=log, env=environment)
        stop, samples = Event(), []
        def monitor():
            while not stop.wait(.05):
                try:
                    values = Path(f'/proc/{process.pid}/statm').read_text().split()
                    samples.append(int(values[1])*os.sysconf('SC_PAGE_SIZE'))
                except (OSError, ValueError, IndexError):
                    pass
        watcher = Thread(target=monitor, daemon=True)
        watcher.start()
        report = dict(units=args.units, source='http-postgresql-spawn', baseline_revision=args.label)
        base=f'http://127.0.0.1:{port}'
        started=time.monotonic()
        try:
            with httpx.Client(base_url=base, timeout=45) as client:
                deadline=time.monotonic()+90
                while time.monotonic()<deadline:
                    if process.poll() is not None:
                        raise RuntimeError('Profile server exited: '+logs.read_text()[-3000:])
                    if Path(ready).exists():
                        try:
                            if client.get('/health/live').status_code==200: break
                        except httpx.ConnectError: pass
                    time.sleep(.2)
                else: raise TimeoutError('Profile server readiness timeout')
                credentials=json.loads(Path(ready).read_text())
                headers={'Authorization':'Bearer '+credentials['token'], 'Idempotency-Key':'resource-profile-test-0001'}
                response=client.post('/api/optimization/comparisons-v2',
                    json={'order_ids':[credentials['order_id']]}, headers=headers)
                report['acceptance_status']=response.status_code
                if response.status_code!=201:
                    report['acceptance_error']=response.json()
                    return report
                path=response.headers['location']
                summary=response.json()
                # Exercise the same stream the page consumes; reliable terminal state is read afterwards.
                event_counts=Counter()
                with client.stream('GET', path+'/events', headers=headers, timeout=1000) as stream:
                    stream.raise_for_status()
                    for line in stream.iter_lines():
                        if line:
                            item=json.loads(line)
                            event_counts[item['event']]+=1
                final=client.get(path,headers=headers)
                final.raise_for_status()
                summary=final.json()
                report.update(terminal=summary['terminal'], supervisor_stopped=summary['supervisor_stopped'],
                    input_sha256=summary['input_sha256'], executions=summary['executions'], events=dict(event_counts))
                details=[]
                for execution in summary['executions']:
                    response=client.get(f"{path}/executions/{execution['execution_id']}",headers=headers)
                    response.raise_for_status()
                    result=response.json()['result']
                    placements=result['placements'] if result else []
                    identities={(p['id_pedido'],p['id_pieza'],p['unit_index']) for p in placements}
                    details.append(dict(method=execution['method'],bytes=len(response.content),
                        result_available=result is not None,placements=len(placements),
                        unique_placements=len(identities)))
                report['persisted_results_read']=details
                release=client.post(path+'/release',json={'expected_version':summary['version']},headers=headers)
                release.raise_for_status()
                report['released_without_confirmation']=release.json()['released']
        finally:
            # SIGTERM is replayed by uvicorn before the caller's finally block;
            # ask the fixture-only loopback server to exit normally so its owned
            # PostgreSQL cluster and resource report are closed deterministically.
            try:
                httpx.post(base+'/__profile__/shutdown',timeout=3)
            except httpx.HTTPError:
                process.terminate()
            try: process.wait(30)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait(5)
            stop.set(); watcher.join(2)
            report.update(http_wall_s=round(time.monotonic()-started,3),
                web_peak_rss_bytes=max(samples,default=0), sample_count=len(samples))
            resources=Path(ready+'.resources')
            if resources.exists(): report.update(json.loads(resources.read_text()))
            report['inventory_unchanged'] = ('inventory_before' in report
                and report['inventory_before']==report['inventory_after'])
            runner=report.get('runner') or {}
            report['complete_and_stopped'] = (bool(report.get('terminal')) and report.get('supervisor_stopped') is True
                and len(report.get('executions',[]))==6 and all(e['complete'] and e['placed_units']==args.units
                    and e['diagnostic']['statistics'].get('runtime_engine_started')==1
                    for e in report.get('executions',[])) and runner.get('all_workers_stopped') is True
                and report['inventory_unchanged'] and all(e['placements']==e['unique_placements']==args.units
                    for e in report.get('persisted_results_read',[])))
            # Keep only structured, synthetic memory diagnostics; no tokens/DSNs/general logs.
            report['resource_log_lines']=[line for line in logs.read_text().splitlines()
                if 'comparison_resource_' in line]
            if args.output:
                Path(args.output).write_text(json.dumps(report,indent=2)+'\n')
        return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--units',type=int,choices=(600,700,800),required=True)
    parser.add_argument('--output')
    parser.add_argument('--label',default='working-tree')
    parser.add_argument('--require-complete',action='store_true')
    parser.add_argument('--server',action='store_true')
    parser.add_argument('--ready')
    parser.add_argument('--port',type=int)
    options=parser.parse_args()
    if options.server: server(options)
    else:
        result=profile(options)
        print(json.dumps(result,indent=2))
        if options.require_complete and not result['complete_and_stopped']:
            raise SystemExit('Profile did not complete six native results with unchanged inventory and joined workers')
