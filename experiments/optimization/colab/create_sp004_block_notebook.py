"""Construye el notebook SP004-Block-Packing con salidas del benchmark real."""
import base64
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TARGET = Path(__file__).resolve().parent / "SP004-Block-Packing.ipynb"
EVIDENCE = ROOT / "docs/evidence/sprint-02/SP-004/benchmark-results"
FIGURES = ROOT / "experiments/optimization/block_packing/figures"
BLOCK_CASE = "BLOCK-DISCRIMINANT-001"
CASE_IDS = ("EXP-SMALL-001", "EXP-MEDIUM-001", "EXP-COMPLEX-001", BLOCK_CASE)
METHODS = ("FF", "BF", "WF", "Pair-Block")
METHOD_CLASSES = {"FF": "FirstFitOptimizer", "BF": "BestFitOptimizer",
                  "WF": "WorstFitOptimizer", "Pair-Block": "BlockPackingExperimental"}
cells = []

with (EVIDENCE / "sp004_block_results.csv").open(encoding="utf-8", newline="") as stream:
    block_rows = list(csv.DictReader(stream))
with (EVIDENCE / "sp004_block_trace.json").open(encoding="utf-8") as stream:
    block_trace = json.load(stream)
with (EVIDENCE / "sp004_djd_diagnostic_results.csv").open(encoding="utf-8", newline="") as stream:
    djd_rows = list(csv.DictReader(stream))
with (EVIDENCE / "sp004_djd_diagnostic_trace.json").open(encoding="utf-8") as stream:
    djd_trace = json.load(stream)


def markdown(text):
    """Agrega una celda Markdown con saltos de línea válidos."""
    cells.append({"cell_type": "markdown", "metadata": {}, "source": text.splitlines(True)})


def code(source, output=None, image=None):
    """Agrega código con output real previamente guardado desde la ejecución local."""
    outputs = []
    if output is not None:
        outputs.append({"output_type": "stream", "name": "stdout", "text": output.splitlines(True)})
    if image is not None:
        outputs.append({"output_type": "display_data", "data": {
            "image/png": base64.b64encode(image.read_bytes()).decode("ascii"),
            "text/plain": [f"<imagen: {image.name}>\n"]}, "metadata": {}})
    count = sum(item["cell_type"] == "code" for item in cells) + 1
    cells.append({"cell_type": "code", "execution_count": count, "metadata": {},
                  "outputs": outputs, "source": source.splitlines(True)})


def section(number, title, what, why, observe, source=None, output=None, interpretation=None, image=None):
    """Agrega explicación antes del código e interpretación después de su salida."""
    markdown(f"## Sección {number}. {title}\n\n### Qué hace esta celda\n\n{what}\n\n### Por qué la necesitamos\n\n{why}\n\n### Qué deberíamos observar\n\n{observe}")
    if source is not None:
        code(source, output, image)
        if interpretation:
            markdown(f"### Interpretación de la salida\n\n{interpretation}")


markdown("""# SP-004 — Pair-Block Packing

Notebook de investigación y experimento. No integra M4 al motor productivo. Ejecuta las políticas en secuencia con el motor y las métricas de NewGlass. Los outputs incluidos provienen de la corrida local guardada; Andro puede repetir las celdas en Google Colab con el repositorio disponible.""")
markdown("""## 2. Candidatos evaluados antes

Filler se descartó como opción principal porque FF real ya ordena por área y sus resultados coincidieron prácticamente en TA-027. DJD-1/3 eligió grupos diferentes en parte de su traza, pero tuvo costo alto y no cambió métricas oficiales. Se conservan los documentos, notebooks y resultados anteriores.""")
markdown("""## 3. Artículo y adaptación

Cai et al. (2023) generan bloques con dos o más piezas de formas complementarias para mejorar la utilización local. El algoritmo publicado también usa espacios residuales con líneas de referencia, puntuación de asignación, operadores de ajuste/movimiento/llenado/reemplazo/intercambio y estrategias de repacking. Este laboratorio limita la idea a pares y no afirma replicar el método completo. [DOI 10.1016/j.cor.2023.106398](https://doi.org/10.1016/j.cor.2023.106398) · [Ficha editorial](https://www.sciencedirect.com/science/article/pii/S0305054823002629).""")
markdown("""## 4. Explicación sencilla y diferencias

Pair-Block busca dos geometrías compatibles que se complementen y las usa como unidad temporal de packing. Dos triángulos opuestos pueden ocupar juntos una caja casi rectangular; cada triángulo conserva su identidad y placement por separado. FF procesa una pieza y toma la primera ubicación; BF y WF comparan el espacio raster que queda para esa pieza. BRF evalúa el espacio residual de una colocación. No encontramos BRF implementado en el backend. Pair-Block evalúa la complementariedad de las propias geometrías antes del packing.""")

