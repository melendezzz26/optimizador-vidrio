"""Construye y ejecuta SP004-DJD.ipynb en orden con salidas locales reales."""
import contextlib
import io
import json
import os
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TARGET = Path(__file__).resolve().parent / "SP004-DJD.ipynb"
cells = []


def markdown(source):
    """Añade una celda Markdown preservando saltos de línea."""
    cells.append({"cell_type": "markdown", "metadata": {}, "source": source.splitlines(True)})


def section(number, title, what, why, observe, source=None, interpretation=None):
    """Añade explicación previa, código comentado opcional e interpretación."""
    markdown(f"## Celda {number}. {title}\n\n### Qué hace esta celda\n\n{what}\n\n### Por qué la necesitamos\n\n{why}\n\n### Qué deberíamos observar\n\n{observe}")
    if source is not None:
        cells.append({"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": source.splitlines(True)})
        if interpretation:
            markdown(f"### Interpretación de la salida\n\n{interpretation}")


section(1,"SP-004 — DJD-1/3", "Presenta el objetivo del Spike y el candidato M4 que se investigará.", "El notebook debe dejar claro desde la primera celda que DJD es experimental.", "FF, BF y WF se conservan como baselines; no se integra DJD en producción.")
section(2,"Filler descartado como candidato principal", "Resume por qué FL queda como evidencia histórica y no como candidato principal.", "La auditoría observó que FF de NewGlass ya ordena por área y ambos coincidieron en los fixtures.", "En SMALL, MEDIUM y COMPLEX, Filler y FF coincidieron en cobertura, número de fuentes y aprovechamiento. La búsqueda Filler sí tuvo trazas y costo propios, pero no mostró una dimensión de selección suficiente para ser el candidato principal de M4. Se conservan su informe, notebook y resultados bajo nombres de candidato descartado.")
section(3,"Qué es Djang and Finch", "Resume el DJD 1D y la adaptación académica a irregular 2D.", "Separar ambos dominios evita aplicar capacidad lineal como si fuera geometría.", "En 2D, DJD selecciona grupos y otra rutina debe validar el placement.")
section(4,"Diferencia frente a FF/BF/WF", "Explica que los baselines puntúan una pieza actual y DJD puede proponer 1, 2 o 3 unidades juntas.", "La diferencia de política debe analizarse en decisiones y no solo en métricas finales.", "Una secuencia de dos piezas elegida como grupo distinguiría decisiones aunque placements finales coincidieran.")
section(5,"Definición DJD-1/3 y tolerancia", "Describe el umbral inicial y `w` basado en la publicación.", "El incremento de desperdicio no debe ser un número arbitrario.", "La fuente académica recomienda empíricamente un incremento de 1/20 del área nominal total del objeto; NewGlass usa el mismo denominador y valida cabida con el raster.")

section(6,"Preparación del entorno", "Configura imports del repo, métodos y casos.", "El loader TA-027 necesita los paquetes de backend y los JSON versionados.", "Se muestra la raíz y se confirma ejecución secuencial.", """from pathlib import Path  # Importamos Path para resolver rutas tanto en local como en Colab.
import sys  # Importamos sys para agregar el backend al path de imports.
import json  # Importamos JSON para leer la instancia discriminante.
from decimal import Decimal  # Usamos Decimal en límites y áreas de configuración.
repo_root = Path.cwd()  # Tomamos el directorio actual como raíz candidata.
if not (repo_root / "experiments/optimization/loader.py").exists():  # Comprobamos que la carpeta actual contenga los fixtures.
    repo_root = Path("/content/NewGlass")  # Usamos la ubicación sugerida para clonar el repositorio en Colab.
if not (repo_root / "experiments/optimization/loader.py").exists():  # Detenemos con instrucción legible si falta el repo.
    raise RuntimeError("Clona NewGlass en /content/NewGlass o ejecuta desde la raíz del repositorio.")  # Explicamos cómo preparar Colab.
sys.path.insert(0, str(repo_root / "backend"))  # Habilitamos los imports app del motor actual.
sys.path.insert(0, str(repo_root))  # Habilitamos imports del loader y del experimento.
from experiments.optimization.loader import CASES, load_problem, read_case  # Reutilizamos la lista y loader TA-027.
from experiments.optimization.djd import DJDExperimental  # Importamos la política aislada DJD.
from experiments.optimization.djd.run_benchmark import DISCRIMINANT, METHODS, load_experimental_case, run_one  # Reutilizamos el ejecutor secuencial.
print("Repositorio:", repo_root)  # Confirmamos la raíz que usa el notebook.
print("Métodos:", [name for name, _ in METHODS], "| multiprocessing: no")  # Confirmamos métodos y modo de recursos.""", "El notebook usa una copia del repositorio y no necesita acceso a base de datos; métodos ejecutan uno por uno.")

