#!/usr/bin/env python3
"""EN-REPO-001: prepara dos repositorios locales filtrados, sin push ni despliegue.

Uso:
  python scripts/repository-split/prepare.py --output ../newglass-split

Requisitos: Git, git-filter-repo y Python >= 3.11.
Nunca trabaja sobre el checkout de origen: clona el ref congelado en un directorio nuevo.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path

SOURCE_URL = "https://github.com/melendezzz26/optimizador-vidrio.git"
SOURCE_REF = "backup/pre-separacion-2026-11-10"
EXPECTED_SHA = "137f2ccd7a542c73e99fd40a792287595cdcd9c8"
OWNER = "melendezzz26"
OLD_REPO = "optimizador-vidrio"


def run(*args: str, cwd: Path | None = None) -> str:
    command = ["git", *args]
    process = subprocess.run(
        command, cwd=cwd, text=True, capture_output=True, check=False
    )
    if process.returncode:
        raise RuntimeError(
            f"Falló {' '.join(command[:4])} (exit={process.returncode}):\n"
            f"{process.stderr[-2400:]}"
        )
    return process.stdout.strip()


def must_replace(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"No se encontró patrón requerido en {label}: {old!r}")
    return text.replace(old, new)


def check_prerequisites() -> None:
    run("--version")
    run("filter-repo", "--version")


def root_setup(original: Path, target: Path, part: str, sha: str) -> None:
    for name in (".editorconfig", ".gitattributes"):
        shutil.copy2(original / name, target / name)
    if part == "backend":
        shutil.copy2(original / ".python-version", target / ".python-version")
        procfile = (original / "Procfile").read_text(encoding="utf-8")
        procfile = must_replace(procfile, "web: cd backend && ", "web: ", "Procfile")
        if "--workers 1" not in procfile:
            raise RuntimeError("El Procfile perdió --workers 1")
        (target / "Procfile").write_text(procfile, encoding="utf-8")
        (target / ".gitignore").write_text(
            "venv/\n.venv/\n__pycache__/\n*.py[cod]\n.pytest_cache/\n"
            ".env\n.env.*\n!.env.example\n.vscode/\n.idea/\n.DS_Store\n",
            encoding="utf-8",
        )
        # El contrato público se conserva y se versiona con su servidor.
        source_contracts = original / "docs" / "contracts"
        if source_contracts.exists():
            shutil.copytree(source_contracts, target / "docs" / "contracts")
        summary = original / ".github" / "scripts" / "backend_failure_summary.py"
        summary_target = target / ".github" / "scripts" / summary.name
        summary_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(summary, summary_target)
    else:
        (target / ".gitignore").write_text(
            "node_modules/\ndist/\ntest-results/\nplaywright-report/\n"
            ".env\n.env.*\n!.env.example\n.vscode/\n.idea/\n.DS_Store\n",
            encoding="utf-8",
        )


def update_references(target: Path, part: str, sha: str, pages_base: str) -> None:
    readme = target / "README.md"
    if readme.exists():
        text = readme.read_text(encoding="utf-8")
        historical = f"https://github.com/{OWNER}/{OLD_REPO}/blob/{sha}/docs/"
        text = text.replace("../docs/", historical)
        text = text.replace("desde \`backend/\`", "desde la raíz de este repositorio")
        text = text.replace("desde \`frontend/\`", "desde la raíz de este repositorio")
        readme.write_text(text, encoding="utf-8")
    if part == "frontend":
        config = target / "config" / "staging.js"
        src = config.read_text(encoding="utf-8")
        src = must_replace(
            src, "PAGES_BASE = '/optimizador-vidrio/'",
            f"PAGES_BASE = '{pages_base}'", str(config)
        )
        config.write_text(src, encoding="utf-8")
        # Mantener la misma ruta esperada en tests y fixtures tras cambiar Pages.
        for file in target.rglob("*"):
            if file.is_file() and file.suffix in {".js", ".jsx", ".html"}:
                body = file.read_text(encoding="utf-8")
                if "/optimizador-vidrio/" in body:
                    file.write_text(
                        body.replace("/optimizador-vidrio/", pages_base),
                        encoding="utf-8",
                    )


def backend_ci(original: Path, target: Path) -> None:
    source = (original / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    block = source[source.index("  backend:\n"):source.index("\n  frontend:\n")]
    block = must_replace(block, "working-directory: backend", "working-directory: .", "CI backend")
    block = must_replace(block, "backend/requirements.txt", "requirements.txt", "CI backend")
    block = must_replace(
        block, "../.github/scripts/backend_failure_summary.py",
        ".github/scripts/backend_failure_summary.py", "CI backend"
    )
    header = (
        "name: Backend CI\n\non:\n  pull_request:\n  push:\n"
        "    branches: [main]\n  workflow_call:\n\n"
        "permissions:\n  contents: read\n\njobs:\n"
    )
    workflows = target / ".github" / "workflows"
    workflows.mkdir(parents=True, exist_ok=True)
    (workflows / "ci.yml").write_text(header + block + "\n", encoding="utf-8")


def frontend_ci(original: Path, target: Path, backend_repo: str) -> None:
    source = (original / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    frontend = source[source.index("  frontend:\n"):source.index("\n  e2e:\n")]
    e2e = source[source.index("  e2e:\n"):]
    frontend = must_replace(
        frontend, "working-directory: frontend", "working-directory: .", "CI frontend"
    )
    frontend = must_replace(
        frontend, "frontend/package-lock.json", "package-lock.json", "CI frontend"
    )
    sha_var = "$" + "{{ vars.NEWGLASS_BACKEND_E2E_SHA }}"
    checkout_old = (
        "      - name: Checkout\n"
        "        uses: actions/checkout@v7\n"
        "        with:\n"
        "          persist-credentials: false\n"
    )
    checkout_new = (
        "      - name: Checkout frontend\n"
        "        uses: actions/checkout@v7\n"
        "        with:\n"
        "          persist-credentials: false\n"
        "          path: frontend\n"
        "      - name: Validate pinned backend SHA\n"
        "        shell: bash\n"
        "        run: |\n"
        f'          [[ "{sha_var}" =~ ^[0-9a-f]{{40}}$ ]]\n'
        "      - name: Checkout backend for E2E\n"
        "        uses: actions/checkout@v7\n"
        "        with:\n"
        "          persist-credentials: false\n"
        f"          repository: {backend_repo}\n"
        f"          ref: {sha_var}\n"
        "          path: backend\n"
        "      - name: Verify checked-out backend SHA\n"
        "        shell: bash\n"
        f'        run: test "$(git -C ../backend rev-parse HEAD)" = "{sha_var}"\n'
    )
    e2e = must_replace(e2e, checkout_old, checkout_new, "CI E2E")
    header = (
        "name: Frontend CI and pinned backend E2E\n\non:\n"
        "  pull_request:\n  push:\n    branches: [main]\n  workflow_call:\n"
        "  workflow_dispatch:\n\npermissions:\n  contents: read\n\njobs:\n"
    )
    workflows = target / ".github" / "workflows"
    workflows.mkdir(parents=True, exist_ok=True)
    (workflows / "ci.yml").write_text(header + frontend + "\n" + e2e, encoding="utf-8")

    pages = (original / ".github" / "workflows" / "deploy-pages.yml").read_text(encoding="utf-8")
    pages = must_replace(
        pages, "  push:\n    branches: [integration-02, test/resource-profile-800]\n",
        "", "Deploy Pages"
    )
    pages = pages.replace(
        "github.ref == 'refs/heads/integration-02' || github.ref == 'refs/heads/test/resource-profile-800'",
        "github.ref == 'refs/heads/main'"
    )
    pages = must_replace(
        pages, "working-directory: frontend", "working-directory: .", "Deploy Pages"
    )
    pages = must_replace(
        pages, "frontend/package-lock.json", "package-lock.json", "Deploy Pages"
    )
    pages = must_replace(pages, "path: frontend/dist", "path: dist", "Deploy Pages")
    (workflows / "deploy-pages.yml").write_text(pages, encoding="utf-8")


def backend_ci_contract(target: Path) -> None:
    source_path = target / "tests" / "unit" / "test_ci_contract.py"
    original = source_path.read_text(encoding="utf-8")
    original = must_replace(
        original,
        "ROOT = Path(__file__).resolve().parents[3]",
        "ROOT = Path(__file__).resolve().parents[2]",
        "backend test_ci_contract.py",
    )
    begin = original.index("def test_ci_covers_backend_frontend_e2e_without_staging_secrets():")
    end = original.index("def test_procfile_runs_a_single_uvicorn_worker():")
    replacement = '''def test_backend_ci_retains_resource_sensitive_suites_and_isolation():
    ci = workflow("ci.yml")
    assert {"pull_request", "push", "workflow_call"} <= ci["on"].keys()
    assert ci["on"]["push"]["branches"] == ["main"]
    assert ci["permissions"] == {"contents": "read"}
    assert set(ci["jobs"]) == {"backend"}
    job = ci["jobs"]["backend"]
    assert job["env"]["NEWGLASS_REQUIRE_POSTGRES"] == "1"
    commands = "\\n".join(step.get("run", "") for step in job["steps"])
    assert "pg_config --bindir" in commands
    assert "initdb" in commands and "pg_ctl" in commands
    assert "python -m pytest tests \\\\" in commands
    for suite in (
        "tests/integration/optimization/test_comparison_calculation.py",
        "tests/integration/optimization/test_comparison_supervision_v2.py",
        "tests/unit/optimization/test_sequential_runner.py",
        "tests/unit/optimization/test_comparison_runner.py",
    ):
        assert f"python -m pytest {suite} -q -ra" in commands
        assert f"--ignore={suite}" in commands
    raw = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "continue-on-error" not in raw
    assert "|| true" not in raw
    assert "--deselect" not in raw
    assert "secrets." not in raw
    assert "DATABASE_URL:" not in raw
    assert (ROOT / ".github/scripts/backend_failure_summary.py").is_file()


'''
    original = original[:begin] + replacement + original[end:]
    # El test Pages pertenece al repositorio frontend, no al backend.
    index = original.index("def test_pages_waits_for_ci_same_commit_and_restricts_source():")
    original = original[:index]
    source_path.write_text(original, encoding="utf-8")


def list_files(repository: Path, rev: str, prefix: str = "") -> list[str]:
    result = subprocess.run(
        ["git", "ls-tree", "-r", "-z", "--name-only", rev, "--", prefix]
        if prefix else ["git", "ls-tree", "-r", "-z", "--name-only", rev],
        cwd=repository, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
    )
    return sorted(p.decode("utf-8") for p in result.stdout.split(b"\0") if p)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=SOURCE_URL, help="URL Git o ruta de clon existente")
    parser.add_argument("--ref", default=SOURCE_REF, help="Rama de respaldo aprobada")
    parser.add_argument("--sha", default=EXPECTED_SHA, help="SHA completo esperado, obligatorio para seguridad")
    parser.add_argument("--output", type=Path, required=True, help="Carpeta nueva para los dos repos locales")
    parser.add_argument("--frontend-repo", default=f"{OWNER}/newglass-frontend")
    parser.add_argument("--backend-repo", default=f"{OWNER}/newglass-backend")
    parser.add_argument("--pages-base", default="/newglass-frontend/")
    args = parser.parse_args()

    if not re.fullmatch(r"[0-9a-f]{40}", args.sha):
        parser.error("--sha debe contener exactamente 40 dígitos hexadecimales")
    if not re.fullmatch(r"/[a-zA-Z0-9._/-]+/", args.pages_base):
        parser.error("--pages-base debe ser una ruta absoluta terminada en /")
    target = args.output.expanduser().resolve()
    if target.exists():
        parser.error(f"La carpeta de salida ya existe: {target}; no se sobrescribe")
    check_prerequisites()

    target.mkdir(parents=True)
    original = target / "_source"
    run("clone", "--no-local", "--single-branch", "--branch", args.ref, args.source, str(original))
    actual = run("rev-parse", "HEAD", cwd=original)
    if actual != args.sha:
        raise RuntimeError(f"SHA inesperado: {actual}; se esperaba {args.sha}. No se filtró nada.")

    manifest = {
        "source": args.source, "reference": args.ref, "source_sha": actual,
        "frontend_remote": args.frontend_repo, "backend_remote": args.backend_repo,
        "pages_base": args.pages_base,
        "open_pr_at_planning": [113],
        "deployment_performed": False,
        "repository_created_on_github": False,
        "repositories": {},
        "notes": [
            "PR #113 requiere revisión/port independiente después del corte.",
            "Git-filter-repo reescribe los SHA de los commits que conserva.",
            "No se han migrado issues, PR, secrets, environments, tags ni protecciones.",
            "Los cambios generados en nuevos repos se dejan SIN COMMIT para revisión.",
        ],
    }
    for part in ("frontend", "backend"):
        dest = target / part  # Nombres locales fijos: Playwright usa ../backend.
        run("clone", "--no-local", "--single-branch", "--branch", args.ref,
            str(original), str(dest))
        run("filter-repo", "--force", "--subdirectory-filter", part, cwd=dest)
        run("branch", "-M", "main", cwd=dest)
        expected = sorted(
            path.removeprefix(part + "/")
            for path in list_files(original, args.sha, part + "/")
        )
        actual_tree = list_files(dest, "HEAD")
        if expected != actual_tree:
            extra = sorted(set(actual_tree) - set(expected))
            missing = sorted(set(expected) - set(actual_tree))
            raise RuntimeError(
                f"Diferencia tras filtrar {part}: faltantes={missing[:10]}, extra={extra[:10]}"
            )
        mapping = dest / ".git" / "filter-repo" / "commit-map"
        if not mapping.is_file():
            raise RuntimeError(f"No se generó commit-map de {part}")
        artifact = target / f"{part}-commit-map.txt"
        shutil.copy2(mapping, artifact)
        root_setup(original, dest, part, args.sha)
        update_references(dest, part, args.sha, args.pages_base)
        if part == "backend":
            backend_ci(original, dest)
            backend_ci_contract(dest)
        else:
            frontend_ci(original, dest, args.backend_repo)
        (dest / "docs").mkdir(exist_ok=True)
        with (dest / "docs" / "MIGRATION.md").open("w", encoding="utf-8") as file:
            file.write(
                f"# NewGlass {part} — procedencia\n\n"
                f"Origen: https://github.com/{OWNER}/{OLD_REPO}/tree/{args.sha}\n\n"
                f"Rama de respaldo: \`{args.ref}\`.\n\n"
                f"Historial filtrado mediante git-filter-repo por \`{part}/\`. "
                f"Mapa de commits: \`../{part}-commit-map.txt\` en el directorio "
                "de artefactos de preparación. El repositorio histórico original "
                "continúa siendo la fuente de evidencias anteriores al corte.\n"
            )
        manifest["repositories"][part] = {
            "filtered_head_sha": run("rev-parse", "HEAD", cwd=dest),
            "original_files": len(expected),
            "working_tree_clean": run("status", "--porcelain", cwd=dest) == "",
            "new_root": str(dest),
            "commit_map": str(artifact),
        }
    (target / "split-manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Preparación correcta: {target}")
    print("Repo locales: frontend/ y backend/; árbol de código filtrado verificado.")
    print("Revisar diff, instalar dependencias, ejecutar CI/E2E; luego hacer commits y")
    print("crear repos GitHub vacíos. Ningún cambio se ha publicado ni desplegado.")


if __name__ == "__main__":
    main()
