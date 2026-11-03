"""Ejecuciones secuenciales aisladas, muestreo RSS y exportación sin inventario."""
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
from time import perf_counter, sleep
from datetime import datetime, timezone

import psutil
from sp006.validation import ROOT, verify_snapshot

METHODS = ("FF", "BF", "WF", "BS-2", "BS-3", "BS-4")
CASES = tuple(f"EXP-{s}-001" for s in ("SMALL", "MEDIUM", "COMPLEX"))


def run_one(case_id, method, *, seconds=30, rss_limit_mib=256, search=None, original_repo=None):
    request = dict(case_id=case_id, method=method, seconds=seconds, rss_limit_mib=rss_limit_mib, search=search or {})
    # original_repo se usa solo en la prueba local de equivalencia, nunca en Colab.
    paths = [str(ROOT)]
    paths += [str(Path(original_repo) / "backend"), str(original_repo)] if original_repo else [str(ROOT / "vendor")]
    env = dict(os.environ, PYTHONPATH=os.pathsep.join(paths), PYTHONUTF8="1")
    with tempfile.TemporaryDirectory(prefix="sp006-") as directory:
        temp = Path(directory)
        (temp / "input.json").write_text(json.dumps(request), encoding="utf-8")
        with (temp / "worker.log").open("w", encoding="utf-8") as log:
            proc = subprocess.Popen([sys.executable, "-m", "sp006.worker", str(temp / "input.json"),
                                     str(temp / "output.json")], cwd=temp, env=env, stdout=log, stderr=log)
            observed, samples, started, killed = 0, 0, perf_counter(), None
            try:
                monitored = psutil.Process(proc.pid)
                while proc.poll() is None:
                    try:
                        observed = max(observed, monitored.memory_info().rss)
                        samples += 1
                    except psutil.NoSuchProcess:
                        break
                    if observed > rss_limit_mib * 1024 ** 2:
                        killed = "RSS_MEMORY_LIMIT"
                    elif perf_counter() - started > seconds + 30:
                        killed = "PROCESS_TIME_LIMIT"
                    if killed:
                        proc.kill()
                        break
                    sleep(0.01)
            finally:
                if proc.poll() is None:
                    proc.kill()
                proc.wait()
        if killed:
            record = dict(case_id=case_id, method=method, status="LIMIT", stop_reason=killed)
        elif not (temp / "output.json").exists():
            record = dict(case_id=case_id, method=method, status="ERROR", error=(temp / "worker.log").read_text(encoding="utf-8")[-2000:])
        else:
            record = json.loads((temp / "output.json").read_text(encoding="utf-8"))
        record.update(peak_rss_mib=observed / 1024 ** 2, rss_samples=samples, rss_sample_interval_ms=10)
        return record


def run_suite(*, repeats=2, context="local_cpu", progress=True, seconds=30):
    manifest = verify_snapshot()
    records = []
    for repeat in range(1, repeats + 1):
        # Alternar orden para comprobar ausencia de contaminación entre métodos.
        methods = METHODS if repeat % 2 else tuple(reversed(METHODS))
        for case_id in CASES:
            for method in methods:
                record = run_one(case_id, method, seconds=seconds)
                record.update(repeat=repeat, origin="measured_" + context, source_commit=manifest["source_commit"])
                records.append(record)
                if progress:
                    print(case_id, method, f"repetición {repeat}", record["status"],
                          f"{record.get('placed', '?')}/{record.get('requested', '?')}", flush=True)
    for record in records:
        siblings = [r for r in records if (r["case_id"], r["method"]) == (record["case_id"], record["method"])]
        eligible = len(siblings) >= 2 and all(r.get("signature") and r.get("status") != "LIMIT" for r in siblings)
        record["deterministic"] = len({r["signature"] for r in siblings}) == 1 if eligible else None
    metadata = dict(context=context, python=platform.python_version(), platform=platform.system(),
        machine=platform.machine(), cpu_count=os.cpu_count(), timestamp_utc=datetime.now(timezone.utc).isoformat(),
        package_versions={name: version(name) for name in ("numpy", "pandas", "matplotlib", "psutil")},
        source_commit=manifest["source_commit"], repeats=repeats, sequential_workers=True,
        seconds_per_solve=seconds, process_seconds_limit=seconds + 30, rss_limit_mib=256,
        fixture_hashes={Path(e["target"]).stem: e["sha256"] for e in manifest["files"] if e["target"].endswith(".json")},
        experiment_hashes={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT / "sp006").glob("*.py"))},
        search_defaults=__import__("dataclasses").asdict(__import__("sp006.beam", fromlist=["SearchLimits"]).SearchLimits()))
    return dict(metadata=metadata, records=records)


def table(bundle):
    import pandas as pd
    rows = []
    for record in bundle["records"]:
        row = {k: record.get(k) for k in ("case_id", "method", "repeat", "origin", "status", "stop_reason", "requested",
               "placed", "processed_units", "sheets_used", "remnants_used", "elapsed_s", "peak_rss_mib", "deterministic")}
        row["unplaced_count"] = len(record["unplaced"]) if "unplaced" in record else None
        row["no_fit_count"] = len(record["no_fit_units"]) if "no_fit_units" in record else None
        row["pending_count"] = len(record["pending_units"]) if "pending_units" in record else None
        row["geometry_valid"] = record.get("validation", {}).get("valid")
        row.update(record.get("metrics") or {})
        rows.append(row)
    frame = pd.DataFrame(rows)
    for name in ("utilization_pct", "placed_piece_area_mm2", "material_area_mm2", "waste_mm2", "recoverable_remnant_mm2"):
        if name not in frame:
            frame[name] = None
        frame[name] = pd.to_numeric(frame[name], errors="coerce")
    return frame


def export(bundle, directory="results"):
    target = Path(directory)
    target.mkdir(parents=True, exist_ok=True)
    (target / "results.json").write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    table(bundle).to_csv(target / "results.csv", index=False, encoding="utf-8-sig")
    deltas(bundle).to_csv(target / "deltas-vs-baselines.csv", index=False, encoding="utf-8-sig")
    return target


def deltas(bundle):
    import pandas as pd
    frame = table(bundle)
    rows = []
    numeric = ("placed", "sheets_used", "remnants_used", "utilization_pct", "waste_mm2",
               "recoverable_remnant_mm2", "elapsed_s", "peak_rss_mib")
    for case_id, part in frame.groupby("case_id"):
        for method in ("BS-2", "BS-3", "BS-4"):
            for baseline in ("FF", "BF", "WF"):
                candidate, reference = part[part.method == method], part[part.method == baseline]
                comparable = (not candidate.empty and not reference.empty
                    and candidate.status.isin(["COMPLETE", "PARTIAL_GEOMETRIC"]).all()
                    and reference.status.isin(["COMPLETE", "PARTIAL_GEOMETRIC"]).all())
                row = dict(case_id=case_id, method=method, baseline=baseline, comparable=bool(comparable))
                for metric in numeric:
                    row["delta_" + metric + ("_pp" if metric == "utilization_pct" else "")] = (
                        float(candidate[metric].median() - reference[metric].median())
                        if comparable and metric in frame else None)
                rows.append(row)
    return pd.DataFrame(rows)


if __name__ == "__main__":
    export(run_suite())
