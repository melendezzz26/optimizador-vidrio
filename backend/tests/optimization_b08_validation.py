"""B08 evidence/document validation only; no services, database or optimizer calls."""
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

REPO = Path(__file__).resolve().parents[2]
OUTPUT = REPO / 'docs/evidence/sprint-02/TA-043/B08'
BASE = 'df4a75be180d9dd59ba4b7fe7697cced3b1c161b'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=REPO, text=True, encoding='utf-8').strip()


def main():
    assert git('branch', '--show-current') == 'feature/TA-043-integracion-seis-motores'
    for name in ('SPEC', 'PLAN'):
        path = f'docs/specs/{name}-TA-043-integracion-seis-motores.md'
        text = (REPO / path).read_text(encoding='utf-8')
        assert text.strip() == git('show', f'{BASE}:{path}')
        assert 'Draft' in text
        assert len(re.findall(r'^\| (?:RF-\d+|RNF-\d+|SM-\d+) \|', text, re.M)) == 36
        if name == 'SPEC':
            assert len(re.findall(r'^\| CA-(?:N|S)?\d+ \|', text, re.M)) == 36
        else:
            assert len(re.findall(r'^### B\d\d ', text, re.M)) == 11
    protected = ['backend/app/modules/optimization/domain', 'backend/app/models.py', 'backend/alembic/versions',
        'backend/app/modules/optimization/application/comparison_limits.py',
        'backend/app/modules/optimization/application/sequential_policy.py',
        'backend/app/modules/optimization/application/engine_execution.py',
        'backend/app/modules/optimization/infrastructure/sequential_runner.py',
        'backend/app/modules/optimization/infrastructure/sequential_worker.py',
        'backend/app/modules/optimization/infrastructure/comparison_v2_snapshot.py',
        'backend/app/modules/optimization/presentation/comparison_supervision_v2.py']
    assert not git('diff', '--name-only', BASE, '--', *protected)
    reports, unique = {}, set()
    for path in sorted(OUTPUT.glob('backend-*.xml')):
        tree = ET.parse(path)
        assert not any(tree.findall('.//' + state) for state in ('failure', 'error', 'skipped'))
        cases = {(c.get('classname'), c.get('name')) for c in tree.findall('.//testcase')}
        assert cases
        unique.update(cases)
        reports[path.name] = len(cases)
    front = ET.parse(OUTPUT / 'frontend-focused.xml')
    assert not any(front.findall('.//' + state) for state in ('failure', 'error', 'skipped'))
    frontend_count = len(front.findall('.//testcase'))
    smokes = {}
    for block in ('B07', 'B08'):
        directory = OUTPUT.parent / block / 'smoke'
        cleanup = json.loads((directory / 'cleanup.json').read_text())
        report = json.loads((directory / 'playwright-report.json').read_text())
        assert cleanup['result'] == 'PASS' and cleanup['runner_exit'] == 0
        assert cleanup['processes_after'] == [] and cleanup['temporary_copy_removed']
        assert report['stats']['expected'] == 2
        assert all(report['stats'][key] == 0 for key in ('unexpected', 'skipped', 'flaky'))
        for path, digest in cleanup['source_sha256'].items():
            assert hashlib.sha256((REPO / path).read_bytes()).hexdigest() == digest, path
        smokes[block] = dict(passed=2, duration_ms=report['stats']['duration'], processes_after=[], cleaned=True)
    deltas = {}
    for project in ('chromium-desktop', 'chromium-mobile'):
        data = json.loads((OUTPUT / 'smoke' / project / 'TA-043-b08-confirmation.json').read_text())
        before, selected, after = data['before'], data['afterSelection'], data['after']
        assert all(before[field] == selected[field] for field in ('sheets', 'remnants', 'movements', 'orders'))
        old = {m['id_movimiento'] for m in before['movements']}
        movements = [m for m in after['movements'] if m['id_movimiento'] not in old]
        assert len(movements) == 1 and movements[0]['cantidad_afectada'] == 1
        assert data['posts'] == 1 and data['retry'] == 'SAME_RECEIPT_NO_DELTA'
        assert data['recovered']['confirmed'] and data['recovered']['confirmation']['method'] == 'M5'
        assert all(o['estado'] == 'CONFIRMADO' for o in after['orders'])
        deltas[project] = dict(comparison_id=data['current']['comparison_id'],
            execution_id=data['current']['selected_execution_id'], method='M5', new_movements=len(movements),
            consumed_quantity=1, selection_inventory_unchanged=True, repeat_no_delta=True,
            new_remnants=len(after['remnants'])-len(before['remnants']),
            order_states=[o['estado'] for o in after['orders']])
    changed = set(git('diff', '--name-only', BASE).splitlines())
    changed.update(git('ls-files', '--others', '--exclude-standard').splitlines())
    code = sorted(path for path in changed if path.startswith(('backend/', 'frontend/')))
    for path in code:
        if path.endswith('.py'):
            ast.parse((REPO / path).read_text(encoding='utf-8'))
    git('diff', '--check')
    output = dict(base=BASE, head=git('rev-parse', 'HEAD'), reports=reports,
        backend_distinct_passed=len(unique), frontend_distinct_passed=frontend_count,
        smokes=smokes, stock_deltas=deltas, requirements=36, acceptance_criteria=36,
        traceability_rows=36, blocks=11, spec_plan_unchanged=True, protected_code_unchanged=True,
        source_files=code, source_sha256={path: hashlib.sha256((REPO/path).read_bytes()).hexdigest() for path in code},
        static_validation='AST and git diff --check PASS', integral_smoke='NOT_EXECUTED_B09_NOT_AUTHORIZED')
    (OUTPUT / 'validation.json').write_text(json.dumps(output, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: output[key] for key in ('backend_distinct_passed', 'frontend_distinct_passed', 'smokes', 'stock_deltas')}))


if __name__ == '__main__':
    main()
