"""Contrato local del CI: gates y publicación solo desde integración."""
from pathlib import Path

import pytest
import yaml

from tests.integration.postgres_support import temporary_postgres

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize("required,ci", [("1", "false"), ("0", "true")])
def test_missing_postgres_fails_when_required(tmp_path, monkeypatch, required, ci):
    monkeypatch.setenv("NEWGLASS_TEST_PG_BIN", str(tmp_path / "missing"))
    monkeypatch.setenv("NEWGLASS_REQUIRE_POSTGRES", required)
    monkeypatch.setenv("CI", ci)
    with pytest.raises(pytest.fail.Exception, match="PostgreSQL obligatorio"):
        with temporary_postgres(tmp_path):
            pytest.fail("No debe iniciar sin binarios")


def workflow(name):
    # BaseLoader conserva la clave YAML 'on' (sin coerción booleana YAML 1.1).
    return yaml.load((ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def test_ci_covers_backend_frontend_e2e_without_staging_secrets():
    ci = workflow("ci.yml")
    assert {"pull_request", "push", "workflow_call"} <= ci["on"].keys()
    assert "integration/sprint-01" in ci["on"]["push"]["branches"]
    assert ci["permissions"] == {"contents": "read"}
    jobs = ci["jobs"]
    backend_commands = '\n'.join(step.get('run', '') for step in jobs['backend']['steps'])
    general_start = 'python -m pytest tests \\'
    assert general_start in backend_commands
    general = backend_commands.split(general_start, 1)[1].split(
        'python -m pytest tests/integration/optimization/test_comparison_calculation.py',
        1,
    )[0]
    for path in (
        'tests/unit/optimization/test_comparison_runner.py',
        'tests/integration/optimization/test_comparison_calculation.py',
        'tests/integration/optimization/test_comparison_supervision_v2.py',
        'tests/unit/optimization/test_sequential_runner.py',
    ):
        assert f'--ignore={path}' in general
    for path in (
        'tests/integration/optimization/test_comparison_calculation.py',
        'tests/integration/optimization/test_comparison_supervision_v2.py',
        'tests/unit/optimization/test_sequential_runner.py',
        'tests/unit/optimization/test_comparison_runner.py',
    ):
        assert f'python -m pytest {path} -q -ra' in backend_commands
    assert 'python -m pytest tests --ignore=tests/unit/optimization/test_comparison_runner.py -q -ra' not in backend_commands
    assert 'continue-on-error' not in backend_commands
    assert '|| true' not in backend_commands
    assert '--deselect' not in backend_commands
    for name in ("backend", "e2e"):
        assert jobs[name]["env"]["NEWGLASS_REQUIRE_POSTGRES"] == "1"
        commands = "\n".join(step.get("run", "") for step in jobs[name]["steps"])
        assert "pg_config --bindir" in commands and "initdb" in commands and "pg_ctl" in commands
    commands = {step.get("run") for step in jobs["frontend"]["steps"] if "run" in step}
    assert {"npm ci", "npm run test:unit", "npm run test:component", "npm run lint", "npm run build"} <= commands
    assert jobs["e2e"]["env"]["PLAYWRIGHT_CHANNEL"] == "chromium"
    e2e_commands = "\n".join(step.get("run", "") for step in jobs["e2e"]["steps"])
    assert 'node scripts/run-e2e-phases.js' in e2e_commands
    assert 'npx playwright test --grep' not in e2e_commands
    orchestrator = (ROOT / 'frontend/scripts/run-e2e-phases.js').read_text(encoding='utf-8')
    assert "['test', '--list', '--reporter=./tests/e2e/e2eGateReporter.js']" in orchestrator
    assert 'for (const phase of E2E_PHASES)' in orchestrator
    assert 'readCombinedEvidence(directory, context)' in orchestrator
    assert 'process.exitCode = summary.ok ? 0 : 1' in orchestrator
    assert "NEWGLASS_E2E_GATE: '1'" in orchestrator
    protocol = (ROOT / 'frontend/tests/e2e/e2ePhases.js').read_text(encoding='utf-8')
    assert "['b02', 'remaining']" in protocol
    assert "phase === 'b02' ? '--grep' : '--grep-invert'" in protocol
    assert 'TA-043 B02 smoke: historia v1 y FF intacta después del upgrade PostgreSQL' in protocol
    config = (ROOT / 'frontend/playwright.config.js').read_text(encoding='utf-8')
    assert 'reuseExistingServer: false' in config
    assert "command: 'python -m tests.e2e_server'" in config
    assert "outputDir: path.join(phase.directory, phase.phase)" in config
    artifact = next(step for step in jobs['e2e']['steps'] if step.get('uses', '').startswith('actions/upload-artifact@'))
    assert artifact['if'] == 'always()'
    assert artifact['with']['if-no-files-found'] == 'error'
    assert 'frontend/test-results/e2e-phases/' in artifact['with']['path']
    assert 'frontend/playwright-report/e2e-phases/' in artifact['with']['path']
    raw = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "secrets." not in raw and "DATABASE_URL:" not in raw
    assert "continue-on-error" not in raw


def test_pages_waits_for_ci_same_commit_and_restricts_source():
    pages = workflow("deploy-pages.yml")
    assert set(pages["on"]) == {"push", "workflow_dispatch"}
    assert pages["on"]["push"]["branches"] == ["integration-02"]
    checks, deploy = pages["jobs"]["checks"], pages["jobs"]["pages"]
    assert checks["uses"] == "./.github/workflows/ci.yml"
    assert deploy["needs"] == "checks"
    assert checks["if"] == deploy["if"] == "github.ref == 'refs/heads/integration-02'"
    assert deploy["permissions"] == {"contents": "read", "pages": "write", "id-token": "write"}
    assert deploy["environment"]["name"] == "github-pages"
    assert deploy["env"]["VITE_API_URL"] == "${{ vars.VITE_API_URL }}"
    assert pages["concurrency"]["cancel-in-progress"] == "false"
    assert any(step.get("with", {}).get("path") == "frontend/dist" for step in deploy["steps"])
    commands = [step.get("run") for step in deploy["steps"]]
    assert "npm run build:staging" in commands and "npm run check:staging" in commands