section(7,"Validación de fixtures", "Lee SMALL, MEDIUM, COMPLEX y el caso didáctico separado.", "La instancia adicional no debe confundirse con TA-027.", "Los conteos se obtienen de los JSON sin modificarlos.", """fixture_data = {}  # Creamos un resumen de entradas para las celdas siguientes.
for case_id in CASES:  # Recorremos los tres fixtures oficiales en su orden estable.
    data = read_case(case_id)  # Leemos una copia del JSON oficial.
    fixture_data[case_id] = data  # Guardamos datos sin escribirlos al archivo.
    print(case_id, "filas de piezas:", len(data["pieces"]), "fuentes:", len(data["stock"]), "config:", data["config"])  # Mostramos los parámetros originales.
discriminant_path = repo_root / "experiments/optimization/djd/cases/DJD-DISCRIMINANT-001.json"  # Localizamos el caso no oficial.
discriminant_data = json.loads(discriminant_path.read_text(encoding="utf-8"))  # Leemos su etiqueta y configuración.
print(discriminant_data["label"], "filas:", len(discriminant_data["pieces"]))  # Separamos explícitamente el caso didáctico.""", "Los tres fixtures oficiales continúan intactos; el JSON discriminante está en el directorio de DJD.")

section(8,"EXP-SMALL-001", "Explica el tamaño del caso SMALL y carga sus snapshots.", "Un caso homogéneo comprueba el recorrido básico con poco costo.", "Se muestran unidades expandidas y grupo material-espesor.", """small_data, small_problem = load_experimental_case("EXP-SMALL-001")  # Reutilizamos la entrada oficial y la construcción de snapshots.
print("unidades expandidas:", len(small_problem.units))  # Contamos las unidades físicas solicitadas.
print("grupos material-espesor:", len(small_problem.groups))  # Confirmamos separación por compatibilidad.""", "SMALL tiene tres unidades de una geometría y fuentes retazo/plancha del mismo material.")
section(9,"EXP-MEDIUM-001", "Explica la heterogeneidad del caso MEDIUM.", "Las combinaciones pequeñas pueden elegir unidades de tamaños diferentes.", "Se informa cantidad expandida y stock compatible.", """medium_data, medium_problem = load_experimental_case("EXP-MEDIUM-001")  # Creamos snapshots nuevos de MEDIUM.
print("unidades expandidas:", len(medium_problem.units))  # Contamos piezas individuales después de expandir cantidades.
print("fuentes físicas:", sum(len(group.stock_candidates) for group in medium_problem.groups))  # Contamos fuentes compatibles.""", "MEDIUM contiene nueve unidades; el loader mantiene material y espesor como clave de agrupación.")
section(10,"EXP-COMPLEX-001", "Carga COMPLEX y resume su número de grupos y fuentes.", "Este caso prueba DJD con varios grupos independientes.", "Se evita combinar unidades incompatibles a través de grupos.", """complex_data, complex_problem = load_experimental_case("EXP-COMPLEX-001")  # Reconstruimos COMPLEX con el loader congelado.
print("unidades expandidas:", len(complex_problem.units))  # Informamos la carga del pedido.
print("grupos material-espesor:", len(complex_problem.groups))  # Contamos grupos compatibles.
print("fuentes físicas:", sum(len(group.stock_candidates) for group in complex_problem.groups))  # Informamos unidades de inventario.""", "COMPLEX tiene 24 unidades y cinco grupos de compatibilidad; DJD reinicia su fuente activa dentro de cada grupo.")

section(11,"Orden de piezas", "Muestra el orden del JSON y el orden estable por área que usará DJD.", "Las permutaciones dentro de cada grupo parten de un orden reproducible.", "El desempate se basa en ID e índice de unidad.", """before = [(row["id_pieza"], row["cantidad"]) for row in medium_data["pieces"]]  # Registramos el orden de filas original.
ordered_units = sorted(medium_problem.units, key=lambda unit: (-unit.area_mm2, unit.piece_id, unit.unit_index, unit.order_id))  # Aplicamos orden decreciente de área con IDs estables.
print("ANTES:", before)  # Mostramos el JSON como fue entregado.
print("DJD:", [(u.piece_id, u.unit_index, str(u.area_mm2)) for u in ordered_units])  # Mostramos unidades expandidas y áreas.""", "La selección combinatoria es determinista; los desempates estables evitan depender del orden del diccionario.")

