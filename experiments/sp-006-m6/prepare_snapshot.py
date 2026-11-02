"""Recrear la copia pura desde el commit auditado; requiere Git solo al desarrollar."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
BASE = "f9cfd4f2644455d616699518948c6660006bdae8"
DOMAIN = "backend/app/modules/optimization/domain/"
SOURCES = [DOMAIN + name + ".py" for name in (
    "problem", "preparation", "raster_mask", "rasterizer", "placement", "rotation",
    "visual_events", "run_geometry", "packing", "first_fit", "best_fit", "worst_fit", "metrics",
)] + [
    "backend/app/modules/optimization/application/" + name + ".py"
    for name in ("ports", "preparation", "stock")
] + [
    "backend/app/modules/orders/domain/geometry.py",
    "backend/app/modules/orders/application/persisted_pieces.py",
    "experiments/optimization/loader.py",
] + [f"experiments/optimization/cases/EXP-{size}-001.json" for size in ("SMALL", "MEDIUM", "COMPLEX")]


def main():
    entries = []
    for source in SOURCES:
        data = subprocess.check_output(["git", "show", f"{BASE}:{source}"], cwd=REPO)
        target = ROOT / "vendor" / source.removeprefix("backend/")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        # Paquetes aislados: los __init__ vacíos no introducen imports de infraestructura.
        parent = target.parent
        while parent != ROOT / "vendor":
            (parent / "__init__.py").touch()
            parent = parent.parent
        entries.append({"source": source, "target": target.relative_to(ROOT).as_posix(),
                        "sha256": hashlib.sha256(data).hexdigest()})
    manifest = {"source_commit": BASE, "integration_branch": "integration/sprint-01",
                "verified_remote_date": "2026-11-02", "files": entries,
                "package_init": "Archivos __init__.py vacíos creados para aislar dependencias."}
    (ROOT / "snapshot-manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Snapshot: {len(entries)} archivos originales sin modificaciones.")


if __name__ == "__main__":
    main()
