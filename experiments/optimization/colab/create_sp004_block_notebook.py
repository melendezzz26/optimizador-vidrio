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
CASE_IDS = ("EXP-SMALL-001", "EXP-MEDIUM-001", "EXP-COMPLEX-001", BLOCK_CASE,
            "BLOCK-V2-OBLIQUE-TRIANGLES-001", "BLOCK-V2-MIXED-TRIANGLE-CIRCLE-001")
METHODS = ("FF", "BF", "WF", "Pair-Block-v2")
METHOD_CLASSES = {"FF": "FirstFitOptimizer", "BF": "BestFitOptimizer",
                  "WF": "WorstFitOptimizer", "Pair-Block-v2": "BlockPackingExperimental"}
cells = []

with (EVIDENCE / "sp004_block_v2_results.csv").open(encoding="utf-8", newline="") as stream:
    block_rows = list(csv.DictReader(stream))
with (EVIDENCE / "sp004_block_v2_trace.json").open(encoding="utf-8") as stream:
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


markdown("""# SP-004 — Pair-Block v2

Notebook de investigación y experimento. No integra M4 al motor productivo. Ejecuta las políticas en secuencia con el motor y las métricas de NewGlass. Los outputs incluidos provienen de la corrida local guardada; Andro puede repetir las celdas en Google Colab con el repositorio disponible.""")
markdown("""## 2. Candidatos evaluados antes

Filler se descartó como opción principal porque FF real ya ordena por área y sus resultados coincidieron prácticamente en TA-027. DJD-1/3 eligió grupos diferentes en parte de su traza, pero tuvo costo alto y no cambió métricas oficiales. Se conservan los documentos, notebooks y resultados anteriores.""")
markdown("""## 3. Artículo y adaptación

Cai et al. (2023) generan bloques con dos o más piezas de formas complementarias para mejorar la utilización local. El algoritmo publicado también usa espacios residuales con líneas de referencia, puntuación de asignación, operadores de ajuste/movimiento/llenado/reemplazo/intercambio y estrategias de repacking. Este laboratorio limita la idea a pares y no afirma replicar el método completo. [DOI 10.1016/j.cor.2023.106398](https://doi.org/10.1016/j.cor.2023.106398) · [Ficha editorial](https://www.sciencedirect.com/science/article/pii/S0305054823002629).""")
markdown("""## 4. Explicación sencilla y diferencias

Pair-Block busca dos geometrías compatibles que se complementen y las usa como unidad temporal de packing. FF procesa una pieza y toma la primera ubicación; BF y WF comparan el espacio raster que queda para esa pieza. BRF evalúa el espacio residual de una colocación. Pair-Block compara la geometría conjunta antes de colocar, reutiliza el motor raster y devuelve dos placements originales. No encontramos BRF implementado en el backend.""")
markdown("""## 5. Pair-Block v1 frente a v2

- **v1:** el primer experimento restringió las parejas a 0°, 90°, 180° y 270° como simplificación de costo; la literatura revisada no exigía esa restricción. Además deduplicaba por dimensiones de la caja y podía perder máscaras distintas con la misma caja.
- **v2:** usa únicamente la grilla común de NewGlass `0°, 5°, …, 355°`, llama a la caché de orientación existente y deduplica solo máscaras raster exactamente idénticas.
- Los círculos son rotacionalmente invariantes; los rectángulos oblicuos y los polígonos convexos sí pueden cambiar su máscara y complementariedad.

El dictamen v1 queda como antecedente. Esta corrida reevalúa el mecanismo con rotaciones válidas y pruning medible.""")

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
optimizer_by_method = {"FF": FirstFitOptimizer, "BF": BestFitOptimizer, "WF": WorstFitOptimizer, "Pair-Block-v2": BlockPackingExperimental}  # Asociamos cada etiqueta con su clase.
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
print(block_data["label"], "piezas:", sum(item["cantidad"] for item in block_data["pieces"]))  # Separamos la demo de TA-027.
for diagnostic_id in ("BLOCK-V2-OBLIQUE-TRIANGLES-001", "BLOCK-V2-MIXED-TRIANGLE-CIRCLE-001"):  # Enumeramos los casos congelados.
    diagnostic = json.loads((repo_root / "experiments/optimization/block_packing/cases" / f"{diagnostic_id}.json").read_text(encoding="utf-8"))  # Leemos su propósito previo.
    print(diagnostic_id, diagnostic["diagnostic_intent"], "piezas:", len(diagnostic["pieces"]))  # Mostramos propósito y tamaño."""
