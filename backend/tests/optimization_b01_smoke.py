"""ST-INC-01/02/03 on a private Linux copy, borrowing installed runtimes/dependencies.

No installs, shared databases or edits to the borrowed runtime. Run from backend:
python -m tests.optimization_b01_smoke --runtime-root /path/to/linux-validation
Add --block B02 for historical data created on the previous schema before upgrade.
Add --block B03 for the available real v1/legacy regression; new adapters are not routed yet.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import tempfile
import time

REPO = Path(__file__).resolve().parents[2]


def owned_processes(root):
    owned = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            cmd = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
            cwd = (entry / "cwd").resolve()
            ticks = (entry / "stat").read_text().split(") ", 1)[1].split()[19]
            if str(root) in cmd or cwd.is_relative_to(root):
                owned.append(dict(pid=int(entry.name), start_ticks=ticks, command=cmd))
        except (OSError, ValueError, IndexError):
            continue
    return owned


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--block", choices=("B01", "B02", "B03"), default="B01")
    args = parser.parse_args()
    runtime = args.runtime_root.resolve()
    block = args.block
    smoke = f"ST-INC-{block[1:]}"
    evidence = REPO / f"docs/evidence/sprint-02/TA-043/{block}/smoke"
    prefix = f"newglass-ta043-{block.lower()}-"
    node = runtime / "node-v22.23.2-linux-x64/bin/node"
    python = runtime / "backend/.venv/wsl/bin/python"
    dependencies = runtime / "frontend/node_modules"
    for path in (node, python, dependencies):
        if not path.exists():
            raise RuntimeError(f"Missing Linux runtime/dependency: {path}")
    for port in (8017, 5188):
        with socket.socket() as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            probe.bind(("127.0.0.1", port))
    root = Path(tempfile.mkdtemp(prefix=prefix)).resolve()
    assert root.parent == Path(tempfile.gettempdir()).resolve() and root.name.startswith(prefix)
    private_tmp = root / "service-tmp"
    private_tmp.mkdir()
    state = private_tmp / "newglass-orders-e2e-8017.json"
    evidence.mkdir(parents=True, exist_ok=True)
    ignored = shutil.ignore_patterns(".env*", "venv", ".venv", "node_modules", "dist",
        "test-results", "playwright-report", "__pycache__", ".pytest_cache", "*.pyc")
    report = dict(scope=f"{smoke}: real historical v1 and legacy; no public six-engine validation",
                  runtime_root=str(runtime), temporary_root=str(root), result="FAIL")
    if block == "B03":
        report.update(new_adapter_service_validation="PENDING_INTEGRATION",
                      public_six_engine_validation="PENDING_INTEGRATION",
                      reused_test_selection="TA-043 B01")
    runner = None
    try:
        for folder in ("backend", "frontend", "docs/contracts"):
            shutil.copytree(REPO / folder, root / folder, ignore=ignored)
        (root / "backend/.venv").mkdir()
        (root / "backend/.venv/wsl").symlink_to(python.parents[1], target_is_directory=True)
        (root / "frontend/node_modules").symlink_to(dependencies, target_is_directory=True)
        (root / "frontend/vite.b01.config.mjs").write_text(
            "import base from './vite.config.js';\nexport default env => ({ ...base(env), cacheDir: "
            + json.dumps(str(root / "vite-cache")) + " });\n")
        (root / "frontend/playwright.b01.config.mjs").write_text("""
