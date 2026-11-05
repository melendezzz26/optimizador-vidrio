"""Validate B05 artifacts/document invariants and derive the measured summary; no DB or engine calls."""
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

REPO = Path(__file__).resolve().parents[2]
OUTPUT = REPO / 'docs/evidence/sprint-02/TA-043/B05'
BASE = '6701060'


def git(*args):
    return subprocess.check_output(['git',*args],cwd=REPO,text=True,encoding='utf-8').strip()


def rows(text,pattern):
    return re.findall(pattern,text,re.M)


def main():
    assert git('branch','--show-current')=='feature/TA-043-integracion-seis-motores'
    spec_path='docs/specs/SPEC-TA-043-integracion-seis-motores.md'
    plan_path='docs/specs/PLAN-TA-043-integracion-seis-motores.md'
    spec,plan=[(REPO/p).read_text(encoding='utf-8') for p in (spec_path,plan_path)]
    original_spec,original_plan=[git('show',f'{BASE}:{p}') for p in (spec_path,plan_path)]
    requirement_pattern=r'^\| (?:RF-\d+|RNF-\d+|SM-\d+) \|.*$'
    acceptance_pattern=r'^\| CA-(?:N|S)?\d+ \|.*$'
    assert len(rows(spec,requirement_pattern))==len(rows(spec,acceptance_pattern))==36
    assert rows(spec,requirement_pattern)==rows(original_spec,requirement_pattern)
    assert rows(spec,acceptance_pattern)==rows(original_spec,acceptance_pattern)
    assert rows(plan,requirement_pattern)==rows(original_plan,requirement_pattern)
    assert len(rows(plan,requirement_pattern))==36
    assert len(rows(plan,r'^### B\d\d .*$'))==11
    assert plan.split('## 3. Bloques incrementales')[1].split('## 4. Actividad')[0]==original_plan.split('## 3. Bloques incrementales')[1].split('## 4. Actividad')[0]
    assert 'Draft' in spec and 'Draft' in plan
    protected=['backend/app/modules/optimization/domain',
        'backend/app/modules/optimization/application/engine_execution.py',
        'backend/app/modules/optimization/application/comparison_catalog.py',
        'backend/app/modules/optimization/application/comparison_v2_contracts.py',
        'backend/app/modules/optimization/application/comparison_limits.py',
        'backend/app/modules/optimization/application/sequential_policy.py',
        'backend/app/modules/optimization/infrastructure/comparison_v2_snapshot.py',
        'backend/app/modules/optimization/infrastructure/sequential_worker.py',
        'backend/app/models.py','backend/alembic/versions','frontend/src']
    assert not git('diff','--name-only',BASE,'--',*protected)
    reports={}; unique=set(); b05=set()
    for name in ['b05-focused.xml','closure-review.xml','recovery-review.xml',
                 'regression.xml','b04-process-regression.xml','v1-process-regression.xml']:
        suites=ET.parse(OUTPUT/name).getroot()
        cases=suites.findall('.//testcase')
        assert cases and not suites.findall('.//failure') and not suites.findall('.//error') and not suites.findall('.//skipped'), name
        identifiers={(c.get('classname'),c.get('name')) for c in cases}
        unique.update(identifiers)
        if name in ['b05-focused.xml','closure-review.xml','recovery-review.xml']: b05.update(identifiers)
        reports[name]=dict(passed=len(cases),failed=0,skipped=0)
    assert len(b05)==38
    smoke=json.loads((OUTPUT/'smoke/cleanup.json').read_text())
    assert smoke['result']=='PASS' and smoke['processes_after']==[] and smoke['temporary_copy_removed']
    for path,digest in smoke['source_sha256'].items():
        assert hashlib.sha256((REPO/path).read_bytes()).hexdigest()==digest, path
    measurement=json.loads((OUTPUT/'six-real.json').read_text())
    report=measurement['processes']
    assert report['all_workers_stopped'] and report['maximum_active_workers']==1
    assert report['global_reason'] is None and report['elapsed_ms']<180000
    assert report['maximum_aggregate_rss']<report['budget']['aggregate_rss_bytes']
    assert measurement['inventory_before']==measurement['inventory_after']
    assert all(s['complete'] for s in measurement['states'])
    own_remaining=[]
    for path in OUTPUT.glob('*.json'):
        data=json.loads(path.read_text())
        for state in data.get('processes',{}).get('executions',{}).values():
            identity=state['identity']
            if identity is None: continue
            try:
                actual=Path(f"/proc/{identity['pid']}/stat").read_text().rsplit(')',1)[1].split()[19]
            except FileNotFoundError: continue
            if actual==identity['start_ticks']: own_remaining.append(identity)
    assert not own_remaining
    sources=sorted((REPO/'backend/app/modules/optimization').rglob('*.py'))+[REPO/'backend/main.py']
    sources+=sorted((REPO/'backend/tests').glob('optimization_b05_*.py'))
    sources+=[REPO/'backend/tests/integration/optimization/test_comparison_supervision_v2.py',
        REPO/'backend/tests/unit/optimization/test_supervision_contracts.py',REPO/'backend/tests/optimization_b01_smoke.py',
        REPO/'backend/tests/api/test_health_api.py']
    for path in sources: ast.parse(path.read_text(encoding='utf-8-sig'),filename=str(path))
    output=dict(state='B05_COMPLETADO_EN_ALCANCE',python=sys.version,baseline=BASE,
        branch=git('branch','--show-current'),head_at_validation=git('rev-parse','HEAD'),
        source_sha256={str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        reports=reports,b05_distinct_cases=len(b05),all_distinct_backend_cases=len(unique),
        preliminary_reports_excluded=['preliminary.xml','initial-integration.xml'],
        requirements=36,acceptance_criteria=36,traceability_rows=36,blocks=11,
        protected_paths_unchanged=protected,smoke='PASS_AVAILABLE_V1_LEGACY',
        public_v2='PENDING_INTEGRATION_B06',own_worker_identities_remaining=own_remaining,
        smoke_cleanup=bool(smoke['temporary_copy_removed'] and not smoke['processes_after']),
        measured_elapsed_ms=report['elapsed_ms'],maximum_aggregate_rss=report['maximum_aggregate_rss'])
    (OUTPUT/'validation.json').write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8')
    lines=['# B05 - Medicion integrada del caso pequeno','',
        'Derivado de `six-real.json`; WSL2, entrada congelada y seis motores productivos a 5 grados.',
        'Startup incluye spawn/handshake y acknowledgements del padre. Calculo externo es tiempo de pared',
        'del adaptador/metricas/callbacks/IPC; no es tiempo puro del algoritmo. Cola se mide aparte.','',
        '| Motor | Cola ms | Startup ms | Calculo externo ms | Cierre ms | RSS muestreado MiB | Virtual MiB | Eventos | Bytes observacion |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for method,state in report['executions'].items():
        worker=state['worker_report']
        lines.append(f"| {method} | {state['queue_ms']:.2f} | {state['startup_ms']:.2f} | {state['execution_external_wall_ms']:.2f} | {state['cleanup_ms']:.2f} | {state['peak_rss']/2**20:.2f} | {state['peak_virtual']/2**20:.2f} | {worker['observations']} | {worker['observation_bytes']} |")
    lines+=['',f"Total runner (incluye persistencia independiente y limpieza): {report['elapsed_ms']/1000:.3f} s / 180 s.",
        f"RSS agregado muestreado incluida reserva: {report['maximum_aggregate_rss']/2**20:.2f} MiB; supervisor: {report['supervisor_peak_rss']/2**20:.2f} MiB.",
        f"Muestreo: {report['samples']} muestras, mayor intervalo {report['maximum_sample_gap_ms']:.2f} ms; maximo un worker.",
        f"Retencion final: visual {measurement['retained_visual_bytes']} bytes, eventos {measurement['retained_event_bytes']} bytes; runner retiene cero.",
        '', 'Seis completos, sin consumo de inventario, sin cambio de cotas. Medicion muestreada, no garantia de picos ni capacidad general/Heroku.',
        'El maxrss nativo se conserva como dato crudo; no sustituye RSS/espacio virtual medidos por procfs.',
        'Las fases puras con/sin observacion siguen siendo el diagnostico B04, no se reinventan aqui.','']
    (OUTPUT/'measurements.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps({k:output[k] for k in ('state','b05_distinct_cases','all_distinct_backend_cases','smoke','measured_elapsed_ms','maximum_aggregate_rss')}))


if __name__=='__main__': main()