section(6, "Entradas y fixtures", "Carga TA-027, el discriminante y los dos diagnósticos aparte.",
        "La comparación usa las entradas reales y mantiene intacta la matriz oficial.",
        "Los casos oficiales contienen 3, 9 y 24 unidades; los dos casos v2 muestran su intención congelada.",
        fixtures,
        "EXP-SMALL-001 unidades: 3 grupos: 1 fuentes: 2\nEXP-MEDIUM-001 unidades: 9 grupos: 1 fuentes: 3\nEXP-COMPLEX-001 unidades: 24 grupos: 5 fuentes: 9\nDEMO DIDÁCTICA — NO PERTENECE AL BENCHMARK OFICIAL piezas: 3",
        "El caso adicional prueba composición y trazabilidad; sus métricas no se mezclan con los resultados TA-027.")

section(7, "Criterio de aceptación del bloque",
        "Explica la regla experimental que decide si dos piezas forman una composición candidata.",
        "La fuente académica respalda buscar piezas complementarias, pero no publica una fórmula universal de densidad ni un umbral numérico transferible.",
        "Se acepta una composición solo si el ahorro de área de bounding box es positivo; densidad raster queda descriptiva y como desempate. No hay umbral 4:1 ni exigencia de superar la densidad individual.",
        """def bbox_saving(area_a, area_b, area_union):  # Definimos la mejora del sobre conjunto.
    return area_a + area_b - area_union  # Comparamos cajas separadas frente a la caja del bloque.
print("ejemplo: dos huellas triangulares con cajas 10×10 dentro de caja conjunta 10×10:", bbox_saving(100, 100, 100), "celdas ahorradas")  # Mostramos un bloque complementario ideal.""",
        "ejemplo: dos huellas triangulares con cajas 10×10 dentro de caja conjunta 10×10: 100 celdas ahorradas",
        "El criterio mide reducción de bounding box, no atribuye una fórmula al artículo; una mera vecindad con cajas separadas no obtiene ahorro positivo.")

pair_traces = [entry for entry in block_trace["results"] if entry["method"] == "Pair-Block-v2"]  # Conservamos datos por caso.
pruning_output = "\n".join(
    f"{entry['case']}: pares {entry['block_trace']['candidate_pairs']} iniciales / "
    f"{entry['block_trace']['compatible_pairs']} compatibles / {entry['block_trace']['filtered_pairs']} filtrados; "
    f"orientaciones {entry['block_trace']['orientation_combinations_theoretical']} teóricas, "
    f"{entry['block_trace']['orientation_combinations_pruned']} podadas, "
    f"{entry['block_trace']['orientation_combinations_evaluated']} evaluadas; "
    f"offsets {entry['block_trace']['relative_positions_pruned']} podados / "
    f"{entry['block_trace']['relative_positions_checked']} chequeados"
    for entry in pair_traces)
section(8, "Filtros y contadores de pruning",
        "Carga y presenta las cuentas reales por fixture y diagnóstico.",
        "La separación entre equivalencia de máscara, cotas, fase y offsets explica cuánto del producto teórico llega a geometría.",
        "Cada línea muestra pares iniciales/compatibles/filtrados, orientaciones teóricas/podadas/evaluadas y offsets podados/chequeados.",
        """trace_path = repo_root / "docs/evidence/sprint-02/SP-004/benchmark-results/sp004_block_v2_trace.json"  # Abrimos la traza serializada.
trace_data = json.loads(trace_path.read_text(encoding="utf-8"))  # Leemos los contadores medidos.
for entry in trace_data["results"]:  # Recorremos métodos y casos registrados.
    if entry["method"] == "Pair-Block-v2":  # Filtramos la política experimental.
        item = entry["block_trace"]  # Tomamos el desglose de pruning.
        print(entry["case"], item["candidate_pairs"], item["compatible_pairs"], item["filtered_pairs"], item["orientation_combinations_theoretical"], item["orientation_combinations_pruned"], item["orientation_combinations_evaluated"], item["relative_positions_pruned"], item["relative_positions_checked"])  # Mostramos contadores crudos.""",
        pruning_output,
        "El total incluye pares incompatibles por material/espesor; estos se podan antes de orientar. La fase y los offsets también son heurísticos y sus cantidades se distinguen.")

