# SP-004 — Evidencia experimental de Filler

## Responsable

Andro Joseph Quispe Cesias.

## Objetivo

Contrastar una política experimental Filler con FF, BF y WF sobre los tres fixtures congelados de TA-027. Filler se mantiene en `experiments/optimization/filler`; no se integra al flujo productivo.

## Entorno

- Repositorio: rama `spike/S2-SP004-filler`.
- Commit base: `afd5f85f9dd1495e4237e1029555f7e56cd53f30`.
- Entorno local de ejecución: Windows, Python 3.11.15, entorno virtual `.venv`.
- Fixtures: `EXP-SMALL-001`, `EXP-MEDIUM-001`, `EXP-COMPLEX-001` cargados mediante `experiments/optimization/loader.py`.
- Configuración: resolución 1 mm, paso angular 5°, margen y separación definidos por cada JSON. Se conservan material, espesor, geometrías, retazos, planchas y límites de residuos.
- Ejecución: secuencial; FF, BF, WF y Filler terminan antes de liberar referencias y continuar. No se usó multiprocessing.

La progresión Filler reutiliza los candidatos geométricos, orientaciones, RasterCache, layouts, colisiones y `calculate_metrics` existentes. El contrato de `pack()` no ofrece una fuente activa persistente durante una búsqueda entre piezas, por lo que el Spike contiene una progresión aislada propia en `filler_experimental.py`. No se modificó producción.

## Procedimiento reproducible

Desde la raíz del repositorio, con sus dependencias instaladas:

```powershell
.venv/Scripts/python experiments/optimization/filler/run_benchmark.py
.venv/Scripts/python experiments/optimization/colab/create_sp004_filler_notebook.py
.venv/Scripts/python experiments/optimization/filler/create_figure.py
.venv/Scripts/python -m pytest experiments/optimization/filler/test_filler.py backend/tests/unit/optimization/test_first_fit.py backend/tests/unit/optimization/test_best_fit.py backend/tests/unit/optimization/test_worst_fit.py -q
```

El notebook [SP004-Filler-descartado.ipynb](../../../../experiments/optimization/colab/SP004-Filler-descartado.ipynb) contiene 36 secciones principales, 30 celdas de Python y salidas ejecutadas localmente. Para correrlo en Google Colab, abre una copia de NewGlass en `/content/NewGlass` o ejecuta el notebook con el repositorio como carpeta actual; después puedes ejecutar todas las celdas de nuevo. Esta sesión no tiene conexión a un kernel de Google Colab, así que las salidas guardadas corresponden a la ejecución local indicada y no a una ejecución remota de Colab.

## Resultados observados

Los cuatro métodos colocaron todas las unidades solicitadas en los tres casos.

| Caso | Método | Colocadas | Retazos | Planchas | Aprovechamiento | Merma (mm²) | Tiempo local (ms) |
|---|---|---:|---:|---:|---:|---:|---:|
| SMALL | FF | 3/3 | 1 | 1 | 60.000% | 0.00 | 11.005 |
| SMALL | BF | 3/3 | 1 | 1 | 60.000% | 0.00 | 10.625 |
| SMALL | WF | 3/3 | 1 | 1 | 60.000% | 0.00 | 10.554 |
| SMALL | Filler | 3/3 | 1 | 1 | 60.000% | 0.00 | 10.581 |
| MEDIUM | FF | 9/9 | 2 | 1 | 28.413% | 201.86 | 20.021 |
| MEDIUM | BF | 9/9 | 2 | 1 | 28.413% | 193.86 | 25.160 |
| MEDIUM | WF | 9/9 | 2 | 2 | 18.584% | 301.86 | 18.221 |
| MEDIUM | Filler | 9/9 | 2 | 1 | 28.413% | 201.86 | 21.335 |
| COMPLEX | FF | 24/24 | 3 | 3 | 29.598% | 746.72 | 89.855 |
| COMPLEX | BF | 24/24 | 3 | 3 | 29.598% | 746.72 | 92.320 |
| COMPLEX | WF | 24/24 | 3 | 4 | 25.309% | 886.72 | 87.516 |
| COMPLEX | Filler | 24/24 | 3 | 3 | 29.598% | 746.72 | 99.183 |

Filler coincide con FF en fuentes utilizadas y aprovechamiento en los tres fixtures. En MEDIUM, BF conserva el aprovechamiento de FF/Filler y reduce merma reportada en 8 mm²; en COMPLEX, BF coincide en las métricas listadas. WF utilizó una plancha adicional en MEDIUM y COMPLEX, con menor aprovechamiento. Los datos no muestran una mejora general de Filler en estos casos.

## Determinismo

Filler se ejecutó tres veces por fixture y produjo firmas idénticas de placements, coordenadas, rotaciones, orden de colocación, skips y cambios de fuente: SMALL PASS, MEDIUM PASS y COMPLEX PASS. El tiempo no forma parte de la firma.

## Pruebas

Comando ejecutado:

```powershell
.venv/Scripts/python -m pytest experiments/optimization/filler/test_filler.py backend/tests/unit/optimization/test_first_fit.py backend/tests/unit/optimization/test_best_fit.py backend/tests/unit/optimization/test_worst_fit.py -q
```

Resultado: **84 passed**. Cubre orden y desempate, skip y selección de pieza posterior, mantenimiento y cambio de fuente, prioridad de retazo, compatibilidad de material/espesor, margen, separación, rotación, determinismo, no solapamiento por `SheetLayout` y no mutación del fixture; además ejecuta las suites unitarias existentes de FF/BF/WF. Pytest emitió una advertencia de permisos al intentar actualizar `.pytest_cache`; no afectó las pruebas.

## Archivos de evidencia

- Resultados tabulares: [sp004_filler_descartado_results.csv](benchmark-results/sp004_filler_descartado_results.csv).
- Trazas y placements: [sp004_filler_descartado_trace.json](benchmark-results/sp004_filler_descartado_trace.json).
- Notebook Colab ejecutado localmente: [SP004-Filler-descartado.ipynb](../../../../experiments/optimization/colab/SP004-Filler-descartado.ipynb).
- Investigación y revisión bibliográfica: [SP-004-filler-candidato-descartado.md](../../../spikes/SP-004-filler-candidato-descartado.md).
- Figura monocroma: [SP-004-filler-example.png](../../../spikes/assets/SP-004-filler-example.png).

## Limitaciones observadas

- Solo se estudiaron los tres fixtures congelados; no se generaliza a la distribución de pedidos reales.
- Filler hace intentos repetidos sobre piezas pendientes y el tiempo observado crece respecto de FF/BF en COMPLEX; estas muestras son cortas y dependientes del equipo.
- SMALL es homogéneo y no distingue las políticas.
- La factibilidad está discretizada al raster de 1 mm y mantiene los límites existentes del motor.
- El nombre Filler se usa en la literatura para una política de selección cuya implementación concreta depende de la heurística de colocación emparejada; aquí se documenta explícitamente la variante contrastada.
- El notebook fue ejecutado localmente con los mismos módulos y fixtures; Andro debe volver a ejecutarlo en Colab para reproducirlo en ese entorno.