setup = """from pathlib import Path  # Importamos Path para resolver rutas en local y Colab.
import sys  # Importamos sys para habilitar imports del backend.
import csv  # Leemos resultados sin depender de pandas.
import json  # Leemos trazas crudas en JSON.
import gc  # Liberamos memoria entre corridas secuenciales.
repo_root = Path.cwd()  # Tomamos el directorio actual como raíz candidata.
if not (repo_root / "experiments/optimization/loader.py").exists():  # Detectamos si Colab abrió desde otra carpeta.
    repo_root = Path("/content/NewGlass")  # Usamos la ruta habitual del clon en Colab.
if not (repo_root / "experiments/optimization/loader.py").exists():  # Validamos que el repositorio esté disponible.
    raise RuntimeError("Abre desde la raíz de NewGlass o clona en /content/NewGlass.")  # Damos una instrucción accionable.
sys.path.insert(0, str(repo_root / "backend"))  # Habilitamos imports de la capa de dominio.
sys.path.insert(0, str(repo_root))  # Habilitamos imports del laboratorio experimental.
from app.modules.optimization.domain.first_fit import FirstFitOptimizer  # Importamos FF actual.
from app.modules.optimization.domain.best_fit import BestFitOptimizer  # Importamos BF actual.
from app.modules.optimization.domain.worst_fit import WorstFitOptimizer  # Importamos WF actual.
from experiments.optimization.block_packing import BlockPackingExperimental  # Importamos Pair-Block aislado.
from experiments.optimization.block_packing.run_benchmark import run_one  # Reutilizamos el ejecutor con métricas NewGlass.
from experiments.optimization.loader import CASES, load_problem, read_case  # Reutilizamos el loader y fixtures congelados.
benchmark_rows = {}  # Guardamos filas y placements para compararlos después.
optimizer_by_method = {"FF": FirstFitOptimizer, "BF": BestFitOptimizer, "WF": WorstFitOptimizer, "Pair-Block": BlockPackingExperimental}  # Asociamos cada etiqueta con su clase.
print("Repositorio:", repo_root)  # Confirmamos qué copia del repo se usa.
print("Ejecución: secuencial; casos oficiales:", CASES)  # Confirmamos orden y ausencia de paralelismo."""
section(5, "Entorno reproducible", "Prepara imports y rutas de trabajo.",
        "Reutilizamos clases geométricas, métricas y optimizadores del repositorio.",
        "Debe aparecer la raíz y la lista SMALL/MEDIUM/COMPLEX.", setup,
        f"Repositorio: {ROOT}\nEjecución: secuencial; casos oficiales: ('EXP-SMALL-001', 'EXP-MEDIUM-001', 'EXP-COMPLEX-001')",
        "Pair-Block se importa desde experiments/; FF/BF/WF siguen siendo el código actual.")

fixtures = """for case_id in CASES:  # Recorremos los fixtures oficiales en el orden congelado.
    case_data = read_case(case_id)  # Leemos el JSON sin modificarlo.
    problem = load_problem(case_id)  # Creamos snapshots independientes para el motor.
    print(case_id, "unidades:", len(problem.units), "grupos:", len(problem.groups), "fuentes:", len(case_data["stock"]))  # Resumimos entrada y compatibilidades.
block_data = json.loads((repo_root / "experiments/optimization/block_packing/cases/BLOCK-DISCRIMINANT-001.json").read_text(encoding="utf-8"))  # Cargamos aparte la demo no oficial.
print(block_data["label"], "piezas:", sum(item["cantidad"] for item in block_data["pieces"]))  # Separamos la demo de TA-027."""
section(6, "Entradas y fixtures", "Carga TA-027 y el caso discriminante aparte.",
        "La comparación usa las entradas reales y mantiene intacta la matriz oficial.",
        "Los casos oficiales deben contener 3, 9 y 24 unidades.",
        fixtures,
        "EXP-SMALL-001 unidades: 3 grupos: 1 fuentes: 2\nEXP-MEDIUM-001 unidades: 9 grupos: 1 fuentes: 3\nEXP-COMPLEX-001 unidades: 24 grupos: 5 fuentes: 9\nDEMO DIDÁCTICA — NO PERTENECE AL BENCHMARK OFICIAL piezas: 3",
        "El caso adicional prueba composición y trazabilidad; sus métricas no se mezclan con los resultados TA-027.")

