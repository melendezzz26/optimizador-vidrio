"""Exploración separada del benchmark definitivo del caso HF-CAPABILITY-001.

El script solo compara FF/HF para elegir el primer diseño que cumpla los
criterios declarados. Cada intento se añade al registro, incluso si falla.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from experiments.optimization.hole_filling.lab import CAPABILITY_LABEL, CASE_DIR, prepare_case  # noqa: E402
from experiments.optimization.hole_filling.optimizer import (  # noqa: E402
    metric_values, placement_signature, run_baseline, run_hole_filling,
)


CASE_ID = "HF-CAPABILITY-001"
CASE_PATH = CASE_DIR / f"{CASE_ID}.json"
LOG_PATH = CASE_DIR / "HF-CAPABILITY-SEARCH.jsonl"


def _seed(piece_id: int, geometry: dict, x: int, y: int) -> dict:
    return {
        "piece_id": piece_id, "geometry": geometry, "role": "seed",
        "stock_material_id": 8201, "x_mm": x, "y_mm": y, "rotation_deg": 0,
    }


def _rect(width: int, height: int) -> dict:
    return {"type": "RECTANGULO", "width_mm": width, "height_mm": height}


def make_case(scale: int, top_slack: int, small_side: int | None = None,
              later_width: int | None = None, later_height: int | None = None,
              later_shape: str = "triangle", panel_mode: str = "framed",
              vertical_offset: int = 0, corner_count: int = 0) -> dict:
    """Escala el marco abierto diagnóstico y reserva una franja exterior ajustada."""
    width, height = 22 * scale + 10, 20 * scale + 25 + vertical_offset
    top_panel_x = 5 + 6 * scale + top_slack
    bottom_panel_y = 18 * scale + 9 + vertical_offset
    small_side = small_side if small_side is not None else 2 * scale - 4
    later_width = later_width if later_width is not None else 5 * scale
    later_height = later_height if later_height is not None else scale - 2
    frame = [
        _seed(1, {"type": "CIRCUNFERENCIA", "radius_mm": 2 * scale}, 9 * scale + 5, 8 * scale + 5 + vertical_offset),
        _seed(2, _rect(4 * scale, 2 * scale), 6 * scale + 5, 2 * scale + 5 + vertical_offset),
        _seed(3, _rect(4 * scale, 2 * scale), 12 * scale + 5, 2 * scale + 5 + vertical_offset),
        _seed(4, _rect(2 * scale, 8 * scale), 4 * scale + 5, 6 * scale + 5 + vertical_offset),
        _seed(5, _rect(2 * scale, 8 * scale), 16 * scale + 5, 6 * scale + 5 + vertical_offset),
        _seed(6, _rect(8 * scale, 2 * scale), 7 * scale + 5, 16 * scale + 5 + vertical_offset),
    ]
    exterior_panels = [
        _seed(7, _rect(width - 5 - top_panel_x, 2 * scale - 3 + vertical_offset), top_panel_x, 5),
        _seed(8, _rect(4 * scale - 5, 16 * scale), 5, 2 * scale + 6 + vertical_offset),
        _seed(9, _rect(4 * scale - 5, 16 * scale), 18 * scale + 10, 2 * scale + 6 + vertical_offset),
        _seed(10, _rect(width - 10, height - 5 - bottom_panel_y), 5, bottom_panel_y),
    ]
    interior_blockers = [
        _seed(13, _rect(3 * scale - 8, 20), 6 * scale + 8, 10 * scale + 10 + vertical_offset),
        _seed(14, _rect(3 * scale - 8, 20), 13 * scale + 10, 10 * scale + 10 + vertical_offset),
    ]
    horizontal_blockers = [
        _seed(15, _rect(10 * scale - 10, 16), 6 * scale + 8, 4 * scale + 8 + vertical_offset),
        _seed(16, _rect(10 * scale - 10, 16), 6 * scale + 8, 12 * scale + 9 + vertical_offset),
    ]
    corner_blockers = [
        _seed(17, _rect(3 * scale - 8, 25), 6 * scale + 10, 6 * scale + 6 + vertical_offset),
        _seed(18, _rect(3 * scale - 8, 25), 13 * scale + 8, 6 * scale + 6 + vertical_offset),
    ]
    pieces = [
        *frame,
        *(exterior_panels if panel_mode in ("framed", "blocked-interior", "sealed") else []),
        *(interior_blockers if panel_mode in ("blocked-interior", "sealed") else []),
        *(horizontal_blockers if panel_mode == "sealed" else []),
        *corner_blockers[:corner_count],
        {"piece_id": 11, "geometry": _rect(small_side, small_side), "role": "pending"},
        {"piece_id": 12, "geometry": (
            _rect(later_width, later_height) if later_shape == "rectangle" else
            {"type": "CIRCUNFERENCIA", "radius_mm": later_width // 2}
            if later_shape == "circle" else
            {"type": "POLIGONO_CONVEXO",
             "vertices_mm": [[0, 0], [later_width, 0], [0, later_height]]}
        ), "role": "pending"},
    ]
    return {
        "schema_version": 1,
        "case_id": CASE_ID,
        "label": CAPABILITY_LABEL,
        "config": {
            "resolution_mm": 1, "angular_step_deg": 5,
            "margin_mm": 5, "separation_mm": 3,
        },
        "material": {"glass_type_id": 1, "thickness_mm": 6},
        "stocks": [
            {"source": "RETAZO", "material_id": 8201, "physical_unit_index": 1,
             "geometry": _rect(width, height)},
            {"source": "PLANCHA", "material_id": 9201, "physical_unit_index": 1,
             "geometry": _rect(width, height)},
        ],
        "pieces": pieces,
    }


def _summary(run: dict) -> dict:
    values = metric_values(run)
    return {
        "placed": values["placed"],
        "sheets": values["new_sheets_used"],
        "utilization_pct": str(values["utilization_pct"]),
        "waste_mm2": str(values["waste_mm2"]),
        "recoverable_mm2": str(values["recoverable_remnant_mm2"]),
        "runtime_ms": round(run["total_ms"], 3),
        "pending_placements": [list(item) for item in placement_signature(run, pending_only=True)],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scale", type=int, required=True)
    parser.add_argument("--top-slack", type=int, required=True)
    parser.add_argument("--small-side", type=int)
    parser.add_argument("--later-width", type=int)
    parser.add_argument("--later-height", type=int)
    parser.add_argument("--later-shape", choices=("triangle", "rectangle", "circle"), default="triangle")
    parser.add_argument("--panel-mode", choices=("framed", "frame-only", "blocked-interior", "sealed"), default="framed")
    parser.add_argument("--vertical-offset", type=int, default=0)
    parser.add_argument("--corner-count", type=int, choices=(0, 1, 2), default=0)
    args = parser.parse_args()
    if LOG_PATH.exists() and any(
        json.loads(line)["valid"] for line in LOG_PATH.read_text(encoding="utf-8").splitlines()
    ):
        raise RuntimeError("La búsqueda ya encontró un caso válido; no se prueban candidatos posteriores.")
    params = {
        "scale": args.scale, "top_slack": args.top_slack,
        "small_side": args.small_side, "later_width": args.later_width,
        "later_height": args.later_height, "later_shape": args.later_shape,
        "panel_mode": args.panel_mode, "vertical_offset": args.vertical_offset,
        "corner_count": args.corner_count,
    }
    case = make_case(**params)
    CASE_PATH.write_text(json.dumps(case, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    record = {"candidate_number": 1 + sum(1 for _ in LOG_PATH.open(encoding="utf-8")) if LOG_PATH.exists() else 1,
              "parameters": params, "valid": False}
    try:
        prepare_case(CASE_ID)
        ff = run_baseline(CASE_ID, "FF")
        hf = run_hole_filling(CASE_ID)
        record["ff"] = _summary(ff)
        record["hf"] = _summary(hf)
        record["pockets_detected"] = hf["diagnostics"]["pocket_components_detected"]
        record["selected_pockets"] = hf["diagnostics"]["selected_pockets"]
        ff_placements = record["ff"]["pending_placements"]
        hf_placements = record["hf"]["pending_placements"]
        record["pattern_changed"] = ff_placements != hf_placements
        record["functional_gain"] = (
            record["hf"]["sheets"] < record["ff"]["sheets"]
            or record["hf"]["placed"] > record["ff"]["placed"]
            or float(record["hf"]["utilization_pct"]) > float(record["ff"]["utilization_pct"])
            or float(record["hf"]["waste_mm2"]) < float(record["ff"]["waste_mm2"])
            or float(record["hf"]["recoverable_mm2"]) > float(record["ff"]["recoverable_mm2"])
        )
        later = case["pieces"][-1]["geometry"]
        later_height = (
            later["height_mm"] if later["type"] == "RECTANGULO"
            else 2 * later["radius_mm"] if later["type"] == "CIRCUNFERENCIA"
            else max(vertex[1] for vertex in later["vertices_mm"])
        )
        record["business_plausible"] = (
            case["pieces"][-2]["geometry"]["width_mm"] >= 18 and later_height >= 10
        )
        record["valid"] = bool(
            record["selected_pockets"]
            and any(item["piece_id"] == 11 for item in record["selected_pockets"])
            and record["pattern_changed"]
            and record["functional_gain"]
            and record["business_plausible"]
        )
    except Exception as error:
        record["error"] = f"{type(error).__name__}: {error}"
    with LOG_PATH.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    print(json.dumps(record, ensure_ascii=False, indent=2, default=str), flush=True)


if __name__ == "__main__":
    main()
