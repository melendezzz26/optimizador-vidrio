"""Frozen TA-027 inputs; no database, random values, clocks or optimization policy."""
import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from app.modules.orders.domain.geometry import GeometryValidator
from app.modules.optimization.application.preparation import prepare_persisted_problem
from app.modules.optimization.application.stock import with_compatible_stock
from app.modules.optimization.domain.problem import MaterialSource, OptimizationConfig, StockCandidate, positive_int

CASES = ("EXP-SMALL-001", "EXP-MEDIUM-001", "EXP-COMPLEX-001")
CASE_DIR = Path(__file__).resolve().parent / "cases"


def read_case(case_id):
    if case_id not in CASES:
        raise ValueError("Unknown frozen case ID.")
    return json.loads((CASE_DIR / f"{case_id}.json").read_text(encoding="utf-8"))


def area(geometry):
    shape = geometry["type"]
    if shape == "RECTANGULO":
        value = GeometryValidator.validate_rectangle(geometry["width_mm"], geometry["height_mm"])
    elif shape == "CIRCUNFERENCIA":
        value = GeometryValidator.validate_circle(geometry["radius_mm"])
    elif shape == "POLIGONO_CONVEXO":
        value = GeometryValidator.validate_convex_polygon(geometry["vertices_mm"])
    else:
        raise ValueError("Unsupported geometry.")
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def build_problem(data):
    """Reconstruct detached snapshots on every call; retain frozen source order."""
    if data["schema_version"] != 1 or data["rotation_allowed"] is not True:
        raise ValueError("Baseline requires schema 1 and enabled rotation.")
    if set(data["config"]) != {"resolution_mm", "angular_step_deg", "margin_mm", "separation_mm"}:
        raise ValueError("All optimizer parameters must be explicit.")
    config = OptimizationConfig(**{k: Decimal(str(v)) for k, v in data["config"].items()})
    if config.angular_step_deg != 5:
        raise ValueError("Baseline requires five-degree rotation.")
    if set(data["residual_limits"]) != {"minimum_width_mm", "minimum_height_mm"}:
        raise ValueError("Residual limits must be explicit.")
    for value in data["residual_limits"].values():
        number = Decimal(str(value))
        if not number.is_finite() or number <= 0:
            raise ValueError("Residual limits must be finite and positive.")
    pieces = [dict(row, area_mm2=area(row["geometria"])) for row in data["pieces"]]
    prepared = prepare_persisted_problem(data["order_ids"], pieces, config)
    candidates = []
    for row in data["stock"]:
        positive_int(row["quantity"], "stock quantity")
        source = MaterialSource(row["source"])
        if source is MaterialSource.REMNANT and row["quantity"] != 1:
            raise ValueError("Each remnant is one physical unit.")
        for index in range(1, row["quantity"] + 1):
            candidates.append(StockCandidate(
                source=source, material_id=row["material_id"], physical_unit_index=index,
                glass_type_id=row["glass_type_id"], thickness_mm=Decimal(str(row["thickness_mm"])),
                geometry=row["geometry"], area_mm2=area(row["geometry"]),
            ))
    if any(c.material_key not in {g.key for g in prepared.groups} for c in candidates):
        raise ValueError("Frozen stock must belong to a requested material group.")

    class FrozenStock:
        def list_compatible(self, key):
            return tuple(c for c in candidates if c.material_key == key)

    return with_compatible_stock(prepared, FrozenStock())


def load_problem(case_id):
    return build_problem(read_case(case_id))