section(7, "Criterio raster de complementariedad",
        "Explica cómo se determina si una pareja mejora la utilización local.",
        "Los pasajes editoriales accesibles respaldan el objetivo de complementariedad, pero no una fórmula autónoma universal.",
        "La adaptación calcula celdas ocupadas entre celdas de la caja envolvente y exige superar la densidad raster individual mayor.")
section(8, "Filtros para mantener acotado el costo",
        "Muestra cuántos pares pasan los filtros y la evaluación geométrica.",
        "Se empieza con parejas, límites de geometría y memoria para un equipo de 8 GB.",
        "El filtro de escala es 4:1; se prueban hasta ocho alineaciones por eje y solo rotaciones cardinales permitidas.",
        """trace_path = repo_root / "docs/evidence/sprint-02/SP-004/benchmark-results/sp004_block_trace.json"  # Ubicamos la traza del benchmark local.
trace_data = json.loads(trace_path.read_text(encoding="utf-8"))  # Cargamos los contadores reales.
for entry in trace_data["results"]:  # Recorremos casos y políticas.
    if entry["method"] == "Pair-Block":  # Seleccionamos filas con datos propios de bloques.
        item = entry["block_trace"]  # Obtenemos los contadores de pares.
        print(entry["case"], item["candidate_pairs"], item["filtered_pairs"], item["geometrically_checked_pairs"], item["accepted_blocks"])  # Mostramos candidatos, filtros, chequeos y bloques.""",
        "EXP-SMALL-001 3 0 3 0\nEXP-MEDIUM-001 36 0 36 0\nEXP-COMPLEX-001 181 0 181 1\nBLOCK-DISCRIMINANT-001 3 0 3 1",
        "COMPLEX evaluó 181 pares compatibles y aceptó una composición; no logró colocarla como bloque y usó el fallback individual. El discriminante sí colocó un bloque.")

section(9, "Rotaciones y separación",
        "Resume cómo se restringen las orientaciones y se valida la distancia entre piezas.",
        "Cada miembro debe cumplir el contrato geométrico vigente de NewGlass.",
        "Se espera el subconjunto cardinal permitido por el paso angular de 5 grados.",
        """small_config = read_case("EXP-SMALL-001")["config"]  # Leemos el paso angular oficial.
allowed_angles = [angle for angle in (0, 90, 180, 270) if angle % small_config["angular_step_deg"] == 0]  # Filtramos a los giros cardinales permitidos.
print("paso angular:", small_config["angular_step_deg"], "orientaciones:", allowed_angles)  # Informamos el subconjunto evaluado.""",
        "paso angular: 5 orientaciones: [0, 90, 180, 270]",
        "La separación interna usa SheetLayout y su regla raster del motor; no se crean rotaciones nuevas.")

demo_path = FIGURES / "block-packing-demo.png"
section(10, "Demo gráfica de dos triángulos",
        "Muestra piezas independientes, bloque temporal y colocación en una fuente.",
        "La caja compuesta nunca reemplaza los dos placements originales.",
        "La figura está rotulada como conceptual y ajena al benchmark oficial.",
        """from IPython.display import Image, display  # Importamos el visor de imágenes de Jupyter/Colab.
demo_path = repo_root / "experiments/optimization/block_packing/figures/block-packing-demo.png"  # Localizamos la ilustración en grises.
display(Image(filename=str(demo_path)))  # Mostramos los tres estados de la composición.""",
        f"Figura cargada: {demo_path.name}",
        "La pareja demostrativa alcanza compactación raster 1.0 y conserva IDs, giros y offsets propios.",
        demo_path)