section(12,"Llenado inicial hasta 1/3", "Corre DJD en el caso discriminante y muestra el ratio inicial de cada fuente.", "El umbral inicial controla cuándo empieza la búsqueda de grupos.", "La primera pieza del ejemplo cubre 40% de la plancha antes de evaluar el par.", """disc_row, disc_detail = run_one(DISCRIMINANT, "DJD-1/3", DJDExperimental)  # Ejecutamos el caso pequeño desde el benchmark real.
disc_trace = disc_detail["djd_trace"]  # Extraemos los diagnósticos producidos por DJD.
for ratio in disc_trace["initial_fill_ratio"]:  # Recorremos las fuentes realmente activadas.
    print(ratio)  # Mostramos capacidad nominal y ocupación del llenado largest-first.""", "La fuente inicia la búsqueda combinatoria tras superar el tercio; el ratio usa el área nominal total y el placement sigue validando el layout raster.")

section(13,"Combinaciones de una pieza", "Cuenta subconjuntos candidatos de tamaño 1 en la salida DJD.", "Los singles siguen siendo la primera opción en cada ronda de selección.", "Se observan candidatos visitados y podados antes del placement.", """print("subconjuntos tamaño 1:", disc_trace["combinations_size_1"])  # Leemos los singles visitados en el caso didáctico.
print("podas de tamaño 1:", disc_trace["pruned_by_size"][1])  # Mostramos los singles excluidos por capacidad o tolerancia.""", "Los singles que no dejan residuo dentro de w se descartan antes de pedir una búsqueda geométrica.")
section(14,"Combinaciones de dos piezas", "Muestra el par finalmente seleccionado y el total de pares visitados.", "DJD puede tomar una decisión conjunta cuando singles no satisfacen el residuo permitido.", "En la demo la pareja B+C deja un residuo estimado de 5 mm².", """print("subconjuntos tamaño 2:", disc_trace["combinations_size_2"])  # Mostramos los pares no ordenados visitados.
for group in disc_trace["selected_groups"]:  # Recorremos los grupos realmente aceptados.
    if group["size"] == 2:  # Aislamos la decisión emparejada.
        print(group)  # Mostramos IDs, tolerancia y residuo estimado.""", "El grupo de dos piezas es una decisión registrada por el algoritmo, no un resultado inventado a partir de la demo.")
section(15,"Combinaciones de tres piezas", "Informa las ternas visitadas en la demo y en los casos oficiales.", "El grupo máximo tres preserva el DJD 1D original y la adaptación 2D.", "Los casos pueden no alcanzar una terna seleccionable.", """print("demo, ternas generadas:", disc_trace["combinations_size_3"])  # Leemos la cuenta de ternas del caso discriminante.
for case_id in CASES:  # Revisamos el contador de cada fixture oficial.
    row, detail = run_one(case_id, "DJD-1/3", DJDExperimental)  # Ejecutamos cada caso por separado.
    print(case_id, "ternas:", detail["djd_trace"]["combinations_size_3"])  # Informamos el contador real.
    del row, detail  # Liberamos detalles antes de cargar la siguiente instancia.""", "El número de ternas depende del stock y de los candidatos que sobreviven a la poda; no se fuerza una selección de tamaño tres.")

section(16,"Tolerancia w", "Calcula el incremento publicado y muestra el paso real de la demo.", "Una regla rastreable permite explicar por qué se relaja el residuo.", "El incremento es área nominal inicial / 20; la demo necesitó un paso.", """from fractions import Fraction  # Importamos Fraction para mostrar exactamente 1/20.
waste_fraction = Fraction(1, 20)  # Fijamos el incremento relativo recomendado en la adaptación 2D.
capacity = Decimal(disc_trace["initial_fill_ratio"][0]["initial_capacity_mm2"])  # Leemos la capacidad usada por la fuente de la demo.
print("fracción incremental:", waste_fraction)  # Mostramos el parámetro exacto y visible.
print("incremento mm²:", capacity * Decimal(waste_fraction.numerator) / Decimal(waste_fraction.denominator))  # Calculamos el valor según el área nominal total.
print("pasos usados:", disc_trace["waste_tolerance_steps"])  # Reportamos el número real de relajaciones.""", "En la fuente de 100 mm² el paso es 5 mm²; la búsqueda necesitó un incremento para aceptar B+C.")

