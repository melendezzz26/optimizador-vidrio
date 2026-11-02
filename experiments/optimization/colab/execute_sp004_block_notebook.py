"""Ejecuta secuencialmente todas las celdas del notebook y actualiza sus outputs."""
import base64
import contextlib
import io
import json
import os
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
NOTEBOOK = Path(__file__).resolve().parent / "SP004-Block-Packing.ipynb"
LAST_IMAGE = None


class NotebookImage:
    """Adaptador de imagen mínimo para capturar display_data sin instalar Jupyter."""
    def __init__(self, filename):
        self.filename = Path(filename)


def display(value):
    """Retiene la imagen que Colab mostrará al ejecutar la misma celda."""
    global LAST_IMAGE
    if isinstance(value, NotebookImage):
        LAST_IMAGE = value.filename


ipython_module = types.ModuleType("IPython")
display_module = types.ModuleType("IPython.display")
display_module.Image = NotebookImage
display_module.display = display
ipython_module.display = display_module
sys.modules["IPython"] = ipython_module
sys.modules["IPython.display"] = display_module

os.chdir(ROOT)
notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
namespace = {"__name__": "__main__"}
execution_count = 0
for index, cell in enumerate(notebook["cells"]):
    if cell["cell_type"] != "code":
        continue
    execution_count += 1
    source = "".join(cell["source"])
    output = io.StringIO()
    LAST_IMAGE = None
    with contextlib.redirect_stdout(output):
        exec(compile(source, f"{NOTEBOOK.name}:cell-{execution_count}", "exec"), namespace)
    outputs = []
    stdout = output.getvalue()
    if stdout:
        outputs.append({"output_type": "stream", "name": "stdout", "text": stdout.splitlines(True)})
    if LAST_IMAGE is not None:
        outputs.append({"output_type": "display_data", "data": {
            "image/png": base64.b64encode(LAST_IMAGE.read_bytes()).decode("ascii"),
            "text/plain": [f"<imagen: {LAST_IMAGE.name}>\n"]}, "metadata": {}})
    cell["execution_count"] = execution_count
    cell["outputs"] = outputs
    print(f"Celda de código {execution_count}: ejecutada")

NOTEBOOK.write_text(json.dumps(notebook, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"Outputs escritos en {NOTEBOOK}")
