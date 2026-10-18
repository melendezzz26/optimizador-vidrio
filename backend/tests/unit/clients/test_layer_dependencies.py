"""Las capas internas de Clients no dependen de frameworks ni de otros módulos."""
import ast
from importlib.util import resolve_name
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[3]
MODULE = BACKEND / "app/modules/clients"
FORBIDDEN = ("fastapi", "starlette", "sqlalchemy", "pydantic", "supabase", "jwt", "app.models", "app.shared")


@pytest.mark.parametrize("layer", ["domain", "application"])
def test_inner_layer_dependencies(layer):
    files = list((MODULE / layer).glob("*.py"))
    assert files
    for path in files:
        package = ".".join(path.parent.relative_to(BACKEND).parts)
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                name = "." * node.level + (node.module or "")
                names = [resolve_name(name, package) if node.level else name]
            for name in names:
                assert not name.startswith(FORBIDDEN), (path, name)
                assert ".presentation" not in name and ".infrastructure" not in name, (path, name)
                if name.startswith("app.modules."):
                    assert name.startswith("app.modules.clients."), (path, name)
                if layer == "domain":
                    assert ".application" not in name, (path, name)