section(17,"Validación geométrica", "Muestra cuántas secuencias se validaron y cuáles fueron físicamente factibles.", "El área solo poda; máscaras y layouts determinan la cabida real.", "Las piezas del par se comprobaron secuencialmente en el raster productivo.", """print("secuencias con chequeo geométrico:", disc_trace["geometric_sequence_checks"])  # Contamos órdenes que llegan a geometría.
print("chequeos pieza-layout:", disc_trace["geometric_checks"])  # Contamos pruebas individuales de placement.
print("secuencias factibles:", disc_trace["feasible_combinations"])  # Contamos grupos completos aceptables geométricamente.
print("secuencias fallidas reutilizadas:", disc_trace["cached_sequences_skipped"])  # Mostramos poda por fallos ya conocidos en el mismo layout.""", "Una secuencia solo se conserva si cada pieza entra en un layout temporal que incluye las anteriores del grupo.")

section(18,"DEMO DIDÁCTICA — NO PERTENECE AL BENCHMARK OFICIAL", "Enumera ejemplos de grupos que DJD evalúa con piezas B, C, D y E.", "La notación ayuda a ver la diferencia con una selección pieza por pieza.", "Se muestran conjuntos candidatos, sin fabricar indicadores de rendimiento.", """demo_candidates = [("B",), ("B", "C"), ("B", "D"), ("C", "D"), ("B", "D", "E")]  # Enumeramos grupos de ejemplo con distintos tamaños.
for group in demo_candidates:  # Recorremos los ejemplos didácticos en orden explícito.
    print(" + ".join(group))  # Mostramos piezas que podrían validarse como secuencia.""", "La lista solo explica la unidad de decisión; la factibilidad benchmark se obtiene de NewGlass y no de esta enumeración didáctica.")

section(19,"DJD SMALL", "Ejecuta la variante DJD-1/3 sobre SMALL.", "El caso pequeño comprueba las reglas y puede coincidir con FF.", "Se reportan cobertura y selección de grupos.", """small_djd_row, small_djd_detail = run_one("EXP-SMALL-001", "DJD-1/3", DJDExperimental)  # Corremos DJD con métricas oficiales.
small_djd_trace = small_djd_detail["djd_trace"]  # Guardamos la traza diagnóstica.
print("cobertura:", small_djd_row["placed_units"], "/", small_djd_row["requested_units"])  # Mostramos unidades colocadas.
print("grupos seleccionados:", small_djd_trace["selected_combination_sizes"])  # Mostramos fase inicial y combinaciones posteriores.""", "SMALL completa sus tres unidades con una fuente de cada tipo; el llenado inicial consume el retazo y los singles siguientes completan el pedido.")

section(20,"FF/BF/WF SMALL", "Ejecuta los tres baselines en orden secuencial con entradas nuevas.", "La corrida independiente evita reutilizar layouts entre métodos.", "Cada método termina antes del siguiente.", """small_baselines = []  # Creamos una lista corta para guardar los tres resultados medidos.
for method_name, optimizer_class in METHODS[:3]:  # Recorremos FF, BF y WF en ese orden.
    row, detail = run_one("EXP-SMALL-001", method_name, optimizer_class)  # Ejecutamos un baseline sobre snapshots nuevos.
    small_baselines.append(row)  # Guardamos métricas comparables y duración.
    print(method_name, row["placed_units"], "/", row["requested_units"], "utilización", row["utilization_pct"])  # Mostramos la salida observada.
    del detail  # Liberamos la traza de placements antes del próximo método.""", "Los tres baselines también colocan las tres unidades; la comparación se completa con el conteo de fuentes y merma.")
section(21,"Comparación SMALL", "Compara métricas de FF/BF/WF y DJD para SMALL.", "El caso homogéneo sirve para validar, aunque no separe heurísticas.", "Se muestran las métricas oficiales de cada método.", """small_comparison = small_baselines + [small_djd_row]  # Unimos baselines y DJD en la misma tabla.
for row in small_comparison:  # Recorremos cada observación del fixture.
    print(row["method"], row["placed_units"], row["remnants_used"], row["sheets_used"], row["utilization_pct"], row["waste"], row["runtime_ms"])  # Imprimimos columnas comparables.""", "SMALL puede coincidir porque es homogéneo; esto no invalida los diagnósticos de DJD.")

