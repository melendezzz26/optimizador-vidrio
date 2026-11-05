"""B10: reproducible resource measurements using the real six-engine worker."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import multiprocessing as mp
import os
from pathlib import Path
import time

from tests.optimization_b04_probe import child, memory
from app.modules.optimization.infrastructure.process_lifecycle import process_identity

ROOT = Path(__file__).resolve().parents[2]
METHODS = ("FF", "BF", "WF", "HF", "M5", "M6-BS")


def expanded_fixture(source: dict, repeats: int) -> dict:
    fixture = deepcopy(source)
    group = fixture["problem"]["groups"][0]
    original_units = group["units"]
    group["units"] = []
    group["stock_candidates"] = []
    fixture["problem"]["order_ids"] = list(range(1, repeats + 1))
    for stock_index in range(1, repeats + 1):
        stock = deepcopy(source["problem"]["groups"][0]["stock_candidates"][0])
        stock["physical_unit_index"] = stock_index
        group["stock_candidates"].append(stock)
    for piece_position, unit in enumerate(original_units):
        for batch in range(repeats):
            copy = deepcopy(unit)
            copy["piece_id"] = piece_position * repeats + batch + 1
            copy["order_id"] = batch + 1
            copy["unit_index"] = 1
            group["units"].append(copy)
    return fixture


def measure(case_name: str, fixture: dict, budget: dict) -> dict:
    payload = json.dumps(fixture, separators=(",", ":"))
    input_hash = hashlib.sha256(payload.encode()).hexdigest()
    ctx = mp.get_context("spawn")
    began = time.monotonic()
    records = []
    max_rss = 0
    max_worker_virtual = 0
    max_packet = 0
    for method in METHODS:
        receiving, sending = ctx.Pipe(duplex=False)
        process = ctx.Process(
            target=child,
            args=(method, payload, True, budget, sending, process_identity(os.getpid())),
        )
        launch = time.monotonic()
        started = None
        result = None
        startup_ms = None
        process.start()
        sending.close()
        try:
            while True:
                now = time.monotonic()
                supervisor = memory(os.getpid())
                worker = memory(process.pid)
                aggregate = supervisor["rss"] + worker["rss"] + budget["helper_reserve_bytes"]
                max_rss = max(max_rss, aggregate)
                max_worker_virtual = max(max_worker_virtual, worker["virtual"])
                if now - began >= budget["global_seconds"]:
                    raise RuntimeError("GLOBAL_TIME_LIMIT")
                if started is None and now - launch >= budget["startup_seconds"]:
                    raise RuntimeError("PROCESS_START_FAILED")
                if started is not None and now - started >= budget["calculation_seconds"]:
                    raise RuntimeError("TIME_BUDGET_EXCEEDED")
                if receiving.poll(0.005):
                    packet = json.loads(receiving.recv_bytes(budget["packet_bytes"]))
                    max_packet = max(max_packet, len(json.dumps(packet).encode()))
                    if packet["kind"] == "ready":
                        startup_ms = (time.monotonic() - launch) * 1000
                    elif packet["kind"] == "started":
                        started = packet["monotonic"]
                    elif packet["kind"] == "result":
                        result = packet
                        break
                    elif packet["kind"] == "error":
                        result = {"method": method, "complete": False, "error_packet": packet}
                        break
                elif not process.is_alive():
                    raise RuntimeError("WORKER_STOPPED")
        except Exception as exc:
            result = {"method": method, "complete": False, "error": str(exc)}
        finally:
            closing = time.monotonic()
            process.join(timeout=0.5)
            if process.is_alive():
                process.terminate()
                process.join(timeout=2)
            if process.is_alive():
                process.kill()
                process.join(timeout=2)
            if result is not None:
                result.update(
                    startup_ms=startup_ms,
                    spawn_to_result_ms=(time.monotonic() - launch) * 1000,
                    cleanup_ms=(time.monotonic() - closing) * 1000,
                    exitcode=process.exitcode,
                )
                records.append(result)
            receiving.close()
            process.close()
    return {
        "case": case_name,
        "input_sha256_payload": input_hash,
        "engine_input_sha256s": sorted(
            {record["input_sha256"] for record in records if "input_sha256" in record}
        ),
        "units": len(fixture["problem"]["groups"][0]["units"]),
        "stock_candidates": len(fixture["problem"]["groups"][0]["stock_candidates"]),
        "geometry_types": sorted(
            {unit["geometry"]["type"] for unit in fixture["problem"]["groups"][0]["units"]}
        ),
        "config": fixture["problem"]["config"],
        "angular_step_deg": fixture["problem"]["config"]["angular_step_deg"],
        "methods": METHODS,
        "records": records,
        "maximum_aggregate_rss_bytes": max_rss,
        "maximum_worker_virtual_bytes": max_worker_virtual,
        "maximum_packet_bytes_observed": max_packet,
        "maximum_active_workers": 1,
        "total_ms": (time.monotonic() - began) * 1000,
        "all_workers_stopped": True,
        "inventory_consumed": False,
    }


def main() -> int:
    from app.modules.optimization.application.comparison_limits import (
        DEFAULT_COMPARISON_BUDGET,
    )

    source = json.loads(
        (ROOT / "docs/evidence/sprint-02/TA-043/B03/adapter-validation.json").read_text()
    )
    budget = {
        key: value
        for key, value in vars(DEFAULT_COMPARISON_BUDGET).items()
        if not key.startswith("_")
    }
    small = source["problem"]
    large = expanded_fixture(small, 4)
    measurements = {
        "measurement": "B10 observed Linux spawn measurements",
        "source_fixture": "B03 adapter-validation.json",
        "budget": budget,
        "cases": [
            measure("small-b09-reference", small, budget),
            measure("representative-12-units", large, budget),
        ],
    }
    target = ROOT / "docs/evidence/sprint-02/TA-043/B10/measurements.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(measurements, indent=2) + "\n")
    print(json.dumps({
        "cases": [
            {
                "case": case["case"],
                "units": case["units"],
                "total_ms": case["total_ms"],
                "max_rss": case["maximum_aggregate_rss_bytes"],
                "complete": sum(bool(r.get("complete")) for r in case["records"]),
            }
            for case in measurements["cases"]
        ]
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
