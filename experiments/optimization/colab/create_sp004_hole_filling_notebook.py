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


def code_cell(source, count):
    namespace = {}
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
- Verificación de placement: `{ROOT / 'experiments/optimization/hole_filling/test_detector.py'}` y `test_optimizer.py`, 11 pruebas PASS. Regresiones FF/BF/WF, placement y ángulos del motor: 145 pruebas PASS.
- La detección acelerada generó el mapa por filas de bits según el patrón existente de `first_position`; el anclaje final usa `SheetLayout.place()` y se revalida reproduciendo todo el layout.
- Las corridas fueron seriales, sin multiprocessing; el pico de RAM no se instrumento.
- No se modificaron TA-042, producción, API, frontend, BD, FF/BF/WF ni fixtures TA-027. No hubo push, PR ni merge.

## Fuentes

- Abeysooriya, Bennell y Martinez-Sykora (2018), [Jostle heuristics for the 2D-irregular shapes bin packing problems with free rotation](https://doi.org/10.1016/j.ijpe.2017.09.014), artículo aceptado: [PDF](https://eprints.whiterose.ac.uk/id/eprint/134688/1/Accepted_article_IJPE.pdf).
- Błażewicz, Hawryluk y Walkowiak (1993), [Using a Tabu Search Approach for Solving the Two-Dimensional Irregular Cutting Problem](https://doi.org/10.1007/BF02022998).
- Burke, Hellier, Kendall y Whitwell (2006), [A New Bottom-Left-Fill Heuristic Algorithm for the Two-Dimensional Irregular Packing Problem](https://doi.org/10.1287/opre.1060.0293), [PDF](https://quaoar.su/files/papers/nesting/opre.1060.0293.pdf).
- Guo et al. (2022), [Two-dimensional irregular packing problems: A review](https://doi.org/10.3389/fmech.2022.966691).

Los outputs del notebook son resúmenes de los artefactos JSON/CSV guardados en `docs/evidence/sprint-02/SP-004/hole-filling/`; no se fabricaron ni se retocaron resultados.
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