section(22,"DJD MEDIUM", "Ejecuta DJD-1/3 sobre MEDIUM y expone diagnósticos.", "MEDIUM permite observar el costo de los candidatos 1/2/3.", "Se muestran métricas y conteos por tamaño.", """medium_djd_row, medium_djd_detail = run_one("EXP-MEDIUM-001", "DJD-1/3", DJDExperimental)  # Medimos DJD en el caso medio.
medium_djd_trace = medium_djd_detail["djd_trace"]  # Extraemos contadores de combinaciones.
print("cobertura:", medium_djd_row["placed_units"], "/", medium_djd_row["requested_units"])  # Reportamos colocación.
print("grupos seleccionados:", medium_djd_trace["selected_combination_sizes"])  # Exponemos tamaños elegidos.
print("podas/geometría:", medium_djd_trace["combinations_pruned"], medium_djd_trace["geometric_checks"])  # Contrastamos costo y poda.""", "DJD completa MEDIUM; las combinaciones generadas y podadas explican el costo más allá del runtime.")
section(23,"FF/BF/WF MEDIUM", "Ejecuta FF, BF y WF en secuencia para MEDIUM.", "Las entradas independientes mantienen comparabilidad.", "Se imprime cobertura, fuentes y aprovechamiento.", """medium_baselines = []  # Inicializamos resultados resumidos de MEDIUM.
for method_name, optimizer_class in METHODS[:3]:  # Conservamos orden serial FF, BF y WF.
    row, detail = run_one("EXP-MEDIUM-001", method_name, optimizer_class)  # Ejecutamos el baseline una sola vez.
    medium_baselines.append(row)  # Guardamos métricas y tiempo.
    print(method_name, row["placed_units"], row["remnants_used"], row["sheets_used"], row["utilization_pct"])  # Informamos la salida.
    del detail  # Liberamos placements serializados.""", "Los baselines se ejecutan después de DJD y comienzan desde problemas recién cargados.")
section(24,"Comparación MEDIUM", "Muestra FF/BF/WF/DJD en las métricas oficiales.", "La lectura incluye fuentes y merma además del aprovechamiento.", "Los datos pueden coincidir aunque las decisiones combinatorias no.", """medium_comparison = medium_baselines + [medium_djd_row]  # Unimos cuatro filas para MEDIUM.
for row in medium_comparison:  # Recorremos los resultados medidos.
    print(row["method"], row["placed_units"], row["remnants_used"], row["sheets_used"], row["utilization_pct"], row["waste"], row["runtime_ms"])  # Mostramos métricas oficiales.""", "La coincidencia o diferencia se informa desde las métricas reales; no se espera que DJD gane por definición.")

section(25,"DJD COMPLEX", "Ejecuta DJD-1/3 sobre los grupos diversos de COMPLEX.", "Este caso permite ver si las permutaciones elevan el costo.", "Se reportan placements, poda y validaciones.", """complex_djd_row, complex_djd_detail = run_one("EXP-COMPLEX-001", "DJD-1/3", DJDExperimental)  # Ejecutamos el caso complejo.
complex_djd_trace = complex_djd_detail["djd_trace"]  # Guardamos la traza experimental.
print("cobertura:", complex_djd_row["placed_units"], "/", complex_djd_row["requested_units"])  # Informamos unidades colocadas.
print("generadas:", [complex_djd_trace[f"combinations_size_{size}"] for size in (1, 2, 3)])  # Mostramos conteos de subconjuntos.
print("podadas/geometría:", complex_djd_trace["combinations_pruned"], complex_djd_trace["geometric_checks"])  # Mostramos trabajo evitado y ejecutado.""", "La traza identifica qué porción del trabajo de DJD terminó en geometría costosa.")
section(26,"FF/BF/WF COMPLEX", "Corre FF, BF y WF de forma secuencial en COMPLEX.", "El fixture mayor puede costar más; no se ejecutan métodos simultáneamente.", "Cada resultado se conserva antes de recolectar referencias.", """complex_baselines = []  # Guardamos solo filas métricas compactas.
for method_name, optimizer_class in METHODS[:3]:  # Mantenemos el orden de control FF, BF y WF.
    row, detail = run_one("EXP-COMPLEX-001", method_name, optimizer_class)  # Cargamos y ejecutamos una entrada nueva.
    complex_baselines.append(row)  # Retenemos métricas y tiempo.
    print(method_name, row["placed_units"], row["sheets_used"], row["utilization_pct"])  # Informamos cobertura y planchas.
    del detail  # Soltamos la serialización detallada para limitar memoria.""", "Todos los baselines terminan antes de pasar a la comparación final.")
