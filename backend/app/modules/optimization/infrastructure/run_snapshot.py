"""Versioned, lossless JSONB snapshot. Independent of the HTTP representation."""
from dataclasses import fields
from decimal import Decimal
from enum import Enum
from collections.abc import Mapping
from ..domain.problem import (OptimizationProblem, OptimizationConfig, MaterialGroup, PieceUnit,
                              StockCandidate, MaterialSource, Placement, OptimizationResult, OptimizationMetrics)


def json_value(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {k: json_value(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [json_value(v) for v in value]
    if hasattr(value, "__dataclass_fields__"):
        return {f.name: json_value(getattr(value, f.name)) for f in fields(value)}
    return value


def encode(result):
    return {"snapshot_version": 1, "result": json_value(result)}


def decode(snapshot):
    if snapshot.get("snapshot_version") != 1:
        raise ValueError("Unsupported durable result version.")
    data = snapshot["result"]
    p = data["problem"]
    groups = []
    def unit(values):
        return PieceUnit(**{**values, "thickness_mm": Decimal(values["thickness_mm"]), "area_mm2": Decimal(values["area_mm2"])})
    def stock(values):
        return StockCandidate(**{**values, "source": MaterialSource(values["source"]),
                                  "thickness_mm": Decimal(values["thickness_mm"]), "area_mm2": Decimal(values["area_mm2"])})
    for g in p["groups"]:
        groups.append(MaterialGroup(glass_type_id=g["glass_type_id"], thickness_mm=Decimal(g["thickness_mm"]),
                                    units=tuple(unit(u) for u in g["units"]),
                                    stock_candidates=tuple(stock(s) for s in g["stock_candidates"])))
    problem = OptimizationProblem(order_ids=tuple(p["order_ids"]),
        config=OptimizationConfig(**{k: Decimal(v) for k, v in p["config"].items()}), groups=tuple(groups))
    placements = tuple(Placement(piece=unit(v["piece"]), stock=stock(v["stock"]), geometry=v["geometry"],
                                **{k: Decimal(v[k]) for k in ("x_mm", "y_mm", "rotation_deg")}) for v in data["placements"])
    metric = data["metrics"]
    if metric is not None:
        metric = OptimizationMetrics(**{k: v if k == "new_sheets_used" else Decimal(v) for k, v in metric.items()})
    return OptimizationResult(problem=problem, placements=placements, metrics=metric,
                              computation_time_ms=data["computation_time_ms"])
