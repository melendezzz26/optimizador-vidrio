"""Genera el notebook local SP-004 con outputs del mini-spike ya ejecutado."""
import contextlib
import io
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "docs/evidence/sprint-02/SP-004/hole-filling"
FIGURES = Path("../hole_filling/figures")
TARGET = Path(__file__).resolve().parent / "SP004-Hole-Filling.ipynb"


def markdown_cell(source):
    return {"cell_type": "markdown", "metadata": {}, "source": source.splitlines(keepends=True)}


def code_cell(source, count, namespace=None):
    namespace = {} if namespace is None else namespace
    capture = io.StringIO()
    with contextlib.redirect_stdout(capture):
        exec(compile(source, f"notebook-cell-{count}", "exec"), namespace, namespace)
    output = capture.getvalue()
    return {
        "cell_type": "code",
        "execution_count": count,
        "metadata": {},
        "outputs": [{"name": "stdout", "output_type": "stream", "text": output.splitlines(keepends=True)}],
        "source": source.splitlines(keepends=True),
    }


def build_notebook():
    diagnostic = json.loads((EVIDENCE / "sp004_hole_filling_trace.json").read_text(encoding="utf-8"))
    detection = json.loads((EVIDENCE / "sp004_hole_filling_detection.json").read_text(encoding="utf-8"))
    official = json.loads((EVIDENCE / "sp004_hole_filling_official_trace.json").read_text(encoding="utf-8"))
    realistic = json.loads((EVIDENCE / "sp004_hf_realistic_trace.json").read_text(encoding="utf-8"))
    capability = json.loads((EVIDENCE / "sp004_hf_capability_trace.json").read_text(encoding="utf-8"))

    cells = [markdown_cell(f"""# SP-004 — Raster Hole Filling / Pocket Filling

**Resultado mini-spike:** {diagnostic['mini_spike_decision']}. **Recomendación TA-042 tras benchmark:** {official['decision_ta042']}. Todo el trabajo permanece local y aislado. Los cuatro diagnósticos llevan la etiqueta *DIAGNÓSTICO HOLE FILLING — NO PERTENECE A TA-027*; los archivos EXP-* son los fixtures experimentales existentes, leídos sin cambios.

## Método publicado y adaptación

Abeysooriya, Bennell y Martinez-Sykora (2018) describen hole filling para irregular bin packing con huecos cerrados representados como polígonos; usan Inner Fit Polygon (IFP) para hallar encajes y prueban los huecos antes del placement normal. Błażewicz et al. (1993) son antecedente de backfilling con búsqueda tabu, y Burke et al. (2006) resumen ese método y el reto de validar movimientos. Ninguna fuente presenta este detector como un algoritmo raster estándar.

**Adaptación experimental NewGlass:** `RasterMask` y `SheetLayout` existentes. Un hueco interno físico es un componente 4-conexo de celdas libres que no toca el exterior del material. Un pocket utilizable es un componente 4-conexo del mapa de anclajes legales para una pieza/orientación que no conecta con el borde del dominio de anclajes. Así, una abertura que no admite la pieza bajo margen/separación deja el pocket desconectado. El tamaño reportado es el número de anclajes posibles, no el área física de la cavidad. La posición elegida se valida con `SheetLayout.place()` y su `check()` existente.

La grilla usa orígenes enteros, conectividad 4-conexa y orientaciones del motor cada 5°. El mapa acelerado sigue la operación por bits de `first_position`; las pruebas comparan sus anclajes con `SheetLayout.check()` para todas las celdas de los diagnósticos. Los layouts son inmutables y se distinguen retazos de planchas mediante `MaterialSource`.

## Diferencia entre las reglas

| Regla | Pregunta que decide |
|---|---|
| FF | ¿Cuál es la primera posición/fuente viable para la pieza actual? |
| BF | ¿Qué fuente deja menos celdas libres después de colocar la pieza actual? |
| WF | ¿Qué fuente deja más celdas libres después de colocar la pieza actual? |
| BRF | ¿Qué calidad tiene el sobrante hipotético de una colocación? |
| Hole Filling | ¿Hay una pieza pendiente que cabe en una región que ya se creó? |

La política local ordena pockets por x mínima e y mínima, intenta la primera pieza/orientación factible y vuelve a FF cuando no encuentra pocket. No minimiza `largest_rectangle`, merma ni usa un score BRF.

## Casos congelados y mapas

Se fijaron dimensiones y geometrías antes de comparar: HF-001 círculo dentro de marco abierto; HF-002 cuatro triángulos; HF-003 polígono convexo, con margen 1 mm; HF-004 control exterior con retazo y plancha. Resolución 1 mm, separación 1 mm y paso angular 5°.

![HF-001: material y anclajes]({FIGURES.as_posix()}/HF-DIAGNOSTIC-001-physical.svg)

![HF-001: mapa de anclajes]({FIGURES.as_posix()}/HF-DIAGNOSTIC-001-used-01-anchors.svg)

![HF-002: anclajes triangulares]({FIGURES.as_posix()}/HF-DIAGNOSTIC-002-used-01-anchors.svg)

![HF-003: anclajes para convexos]({FIGURES.as_posix()}/HF-DIAGNOSTIC-003-used-01-anchors.svg)

![HF-004: control negativo]({FIGURES.as_posix()}/HF-DIAGNOSTIC-004-anchors.svg)

### Qué hace

Lee el trace generado por las cuatro comparaciones y resume A–E, pockets y tiempos.

### Por qué

Deja el resultado reproducible desde los artefactos locales sin volver a correr el optimizador.

### Qué esperamos observar

Tres cambios de patrón con pockets usados y el control negativo sin pocket.
""")]

    code1 = '''# Importamos json para leer la traza que dejó el benchmark diagnóstico real.
import json
# Importamos Path para ubicar el repositorio desde la carpeta de ejecución.
from pathlib import Path
# Buscamos entre la carpeta actual y sus padres el artefacto diagnóstico del repositorio.
ROOT = next(path for path in (Path.cwd(), *Path.cwd().parents) if (path / "docs/evidence/sprint-02/SP-004/hole-filling/sp004_hole_filling_trace.json").exists())
# Abrimos el archivo JSON con los placements, métricas y tiempos efectivamente medidos.
diagnostic = json.loads((ROOT / "docs/evidence/sprint-02/SP-004/hole-filling/sp004_hole_filling_trace.json").read_text(encoding="utf-8"))
# Escribimos los títulos de la tabla breve para lectura directa.
print("Caso | Clase | opciones pocket | anclajes | componentes | usados | deteccion ms | placement ms | total ms | ratio")
# Recorremos los cuatro casos congelados en el orden de la evidencia.
for case in diagnostic["cases"]:
    # Tomamos el resultado del clasificador predeclarado.
    category = case["classification"]["category"]
    # Tomamos los contadores y el runtime total de Hole Filling.
    details = case["hole_filling"]["diagnostics"]
    # Imprimimos una fila con valores de la corrida guardada.
    print(f"{case['case_id']} | {category} | {details['pocket_options_by_decision']} | {details['geometric_positions_evaluated']} | {details['pocket_components_detected']} | {details['pockets_used']} | {details['pocket_detection_ms']:.2f} | {details['placement_search_ms']:.2f} | {details['total_ms']:.2f} | {case['classification']['runtime_ratio_vs_fastest_baseline']:.2f}x")
'''
    cells.append(code_cell(code1, 1))
    cells.append(markdown_cell("""### Interpretación de la salida

Los casos 001–003 se clasificaron B: el método colocó una pieza en un pocket y cambió su posición respecto de los baselines, con métricas empatadas. HF-004 se clasificó A y usó fallback FF hacia la plancha porque el retazo no admitía la pieza pendiente. El control no inventó un pocket.

## Mapa de regiones y búsqueda de posiciones

### Qué hace

Lee las métricas de detección física y del mapa de anclajes para cada layout congelado.

### Por qué

Separa el hueco físico cerrado del pocket específico de una pieza, que puede existir con una abertura estrecha.

### Qué esperamos observar

Las semillas dejan el espacio físico conectado al exterior; el pocket aparece en el dominio de anclajes de la pieza.
"""))

    code2 = '''# Importamos json para abrir la evidencia independiente de detección.
import json
# Importamos Path para localizar el directorio de evidencia.
from pathlib import Path
# Buscamos el repositorio que contiene el JSON de detección raster.
ROOT = next(path for path in (Path.cwd(), *Path.cwd().parents) if (path / "docs/evidence/sprint-02/SP-004/hole-filling/sp004_hole_filling_detection.json").exists())
# Leemos regiones físicas y componentes de anclajes calculadas antes del placement.
detection = json.loads((ROOT / "docs/evidence/sprint-02/SP-004/hole-filling/sp004_hole_filling_detection.json").read_text(encoding="utf-8"))
# Mostramos los campos que separan hueco físico, pocket y costo de clasificación.
print("Caso | huecos fisicos | orientaciones | anclajes examinados | pockets | fisico ms | mapa ms | componentes ms")
# Recorremos cada caso de detección real.
for case in detection:
    # Imprimimos la medida física y la cantidad de estados de anclaje revisados.
    print(f"{case['case_id']} | {case['internal_holes']} | {case['candidate_orientations']} | {case['anchor_positions_examined']} | {case['pocket_components']} | {case['physical_detection_ms']:.3f} | {case['anchor_generation_ms']:.3f} | {case['anchor_component_detection_ms']:.3f}")
'''
    cells.append(code_cell(code2, 2))
    cells.append(markdown_cell("""### Interpretación de la salida

Los cuatro layouts tienen cero huecos físicos cerrados porque las separaciones y aberturas mantienen el espacio conectado. El detector candidato por pieza sí encontró componentes interiores para círculo, triángulo y polígono convexo; el control negativo no tuvo ninguno. Esto es el resultado esperado para la definición de pocket basada en posiciones factibles.

## Benchmark formal condicionado

El mini-spike fue VIABLE; por esa puerta se compararon FF/BF/WF/HF en los tres casos EXP congelados existentes. La grilla, geometrías, stock, separación, margen y métricas se leyeron sin cambios. HF se repitió tres veces por caso.

### Qué hace

Lee las trazas oficiales del benchmark y muestra métricas funcionales, clase y costo medido.

### Por qué

El diagnóstico valida que el mecanismo puede funcionar; este benchmark evalúa si aparece en los casos experimentales mayores.

### Qué esperamos observar

Si los fixtures contienen pockets útiles, aparecerán conteos y placements HF diferentes; de lo contrario, el algoritmo volverá a FF.
"""))

    code3 = '''# Importamos json para leer el benchmark oficial que pasó por la puerta VIABLE.
import json
# Importamos Path para encontrar la traza dentro del repositorio.
from pathlib import Path
# Buscamos la raíz local que contiene el benchmark EXP.
ROOT = next(path for path in (Path.cwd(), *Path.cwd().parents) if (path / "docs/evidence/sprint-02/SP-004/hole-filling/sp004_hole_filling_official_trace.json").exists())
# Leemos los resultados secuenciales FF/BF/WF/HF ya ejecutados.
official = json.loads((ROOT / "docs/evidence/sprint-02/SP-004/hole-filling/sp004_hole_filling_official_trace.json").read_text(encoding="utf-8"))
# Imprimimos encabezados para el resumen funcional.
print("Caso | Método | Clase HF | Colocadas | Planchas | Uso % | Merma mm² | Recuperable mm² | ms")
# Recorremos cada fixture oficial experimental.
for case in official["cases"]:
    # Combinamos baselines con la corrida HF resumida del mismo caso.
    runs = case["baselines"] + [case["hole_filling"]]
    # Recorremos las cuatro políticas con las métricas originales.
    for run in runs:
        # Leemos métricas y mostramos una fila sin recalcularlas.
        values = run["metrics"]
        # Imprimimos la fila usando los valores originales del benchmark.
        print(f"{case['case_id']} | {run['method']} | {case['classification']['category'] if run['method'] == 'Hole-Filling' else '-'} | {values['placed']}/{values['requested']} | {values['new_sheets_used']} | {values['utilization_pct']} | {values['waste_mm2']} | {values['recoverable_remnant_mm2']} | {run['total_ms']:.2f}")
'''
    cells.append(code_cell(code3, 3))
    cells.append(markdown_cell(f"""### Interpretación de la salida

SMALL empata con FF y no encuentra pockets (A). MEDIUM reproduce el resultado FF y queda por detrás de BF en merma/recuperable (D). COMPLEX tampoco detecta pockets y cuesta más de 10× el baseline más rápido (E por el límite congelado). Las tres corridas HF de cada fixture tienen la misma firma funcional.

**Dictamen:** el detector y el placement son viables en diagnósticos diseñados, pero no hay evidencia de aplicación en EXP-SMALL/MEDIUM/COMPLEX. **NO-GO para TA-042** por ausencia de pockets usados y costo alto en COMPLEX.

## Rendimiento y verificación

- Mini-spike: cuatro casos, 3/3 deterministas; clasificaciones B, B, B, A. HF usó 1 pocket en cada positivo y 0 en el control.
- Runtime relativo a baseline más rápido: {', '.join(f"{case['case_id']} {case['classification']['runtime_ratio_vs_fastest_baseline']:.2f}×" for case in diagnostic['cases'])}.
- Benchmark: {', '.join(f"{case['case_id']} {case['classification']['category']} / {case['classification']['runtime_ratio_vs_fastest_baseline']:.2f}×" for case in official['cases'])}.
- Verificación de placement: `{ROOT / 'experiments/optimization/hole_filling/test_detector.py'}` y `test_optimizer.py`, 13 pruebas PASS. Regresiones FF/BF/WF, placement y ángulos del motor: 145 pruebas PASS.
- La detección acelerada generó el mapa por filas de bits según el patrón existente de `first_position`; el anclaje final usa `SheetLayout.place()` y se revalida reproduciendo todo el layout.
- Las corridas fueron seriales, sin multiprocessing; el pico de RAM no se instrumento.
- No se modificaron TA-042, producción, API, frontend, BD, FF/BF/WF ni fixtures TA-027. No hubo push, PR ni merge.

## Fuentes

- Abeysooriya, Bennell y Martinez-Sykora (2018), [Jostle heuristics for the 2D-irregular shapes bin packing problems with free rotation](https://doi.org/10.1016/j.ijpe.2017.09.014), artículo aceptado: [PDF](https://eprints.whiterose.ac.uk/id/eprint/134688/1/Accepted_article_IJPE.pdf).
- Błażewicz, Hawryluk y Walkowiak (1993), [Using a Tabu Search Approach for Solving the Two-Dimensional Irregular Cutting Problem](https://doi.org/10.1007/BF02022998).
- Burke, Hellier, Kendall y Whitwell (2006), [A New Bottom-Left-Fill Heuristic Algorithm for the Two-Dimensional Irregular Packing Problem](https://doi.org/10.1287/opre.1060.0293), [PDF](https://quaoar.su/files/papers/nesting/opre.1060.0293.pdf).
- Guo et al. (2022), [Two-dimensional irregular packing problems: A review](https://doi.org/10.3389/fmech.2022.966691).

Los outputs de las secciones anteriores son resúmenes de los artefactos JSON/CSV guardados en `docs/evidence/sprint-02/SP-004/hole-filling/`; no se fabricaron ni se retocaron resultados. La sección demostrativa final ejecuta los cuatro métodos directamente.
"""))

    cells.append(markdown_cell(f"""# Validación final con pedidos realistas

Se fijaron tres pedidos sintéticos plausibles antes de comparar. Los SHA-256 y el commit de congelación se leen desde la traza. Cada método usa el mismo stock, material, espesor y configuración; los tres HF se ejecutaron en serie.

Clasificaciones registradas: {', '.join(f"{case['case_id']} {case['classification']['category']}" for case in realistic['cases'])}. E prevalece cuando HF supera 10× el baseline más rápido, criterio declarado en el manifiesto previo.
"""))

    for index, case in enumerate(realistic["cases"], start=1):
        case_id = case["case_id"]
        shape_counts = {}
        for item in case["pieces"]:
            shape = item["geometry"]["type"]
            shape_counts[shape] = shape_counts.get(shape, 0) + 1
        figure_lines = []
        if case["figures"]:
            primary = (ROOT / case["figures"][0]).relative_to(ROOT / "experiments/optimization")
            figure_lines.append(f"![Placement pocket-first {case_id}](../{primary.as_posix()})")
            if len(case["figures"]) > 1:
                extras = ", ".join(
                    f"[`pocket {number:02d}`](../{(ROOT / name).relative_to(ROOT / 'experiments/optimization').as_posix()})"
                    for number, name in enumerate(case["figures"][1:], start=2)
                )
                figure_lines.append(f"Figuras adicionales: {extras}.")
        else:
            figure_lines.append("No se genera figura de pocket: HF no utilizó ninguno en este pedido.")

        cells.append(markdown_cell(f"""## {case_id} — {['círculos', 'triángulos y convexos', 'pedido mixto'][index-1]}

Unidades: {case['requested_units']}; geometrías: {shape_counts}; material {case['material']['glass_type_id']}, espesor {case['material']['thickness_mm']} mm. Fixture SHA-256: `{case['fixture_freeze']['fixture_sha256']}`; commit de congelación `{case['fixture_freeze']['fixture_freeze_commit'][:8]}`.

{' '.join(figure_lines)}

### Qué hace

Lee la comparación guardada de FF/BF/WF y las tres repeticiones HF, incluidos placements y decisiones pocket/fallback.

### Por qué

El pedido quedó congelado antes del benchmark; esta celda expone sus resultados sin volver a correr el optimizador.

### Qué esperamos observar

Métricas iguales o distintas, cantidad de pockets usados y costo por método para este perfil de pedido.
"""))

        code = f'''# Importamos json para leer la traza real del benchmark realista.
import json
# Importamos Path para localizar el repositorio desde la carpeta de trabajo.
from pathlib import Path
# Buscamos la raiz que contiene los resultados congelados de SP-004.
ROOT = next(path for path in (Path.cwd(), *Path.cwd().parents) if (path / "docs/evidence/sprint-02/SP-004/hole-filling/sp004_hf_realistic_trace.json").exists())
# Leemos la traza completa que incluye baselines y tres repeticiones HF.
trace = json.loads((ROOT / "docs/evidence/sprint-02/SP-004/hole-filling/sp004_hf_realistic_trace.json").read_text(encoding="utf-8"))
# Seleccionamos solo el caso explicado en esta sección.
case = next(item for item in trace["cases"] if item["case_id"] == "{case_id}")
# Mostramos la tabla funcional medida para cada método.
print("Método | colocadas | retazos | planchas | uso % | merma mm² | recuperable mm² | runtime ms")
# Recorremos FF, BF, WF y el resumen HF del mismo pedido.
for run in case["baselines"] + [case["hole_filling"]]:
    # Leemos las métricas oficiales ya calculadas por el motor.
    metrics = run["official_metrics"]
    # Imprimimos cada método sin recalcular métricas.
    print(f"{{run['method']}} | {{metrics['placed_units']}}/{{metrics['requested_units']}} | {{metrics['remnants_used']}} | {{metrics['sheets_used']}} | {{metrics['utilization_pct']}} | {{metrics['waste_mm2']}} | {{metrics['recoverable_area_mm2']}} | {{metrics['runtime_ms']:.2f}}")
# Leemos los contadores específicos de Hole Filling.
hf = case["hole_filling"]
# Imprimimos la decisión, el costo y el determinismo medidos.
print(f"Clase {{case['classification']['category']}} | pockets {{hf['pockets_detected']}}/{{hf['pockets_used']}} | piezas en pocket {{hf['pieces_placed_in_pockets']}} | opciones {{hf['pocket_candidates_checked']}} | detección ms {{hf['pocket_detection_ms']:.2f}} | placement ms {{hf['pocket_placement_ms']:.2f}} | fallback {{hf['fallback_count']}} | cambios de fuente {{hf['source_switches']}} | determinista {{case['deterministic']}}")
# Leemos las tres repeticiones HF guardadas para este mismo fixture.
repetitions = case["hf_repetitions"]
# Imprimimos cada runtime individual sin incluirlo en la firma funcional.
print("HF repeticiones runtime ms | " + " | ".join(f"{{run['official_metrics']['runtime_ms']:.2f}}" for run in repetitions))
# Recorremos cada placement HF con su decisión de pocket o fallback.
for placement in hf["placements"]:
    # Imprimimos identidad, fuente, giro, coordenadas y decisión.
    print(f"pieza {{placement['piece_id']}} | {{placement['source']}} | {{placement['rotation_deg']}} grados | ({{placement['x_mm']}}, {{placement['y_mm']}}) mm | {{placement['decision']}}")
'''
        cells.append(code_cell(code, 3 + index))

        interpretations = {
            "HF-REALISTIC-001": "Los círculos no generaron componentes pocket utilizables. HF reprodujo el baseline en placements y métricas, pero su barrido fue de clase E por costo.",
            "HF-REALISTIC-002": "HF colocó la pieza 5 en un pocket y cambió el patrón. Las métricas empataron con FF/BF/WF; el runtime mantuvo la clase E.",
            "HF-REALISTIC-003": "HF colocó seis piezas en pockets, pero dejó una sin colocar y empeoró uso, merma y recuperable. El costo también superó ampliamente el umbral E.",
        }
        cells.append(markdown_cell(f"""### Interpretación de la salida

{interpretations[case_id]}
"""))

    capability_namespace = {}
    next_count = 7

    def append_capability_code(source):
        nonlocal next_count
        cells.append(code_cell(source, next_count, capability_namespace))
        next_count += 1

    cells.append(markdown_cell(f"""# Experimento demostrativo de capacidad de Hole Filling

## Experimento demostrativo — pedido favorable a Hole Filling

> **CASO CONTROLADO DISEÑADO PARA MOSTRAR LA CLASE DE PEDIDO EN LA QUE HOLE FILLING PUEDE SER ÚTIL. NO REPRESENTA RENDIMIENTO GENERAL.**

## Por qué existe este experimento

SMALL/MEDIUM/COMPLEX y HF-REALISTIC-001/002/003 constituyen la evaluación general de SP-004; su dictamen NO-GO para TA-042 permanece. Este caso dirigido muestra una capacidad concreta del mecanismo. La búsqueda FF/HF probó {capability['search_candidates_tried']} configuraciones y se detuvo en la primera que cumplió los criterios predeclarados. Fixture SHA-256: `{capability['fixture_freeze']['fixture_sha256']}`; commit de congelación: `{capability['fixture_freeze']['fixture_freeze_commit'][:8]}`.

## Qué tipo de pedido favorece HF

Un layout ya ocupado por círculos y paneles puede dejar pockets de anclajes para insertos pequeños. Si queda una región exterior ajustada, poner allí el inserto puede impedir colocar una pieza posterior. La composición controlada tiene dieciséis piezas previas, un inserto cuadrado y un círculo posterior; el stock incluye retazo y plancha compatibles.

## Fixture controlado

### Qué hace

Lee el fixture congelado, verifica su hash y muestra configuración, stock y piezas antes de ejecutar heurísticas.

### Por qué

Permite revisar el diseño intencional y confirmar que el notebook usa exactamente el JSON congelado.

### Qué esperamos observar

Raster 1 mm, giros cada 5°, margen 5 mm, separación 3 mm y el inserto de 32 × 32 mm procesado antes del círculo de Ø36 mm.
"""))

    code_setup = f'''# Importamos hashlib para verificar los bytes del fixture congelado.
import hashlib
# Importamos statistics para resumir las tres duraciones HF.
import statistics
# Importamos sys para cargar los paquetes locales del repositorio.
import sys
# Importamos Path para ubicar casos, trazas y figuras.
from pathlib import Path
# Encontramos la raíz que contiene el fixture de capacidad.
ROOT = next(path for path in (Path.cwd(), *Path.cwd().parents) if (path / "experiments/optimization/hole_filling/cases/HF-CAPABILITY-001.json").exists())
# Exponemos el backend real al intérprete del notebook.
sys.path.insert(0, str(ROOT / "backend"))
# Exponemos los experimentos del repositorio al intérprete.
sys.path.insert(0, str(ROOT))
# Importamos el lector del fixture y su validación de semillas.
from experiments.optimization.hole_filling.lab import read_case, prepare_case
# Importamos las cuatro heurísticas experimentales y las métricas originales.
from experiments.optimization.hole_filling.optimizer import run_baseline, run_hole_filling, metric_values
# Importamos la firma funcional usada por el benchmark definitivo.
from experiments.optimization.hole_filling.run_realistic_benchmark import _determinism_signature
# Importamos los renderizadores grises que usan placements reales.
from experiments.optimization.hole_filling.visualize import render_capability_comparison, render_pocket_placement
# Formamos la ruta al JSON congelado.
case_path = ROOT / "experiments/optimization/hole_filling/cases/HF-CAPABILITY-001.json"
# Verificamos que ningún byte del fixture cambió después de la congelación.
assert hashlib.sha256(case_path.read_bytes()).hexdigest() == "{capability['fixture_freeze']['fixture_sha256']}"
# Leemos la misma configuración que usarán FF, BF, WF y HF.
case = read_case("HF-CAPABILITY-001")
# Validamos todas las piezas previas con SheetLayout.check/place antes de correr.
setup = prepare_case("HF-CAPABILITY-001")
# Mostramos la configuración compartida por todos los métodos.
print("Configuración:", case["config"], "| material:", case["material"])
# Recorremos retazo y plancha del fixture controlado.
for stock in case["stocks"]:
    # Mostramos fuente, identificador y dimensiones sin modificarlos.
    print("Stock:", stock["source"], stock["material_id"], stock["geometry"])
# Recorremos cada pieza para distinguir las previas de las pendientes.
for piece in case["pieces"]:
    # Mostramos identidad, geometría y estado inicial de cada pieza.
    print("Pieza:", piece["piece_id"], piece["role"], piece["geometry"])
'''
    append_capability_code(code_setup)
    cells.append(markdown_cell("""### Interpretación de la salida

La traza del fixture muestra dieciséis placements previos comunes y dos piezas pendientes. El círculo inicial y los paneles conforman el layout de partida; las dos fuentes y los parámetros son idénticos para los cuatro métodos.

## Comportamiento esperado

La intención congelada esperaba un pocket apto para el inserto y una franja superior que pudiera reservarse para el círculo posterior. El pocket realmente seleccionado puede diferir del imaginado al diseñar; las celdas siguientes muestran lo que calculó el motor.
"""))

    method_names = {"FF": "First Fit", "BF": "Best Fit", "WF": "Worst Fit"}
    method_vars = {"FF": "ff_run", "BF": "bf_run", "WF": "wf_run"}
    for method in ("FF", "BF", "WF"):
        variable = method_vars[method]
        cells.append(markdown_cell(f"""## {method_names[method]}

### Qué hace

Ejecuta {method_names[method]} sobre el fixture congelado y muestra los placements pendientes, fuente, orientación, posición y métricas medidas.

### Por qué

Es la referencia real del motor para comparar la decisión pocket-first de HF.

### Qué esperamos observar

El método procesa primero el inserto por área; la posición y la fuente del círculo posterior salen de sus propias reglas.
"""))
        code_method = f'''# Ejecutamos el método {method} con las semillas validadas y el fixture congelado.
{variable} = run_baseline("HF-CAPABILITY-001", "{method}")
# Leemos las métricas calculadas por el motor para esta corrida.
values = metric_values({variable})
# Mostramos cobertura, planchas, utilización, merma, recuperable y runtime real.
print("{method}:", values["placed"], "/", values["requested"], "| planchas", values["new_sheets_used"], "| uso", values["utilization_pct"], "| merma", values["waste_mm2"], "| recuperable", values["recoverable_remnant_mm2"], "| ms", round({variable}["total_ms"], 2))
# Recorremos los placements producidos por el método.
for placement in {variable}["result"].placements:
    # Filtramos las piezas pendientes para distinguirlas del layout previo común.
    if placement.piece.piece_id in (11, 12):
        # Imprimimos pieza, fuente, giro y coordenadas efectivamente usadas.
        print("Pieza", placement.piece.piece_id, placement.stock.source.value, str(placement.rotation_deg) + "°", "(", placement.x_mm, ",", placement.y_mm, ") mm")
'''
        append_capability_code(code_method)
        if method == "FF":
            interpretation = "FF colocó el inserto en la franja exterior de la esquina superior izquierda. El círculo posterior pasó a la plancha."
        elif method == "BF":
            interpretation = "BF eligió la misma franja para el inserto y necesitó la plancha para el círculo posterior."
        else:
            interpretation = "WF también ocupó la franja con el inserto; el círculo posterior quedó en la plancha."
        cells.append(markdown_cell(f"""### Interpretación de la salida

{interpretation}
"""))

    cells.append(markdown_cell("""## Hole Filling

### Qué hace

Ejecuta HF tres veces sobre el fixture congelado, imprime las decisiones de pocket/fallback y compara sus firmas funcionales.

### Por qué

Confirma con corridas reales que el inserto entra en un pocket y que la decisión se repite sin depender del runtime.

### Qué esperamos observar

Un pocket usado para la pieza 11 y la pieza 12 colocada después en el retazo.
"""))
    code_hf = '''# Creamos una lista para conservar las tres corridas independientes de HF.
hf_runs = []
# Ejecutamos HF tres veces de forma serial sobre el mismo JSON congelado.
for repetition in range(1, 4):
    # Guardamos cada corrida completa para comparar placements y métricas.
    hf_runs.append(run_hole_filling("HF-CAPABILITY-001"))
    # Mostramos el runtime individual sin usarlo como parte de la firma.
    print("HF repetición", repetition, "| ms", round(hf_runs[-1]["total_ms"], 2))
# Construimos las firmas funcionales que excluyen el tiempo.
hf_signatures = [_determinism_signature(run) for run in hf_runs]
# Comprobamos que las tres firmas se repitieron exactamente.
hf_deterministic = len(set(hf_signatures)) == 1
# Mostramos PASS o FAIL de determinismo.
print("Determinismo:", "PASS" if hf_deterministic else "FAIL")
# Conservamos la primera corrida para sus placements y figuras.
hf_run = hf_runs[0]
# Leemos las métricas originales de Hole Filling.
hf_values = metric_values(hf_run)
# Imprimimos cobertura, uso, merma y fuentes de la primera corrida.
print("HF:", hf_values["placed"], "/", hf_values["requested"], "| planchas", hf_values["new_sheets_used"], "| uso", hf_values["utilization_pct"], "| merma", hf_values["waste_mm2"], "| recuperable", hf_values["recoverable_remnant_mm2"])
# Mostramos componentes detectados, pockets usados y fallbacks.
print("Pockets:", hf_run["diagnostics"]["pocket_components_detected"], "| usados:", hf_run["diagnostics"]["pockets_used"], "| fallback:", hf_run["diagnostics"]["fallback_placements"] + hf_run["diagnostics"]["fallback_unplaced"])
# Recorremos las piezas pendientes colocadas por HF.
for placement in hf_run["result"].placements:
    # Separamos las dos piezas pendientes de las dieciséis semillas.
    if placement.piece.piece_id in (11, 12):
        # Etiquetamos el placement según el pocket seleccionado.
        decision = "pocket" if any(item["piece_id"] == placement.piece.piece_id for item in hf_run["diagnostics"]["selected_pockets"]) else "fallback"
        # Mostramos pieza, fuente, giro, posición y decisión.
        print("Pieza", placement.piece.piece_id, placement.stock.source.value, str(placement.rotation_deg) + "°", "(", placement.x_mm, ",", placement.y_mm, ") mm", decision)
'''
    append_capability_code(code_hf)
    cells.append(markdown_cell("""### Interpretación de la salida

HF detectó siete componentes candidatos y usó uno para el inserto P11 en el retazo, a 0° y (51, 191) mm. P12 quedó en la franja superior del mismo retazo mediante fallback. Las tres firmas funcionales coincidieron; los tiempos individuales pueden variar.
"""))

    cells.append(markdown_cell("""## Comparación visual

### Qué hace

Dibuja los cuatro layouts finales usando las máscaras raster de los placements recién ejecutados. En el panel HF marca el componente de anclajes pocket y el inserto.

### Por qué

La imagen permite seguir el espacio exterior que ocupan los baselines y que HF conserva para el círculo posterior.

### Qué esperamos observar

FF/BF/WF usan retazo y plancha; HF termina en el retazo. La figura por etapas muestra el layout previo, pocket y pieza pendiente.
"""))
    code_figures = '''# Indicamos la carpeta de figuras dentro del experimento aislado.
figure_dir = ROOT / "experiments/optimization/hole_filling/figures"
# Dibujamos los cuatro layouts finales a partir de las corridas vivas.
render_capability_comparison({"FF": ff_run, "BF": bf_run, "WF": wf_run, "HF": hf_run}, figure_dir / "HF-CAPABILITY-001-comparison.svg")
# Extraemos el estado inmediatamente anterior al placement pocket de HF.
layout, anchor_map, selected_anchor, pending_mask = hf_run["pocket_placement_contexts"][0]
# Dibujamos layout previo, anclajes, pocket, inserto y posición elegida.
render_pocket_placement(layout, anchor_map, selected_anchor, pending_mask, figure_dir / "HF-CAPABILITY-001-pocket-stage.svg", "HF-CAPABILITY-001 | antes y durante el pocket")
# Confirmamos las rutas de las dos figuras generadas por el código.
print("Figuras:", figure_dir / "HF-CAPABILITY-001-comparison.svg", "|", figure_dir / "HF-CAPABILITY-001-pocket-stage.svg")
'''
    append_capability_code(code_figures)
    cells.append(markdown_cell("""### Interpretación de la salida

El contorno y la etiqueta del pocket aparecen solo en HF. La plancha queda sin uso en su panel; los tres baselines la usan para P12. El mapa de la segunda figura separa anclajes legales exteriores y el componente pocket específico de P11.

![FF, BF, WF y HF: layouts finales](../hole_filling/figures/HF-CAPABILITY-001-comparison.svg)

![Layout previo, pocket y pieza pendiente](../hole_filling/figures/HF-CAPABILITY-001-pocket-stage.svg)
"""))

    cells.append(markdown_cell("""## Comparación de métricas

### Qué hace

Resume los cuatro métodos desde las corridas ejecutadas en este notebook; HF usa la mediana de sus tres tiempos.

### Por qué

La diferencia funcional debe salir de las métricas oficiales y de las fuentes usadas, no de la intención del diseñador.

### Qué esperamos observar

La misma cobertura, pero una plancha menos para HF si el pocket preservó la franja exterior.
"""))
    code_compare = '''# Mostramos las columnas oficiales para comparar los cuatro métodos.
print("Método | colocadas | retazos | planchas | uso % | merma mm² | recuperable mm² | runtime ms")
# Recorremos FF, BF, WF y HF en el mismo orden que el benchmark definitivo.
for method, run in (("FF", ff_run), ("BF", bf_run), ("WF", wf_run), ("HF", hf_run)):
    # Leemos las métricas calculadas por el mismo motor para cada corrida.
    values = metric_values(run)
    # Contamos las unidades físicas de retazo usadas por los placements.
    remnants = len({(p.stock.material_id, p.stock.physical_unit_index) for p in run["result"].placements if p.stock.source.value == "RETAZO"})
    # Resumimos el runtime HF con sus tres repeticiones; los demás tienen una.
    duration = statistics.median(item["total_ms"] for item in hf_runs) if method == "HF" else run["total_ms"]
    # Imprimimos la fila sin alterar las fórmulas oficiales.
    print(method, "|", str(values["placed"]) + "/" + str(values["requested"]), "|", remnants, "|", values["new_sheets_used"], "|", values["utilization_pct"], "|", values["waste_mm2"], "|", values["recoverable_remnant_mm2"], "|", round(duration, 2))
'''
    append_capability_code(code_compare)

    hf_metrics = capability["hole_filling"]["official_metrics"]
    baseline_metrics = capability["baselines"][0]["official_metrics"]
    cells.append(markdown_cell(f"""### Interpretación de la salida

El benchmark definitivo colocó 18/18 en todos los métodos. FF/BF/WF usaron un retazo y una plancha; HF usó solo el retazo. El uso pasó de {baseline_metrics['utilization_pct']}% a {hf_metrics['utilization_pct']}% y la merma de {baseline_metrics['waste_mm2']} a {hf_metrics['waste_mm2']} mm². El área recuperable registrada bajó de {baseline_metrics['recoverable_area_mm2']} a {hf_metrics['recoverable_area_mm2']} mm²; se informa aunque el ahorro de una plancha sea la mejora principal. Runtime HF mediano: {hf_metrics['runtime_ms']:.2f} ms; FF/BF/WF: {', '.join(f"{item['method']} {item['official_metrics']['runtime_ms']:.2f} ms" for item in capability['baselines'])}.

## Qué demuestra este caso

1. Dieciséis piezas previas crean un componente pocket de anclajes para el inserto P11. El componente usado quedó en la parte inferior izquierda del marco, distinto de la cavidad superior inicialmente imaginada.
2. FF/BF/WF colocan P11 en (5, 5) mm del retazo y P12 en (5, 5) mm de la plancha.
3. HF coloca P11 dentro del pocket en (51, 191) mm; después P12 cabe en (5, 5) mm del retazo. La diferencia procede de la decisión pocket-first con las mismas reglas geométricas, de inventario y métricas.
4. Las tres repeticiones HF dieron la misma firma funcional. El experimento alcanzó el nivel 1 predeclarado: una plancha menos.

**Recomendación exploratoria para TA-042:** investigar activación solo si hay geometrías como círculos o convexos, mezcla de tamaños, ocupación alta, piezas menores pendientes y un pocket legal detectado con un filtro barato. Este caso no implementa esa activación.

El resultado es una prueba de capacidad de un pedido deliberadamente diseñado. No estima frecuencia ni rendimiento promedio y no cambia el NO-GO basado en EXP y REALISTIC. Los [resultados definitivos](../../../docs/evidence/sprint-02/SP-004/hole-filling/sp004_hf_capability_results.csv), [traza completa](../../../docs/evidence/sprint-02/SP-004/hole-filling/sp004_hf_capability_trace.json) y [registro de búsqueda](../hole_filling/cases/HF-CAPABILITY-SEARCH.jsonl) conservan los números, placements y veinte intentos.
"""))

    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.11"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


if __name__ == "__main__":
    TARGET.write_text(json.dumps(build_notebook(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(TARGET)
