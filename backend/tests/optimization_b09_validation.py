"""Validate B09 evidence without starting services or touching a database."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/evidence/sprint-02/TA-043/B09"
BASE = "d85a8d3c4fa2ba1b3f70c401ed947adcfbe2470b"


def git(*args):
    return subprocess.check_output(
        ["git", "-c", "core.safecrlf=false", *args],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
    ).strip()


def main():
    assert git("branch", "--show-current") == "feature/TA-043-integracion-seis-motores"
    assert git("rev-parse", "integration-02") == BASE
    for path in (
        ROOT / "docs/specs/SPEC-TA-043-integracion-seis-motores.md",
        ROOT / "docs/specs/PLAN-TA-043-integracion-seis-motores.md",
    ):
        text = path.read_text(encoding="utf-8")
        assert "Draft" in text
        assert len(re.findall(r"^\| (?:RF-\d+|RNF-\d+|SM-\d+) \|", text, re.M)) == 36
    spec = (ROOT / "docs/specs/SPEC-TA-043-integracion-seis-motores.md").read_text(
        encoding="utf-8"
    )
    plan = (ROOT / "docs/specs/PLAN-TA-043-integracion-seis-motores.md").read_text(
        encoding="utf-8"
    )
    assert len(re.findall(r"^\| CA-(?:N|S)?\d+ \|", spec, re.M)) == 36
    assert len(re.findall(r"^### B\d\d ", plan, re.M)) == 11

    report = json.loads((OUT / "smoke/playwright-report.json").read_text())
    stats = report["stats"]
    assert stats == {
        "startTime": stats["startTime"],
        "duration": stats["duration"],
        "expected": 4,
        "skipped": 0,
        "unexpected": 0,
        "flaky": 0,
    }
    cleanup = json.loads((OUT / "smoke/cleanup.json").read_text())
    assert cleanup["result"] == "PASS"
    assert cleanup["runner_exit"] == 0
    assert cleanup["processes_before"] == []
    assert cleanup["processes_after"] == []
    assert cleanup["temporary_copy_removed"] is True
    assert cleanup["scenarios"] == ["TA-043 B07 smoke", "TA-043 B08 smoke"]

    projects = {}
    for project in ("chromium-desktop", "chromium-mobile"):
        b07 = json.loads(
            (OUT / f"smoke/{project}/TA-043-b07-six-engine-ui.json").read_text()
        )
        b08 = json.loads(
            (OUT / f"smoke/{project}/TA-043-b08-confirmation.json").read_text()
        )
        assert len(b07["current"]["executions"]) == 6
        assert all(
            execution["complete"] and execution["result_available"]
            for execution in b07["current"]["executions"]
        )
        assert b07["current"]["terminal"] and b07["current"]["supervisor_stopped"]
        assert b07["current"]["configuration"]["paso_angular_grados"] == "5.00"
        assert b07["postsAfterRestore"] == 1
        assert b07["inventoryBefore"] == b07["inventoryAfterV2"]
        assert b08["posts"] == 1
        assert b08["retry"] == "SAME_RECEIPT_NO_DELTA"
        assert b08["recovered"]["confirmed"] is True
        assert len(b08["after"]["movements"]) == len(b08["before"]["movements"]) + 1
        projects[project] = {
            "six_engines_complete": True,
            "configuration_angle": b07["current"]["configuration"]["paso_angular_grados"],
            "v2_posts_after_reload": b07["postsAfterRestore"],
            "confirmation_posts": b08["posts"],
            "idempotent_retry": b08["retry"],
            "inventory_unchanged_before_confirmation": True,
            "new_movements": 1,
        }

    for path, digest in cleanup["source_sha256"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, path
    for name in ("backend-focused.xml", "backend-confirmed-residual-review.xml",
                 "backend-connection-review.xml", "backend-regression.xml",
                 "frontend-focused.xml"):
        assert (ROOT / f"docs/evidence/sprint-02/TA-043/B08/{name}").exists()
    output = {
        "state": "B09_COMPLETADO",
        "base": BASE,
        "head": git("rev-parse", "HEAD"),
        "st_int": {
            "desktop": "PASS",
            "mobile": "PASS",
            "tests": 4,
            "duration_ms": stats["duration"],
            "processes_after": [],
            "temporary_copy_removed": True,
        },
        "projects": projects,
        "prior_distinct_backend_passed": 183,
        "prior_distinct_frontend_passed": 54,
        "spec_plan_draft": True,
        "requirements": 36,
        "acceptance_criteria": 36,
        "blocks": 11,
        "conditional_rf20": "NOT_EXECUTED_HU018_NOT_INTEGRATED",
        "b10_resource_capacity": "PENDING_B10",
        "source_sha256": cleanup["source_sha256"],
    }
    (OUT / "validation.json").write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(output["st_int"]))


if __name__ == "__main__":
    main()