section(27,"Comparación COMPLEX", "Compara los cuatro métodos en el caso complejo.", "Las fuentes consumidas y decisiones importan además de utilización.", "La salida contiene todas las métricas oficiales.", """complex_comparison = complex_baselines + [complex_djd_row]  # Juntamos FF, BF, WF y DJD.
for row in complex_comparison:  # Leemos las cuatro observaciones.
    print(row["method"], row["placed_units"], row["remnants_used"], row["sheets_used"], row["utilization_pct"], row["waste"], row["runtime_ms"])  # Mostramos datos reales.""", "La diferencia se evalúa con placements y trazas además de las métricas agregadas.")

section(28,"Determinismo SMALL ×3", "Repite la firma de DJD para SMALL.", "Se compara el algoritmo sin incluir tiempo de ejecución variable.", "Las tres firmas deben coincidir.", """def djd_signature(case_id):  # Definimos una firma estable de placements y decisiones.
    row, detail = run_one(case_id, "DJD-1/3", DJDExperimental)  # Ejecutamos DJD sobre snapshots nuevos.
    trace = detail["djd_trace"]  # Extraemos los diagnósticos deterministas.
    placements = tuple((item["piece_id"], item["unit_index"], item["source"], item["material_id"], item["x_mm"], item["y_mm"], item["rotation_deg"]) for item in detail["placements"])  # Normalizamos placements.
    decision = (tuple(trace["selected_combination_sizes"]), tuple(tuple(group["unit_ids"]) for group in trace["selected_groups"] if "unit_ids" in group), trace["source_switches"])  # Excluimos duraciones.
    return placements, decision  # Devolvemos solo decisiones repetibles.
small_signatures = [djd_signature("EXP-SMALL-001") for _ in range(3)]  # Hacemos tres corridas independientes.
print("PASS" if small_signatures[0] == small_signatures[1] == small_signatures[2] else "FAIL")  # Comparamos las tres salidas.""", "La verificación cubre placements, rotaciones, grupos elegidos y cambios de fuente.")
section(29,"Determinismo MEDIUM ×3", "Repite la firma para MEDIUM.", "El caso medio contiene alternativas de selección adicionales.", "Se informa el resultado de la comparación de firmas.", """medium_signatures = [djd_signature("EXP-MEDIUM-001") for _ in range(3)]  # Repetimos MEDIUM en ejecuciones independientes.
print("PASS" if medium_signatures[0] == medium_signatures[1] == medium_signatures[2] else "FAIL")  # Confirmamos orden, grupos y placements.""", "El runtime puede variar y queda fuera de la firma de determinismo.")
section(30,"Determinismo COMPLEX ×3", "Repite la firma para COMPLEX.", "La carga mayor prueba la estabilidad entre grupos.", "Se espera identidad de decisiones sin depender del reloj.", """complex_signatures = [djd_signature("EXP-COMPLEX-001") for _ in range(3)]  # Repetimos la instancia compleja tres veces.
print("PASS" if complex_signatures[0] == complex_signatures[1] == complex_signatures[2] else "FAIL")  # Validamos igualdad estructural.""", "PASS significa que las tres corridas generaron las mismas decisiones.")

section(31,"Tabla consolidada", "Carga el CSV versionado de DJD y muestra métricas oficiales y diagnósticos.", "El archivo crudo es la fuente trazable de resultados.", "Hay cuatro métodos en cada fixture y cuatro métodos en la demo separada.", """import csv  # Importamos csv para leer los 16 resultados guardados.
csv_path = repo_root / "docs/evidence/sprint-02/SP-004/benchmark-results/sp004_djd_results.csv"  # Construimos la ruta del benchmark.
with csv_path.open(encoding="utf-8", newline="") as stream:  # Abrimos el CSV sin alterar sus filas.
    consolidated = list(csv.DictReader(stream))  # Convertimos el archivo en filas con nombre.
for row in consolidated:  # Recorremos TA-027 y el caso didáctico por separado.
    print(row["case"], row["method"], row["requested_units"], row["placed_units"], row["remnants_used"], row["sheets_used"], row["utilization_pct"], row["waste"], row["runtime_ms"])  # Mostramos métricas oficiales.""", "Las cuatro filas del caso discriminante se identifican por su case ID y no se agregan a TA-027.")
