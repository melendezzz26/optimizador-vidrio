import ast
from pathlib import Path

import pytest

MODULE = Path(__file__).resolve().parents[4] / "app/modules/orders"


@pytest.mark.parametrize("layer", ["domain", "application"])
def test_inner_layers_do_not_depend_on_outer_layers(layer):
    forbidden = {"presentation", "infrastructure", "fastapi", "sqlalchemy", "pydantic", "models", "shared"}
    if layer == "domain":
        forbidden.add("application")
    for path in (MODULE / layer).glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        for node in ast.walk(tree):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else (
                [node.module or "", *(a.name for a in node.names)] if isinstance(node, ast.ImportFrom) else []
            )
            for name in names:
                assert not forbidden.intersection(name.split(".")), (path, name)
