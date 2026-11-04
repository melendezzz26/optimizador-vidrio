"""Real TCP/Uvicorn restart against one isolated PostgreSQL DB; no retained runtime reused."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

import httpx
from sqlalchemy import select,func

from app.models import Optimizacion,EjecucionOptimizacion
from app.shared.security import create_access_token
from app.modules.optimization.infrastructure.process_lifecycle import process_identity
from .test_runs import prepared  # noqa: F401
from .test_comparison_supervision_v2 import inventory


def test_real_http_disconnect_then_backend_restart_never_recalculates(session_factory,prepared,tmp_path):
    actor,ids,_=prepared
    engine=session_factory.kw['bind']
    assert engine.url.host=='127.0.0.1' and engine.url.username=='r1_test'
    with socket.socket() as reserved:
        reserved.bind(('127.0.0.1',0)); port=reserved.getsockname()[1]
    backend=Path(__file__).resolve().parents[3]
    environment={**os.environ,'PYTHON_DOTENV_DISABLED':'1','DATABASE_URL':engine.url.render_as_string(hide_password=False)}
    headers={'Authorization':'Bearer '+create_access_token(actor,'O73000001','Operario')}
    process=None
    log=(tmp_path/'uvicorn.txt').open('w',encoding='utf-8')
    server_identities=[]
    report=None
    def launch():
        nonlocal process
        process=subprocess.Popen([sys.executable,'-m','uvicorn','main:app','--host','127.0.0.1',
            '--port',str(port),'--workers','1','--no-access-log'],cwd=backend,env=environment,stdout=log,stderr=subprocess.STDOUT)
        server_identities.append(process_identity(process.pid))
        deadline=time.monotonic()+20
        while time.monotonic()<deadline:
            assert process.poll() is None,'Owned API server exited; see uvicorn log'
            try:
                if client.get('/health/ready').status_code==200: return
            except httpx.TransportError: pass
            time.sleep(.05)
        pytest_fail('Owned API server did not become ready')
    def stop():
        nonlocal process
        if process is not None:
            if process.poll() is None:
                process.terminate()
                try: process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill(); process.wait(timeout=5)
                    pytest_fail('Owned API required forced cleanup')
            assert process.poll() is not None
            process=None
    before=inventory(session_factory)
    with httpx.Client(base_url=f'http://127.0.0.1:{port}',timeout=25) as client:
        try:
            launch()
            post=client.post('/api/optimization/comparisons-v2',json={'order_ids':ids},headers={**headers,'Idempotency-Key':'b06-tcp-restart-0001'})
            assert post.status_code==201,post.text
            location=post.headers['location']
            disconnected_at=None
            with client.stream('GET',location+'/events',headers=headers) as stream:
                assert stream.status_code==200
                for line in stream.iter_lines():
                    value=json.loads(line)
                    if value['event']=='engine_started':
                        disconnected_at=value['sequence']; break
            assert disconnected_at is not None
            deadline=time.monotonic()+25
            while time.monotonic()<deadline:
                response=client.get(location,headers=headers)
                assert response.status_code==200,response.text
                current=response.json()
                if current['terminal']: break
                time.sleep(.04)
            assert current['terminal'] and all(e['complete'] for e in current['executions'])
            results=[client.get(location+f"/executions/{e['execution_id']}",headers=headers).json() for e in current['executions']]
            with session_factory() as session:
                row=session.get(Optimizacion,current['comparison_id'])
                raw_before=dict(row.comparison_snapshot)
                workers=list(raw_before['runtime']['workers'].values())
            stop(); launch()
            assert client.get(location,headers=headers).json()==current
            assert client.get('/api/optimization/comparisons-v2/requests/b06-tcp-restart-0001',headers=headers).json()==current
            repeated=client.post('/api/optimization/comparisons-v2',json={'order_ids':ids},headers={**headers,'Idempotency-Key':'b06-tcp-restart-0001'})
            assert repeated.status_code==201 and repeated.json()==current
            assert client.get(location+'/events',headers=headers).status_code==410
            assert [client.get(location+f"/executions/{e['execution_id']}",headers=headers).json() for e in current['executions']]==results
            with session_factory() as session:
                assert session.get(Optimizacion,current['comparison_id']).comparison_snapshot==raw_before
                assert session.scalar(select(func.count()).select_from(EjecucionOptimizacion))==6
            # A fresh process serving only history has not spawned workers/trackers.
            children=[]
            for stat in Path('/proc').glob('[0-9]*/stat'):
                try:
                    values=stat.read_text().rsplit(')',1)[1].split()
                    if int(values[1])==process.pid: children.append(int(stat.parent.name))
                except (FileNotFoundError,ProcessLookupError): pass
            assert children==[]
            assert inventory(session_factory)==before
            for worker in workers: assert process_identity(worker['pid'])!=worker
            report=dict(result='PASS',server_identities=server_identities,disconnected_at_sequence=disconnected_at,
                summary=current,executions=results,workers=workers,new_server_children=children,
                immutable_snapshot_after_restart=True,inventory_before=before,inventory_after=inventory(session_factory))
        finally:
            stop(); log.close()
    assert all(process_identity(p['pid'])!=p for p in server_identities)
    destination=os.environ.get('NEWGLASS_B06_EVIDENCE_DIR')
    if destination and report is not None:
        report['servers_stopped_after_cleanup']=True
        (Path(destination)/'http-restart.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')


def pytest_fail(message):
    import pytest
    pytest.fail(message)
