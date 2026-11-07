"""B06 evidence/document/source audit, without importing the app or touching a database."""
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'docs/evidence/sprint-02/TA-043/B06'
BASE='18c36bc'


def git(*args):
    return subprocess.check_output(['git','-c','core.safecrlf=false',*args],cwd=ROOT,text=True,encoding='utf-8').strip()


def functions(source,cls):
    node=next(n for n in ast.parse(source).body if isinstance(n,ast.ClassDef) and n.name==cls)
    return {n.name:ast.dump(n,include_attributes=False) for n in node.body if isinstance(n,ast.FunctionDef)}


def main():
    assert git('branch','--show-current')=='feature/TA-043-integracion-seis-motores'
    assert git('rev-parse','integration-02')=='d85a8d3c4fa2ba1b3f70c401ed947adcfbe2470b'
    specpath='docs/specs/SPEC-TA-043-integracion-seis-motores.md'
    planpath='docs/specs/PLAN-TA-043-integracion-seis-motores.md'
    spec,plan=[(ROOT/p).read_text(encoding='utf-8') for p in (specpath,planpath)]
    oldspec,oldplan=[git('show',f'{BASE}:{p}') for p in (specpath,planpath)]
    def rows(text,pattern): return re.findall(pattern,text,re.M)
    req=r'^\| (?:RF-\d+|RNF-\d+|SM-\d+) \|.*$'
    ca=r'^\| CA-(?:N|S)?\d+ \|.*$'
    assert len(rows(spec,req))==len(rows(spec,ca))==len(rows(plan,req))==36
    assert rows(spec,req)==rows(oldspec,req) and rows(spec,ca)==rows(oldspec,ca)
    assert rows(plan,req)==rows(oldplan,req)
    assert len(rows(plan,r'^### B\d\d .*$'))==11
    assert plan.split('## 3. Bloques incrementales')[1].split('## 4. Actividad')[0]==oldplan.split('## 3. Bloques incrementales')[1].split('## 4. Actividad')[0]
    assert 'Draft' in spec and 'Draft' in plan
    protected=['backend/app/modules/optimization/domain',
        'backend/app/modules/optimization/application/engine_execution.py',
        'backend/app/modules/optimization/application/comparison_catalog.py',
        'backend/app/modules/optimization/application/comparison_v2_contracts.py',
        'backend/app/modules/optimization/application/comparison_acceptance_v2.py',
        'backend/app/modules/optimization/application/comparison_calculation_v2.py',
        'backend/app/modules/optimization/application/supervision_contracts.py',
        'backend/app/modules/optimization/application/comparison_limits.py',
        'backend/app/modules/optimization/application/sequential_policy.py',
        'backend/app/modules/optimization/infrastructure/comparison_v2_snapshot.py',
        'backend/app/modules/optimization/infrastructure/sequential_worker.py',
        'backend/app/modules/optimization/infrastructure/sequential_runner.py',
        'backend/app/modules/optimization/presentation/comparison_v2_schemas.py',
        'backend/app/modules/optimization/presentation/run_schemas.py',
        'backend/app/models.py','backend/alembic/versions','frontend/src']
    assert not git('diff','--name-only',BASE,'--',*protected)
    lifecycle='backend/app/modules/optimization/presentation/comparison_supervision_v2.py'
    before=functions(git('show',f'{BASE}:{lifecycle}'),'ComparisonV2Coordinator')
    after=functions((ROOT/lifecycle).read_text(encoding='utf-8'),'ComparisonV2Coordinator')
    for name in ('_close','_reap','shutdown','recover_pending'): assert before[name]==after[name],name
    reports={}; cases=set(); b06=set()
    selected=['api-final.xml','transport-review.xml','recovery-review.xml','regression.xml','b04-processes.xml','v1-processes.xml']
    for name in selected:
        suite=ET.parse(OUT/name).getroot(); tests=suite.findall('.//testcase')
        assert tests and not any(suite.findall('.//'+kind) for kind in ('failure','error','skipped')),name
        ids={(t.get('classname'),t.get('name')) for t in tests}
        cases.update(ids)
        if name in selected[:3]: b06.update(ids)
        reports[name]=dict(passed=len(tests),failed=0,skipped=0)
    assert len(b06)==37 and len(cases)==419,(len(b06),len(cases))
    frontend=json.loads((OUT/'frontend-contracts.json').read_text(encoding='utf-8'))
    assert frontend['numPassedTests']==23 and frontend['numFailedTests']==frontend['numPendingTests']==0
    smoke=json.loads((OUT/'smoke/cleanup.json').read_text())
    assert smoke['result']=='PASS' and smoke['processes_after']==[] and smoke['temporary_copy_removed']
    browser=json.loads((OUT/'smoke/playwright-report.json').read_text())
    assert browser['stats']['expected']==2 and browser['stats']['unexpected']==browser['stats']['skipped']==0
    for project in ('chromium-desktop','chromium-mobile'):
        live=json.loads((OUT/f'smoke/{project}/TA-043-b06-six-results.json').read_text())
        assert live['allInventoryBefore']==live['allInventoryAfter']
        assert len(live['results'])==6 and all(e['execution']['complete'] for e in live['results'])
        assert float(live['current']['configuration']['paso_angular_grados'])==5
    for path,digest in smoke['source_sha256'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest,path
    wire=json.loads((OUT/'api-real.json').read_text()); resource=wire['resources']
    assert len(wire['executions'])==6 and all(e['execution']['complete'] for e in wire['executions'])
    assert wire['inventory_before']==wire['inventory_after'] and wire['restart_without_recalculation']
    assert resource['maximum_active_workers']==1 and resource['all_workers_stopped'] and resource['global_reason'] is None
    assert resource['retained_bytes']=={'visual':0,'event':0}
    tcp=json.loads((OUT/'http-restart.json').read_text())
    assert tcp['result']=='PASS' and tcp['servers_stopped_after_cleanup'] and not tcp['new_server_children']
    assert tcp['immutable_snapshot_after_restart'] and tcp['inventory_before']==tcp['inventory_after']
    own=list(tcp['server_identities'])+list(tcp['workers'])
    own.extend(state['identity'] for state in resource['executions'].values() if state['identity'])
    remaining=[]
    for identity in own:
        try: ticks=Path(f"/proc/{identity['pid']}/stat").read_text().rsplit(')',1)[1].split()[19]
        except FileNotFoundError: continue
        if ticks==identity['start_ticks']: remaining.append(identity)
    assert not remaining
    sources=sorted((ROOT/'backend/app/modules/optimization').rglob('*.py'))+[ROOT/'backend/main.py',Path(__file__)]
    sources+=[ROOT/'backend/tests/api/optimization/test_comparisons_v2_api.py',
        ROOT/'backend/tests/integration/optimization/test_comparison_v2_http_restart.py',
        ROOT/'backend/tests/optimization_b01_smoke.py']
    for path in sources: ast.parse(path.read_text(encoding='utf-8-sig'),filename=str(path))
    sources.append(ROOT/'frontend/tests/e2e/optimization-comparison.spec.js')
    output=dict(state='B06_COMPLETADO_EN_ALCANCE',baseline=BASE,python=sys.version,
        branch=git('branch','--show-current'),head_at_validation=git('rev-parse','HEAD'),
        local_integration_base=git('rev-parse','integration-02'),remote_integration_02='ABSENT_AFTER_FETCH_2026_11_04',
        source_sha256={str(p.resolve().relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        reports=reports,distinct_b06_backend_cases=len(b06),distinct_backend_cases=len(cases),
        frontend_contract_cases=23,smoke='PASS_PUBLIC_V2_API_AND_EXISTING_UI',visual_v2='PENDING_B07',
        selection_confirmation_v2='PENDING_B08',integral_smoke='PENDING_B09_B11',
        b05_closure_ast_unchanged=True,protected_paths_unchanged=protected,
        requirements=36,acceptance_criteria=36,traceability_rows=36,blocks=11,
        own_process_identities_remaining=remaining,smoke_temporary_copy_removed=True,
        preliminary_reports_excluded=['preliminary-api.xml','preliminary-api-corrected.xml','api-initial.xml','http-restart-initial.xml'],
        applied_migration='s2cmp02d4e6f8 (B02 unchanged; no B06 migration)')
    (OUT/'validation.json').write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({key:output[key] for key in ('state','distinct_b06_backend_cases','distinct_backend_cases','frontend_contract_cases','smoke','b05_closure_ast_unchanged')}))


if __name__=='__main__': main()