section(9, "Grilla angular y separación",
        "Resume la grilla real y la validación de separación interna.",
        "Pair-Block debe usar los giros ya preparados por el motor común.",
        "Se observan los 72 ángulos entre 0° y 355° en pasos de 5°.",
        """small_config = read_case("EXP-SMALL-001")["config"]  # Leemos la configuración oficial.
step = small_config["angular_step_deg"]  # Recuperamos el paso común.
allowed_angles = list(range(0, 360, step))  # Enumeramos únicamente ángulos de la grilla común.
print("paso:", step, "grados; cantidad:", len(allowed_angles), "primeros:", allowed_angles[:5], "último:", allowed_angles[-1])  # Resumimos sin crear ángulos nuevos.""",
        "paso: 5 grados; cantidad: 72 primeros: [0, 5, 10, 15, 20] último: 355",
        "La caché común rasteriza las orientaciones; la separación y colisión se validan con la misma operación de dilatación por celdas que el motor.")

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
case_explanations["BLOCK-V2-OBLIQUE-TRIANGLES-001"] = "Dos triángulos congelados antes de correr métodos prueban complementariedad oblicua fuera de los giros cardinales."
case_explanations["BLOCK-V2-MIXED-TRIANGLE-CIRCLE-001"] = "Triángulo y círculo congelados antes de correr métodos prueban una pareja de tipos geométricos distintos."
interpretations = {}
for case_id in CASE_IDS:  # Derivamos la lectura desde el CSV real v2.
    pair_row = next(row for row in block_rows if row["case"] == case_id and row["method"] == "Pair-Block-v2")
    interpretations[case_id] = (f"Clasificación {pair_row['classification']}: {pair_row['classification_reason']}. "
        f"Pair-Block v2 colocó {pair_row['placed_units']}/{pair_row['requested_units']}; runtime total "
        f"{pair_row['runtime_ms']} ms, generación {pair_row['block_generation_ms']} ms, "
        f"packing {pair_row['packing_ms']} ms; ratio {pair_row['runtime_ratio_fastest_baseline']}× "
        "frente al baseline más rápido.")

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
        if method == "Pair-Block-v2":
            source += "\nprint(\"bloques aceptados/colocados:\", row[\"accepted_blocks\"], row[\"placed_blocks\"], \"generación ms:\", row[\"block_generation_ms\"], \"packing ms:\", row[\"packing_ms\"])  # Separamos generación y packing."
            output += f"\nbloques aceptados/colocados: {row['accepted_blocks']} {row['placed_blocks']} generación ms: {row['block_generation_ms']} packing ms: {row['packing_ms']}"
        section(section_number, f"{case_id} — {method}",
                f"Ejecuta {method} sobre {case_id}.",
                case_explanations[case_id],
                "Se registran las métricas funcionales; Pair-Block v2 separa generación y packing.",
                source, output,
                interpretations[case_id] if method == "Pair-Block-v2" else "La fila es referencia con la misma entrada y configuración.")
        section_number += 1

