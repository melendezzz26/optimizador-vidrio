import ast
from pathlib import Path

from app.modules.optimization.application.ports import RasterizedPiece
from app.modules.optimization.domain.raster_mask import RasterMask
from app.modules.optimization.presentation.serialization import raster_response


def test_lossless_runs_above_53_bits_and_empty_row():
    mask = RasterMask(5, 80, (1 | (1 << 79), 0, (1 << 80) - 1))
    piece = dict(id_pedido=10, id_pieza=25, tipo_forma="RECTANGULO", cantidad=5,
                 geometria=dict(type="RECTANGULO", width_mm=400, height_mm=15),
                 id_tipo_vidrio=7, espesor_mm="6.00")
    data = raster_response(RasterizedPiece(piece, mask)).model_dump(mode="json")
    assert data["spans_by_row"][1] == {"row": 1, "runs": []}
    restored = [sum(((1 << (end - start)) - 1) << start for start, end in row["runs"])
                for row in data["spans_by_row"]]
    assert tuple(restored) == mask.rows
    assert sum(end - start for row in data["spans_by_row"] for start, end in row["runs"]) == data["occupied_cells"]
    assert len(data["spans_by_row"]) == 3 and data["cantidad"] == 5
    assert data["espesor_mm"] == "6.00"


def test_inner_layers_remain_independent_of_http_orm_and_orders_internals():
    root = Path(__file__).resolve().parents[3] / "app/modules/optimization"
    forbidden = {"sqlalchemy", "fastapi", "pydantic", "models", "infrastructure", "presentation"}
    for layer in ("application", "domain"):
        for path in (root / layer).glob("*.py"):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                names = [a.name for a in node.names] if isinstance(node, ast.Import) else (
                    [node.module or ""] if isinstance(node, ast.ImportFrom) else [])
                assert all(not forbidden.intersection(name.split(".")) for name in names), path


def test_response_preserves_persisted_integer_vertices_without_float_coercion():
    origin = 9007199254740993
    geometry = dict(type="POLIGONO_CONVEXO", vertices_mm=[[origin, 0], [origin + 10, 0], [origin, 10]])
    piece = dict(id_pedido=10, id_pieza=25, tipo_forma="POLIGONO_CONVEXO", cantidad=5,
                 geometria=geometry, id_tipo_vidrio=7, espesor_mm="6.00")
    data = raster_response(RasterizedPiece(piece, RasterMask(5, 2, (3, 1)))).model_dump(mode="json")
    assert data["geometria"] == geometry
    assert str(origin) in raster_response(RasterizedPiece(piece, RasterMask(5, 2, (3, 1)))).model_dump_json()
