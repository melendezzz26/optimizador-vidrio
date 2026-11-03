"""Diagnóstico acotado DJD sobre cuatro casos fijados antes de ejecutar."""
import csv
import gc
import json
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from experiments.optimization.djd.run_benchmark import run_one
from experiments.optimization.djd import DJDExperimental
from app.modules.optimization.domain.best_fit import BestFitOptimizer
from app.modules.optimization.domain.first_fit import FirstFitOptimizer
from app.modules.optimization.domain.worst_fit import WorstFitOptimizer

CASE_IDS = tuple(f"DJD-DIAGNOSTIC-{index:03d}" for index in range(1, 5))
METHODS = (("FF", FirstFitOptimizer), ("BF", BestFitOptimizer),
           ("WF", WorstFitOptimizer), ("DJD-1/3", DJDExperimental))
OUTPUT = ROOT / "docs/evidence/sprint-02/SP-004/benchmark-results"
FUNCTIONAL = ("placed_units", "remnants_used", "sheets_used", "utilization_pct", "waste", "recoverable_area")


def _case_run(case_id, method_name, optimizer):
    """Reuse the prior DJD runner's serializer for all four predeclared cases."""
    from experiments.optimization.djd.run_benchmark import load_experimental_case
    original = load_experimental_case
    def load_any(requested_case):
        if requested_case in CASE_IDS:
            path = ROOT / "experiments/optimization/djd/cases" / f"{requested_case}.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            from experiments.optimization.loader import build_problem
            return data, build_problem(data)
        return original(requested_case)
    import experiments.optimization.djd.run_benchmark as runner
    runner.load_experimental_case = load_any
    try:
        return run_one(case_id, method_name, optimizer)
    finally:
        runner.load_experimental_case = original


def _classification(rows, details):
    baseline_rows = [row for row in rows if row["method"] != "DJD-1/3"]
    djd = next(row for row in rows if row["method"] == "DJD-1/3")
    best_baseline = min(baseline_rows, key=lambda row: (-int(row["placed_units"]),
        int(row["sheets_used"]), -Decimal(row["utilization_pct"] or "0"),
        Decimal(row["waste"] or "0"), -Decimal(row["recoverable_area"] or "0")))
    detail_by_method = {item["method"]: item for item in details}
    djd_detail = detail_by_method["DJD-1/3"]
    decision_differs = any(detail_by_method[method]["placements"] != djd_detail["placements"]
        for method in ("FF", "BF", "WF")) \
        or any(int(size) > 1 for size in djd["selected_combination_sizes"].split(";") if size)
    equal_to_best = all(djd[field] == best_baseline[field] for field in FUNCTIONAL)
    equal_to_all = all(all(djd[field] == baseline[field] for field in FUNCTIONAL)
        for baseline in baseline_rows)
    if equal_to_best and (decision_differs or equal_to_all):
        category = "A"
        equivalence = "iguales a FF/BF/WF" if equal_to_all else "iguales al mejor baseline"
        reason = f"Métricas funcionales {equivalence}; DJD " + ("sí cambió grupo/placement frente a algún método." if decision_differs else "no mostró una decisión de grupo distinta.")
    else:
        improves = int(djd["placed_units"]) > int(best_baseline["placed_units"]) \
            or int(djd["sheets_used"]) < int(best_baseline["sheets_used"]) \
            or Decimal(djd["utilization_pct"] or "0") > Decimal(best_baseline["utilization_pct"] or "0") \
            or Decimal(djd["waste"] or "0") < Decimal(best_baseline["waste"] or "0") \
            or Decimal(djd["recoverable_area"] or "0") > Decimal(best_baseline["recoverable_area"] or "0")
        notable_worsening = int(djd["placed_units"]) < int(best_baseline["placed_units"]) \
            or int(djd["sheets_used"]) > int(best_baseline["sheets_used"]) \
            or Decimal(djd["utilization_pct"] or "0") <= Decimal(best_baseline["utilization_pct"] or "0") - Decimal(5) \
            or Decimal(djd["waste"] or "0") > Decimal(best_baseline["waste"] or "0") \
                + max(Decimal(1), abs(Decimal(best_baseline["waste"] or "0")) * Decimal("0.05"))
        category = "D" if notable_worsening else "C" if improves else "B"
        reason = "Clasificación respecto al mejor baseline lexicográfico (cobertura, planchas, aprovechamiento, merma, recuperable); D requiere pérdida de cobertura/plancha, caída de al menos 5 puntos o merma superior a 5% (piso 1 mm²)."
    return {"category": category, "decision_differs": decision_differs, "reason": reason,
            "djd_runtime_ms": djd["runtime_ms"], "selected_group_sizes": djd["selected_combination_sizes"],
            "selected_groups": djd_detail["djd_trace"]["selected_groups"]}


def main():
    """Corre FF/BF/WF/DJD-1/3 en serie y conserva todas las filas aunque pierda."""
    OUTPUT.mkdir(parents=True, exist_ok=True)
    all_rows, all_details, classifications = [], [], {}
    for case_id in CASE_IDS:
        case_rows, case_details = [], []
        for method, optimizer in METHODS:
            row, detail = _case_run(case_id, method, optimizer)
            case_rows.append(row)
            case_details.append(detail)
            all_rows.append(row)
            all_details.append(detail)
            print(f"{case_id} {method}: {row['placed_units']}/{row['requested_units']}; "
                  f"plancha={row['sheets_used']}; utilización={row['utilization_pct']}%; "
                  f"merma={row['waste']} mm²; ms={row['runtime_ms']}; "
                  f"grupos={row['selected_combination_sizes']}")
            gc.collect()
        classifications[case_id] = _classification(case_rows, case_details)
        print(f"  clasificación {classifications[case_id]['category']}: {classifications[case_id]['reason']}")
    csv_path = OUTPUT / "sp004_djd_diagnostic_results.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(all_rows[0]))
        writer.writeheader()
        writer.writerows(all_rows)
    json_path = OUTPUT / "sp004_djd_diagnostic_trace.json"
    json_path.write_text(json.dumps({"cases": CASE_IDS, "results": all_details,
        "classification_rule": "A: decisiones distintas y métricas iguales al mejor baseline (o iguales a todos); B: cambian sin mejora frente al mejor baseline; C: mejora frente al mejor baseline; D: pérdida de cobertura/plancha, caída de 5 puntos de utilización o aumento de merma superior a 5% (piso 1 mm²).",
        "classifications": classifications}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(csv_path)
    print(json_path)


if __name__ == "__main__":
    main()