case_explanations = {
    "EXP-SMALL-001": "Tres rectángulos iguales comprueban que no se fuercen bloques sin ganancia local.",
    "EXP-MEDIUM-001": "Nueve rectángulos y círculos comprueban cobertura y fallback a piezas individuales.",
    "EXP-COMPLEX-001": "Veinticuatro piezas en cinco grupos exponen el costo de evaluar pares y fallback cuando el bloque no cabe.",
    BLOCK_CASE: "La demo prueba un bloque real de triángulos y conserva los placements por pieza.",
}
interpretations = {
    "EXP-SMALL-001": "Los cuatro métodos colocaron 3/3 unidades, usaron un retazo y una plancha, y lograron 60%. Pair-Block no formó pareja útil.",
    "EXP-MEDIUM-001": "Pair-Block igualó FF en métricas y colocación total: 9/9, dos retazos y una plancha. No formó bloques.",
    "EXP-COMPLEX-001": "Pair-Block colocó 24/24 y propuso un par de compactación 0.778, pero no cupo como bloque y pasó al fallback individual. Igualó FF en fuentes, aprovechamiento y merma; tomó unos 3.00 s frente a 0.17 s de FF.",
    BLOCK_CASE: "Pair-Block colocó un bloque con triángulos en 0°/180°, preservó sus IDs y mantuvo 3/3. Las métricas globales empataron con FF/BF/WF.",
}

section_number = 11
for case_id in CASE_IDS:
    for method in METHODS:
        row = next(item for item in block_rows if item["case"] == case_id and item["method"] == method)
        output = (f"{case_id} {method}: {row['placed_units']}/{row['requested_units']}; uso={row['utilization_pct']}%; "
                  f"merma={row['waste']} mm²; retazos={row['remnants_used']}; planchas={row['sheets_used']}; "
                  f"runtime={row['runtime_ms']} ms")
        source = f"""case_id = "{case_id}"  # Seleccionamos una instancia fija de la matriz.
method_name = "{method}"  # Elegimos el método que corre en esta celda.
optimizer_class = {METHOD_CLASSES[method]}  # Reutilizamos el optimizador real o el laboratorio aislado.
row, detail = run_one(case_id, method_name, optimizer_class)  # Ejecutamos packing y métricas NewGlass.
benchmark_rows[(case_id, method_name)] = (row, detail)  # Guardamos métricas y placements para comparar.
print(f"{case_id} {method}: {{row['placed_units']}}/{{row['requested_units']}}; uso={{row['utilization_pct']}}%; merma={{row['waste']}} mm²; retazos={{row['remnants_used']}}; planchas={{row['sheets_used']}}; runtime={{row['runtime_ms']}} ms")  # Mostramos la medición."""
        if method == "Pair-Block":
            source += "\nprint(\"bloques colocados:\", row[\"placed_blocks\"], \"compactación:\", row[\"block_compaction\"])  # Añadimos las métricas específicas Pair-Block."
            output += f"\nbloques colocados: {row['placed_blocks']} compactación: {row['block_compaction']}"
        section(section_number, f"{case_id} — {method}",
                f"Ejecuta {method} sobre {case_id}.",
                case_explanations[case_id],
                "Se registran las métricas funcionales y, en Pair-Block, los contadores propios.",
                source, output,
                interpretations[case_id] if method == "Pair-Block" else "La fila es referencia con la misma entrada y configuración.")
        section_number += 1

summary_source = """csv_path = repo_root / "docs/evidence/sprint-02/SP-004/benchmark-results/sp004_block_results.csv"  # Abrimos el CSV real del benchmark.
with csv_path.open(encoding="utf-8", newline="") as file:  # Leemos filas UTF-8 sin alterar columnas.
    consolidated = list(csv.DictReader(file))  # Convertimos las filas en diccionarios.
print("caso | método | puestas | retazos | planchas | uso % | merma mm² | recuperable mm² | ms")  # Imprimimos el encabezado.
for item in consolidated:  # Recorremos las 16 combinaciones de caso y método.
    print(item["case"], item["method"], item["placed_units"], item["remnants_used"], item["sheets_used"], item["utilization_pct"], item["waste"], item["recoverable_area"], item["runtime_ms"], sep=" | ")  # Mostramos métricas comparables."""
