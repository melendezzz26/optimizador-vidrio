"""Validate the committed B10 resource measurement evidence."""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
METHODS = ("FF", "BF", "WF", "HF", "M5", "M6-BS")


def main() -> int:
    evidence = json.loads(
        (ROOT / "docs/evidence/sprint-02/TA-043/B10/measurements.json").read_text()
    )
    budget = evidence["budget"]
    assert budget["aggregate_rss_bytes"] == 1_073_741_824
    assert budget["supervisor_rss_bytes"] == 251_658_240
    assert budget["worker_address_bytes"] == 268_435_456
    assert budget["startup_seconds"] == 30
    assert budget["calculation_seconds"] == 120
    assert budget["global_seconds"] == 180
    assert len(evidence["cases"]) == 2
    assert evidence["cases"][0]["units"] == 3
    assert evidence["cases"][1]["units"] == 12
    for case in evidence["cases"]:
        assert tuple(case["methods"]) == METHODS
        assert case["maximum_active_workers"] == 1
        assert case["all_workers_stopped"] is True
        assert case["inventory_consumed"] is False
        assert case["geometry_types"] == [
            "CIRCUNFERENCIA",
            "POLIGONO_CONVEXO",
            "RECTANGULO",
        ]
        assert case["angular_step_deg"] == "5"
        assert len(case["engine_input_sha256s"]) == 1
        assert len(case["records"]) == 6
        assert all(record["complete"] for record in case["records"])
        assert all(
            record["input_sha256"] == case["engine_input_sha256s"][0]
            for record in case["records"]
        )
        assert all(record["exitcode"] == 0 for record in case["records"])
        assert all(record["cleanup_ms"] < 1000 for record in case["records"])
        assert case["maximum_aggregate_rss_bytes"] <= budget["aggregate_rss_bytes"]
        assert case["maximum_worker_virtual_bytes"] <= budget["worker_address_bytes"]
        assert case["maximum_packet_bytes_observed"] <= budget["packet_bytes"]
        assert case["total_ms"] < budget["global_seconds"] * 1000
    print("B10 evidence PASS: two scenarios, six complete engines, one worker, clean shutdown")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