section(32,"Número de combinaciones", "Resume subconjuntos generados, podas y secuencias geométricas DJD.", "El costo de búsqueda no se entiende observando solo el runtime.", "Se separan grupos sin orden, secuencias ordenadas y chequeos por pieza.", """for case_id in (*CASES, DISCRIMINANT):  # Recorremos fixtures oficiales y caso adicional.
    row = next(item for item in consolidated if item["case"] == case_id and item["method"] == "DJD-1/3")  # Seleccionamos la fila DJD.
    print(case_id, "grupos 1/2/3:", row["combinations_size_1"], row["combinations_size_2"], row["combinations_size_3"], "podados:", row["combinations_pruned"], "secuencias geométricas:", row["geometric_sequence_checks"], "checks pieza:", row["geometric_checks"], "factibles:", row["feasible_combinations"])  # Mostramos contadores.""", "Los contadores se acumulan por los pasos de tolerancia; las permutaciones se contabilizan como secuencias geométricas.")

section(33,"Aprovechamiento", "Genera un gráfico SVG monocromo de aprovechamiento oficial para TA-027.", "El gráfico permite comparar métodos en los tres casos originales.", "El caso discriminante queda excluido de la comparación oficial.", """def svg_bars(rows, metric, title):  # Define un gráfico vectorial sencillo sin dependencias de plotting.
    cases = list(CASES)  # Fijamos únicamente los IDs oficiales de TA-027.
    methods = ["FF", "BF", "WF", "DJD-1/3"]  # Definimos orden de métodos.
    shades = ["#222222", "#666666", "#999999", "#cccccc"]  # Usamos fondo blanco y escala de grises.
    width, height = 900, 410  # Seleccionamos un tamaño de lectura para Colab.
    maximum = max(float(row[metric]) for row in rows if row["case"] in cases) or 1  # Calculamos una escala global de los fixtures.
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">', '<rect width="100%" height="100%" fill="white"/>']  # Iniciamos un canvas blanco.
    parts.append(f'<text x="20" y="28" font-family="sans-serif" font-size="20">{title}</text>')  # Rotulamos el gráfico.
    for case_index, case in enumerate(cases):  # Recorremos cada caso oficial.
        for method_index, method in enumerate(methods):  # Recorremos los métodos en orden fijo.
            row = next(item for item in rows if item["case"] == case and item["method"] == method)  # Encontramos la métrica real.
            value = float(row[metric])  # Convertimos el campo CSV a número para escalarlo.
            bar_height = value * 270 / maximum  # Aplicamos una escala común para todas las barras.
            x = 90 + case_index * 265 + method_index * 45  # Ubicamos la barra dentro del grupo.
            parts.append(f'<rect x="{x}" y="{330-bar_height:.1f}" width="32" height="{bar_height:.1f}" fill="{shades[method_index]}"/>')  # Dibujamos la barra gris.
            parts.append(f'<text x="{x}" y="350" font-family="sans-serif" font-size="10">{method}</text>')  # Añadimos etiqueta de método.
        parts.append(f'<text x="90" y="380" font-family="sans-serif" font-size="13">{case.replace("EXP-", "").replace("-001", "")}</text>')  # Etiquetamos el fixture.
    parts.append('</svg>')  # Cerramos la imagen vectorial.
    return "".join(parts)  # Devolvemos la salida que guardará el notebook.
official_rows = [row for row in consolidated if row["case"] in CASES]  # Excluimos la demo del análisis TA-027.
utilization_chart = svg_bars(official_rows, "utilization_pct", "Aprovechamiento oficial (%)")  # Generamos comparación de utilización.
print(utilization_chart)  # El constructor guarda este texto como salida SVG renderizable.""", "El gráfico describe las métricas obtenidas y no predice resultados de otras órdenes.")

section(34,"Fuentes utilizadas", "Resume retazos y planchas consumidas en TA-027.", "El uso de fuentes es un indicador operativo aparte del aprovechamiento.", "Retazos y planchas se comparan con prioridad vigente preservada.", """for row in official_rows:  # Recorremos las métricas oficiales para detallar cada tipo de fuente.
    print(row["case"], row["method"], "retazos:", row["remnants_used"], "planchas:", row["sheets_used"])  # Reportamos inventario consumido.""", "Las fuentes utilizadas se reportan por tipo y caso; la política común conserva retazo antes que plancha.")