summary_output = "caso | método | puestas | retazos | planchas | uso % | merma mm² | recuperable mm² | ms\n" + "\n".join(
    " | ".join(row[key] for key in ("case", "method", "placed_units", "remnants_used", "sheets_used", "utilization_pct", "waste", "recoverable_area", "runtime_ms"))
    for row in block_rows)
section(27, "Tabla consolidada", "Lee y presenta la evidencia CSV sin transcribir números.",
        "FF/BF/WF/Pair-Block usan el mismo cálculo oficial de métricas.",
        "Hay 16 filas para cuatro casos y cuatro métodos.", summary_source, summary_output,
        "El discriminante prueba formaci\u00f3n, mientras la decisi\u00f3n se apoya en TA-027. Pair-Block empata con FF en los tres fixtures; BF reduce 8 mm\u00b2 de merma en MEDIUM.")

blocks_source = """trace_path = repo_root / "docs/evidence/sprint-02/SP-004/benchmark-results/sp004_block_trace.json"  # Localizamos la traza de placements.
trace_data = json.loads(trace_path.read_text(encoding="utf-8"))  # Leemos giros, offsets e identidades.
for entry in trace_data["results"]:  # Recorremos todos los casos y métodos.
    if entry["method"] == "Pair-Block":  # Nos quedamos con bloques y fallback.
        print(entry["case"], entry["block_trace"]["selected_blocks"])  # Mostramos composición y ubicación."""
block_lines = [f"{item['case']} {item['block_trace']['selected_blocks']}" for item in block_trace["results"] if item["method"] == "Pair-Block"]
section(28, "Bloques seleccionados y placements originales",
        "Muestra IDs, rotaciones, offsets internos y fuente de cada bloque.",
        "La trazabilidad de piezas debe sobrevivir a la colocación como máscara compuesta.",
        "Solo COMPLEX y el discriminante contienen un bloque seleccionado.", blocks_source,
        "\n".join(block_lines),
        "En COMPLEX se aceptó geométricamente un par pero no cupo como bloque, así que pasó al fallback individual. En el discriminante los triángulos sí se colocaron como bloque con giros 0°/180° y un offset de una celda.")

det_source = """det_path = repo_root / "docs/evidence/sprint-02/SP-004/benchmark-results/sp004_block_trace.json"  # Abrimos el resumen de repeticiones.
determinism = json.loads(det_path.read_text(encoding="utf-8"))["determinism"]  # Separamos estados de determinismo.
for case_id, status in determinism.items():  # Recorremos SMALL, MEDIUM, COMPLEX y la demo.
    print(case_id, status["runs"], "PASS" if status["pass"] else "FAIL", status["runtime_ms"])  # Reportamos firma y tiempos."""
det_output = "\n".join(f"{case} x{value['runs']} {'PASS' if value['pass'] else 'FAIL'} runtime_ms={value['runtime_ms']}" for case, value in block_trace["determinism"].items())
section(29, "Determinismo ×3", "Compara layouts, pares, giros y métricas funcionales de tres corridas.",
        "El reloj puede variar, pero las decisiones geométricas deben permanecer iguales.",
        "Los cuatro casos deben registrar PASS.", det_source, det_output,
        "Los placements y bloques coincidieron en las tres ejecuciones de cada caso; solo cambian los tiempos.")

djd_source = """diagnostic_path = repo_root / "docs/evidence/sprint-02/SP-004/benchmark-results/sp004_djd_diagnostic_results.csv"  # Abrimos el CSV DJD no oficial.
with diagnostic_path.open(encoding="utf-8", newline="") as file:  # Leemos las comparaciones completas.
    diagnostic_rows = list(csv.DictReader(file))  # Guardamos FF/BF/WF/DJD.
classification_path = repo_root / "docs/evidence/sprint-02/SP-004/benchmark-results/sp004_djd_diagnostic_trace.json"  # Localizamos grupos y categorías.
classification = json.loads(classification_path.read_text(encoding="utf-8"))  # Leemos la clasificación previa.
for case_id, item in classification["classifications"].items():  # Recorremos los cuatro casos fijados.
    row = next(value for value in diagnostic_rows if value["case"] == case_id and value["method"] == "DJD-1/3")  # Encontramos sus métricas oficiales.
    print(case_id, item["category"], "grupos:", item["selected_group_sizes"], "colocadas:", row["placed_units"], "planchas:", row["sheets_used"], "uso:", row["utilization_pct"], "merma:", row["waste"], "ms:", row["runtime_ms"])  # Resumimos selección, resultado y costo."""
