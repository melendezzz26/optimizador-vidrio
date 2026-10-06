"""Regla de arquitectura del módulo de usuarios: dominio y aplicación sin frameworks.

Presentation -> Application -> Domain. La infraestructura implementa los
contratos; el dominio nunca importa FastAPI, SQLAlchemy ni la base.
"""
import ast
from pathlib import Path

import pytest

MODULE_DIR = Path(__file__).resolve().parents[3] / "app" / "modules" / "users"
FORBIDDEN = ("fastapi", "starlette", "sqlalchemy", "pydantic", "jwt", "bcrypt", "app.models", "app.shared")


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module)
    return names


def python_files(layer: str) -> list[Path]:
    return sorted((MODULE_DIR / layer).rglob("*.py"))


@pytest.mark.parametrize("layer", ["domain", "application"])
def test_inner_layers_do_not_import_frameworks_or_infrastructure(layer):
    files = python_files(layer)
    assert files, f"no se encontraron archivos en {layer}"
    for path in files:
        for name in imported_modules(path):
            assert not name.startswith(FORBIDDEN), f"{path.name} importa {name}"
            assert ".infrastructure" not in name, f"{path.name} importa {name}"
            assert ".presentation" not in name, f"{path.name} importa {name}"


def test_domain_does_not_import_the_application_layer():
    for path in python_files("domain"):
        for name in imported_modules(path):
            assert ".application" not in name, f"{path.name} importa {name}"
