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
    for name in ("backend", "e2e"):
        assert jobs[name]["env"]["NEWGLASS_REQUIRE_POSTGRES"] == "1"
        commands = "\n".join(step.get("run", "") for step in jobs[name]["steps"])
        assert "pg_config --bindir" in commands and "initdb" in commands and "pg_ctl" in commands
    commands = {step.get("run") for step in jobs["frontend"]["steps"] if "run" in step}
    assert {"npm ci", "npm run test:unit", "npm run test:component", "npm run lint", "npm run build"} <= commands
    assert jobs["e2e"]["env"]["PLAYWRIGHT_CHANNEL"] == "chromium"
    assert any(step.get("run") == "npm run test:e2e" for step in jobs["e2e"]["steps"])
    raw = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "secrets." not in raw and "DATABASE_URL:" not in raw
    assert "continue-on-error" not in raw


def test_pages_waits_for_ci_same_commit_and_restricts_source():
    pages = workflow("deploy-pages.yml")
    assert set(pages["on"]) == {"push", "workflow_dispatch"}
    assert pages["on"]["push"]["branches"] == ["integration/sprint-01"]
    checks, deploy = pages["jobs"]["checks"], pages["jobs"]["pages"]
    assert checks["uses"] == "./.github/workflows/ci.yml"
    assert deploy["needs"] == "checks"
    assert checks["if"] == deploy["if"] == "github.ref == 'refs/heads/integration/sprint-01'"
    assert deploy["permissions"] == {"contents": "read", "pages": "write", "id-token": "write"}
    assert deploy["environment"]["name"] == "github-pages"
    assert deploy["env"]["VITE_API_URL"] == "${{ vars.VITE_API_URL }}"
    assert pages["concurrency"]["cancel-in-progress"] == "false"
    assert any(step.get("with", {}).get("path") == "frontend/dist" for step in deploy["steps"])
    commands = [step.get("run") for step in deploy["steps"]]
    assert "npm run build:staging" in commands and "npm run check:staging" in commands