djd_output = "\n".join(f"{case} {item['category']} grupos={item['selected_group_sizes']} colocadas={next(row for row in djd_rows if row['case'] == case and row['method'] == 'DJD-1/3')['placed_units']} planchas={next(row for row in djd_rows if row['case'] == case and row['method'] == 'DJD-1/3')['sheets_used']} uso={next(row for row in djd_rows if row['case'] == case and row['method'] == 'DJD-1/3')['utilization_pct']} merma={next(row for row in djd_rows if row['case'] == case and row['method'] == 'DJD-1/3')['waste']} ms={item['djd_runtime_ms']}"
                       for case, item in djd_trace["classifications"].items())
section(30, "Diagnóstico adicional DJD", "Lee cuatro casos externos con la intención fijada antes de las corridas.",
        "La matriz comprueba grupos y métricas, no representa una muestra estadística.",
        "Se espera categoría A/B/C/D, tamaño de grupos y runtime.", djd_source, djd_output,
        "El caso 003 eligió una terna con métricas iguales. El caso 004 igualó al mejor baseline y se diferenció de WF. DJD no superó a FF/BF en estas pruebas.")

for number, title, file_name, meaning in (
    (31, "Aprovechamiento por método", "utilization-by-method.png", "Pair-Block no cambia aprovechamiento oficial en SMALL/MEDIUM/COMPLEX; todos empatan en el discriminante."),
    (32, "Fuentes por método", "sources-by-method.png", "WF abrió más planchas en MEDIUM y COMPLEX; Pair-Block coincide con FF/BF en cantidad."),
    (33, "Tiempo por método", "runtime-by-method.png", "Pair-Block tarda alrededor de 0.29 s en MEDIUM y 3.00 s en COMPLEX; el eje de tiempo es logarítmico."),
):
    chart = FIGURES / file_name
    chart_source = f"""from IPython.display import Image, display  # Importamos el renderizador de Colab.
chart_path = repo_root / "experiments/optimization/block_packing/figures/{file_name}"  # Localizamos el gráfico en el repo.
display(Image(filename=str(chart_path)))  # Mostramos el PNG de la corrida real."""
    section(number, title, "Carga la figura generada a partir de métricas crudas.",
            "El gráfico ayuda a comparar patrones sin sustituir los valores tabulares.",
            "Las cuatro barras por grupo representan FF, BF, WF y Pair-Block.", chart_source,
            f"Figura cargada: {file_name}", meaning, chart)

section(34, "Evaluación comparativa y selección de candidato M4",
        "Resume resultados y conecta la evidencia de Filler, DJD y Pair-Block.",
        "Una heurística debe aportar diferencia útil a un costo que compense.",
        "Pair-Block demuestra mecanismo y trazabilidad, pero el beneficio oficial es pequeño frente al aumento de runtime.")
markdown("""### Lectura de esta corrida

- **Filler:** sigue descartado como opción principal; sus documentos y resultados anteriores se preservan.
- **DJD-1/3:** el diagnóstico no encontró una mejora de grupo sobre el mejor baseline. Una terna produjo la misma métrica final.
- **Pair-Block:** GO para probar el mecanismo en laboratorio; NO-GO para TA-042 ahora. Ningún bloque se colocó en los fixtures oficiales; en COMPLEX la política igualó a FF y tomó cerca de 17.7 veces más. El discriminante sí colocó un bloque y cambió el patrón, pero empató en métricas.

Recomendación: no integrar ninguno de los tres como M4 productiva con esta evidencia. Pair-Block es la opción más directamente alineada con formas complementarias para una futura investigación, condicionada a reducir el costo de generar pares y demostrar cambios funcionales en más instancias razonables.""")

notebook = {
    "cells": cells,
    "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                 "language_info": {"name": "python", "version": "3.11.0"}},
    "nbformat": 4, "nbformat_minor": 5,
}
TARGET.write_text(json.dumps(notebook, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"Notebook escrito: {TARGET}")
print(f"Secciones: 34; celdas: {len(cells)}; código: {sum(item['cell_type'] == 'code' for item in cells)}")