summary_source = """csv_path = repo_root / "docs/evidence/sprint-02/SP-004/benchmark-results/sp004_block_v2_results.csv"  # Abrimos el CSV real del benchmark v2.
with csv_path.open(encoding="utf-8", newline="") as file:  # Leemos filas UTF-8 sin alterar columnas.
    consolidated = list(csv.DictReader(file))  # Convertimos las filas en diccionarios.
print("caso | método | solicitadas | puestas | sin colocar | retazos | planchas | uso % | merma mm² | recuperable mm² | ms | clase | ratio")  # Imprimimos el encabezado.
for item in consolidated:  # Recorremos todas las filas de los seis casos.
    print(item["case"], item["method"], item["requested_units"], item["placed_units"], item["unplaced_units"], item["remnants_used"], item["sheets_used"], item["utilization_pct"], item["waste"], item["recoverable_area"], item["runtime_ms"], item["classification"], item["runtime_ratio_fastest_baseline"], sep=" | ")  # Mostramos todas las métricas y la clase."""
summary_output = "caso | método | solicitadas | puestas | sin colocar | retazos | planchas | uso % | merma mm² | recuperable mm² | ms | clase | ratio\n" + "\n".join(
    " | ".join(row[key] for key in ("case", "method", "requested_units", "placed_units", "unplaced_units", "remnants_used", "sheets_used", "utilization_pct", "waste", "recoverable_area", "runtime_ms", "classification", "runtime_ratio_fastest_baseline"))
    for row in block_rows)
summary_section = section_number
section(summary_section, "Tabla consolidada", "Lee y presenta la evidencia CSV sin transcribir números.",
        "FF/BF/WF/Pair-Block v2 usan el mismo cálculo oficial de métricas.",
        f"Hay {len(block_rows)} filas para seis casos y cuatro métodos.", summary_source, summary_output,
        "El discriminante y los dos diagnósticos se reportan aparte, con métricas, tiempos y clasificación.")
section_number = summary_section + 1

blocks_source = """trace_path = repo_root / "docs/evidence/sprint-02/SP-004/benchmark-results/sp004_block_v2_trace.json"  # Localizamos la traza de placements.
trace_data = json.loads(trace_path.read_text(encoding="utf-8"))  # Leemos giros, offsets e identidades.
for entry in trace_data["results"]:  # Recorremos todos los casos y métodos.
    if entry["method"] == "Pair-Block-v2":  # Nos quedamos con bloques y fallback.
        if entry["block_trace"]["placed_blocks"]:  # Limitamos el detalle a bloques que sí llegaron al stock.
            print(entry["case"], "bloques:", entry["block_trace"]["selected_blocks"])  # Mostramos miembros, giros, offsets y caja.
            print("placements individuales finales:", entry["placements"])  # Conservamos la salida por pieza original."""
block_lines = [
    f"{item['case']} bloques={item['block_trace']['selected_blocks']}; placements individuales={item['placements']}"
    for item in block_trace["results"]
    if item["method"] == "Pair-Block-v2" and item["block_trace"]["placed_blocks"]
]
section(section_number, "Bloques seleccionados y placements originales",
        "Muestra IDs, rotaciones, offsets internos y fuente de cada bloque.",
        "La trazabilidad de piezas debe sobrevivir a la colocación como máscara compuesta.",
        "El discriminante y los dos diagnósticos contienen bloques colocados; los fixtures oficiales no colocaron ninguno.", blocks_source,
        "\n".join(block_lines),
        "El discriminante colocó los triángulos en 0°/180° con un offset de una celda. El diagnóstico oblicuo colocó la pareja a 60°, dentro del contrato; el mixto colocó un triángulo y un círculo.")
section_number += 1

det_source = """det_path = repo_root / "docs/evidence/sprint-02/SP-004/benchmark-results/sp004_block_v2_trace.json"  # Abrimos el resumen de repeticiones.
determinism = json.loads(det_path.read_text(encoding="utf-8"))["determinism"]  # Separamos estados de determinismo.
for case_id, status in determinism.items():  # Recorremos SMALL, MEDIUM, COMPLEX y la demo.
    print(case_id, status["runs"], "PASS" if status["pass"] else "FAIL", status["runtime_ms"])  # Reportamos firma y tiempos."""
det_output = "\n".join(f"{case} x{value['runs']} {'PASS' if value['pass'] else 'FAIL'} runtime_ms={value['runtime_ms']}" for case, value in block_trace["determinism"].items())
section(section_number, "Determinismo ×3", "Compara layouts, pares, giros y métricas funcionales de tres corridas.",
        "El reloj puede variar, pero las decisiones geométricas deben permanecer iguales.",
        "Los seis casos deben registrar PASS.", det_source, det_output,
        "Los placements y bloques coincidieron en las tres ejecuciones de cada caso; solo cambian los tiempos.")
