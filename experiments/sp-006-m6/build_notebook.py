"""Construye el notebook autosuficiente y un ZIP opcional, sin red ni rutas de máquina."""
import base64
import hashlib
import io
import json
from pathlib import Path
import textwrap
import zipfile

ROOT = Path(__file__).resolve().parent


def build():
    paths = sorted([*ROOT.glob("vendor/**/*.py"), *ROOT.glob("vendor/**/*.json"),
                    *ROOT.glob("sp006/*.py"), ROOT / "snapshot-manifest.json", ROOT / "requirements.txt"])
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in paths:
            info = zipfile.ZipInfo(path.relative_to(ROOT).as_posix(), date_time=(2026, 11, 2, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())
    payload = buffer.getvalue()
    encoded = base64.b64encode(payload).decode()
    cells = []

    def md(source):
        cells.append(dict(cell_type="markdown", metadata={}, source=textwrap.dedent(source).strip() + "\n"))

    def code(source):
        cells.append(dict(cell_type="code", metadata={}, execution_count=None, outputs=[],
                          source=textwrap.dedent(source).strip() + "\n"))

    md("""
    # NEWGLASS · SP-006 · Beam Search acotada (BS-k)
    **Experimento CPU, en español y sin acceso al repositorio. Versión SP006-BS-v1.**

    Objetivo: investigar si M6 toma decisiones propias, mejora algún resultado y tiene un
    costo razonable. La elección de M6 queda pendiente de la revisión de Fabricio.
    Este cuaderno no implementa TA-053 T01/T02 ni modifica inventario o aplicación.

    **Primera vez en Colab:** sube este `.ipynb` desde Archivo → Subir cuaderno. Selecciona
    un entorno Python 3 con CPU (no hace falta GPU) y usa Entorno de ejecución → Ejecutar todas.
    Las celdas se ejecutan de arriba hacia abajo con ▶. Espera a que termine cada indicador.
    El archivo incluye código y fixtures: no necesitas subir otros archivos ni montar Drive.
    Requiere Internet solo para instalar dependencias públicas. Guarda una copia del cuaderno
    y descarga los resultados antes de cerrar el entorno temporal de Colab.

    Los números aparecerán al ejecutar. Este archivo limpio no contiene mediciones precargadas.
    """)
    md("""
    ## 1. El problema y los casos que realmente tenemos
    Colocar rectángulos, circunferencias y polígonos convexos sobre stock compatible sin
    superposiciones, conservando margen, separación y prioridad de retazos factibles.
    Las cantidades representan unidades físicas; una misma fuente puede contener varias piezas.

    Usamos **exactamente** `EXP-SMALL-001`, `EXP-MEDIUM-001`, `EXP-COMPLEX-001` de
    `experiments/optimization/cases/` (TA-027), integración congelada en
    `f9cfd4f2644455d616699518948c6660006bdae8`. SMALL tiene 3 unidades y 2 fuentes;
    MEDIUM 9 y 4; COMPLEX 24 y 7, en dos materiales. El nombre COMPLEX no significa
    escala industrial: las fuentes llegan solo a 22 × 16 mm. No se escalan ni regeneran.

    La comparación es fiel al dominio de ese snapshot y **exploratoria de SP-006**.
    No representa un benchmark oficial de producción ni mide backend, red, BD o coordinador.
    """)
    md("""
    ## 2. Beam Search sin conocimientos previos
    Un **nodo** es un dibujo parcial: qué piezas ya colocamos y qué espacio queda.
    Una **rama** representa una decisión: fuente, posición y giro de la siguiente pieza.
    Al añadir sucesivas piezas construimos un **árbol** de alternativas.

    ```text
                           Stock vacío (raíz)
                      /             |             \\
                decisión A     decisión B      decisión C
                 /    \\          /    \\          /    \\
              A1     A2        B1     B2        C1     C2
    ```

    Explorar todo crece muy rápido. Beam Search conserva solo **k nodos** prometedores
    por nivel. Aquí probamos k=2, 3 y 4. Cada nivel decide la siguiente unidad en el mismo
    orden de NewGlass. La puntuación compara soluciones parciales y descarta el resto.
    La poda puede eliminar una solución que habría sido mejor más adelante: no hay garantía
    de óptimo ni de que aumentar k mejore el resultado.
    """)
    md("""
    ## 3. Referencias académicas comprobadas
    - Bennell y Song (2010), *A beam search implementation for the irregular shape packing
      problem*, Journal of Heuristics 16, 167–188.
      [DOI 10.1007/s10732-008-9095-x](https://doi.org/10.1007/s10732-008-9095-x).
      [Registro universitario](https://researchportal.port.ac.uk/en/publications/a-beam-search-implementation-for-the-irregular-shape-packing-prob/).
      Busca órdenes de piezas usando una heurística de colocación y no-fit polygons.
    - Bennell, Cabo Nodar y Martínez-Sykora (2018), *A beam search approach to solve the
      convex irregular bin packing problem with guillotine cuts*, EJOR 270, 89–102.
      [DOI 10.1016/j.ejor.2018.03.029](https://doi.org/10.1016/j.ejor.2018.03.029).
      [Repositorio universitario](https://eprints.whiterose.ac.uk/id/eprint/134687/).
      Estudia piezas convexas, bins de varios tamaños y cortes guillotina.
    - Fontan y Libralesso (2020), *An anytime tree search algorithm for two-dimensional
      two- and three-staged guillotine packing problems*.
      [Preprint de los autores, versión 2](https://arxiv.org/abs/2004.02603v2).
      Es contexto sobre búsqueda en árboles para cutting, no la receta exacta de esta M6.

    Consulta de fuentes: 02/11/2026. **Nuestra adaptación no reproduce esos algoritmos**:
    mantiene orden fijo y explora placements con raster NewGlass; no incorpora no-fit
    polygons, búsqueda del orden ni garantiza cortes guillotina. Las mejoras de los artículos
    no demuestran mejoras de NewGlass. No se redistribuyen los artículos.
    """)
    md("""
    ## 4. Adaptación M6 y fidelidad
    Nodo inmutable: layouts de todas las fuentes físicas, placements, número procesado y
    traza de decisiones. Sucesores: todas las orientaciones distintas de la rejilla 0..355°
    en pasos de 5°; por orientación/fuente factible se proponen la **primera y última posición
    válida** por orden fila/columna. Las posiciones interiores intermedias se podan.

    Primero se comprueba, con todas las orientaciones, si existe algún retazo compatible
    factible en el estado actual. Si existe, solo se generan hijos sobre esos retazos.
    Si ninguno cabe, se habilitan planchas. Si no existe ningún placement, se registra NO_FIT
    y se continúa con la siguiente unidad. Agotar un presupuesto produce LIMIT y deja unidades
    pendientes; no autoriza NO_FIT ni ignorar retazos.

    Se minimiza, en orden lexicográfico: **(faltantes procesados, −área nominal colocada,
    planchas usadas, área nominal de fuentes usadas, −suma de máximos rectángulos libres
    en celdas, suma de envolventes ocupadas en celdas, traza)**. La traza desempata por fuente,
    rango de orientación deduplicada, fila y columna. No hay pesos ocultos ni aleatoriedad.
    El rectángulo libre del score es una guía, no la métrica final de recuperable.

    Por padre se retienen 12 hijos y globalmente los mejores k. Se elige el menor score
    del último nivel completamente terminado. Un nivel interrumpido se descarta entero.
    Esta función puede favorecer un buen resultado parcial y perder oportunidades posteriores.

    FF/BF/WF son **las implementaciones originales copiadas**, no aproximaciones. Usan solo
    primera posición/orientación factible por fuente; FF toma la primera fuente; BF minimiza
    y WF maximiza celdas libres posteriores dentro del nivel permitido. M6 amplía las
    decisiones de colocación; nunca llama a esos optimizadores para escoger ganador.

    Se copian sin cambios raster, rotación, preparación y métricas. Pieza = máscara
    conservadora; material = máscara interior. Margen por erosión y separación por dilatación
    cuadrada de celdas, redondeando distancias hacia arriba. **No se sustituye por Shapely
    ni por cajas envolventes.** La única envolvente aquí se usa como término de puntuación.
    """)
    md("""
    ## 5. Recuperar el paquete incluido e instalar dependencias
    Esta celda extrae los archivos portables junto al cuaderno y verifica su integridad.
    El bloque base64 es el ZIP incluido, no una descarga del repositorio privado.
    No lo edites. Después se instalan versiones fijadas de las bibliotecas de gráficos y RSS.
    """)
    code(f'''
import base64, hashlib, io, os, sys, zipfile
from pathlib import Path
PAYLOAD = "{encoded}"
blob = base64.b64decode(PAYLOAD)
assert hashlib.sha256(blob).hexdigest() == "{hashlib.sha256(payload).hexdigest()}"
if "SP006_BASE" not in globals():
    SP006_BASE = Path.cwd()
work = SP006_BASE / "sp006_colab"
work.mkdir(exist_ok=True)
with zipfile.ZipFile(io.BytesIO(blob)) as archive:
    for entry in archive.infolist():
        destination = (work / entry.filename).resolve()
        assert destination.is_relative_to(work.resolve()), "Ruta inválida en el paquete"
    archive.extractall(work)
os.chdir(work)
sys.path[:0] = [str(work.resolve() / "vendor"), str(work.resolve())]
print("Paquete portátil extraído. Python", sys.version.split()[0])
''')
    code('''
import subprocess
assert sys.version_info >= (3, 11), "Selecciona Python 3.11 o posterior."
subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "-r", "requirements.txt"])
from sp006.validation import verify_snapshot
manifest = verify_snapshot()
print("Integridad correcta:", len(manifest["files"]), "archivos originales; commit", manifest["source_commit"])
''')
    md("""
    ## 6. Parámetros: distinguir reglas originales y límites de investigación
    La configuración geométrica está en cada JSON y **no se modifica**. SMALL usa margen y
    separación 0; MEDIUM/COMPLEX 1 mm. Todos usan resolución 1 mm, paso 5° y residual mínimo
    1 × 1 mm. No hay un valor geométrico faltante en esos tres casos.

    Límites propuestos de investigación: k=2/3/4, 12 hijos retenidos por padre, dos posiciones
    por orientación, 60.000 placements generados, 1.000.000 consultas geométricas y 32 MiB
    de cota conservadora para estados. La caché original conserva su límite de 64 MiB.
    Tiempo cooperativo: 30 s por cálculo; supervisor: 60 s por proceso (incluye arranque y
    validación), RSS observado máximo permitido 256 MiB. No son parámetros aprobados de TA-053.

    Las consultas cuentan cada first_position y cada check de posición alternativa; no las
    operaciones internas de bits. La cota de estados no es memoria medida. RSS se muestrea
    cada 10 ms: puede perder picos cortos, incluye intérprete y auditoría, y se mide por
    proceso nuevo para evitar contaminación entre métodos. El tiempo incluye reconstrucción,
    preparación, búsqueda y métricas; excluye arranque, auditoría y gráficos.
    """)
    code('''
from dataclasses import asdict
from sp006.beam import SearchLimits
import pandas as pd
display(pd.DataFrame([asdict(SearchLimits(width=k)) for k in (2, 3, 4)]))
REPETICIONES = 2  # Prueba de determinismo; aumentar después para estudiar variación temporal.
''')
    md("""
    ## 7. Cargar y revisar SMALL, MEDIUM y COMPLEX
    Los JSON, loader y sus hashes vienen de TA-027. El stock congelado ya es candidato
    disponible: no contiene estados ni fechas de inventario. Se conserva el orden original
    por nivel y se expande quantity en unidades físicas 1..N. No se inventa stock extra.
    La tabla permite comprobar cantidades, materiales y reglas antes de ejecutar.
    """)
    code('''
from experiments.optimization.loader import CASES, read_case, load_problem
rows = []
for case_id in CASES:
    data, problem = read_case(case_id), load_problem(case_id)
    stocks = [s for g in problem.groups for s in g.stock_candidates]
    rows.append(dict(caso=case_id, piezas_distintas=len(data["pieces"]), unidades=len(problem.units),
        retazos=sum(s.source.value == "RETAZO" for s in stocks),
        planchas=sum(s.source.value == "PLANCHA" for s in stocks), materiales=len(problem.groups), **data["config"]))
display(pd.DataFrame(rows))
display(pd.DataFrame([e for e in manifest["files"] if e["target"].endswith(".json")])[["source", "sha256"]])
# Para inspeccionar el contenido íntegro de un caso, descomenta:
# display(read_case("EXP-COMPLEX-001"))
''')
    md("""
    ## 8. Implementación experimental independiente
    La siguiente celda escribe el código completo de BS-k para que puedas leerlo.
    Los módulos geométricos permanecen separados en vendor/app. No necesitas editar código
    para ejecutar el experimento. Cualquier modificación exige volver a medir y documentar
    una nueva versión del método. El algoritmo exacto es este archivo, no solo su nombre.
    """)
    code("%%writefile sp006/beam.py\n" + (ROOT / "sp006/beam.py").read_text(encoding="utf-8"))
    md("""
    ## 9. Ejecutar los seis métodos con la misma entrada
    Cada combinación se ejecuta en un proceso CPU nuevo, secuencialmente, con idéntico JSON,
    reglas, stock y mecanismo geométrico. La segunda repetición invierte el orden de métodos.
    Espera a que aparezcan 36 líneas de progreso; LIMIT/ERROR son resultados incompletos,
    no ceros ni evidencia de imposibilidad geométrica. Los tiempos locales previos no se cargan.
    """)
    code('''
beam_file = Path("sp006/beam.py")
# %%writefile usa CRLF en Windows; normalizar LF conserva el mismo hash del código portable.
beam_file.write_bytes(beam_file.read_text(encoding="utf-8").encode("utf-8"))
from sp006.runner import run_suite, table, deltas, export
CONTEXTO = "colab_cpu" if "google.colab" in sys.modules else "local_notebook_cpu"
bundle = run_suite(repeats=REPETICIONES, context=CONTEXTO)
frame = table(bundle)
display(frame)
print("Entorno de estas mediciones:", bundle["metadata"])
''')
    md("""
    ## 10. Métricas y diferencias respecto de FF/BF/WF
    Definiciones vigentes: material = suma de áreas nominales de fuentes **usadas**;
    aprovechada = suma de áreas nominales persistidas de piezas colocadas;
    aprovechamiento = aprovechada/material × 100, HALF_UP a 0,001 puntos porcentuales.
    Recuperable = un máximo rectángulo raster libre por fuente usada que cumpla los mínimos;
    merma = material − aprovechada − recuperable. Recuperable no equivale a todo el espacio libre.
    Si no se coloca nada, las métricas de área son ausentes, no cero.

    Las áreas originales se validan y redondean HALF_UP a 0,01 mm² como TA-027; incluyen
    círculos y polígonos. El informe muestra unidades faltantes y fuentes físicas, no solo
    porcentajes: un mayor porcentaje con menos piezas colocadas no basta para concluir mejora.
    Las diferencias siguientes son BS menos baseline, usando medianas de repeticiones.
    `delta_utilization_pct_pp` está en **puntos porcentuales**. Un estado LIMIT/ERROR no se compara.
    """)
    code('''
display(deltas(bundle))
for record in bundle["records"]:
    if record["repeat"] == 1:
        print(record["case_id"], record["method"], "no colocadas (pieza, unidad):", record.get("unplaced", "sin resultado"))
''')
    md("""
    ## 11. Ver las planchas, retazos y piezas
    Se dibujan las máscaras realmente aceptadas a 1 mm. Oscuro = exterior, gris = margen,
    naranja = separación reservada, verde discontinuo = recuperable. Las etiquetas indican
    pieza.unidad y giro en grados; se muestran también fuentes sin usar y una galería de
    faltantes. `pend.` distingue unidades sin explorar de NO_FIT demostrado.

    Se guardan imágenes de todos los casos/métodos. Abajo aparecen los tres casos con BS-3.
    Cambia `METODO_PARA_VER` para inspeccionar FF, BF, WF, BS-2 o BS-4 y vuelve a ejecutar la celda.
    """)
    code('''
import matplotlib.pyplot as plt
from sp006.plots import plot_layout, plot_comparison, descriptive_analysis
Path("results/figures").mkdir(parents=True, exist_ok=True)
METODO_PARA_VER = "BS-3"
for record in bundle["records"]:
    if record["repeat"] != 1:
        continue
    fig = plot_layout(record)
    fig.savefig(f"results/figures/{record['case_id']}_{record['method']}.png", dpi=120, bbox_inches="tight")
    if record["method"] == METODO_PARA_VER:
        display(fig)
    plt.close(fig)
''')
    md("""
    ## 12. Comparación gráfica de resultados y recursos
    Cada barra es la mediana de repeticiones del mismo entorno. En piezas colocadas y
    aprovechamiento, más puede ser favorable; en planchas, tiempo y merma, menos puede serlo.
    Observa primero completitud y validez. Dos repeticiones no permiten inferencia estadística
    ni certificar el rendimiento industrial; la RSS puede variar aunque el layout sea idéntico.
    """)
    code('''
fig = plot_comparison(frame)
fig.savefig("results/figures/comparison.png", dpi=120, bbox_inches="tight")
display(fig)
plt.close(fig)
''')
    md("""
    ## 13. ¿Se repite exactamente la solución?
    Comparamos hashes de placements, métricas, prefijo procesado, estado y traza, excluyendo
    tiempo y memoria. `True` indica igualdad observada; no una demostración para toda entrada.
    Si hubo límite, se informa desconocido: un corte por reloj puede depender de la máquina.
    También se comprueba que el stock y los datos de entrada no cambiaron.
    """)
    code('''
display(frame[["case_id", "method", "repeat", "status", "deterministic", "geometry_valid"]])
print("Entradas intactas:", all(r.get("input_unchanged", False) for r in bundle["records"]))
for case_id in CASES:
    selected = [r for r in bundle["records"] if r["case_id"] == case_id and r["repeat"] == 1 and "placements" in r]
    baselines = [r["placements"] for r in selected if r["method"] in ("FF", "BF", "WF")]
    for record in selected:
        if record["method"].startswith("BS-"):
            print(case_id, record["method"], "layout distinto de los tres baselines:", record["placements"] not in baselines)
''')
    md("""
    ## 14. Pruebas de reglas y límites
    Además de revalidar **todos** los placements medidos, se ejecutan controles positivos y
    negativos: margen, separación, superposición, rotación 5°, retazo prioritario e interrupción
    de búsqueda. Las variaciones pequeñas de prueba son controles sintéticos y no reemplazan
    los fixtures oficiales. Un fallo detiene esta celda y debe investigarse antes de decidir.
    La prueba local adicional contra imports del repositorio original se documenta fuera
    del cuaderno; Colab solo puede verificar la copia incluida y sus hashes.
    """)
    code('''
from sp006.checks import self_checks
display(pd.DataFrame(self_checks()))
display(pd.DataFrame([dict(caso=r["case_id"], metodo=r["method"], repeticion=r["repeat"],
    **r.get("validation", {})) for r in bundle["records"]]))
display(pd.DataFrame([dict(caso=r["case_id"], metodo=r["method"], **r.get("search_statistics", {}))
    for r in bundle["records"] if r["repeat"] == 1 and r["method"].startswith("BS-")]))
''')
    md("""
    ## 15. Exportar CSV/JSON e imágenes
    JSON conserva posiciones, ángulos, identidades sintéticas, auditoría y metadatos;
    CSV facilita abrir la tabla en Excel; otro CSV conserva las diferencias con cada baseline.
    Las mediciones se identifican como `measured_colab_cpu` cuando se ejecuta en Colab.
    No se importan resultados históricos. El ZIP permite descargarlos juntos desde el panel
    de archivos. La descarga automática es opcional para evitar diálogos durante Ejecutar todas.
    """)
    code('''
target = export(bundle, "results")
import shutil
shutil.make_archive("SP-006_resultados", "zip", target)
print("Exportado: results/results.csv, results/results.json, results/deltas-vs-baselines.csv, figures/")
print("ZIP: SP-006_resultados.zip (panel de archivos → menú del archivo → Descargar)")
DESCARGAR_AHORA = False
if DESCARGAR_AHORA and "google.colab" in sys.modules:
    from google.colab import files
    files.download("SP-006_resultados.zip")
''')
    md("""
    ## 16. Análisis descriptivo automático
    El texto resume diferencias medidas, sin declarar un ganador. Una distribución distinta
    demuestra comportamiento propio solo para esa entrada. Si no hay mejora, se dice por los
    valores; si hay un intercambio de costo/calidad, se debe evaluar explícitamente.
    """)
    code('''
analysis = descriptive_analysis(frame)
print(analysis)
Path("results/analysis.txt").write_text(analysis + "\\n", encoding="utf-8")
# Actualizar el ZIP para incluir también el análisis.
shutil.make_archive("SP-006_resultados", "zip", "results")
''')
    md("""
    ## 17. Mis conclusiones de SP-006 — completar después de observar
    - Fecha y entorno de ejecución:
    - ¿Todas las reglas y repeticiones resultaron válidas? ¿Hubo LIMIT/ERROR?:
    - ¿Qué decisiones de M6 son distintas? Anotar caso, fuente, posición o giro:
    - ¿Qué mejoró frente a cada baseline y qué empeoró? Incluir piezas y fuentes:
    - ¿Cuánto tiempo/memoria adicional cuesta? ¿Es aceptable para el uso previsto?:
    - ¿k=2, 3 o 4 aporta una diferencia suficiente para su costo?:
    - Limitaciones y datos adicionales necesarios:
    - Decisión personal: aceptar como candidata / ajustar y repetir / descartar / inconcluso:
    - Justificación y archivos de resultados que sustentan la decisión:

    No hay umbrales de aceptación de M6 ni SLA experimental SP-006 aprobados en el repositorio
    auditado. Tampoco hay casos oficiales adicionales a escala industrial ni presupuesto
    productivo aprobado para esta nueva búsqueda. No se inventan esos criterios.
    Incluso con mejoras en estos fixtures, conviene revisar nuevas instancias representativas
    versionadas antes de generalizar. **TA-053 T01/T02 sigue pendiente de autorización posterior.**
    """)
    notebook = dict(cells=cells, metadata={"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.11"}, "colab": {"name": "SP-006_M6_Beam_Search.ipynb", "provenance": []}},
        nbformat=4, nbformat_minor=5)
    # IDs estables admitidos por nbformat 4.5.
    for index, cell in enumerate(cells):
        cell["id"] = f"sp006-{index:02}"
        cell["source"] = cell["source"].splitlines(keepends=True)
    (ROOT / "SP-006_M6_Beam_Search.ipynb").write_text(
        json.dumps(notebook, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    # ZIP de entrega opcional incluye documentación, fuentes legibles y notebook.
    with zipfile.ZipFile(ROOT / "SP-006_M6_Colab.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for path in paths + [ROOT / "SP-006_M6_Beam_Search.ipynb", *sorted(ROOT.glob("*.md"))]:
            archive.write(path, path.relative_to(ROOT).as_posix())
    print(f"Notebook: {len(cells)} celdas; payload {len(payload)} bytes.")


if __name__ == "__main__":
    build()