import base from './playwright.config.js';
export default { ...base, testMatch: 'optimization-comparison.spec.js',
  outputDir: './test-results/b01',
  reporter: [['list'], ['json', { outputFile: './test-results/b01-report.json' }]],
  use: { ...base.use, baseURL: 'http://127.0.0.1:5188', channel: 'chromium' },
  webServer: [
    { ...base.webServer[0], env: { PYTHON_DOTENV_DISABLED: '1', CORS_ORIGINS: 'http://127.0.0.1:5188' } },
    { ...base.webServer[1], command: 'npm run dev -- --config vite.b01.config.mjs --configLoader native --host 127.0.0.1 --port 5188 --strictPort',
      url: 'http://127.0.0.1:5188/hu007-t01.html' },
  ],
};
""", encoding="utf-8")
        env = dict(os.environ)
        for name in ("DATABASE_URL", "SECRET_KEY"):
            env.pop(name, None)
        env.update(PYTHON_DOTENV_DISABLED="1", NEWGLASS_REQUIRE_POSTGRES="1",
            NEWGLASS_TEST_PG_BIN="/usr/lib/postgresql/18/bin", PLAYWRIGHT_CHANNEL="chromium",
            TMPDIR=str(private_tmp), NEWGLASS_E2E_SCHEMA_REVISION="s2cmp01a1b2c" if block == "B02" else "head",
            NEWGLASS_OPTIMIZATION_EVIDENCE_DIR=str(evidence),
            PATH=f"{root / 'backend/.venv/wsl/bin'}:{node.parent}:{env.get('PATH', '')}")
        # This is an explicit local subset, not the complete CI gate of all critical specs.
        if env.get("CI") == "true" or env.get("NEWGLASS_E2E_GATE") == "1":
            raise RuntimeError("Use the complete CI gate in CI; this helper is a local B01 subset")
        source_files = sorted((root / "backend/app/modules/optimization").rglob("*.py"))
        source_files += [root / "backend/app/models.py"]
        source_files += sorted((root / "backend/alembic/versions").glob("*.py"))
        report["source_sha256"] = {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
                                   for path in source_files}
        report["processes_before"] = owned_processes(root)
        with (evidence / "execution.txt").open("w", encoding="utf-8") as log:
            runner = subprocess.Popen([str(node), str(root / "frontend/node_modules/@playwright/test/cli.js"),
                "test", "--config=playwright.b01.config.mjs", "--grep", "TA-043 B01" if block == "B03" else f"TA-043 {block}"],
                cwd=root / "frontend", env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            report["runner_exit"] = runner.wait(timeout=300)
        report_file = root / "frontend/test-results/b01-report.json"
        if report_file.exists():
            shutil.copy2(report_file, evidence / "playwright-report.json")
        if report["runner_exit"] == 0:
            report["result"] = "PASS"
    finally:
        if runner is not None and runner.poll() is None:
            os.killpg(runner.pid, signal.SIGTERM)
            try:
                runner.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(runner.pid, signal.SIGKILL)
                runner.wait(timeout=10)
        # State and the PostgreSQL cluster are inside this run's private TMPDIR.
        if state.exists() and (root / "backend").exists():
            cleanup = subprocess.run([str(root / "backend/.venv/wsl/bin/python"), "-m", "tests.e2e_server", "--stop"],
                cwd=root / "backend", env={**os.environ, "PYTHON_DOTENV_DISABLED": "1", "TMPDIR": str(private_tmp)},
                capture_output=True, timeout=30)
            report["postgres_cleanup_exit"] = cleanup.returncode
            if cleanup.returncode:
                report["result"] = "FAIL"
        for _ in range(50):
            if not owned_processes(root):
                break
            time.sleep(.1)
        remaining = owned_processes(root)
        report["processes_after"] = remaining
        if remaining or state.exists():
            report["result"] = "FAIL"
        for process in remaining:
            current = {p["pid"]: p for p in owned_processes(root)}.get(process["pid"])
            if current and current["start_ticks"] == process["start_ticks"]:
                os.kill(process["pid"], signal.SIGKILL)
        assert root.parent == Path(tempfile.gettempdir()).resolve() and root.name.startswith(prefix)
        shutil.rmtree(root)  # Only the private, resolved root created above; symlinks are not followed.
        report["temporary_copy_removed"] = not root.exists()
        (evidence / "cleanup.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(smoke + ": " + report["result"] + "; evidence: " + str(evidence))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