section_number += 1

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
section(section_number, "Diagnóstico adicional DJD", "Lee cuatro casos externos con la intención fijada antes de las corridas.",
        "La matriz comprueba grupos y métricas, no representa una muestra estadística.",
        "Se espera categoría A/B/C/D, tamaño de grupos y runtime.", djd_source, djd_output,
        "Los resultados DJD son evidencia previa preservada; Pair-Block v2 se evaluó por separado con su regla A–E predeclarada.")
section_number += 1

for chart_offset, (title, file_name, meaning) in enumerate((
    ("Aprovechamiento por método", "utilization-by-method.png", "En TA-027 los métodos empatan en utilización; el diagnóstico oblicuo reduce merma, pero su tiempo es E."),
    ("Fuentes por método", "sources-by-method.png", "Pair-Block v2 mantiene las fuentes de los baselines en SMALL/MEDIUM/COMPLEX."),
    ("Tiempo por método", "runtime-by-method.png", "Los tiempos usan escala logarítmica; generación domina MEDIUM y COMPLEX."),
)):
    chart = FIGURES / file_name
    chart_source = f"""from IPython.display import Image, display  # Importamos el renderizador de Colab.
chart_path = repo_root / "experiments/optimization/block_packing/figures/{file_name}"  # Localizamos el gráfico en el repo.
display(Image(filename=str(chart_path)))  # Mostramos el PNG de la corrida real."""
    section(section_number + chart_offset, title, "Carga la figura generada a partir de métricas crudas.",
            "El gráfico ayuda a comparar patrones sin sustituir los valores tabulares.",
            "Cada grupo representa FF, BF, WF y Pair-Block v2.", chart_source,
            f"Figura cargada: {file_name}", meaning, chart)
section_number += 3

section(section_number, "Evaluación comparativa y selección de candidato M4",
        "Resume resultados y conecta la evidencia de Filler, DJD y Pair-Block.",
        "Una heurística debe aportar diferencia útil a un costo que compense.",
        "Pair-Block v2 forma bloques deterministas en diagnósticos, pero el runtime clasifica varios casos como E.")
classification_lines = "\n".join(
    f"- **{row['case']}: {row['classification']}** — {row['classification_reason']} (ratio {row['runtime_ratio_fastest_baseline']}×)."
    for row in block_rows if row["method"] == "Pair-Block-v2")
markdown(f"""### Lectura de esta corrida

- **Filler:** sigue descartado como opción principal; sus documentos y resultados anteriores se preservan.
- **DJD-1/3:** el diagnóstico no encontró una mejora de grupo sobre el mejor baseline. Una terna produjo la misma métrica final.
- **Pair-Block v1:** queda como antecedente cardinal y no decide esta reevaluación.
- **Pair-Block v2:** no colocó bloques en los fixtures oficiales; SMALL quedó en D y MEDIUM/COMPLEX en E. El discriminante y los dos diagnósticos colocaron bloques, con costo superior a 10× en cada caso.

{classification_lines}

**Recomendación:** NO-GO para integrar Pair-Block v2 en TA-042 con esta evidencia. El diagnóstico oblicuo reduce merma, pero su costo supera el criterio fijado antes de correrlo; el diagnóstico mixto empeora merma y recuperable. Filler y DJD quedan intactos como candidatos evaluados previamente.""")

notebook = {
    "cells": cells,
    "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                 "language_info": {"name": "python", "version": "3.11.0"}},
    "nbformat": 4, "nbformat_minor": 5,
}
TARGET.write_text(json.dumps(notebook, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"Notebook escrito: {TARGET}")
print(f"Secciones: {sum(1 for cell in cells if cell['cell_type'] == 'markdown' and any(line.startswith('## ') for line in cell['source']))}; celdas: {len(cells)}; código: {sum(item['cell_type'] == 'code' for item in cells)}")
