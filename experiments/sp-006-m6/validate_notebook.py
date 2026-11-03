"""Validación secuencial: ejecutar solo el .ipynb en un directorio limpio."""
import json
import hashlib
import os
from pathlib import Path
import shutil
import sys
import tempfile
from time import perf_counter

import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parent


def main():
    notebook_path = ROOT / "SP-006_M6_Beam_Search.ipynb"
    notebook = nbformat.read(notebook_path, as_version=4)
    nbformat.validate(notebook)
    assert all(not c.get("outputs") and c.get("execution_count") is None
               for c in notebook.cells if c.cell_type == "code")
    text = notebook_path.read_text(encoding="utf-8")
    assert ":\\\\Users\\\\" not in text and "/home/" not in text and "/mnt/" not in text
    (ROOT / "results").mkdir(exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="clean-notebook-", dir=ROOT / "results"))
    shutil.copy2(notebook_path, work / notebook_path.name)
    for name in ("JUPYTER_RUNTIME_DIR", "IPYTHONDIR"):
        path = ROOT / "results" / name.lower()
        path.mkdir(parents=True, exist_ok=True)
        os.environ[name] = str(path)
    os.environ["PYTHONNOUSERSITE"] = "1"
    os.environ.pop("PYTHONPATH", None)
    started = perf_counter()
    client = NotebookClient(notebook, timeout=180, kernel_name="python3", resources={"metadata": {"path": str(work)}})
    client.execute()
    elapsed = perf_counter() - started
    assert not [out for c in notebook.cells for out in c.get("outputs", []) if out.output_type == "error"]
    nbformat.write(notebook, ROOT / "results" / "SP-006.executed.ipynb")
    results = work / "sp006_colab" / "results"
    bundle = json.loads((results / "results.json").read_text(encoding="utf-8"))
    assert len(bundle["records"]) == 36
    for name, digest in bundle["metadata"]["experiment_hashes"].items():
        assert hashlib.sha256((ROOT / "sp006" / name).read_bytes()).hexdigest() == digest
    assert all(r["status"] == "COMPLETE" and r["deterministic"] and r["validation"]["valid"] for r in bundle["records"])
    assert len(list((results / "figures").glob("*.png"))) == 19
    assert (work / "sp006_colab" / "SP-006_resultados.zip").is_file()
    evidence = ROOT / "evidence"
    evidence.mkdir(exist_ok=True)
    for filename in ("results.json", "results.csv", "deltas-vs-baselines.csv", "analysis.txt"):
        shutil.copy2(results / filename, evidence / ("local-cpu-" + filename))
    for size in ("SMALL", "MEDIUM", "COMPLEX"):
        name = f"EXP-{size}-001_BS-3.png"
        shutil.copy2(results / "figures" / name, evidence / name)
    report = dict(notebook_valid=True, cells=len(notebook.cells),
        code_cells=sum(c.cell_type == "code" for c in notebook.cells),
        sequential_execution=True, clean_input="Solo se copió el notebook; bootstrap reconstruyó sus archivos.",
        execution_seconds=elapsed, records=36, complete=36, geometry_valid=36,
        deterministic=36, figures=19, csv_json_zip=True, skipped_cells=0,
        actual_colab_execution=False, python=sys.version.split()[0],
        limitations=["Validación local Windows CPU, no sesión real de Google Colab.",
                     "No certifica escala industrial ni rendimiento del backend."])
    (evidence / "notebook-validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