section(35,"Tiempo computacional", "Grafica el runtime local medido y muestra el número de pasos de tolerancia DJD.", "La combinatoria puede elevar el costo aun cuando la solución final coincida.", "Complejo contiene más candidatos y secuencias que SMALL.", """runtime_chart = svg_bars(official_rows, "runtime_ms", "Tiempo observado por ejecución (ms)")  # Generamos las barras de tiempo con escala compartida.
print(runtime_chart)  # Embebemos el gráfico como SVG.
for case_id in CASES:  # Recorremos solamente TA-027 para leer tolerancia.
    row = next(item for item in consolidated if item["case"] == case_id and item["method"] == "DJD-1/3")  # Seleccionamos DJD.
    print(case_id, "pasos de w:", row["waste_tolerance_steps"], "tiempo ms:", row["runtime_ms"])  # Informamos costo y relajaciones.""", "El tiempo depende de máquina y carga; combina con contadores de poda y geometría para interpretar el costo.")

section(36,"Observaciones experimentales", "Resume cobertura, diferencias de grupos, costo y límites observados.", "El objetivo es fundamentar GO/NO-GO sin buscar declarar un método ganador.", "El caso discriminante comprueba agrupación; los tres fixtures determinan el comportamiento comparativo.", """for case_id in (*CASES, DISCRIMINANT):  # Resumimos fixtures y el caso didáctico por separado.
    rows = [row for row in consolidated if row["case"] == case_id]  # Filtramos cuatro métodos.
    coverage = {row["placed_units"] for row in rows}  # Comprobamos si la cobertura cambia entre métodos.
    print(case_id, "cobertura igual:", len(coverage) == 1, "unidades: ", [row["placed_units"] for row in rows])  # Presentamos cobertura observada.
print("DJD seleccionó tamaños:", disc_trace["selected_combination_sizes"])  # Confirmamos que el ejemplo ejercita tamaño 2.
for case_id in ("EXP-MEDIUM-001", "EXP-COMPLEX-001"):  # Revisamos los casos donde DJD paga mayor costo.
    djd = next(row for row in consolidated if row["case"] == case_id and row["method"] == "DJD-1/3")  # Leemos DJD.
    ff = next(row for row in consolidated if row["case"] == case_id and row["method"] == "FF")  # Leemos FF de referencia.
    ratio = Decimal(djd["runtime_ms"]) / Decimal(ff["runtime_ms"])  # Calculamos el factor de runtime observado.
    print(case_id, "DJD/FF runtime:", round(ratio, 1), "x")  # Informamos el costo relativo medido.
print("Limitación: el caso discriminante es didáctico y no pertenece a TA-027.")  # Evitamos tratar la demo como un benchmark oficial.
print("La decisión GO/NO-GO se basa en comportamiento, reglas y costo de TA-027, no en una sola métrica.")  # Enmarcamos el criterio de viabilidad.""", "DJD toma decisiones de grupo distintas, pero en MEDIUM y COMPLEX no mejora las métricas finales y tarda considerablemente más que FF. El costo observado sostiene NO-GO para TA-042 con esta implementación.")


def main():
    """Ejecuta las celdas en orden y guarda resultados como notebook ejecutado."""
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT / "backend"))
    sys.path.insert(0, str(ROOT))
    namespace = {"__name__": "__main__"}
    execution_count = 0
    for cell in cells:
        if cell["cell_type"] != "code":
            continue
        execution_count += 1
        source = "".join(cell["source"])
        captured = io.StringIO()
        try:
            with contextlib.redirect_stdout(captured):
                exec(compile(source, f"SP004-DJD-cell-{execution_count}", "exec"), namespace)
        except Exception:
            captured.write(traceback.format_exc())
            raise
        output = captured.getvalue()
        if output.strip().startswith("<svg"):
            cell["outputs"] = [{"output_type": "display_data", "data": {"image/svg+xml": output.strip()}, "metadata": {}}]
        else:
            cell["outputs"] = [{"output_type": "stream", "name": "stdout", "text": output.splitlines(True)}] if output else []
        cell["execution_count"] = execution_count
        print(f"ejecutada celda Python {execution_count}")
    notebook = {
        "cells": cells,
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                     "language_info": {"name": "python", "version": sys.version.split()[0]},
                     "colab": {"name": "SP004-DJD.ipynb", "provenance": []}},
        "nbformat": 4, "nbformat_minor": 5,
    }
    TARGET.write_text(json.dumps(notebook, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"notebook ejecutado: {TARGET}; secciones=36; celdas_python={execution_count}")


if __name__ == "__main__":
    main()
