"""Reproducible final audit for TA-043/B11 without self-referential hashes."""
from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "docs/evidence/sprint-02/TA-043"
SPEC = ROOT / "docs/specs/SPEC-TA-043-integracion-seis-motores.md"
PLAN = ROOT / "docs/specs/PLAN-TA-043-integracion-seis-motores.md"
EXPECTED_BLOCKS = tuple(f"B{i:02d}" for i in range(1, 12))


def count_rows(path: Path, prefix: str) -> int:
    text = path.read_text(encoding="utf-8")
    return len(re.findall(rf"^\| {re.escape(prefix)}", text, re.MULTILINE))


def main() -> int:
    assert SPEC.exists() and PLAN.exists()
    assert count_rows(SPEC, "RF-") == 20
    assert count_rows(SPEC, "RNF-") == 6
    assert count_rows(SPEC, "SM-") == 10
    assert len(re.findall(r"^\| CA-[A-Z0-9-]+", SPEC.read_text(encoding="utf-8"), re.MULTILINE)) == 36
    assert tuple(path.name for path in sorted(EVIDENCE.iterdir()) if path.is_dir()) == EXPECTED_BLOCKS
    for block in EXPECTED_BLOCKS:
        assert (EVIDENCE / block / "README.md").exists()
    b09 = (EVIDENCE / "B09" / "validation.json").read_text(encoding="utf-8")
    assert '"state": "B09_COMPLETADO"' in b09
    assert '"desktop": "PASS"' in b09 and '"mobile": "PASS"' in b09
    b10 = (EVIDENCE / "B10" / "measurements.json").read_text(encoding="utf-8")
    assert '"units": 12' in b10
    traceability = (EVIDENCE / "B11" / "traceability.md").read_text(encoding="utf-8")
    assert len(re.findall(r"^\| (?:RF|RNF|SM)-\d+", traceability, re.MULTILINE)) == 36
    assert "RF-20" in traceability and "CONDICIONADO" in traceability
    assert "HU-018" in traceability
    assert "Heroku" in (EVIDENCE / "B11" / "risks.md").read_text(encoding="utf-8")
    print("B11 validation PASS: 20 RF, 6 RNF, 10 SM, 36 CA, B01-B11 evidence present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
