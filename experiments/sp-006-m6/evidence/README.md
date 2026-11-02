# SP-006 — Evidencia local CPU

Las mediciones de este directorio proceden de la ejecución secuencial real del
notebook en un kernel Windows/Python 3.11.9. **No se ejecutó una sesión real de
Google Colab.** El cuaderno limpio entregado no precarga estas mediciones.

- `local-cpu-results.json`: 36 corridas, con placements, áreas, auditoría,
  metadatos del entorno, hashes del código/fixtures y origen
  `measured_local_notebook_cpu`.
- `local-cpu-results.csv`: las mismas corridas en tabla, incluidas repeticiones,
  tiempos y máximo RSS observado por proceso. Sin promediar ni ocultar fallos.
- `local-cpu-deltas-vs-baselines.csv`: 27 comparaciones BS menos FF/BF/WF;
  tiempos por mediana, diferencias de aprovechamiento en puntos porcentuales.
- `local-cpu-analysis.txt`: descripción automática, sin recomendación de ganador.
- `notebook-validation.json`: 31 celdas, 13 de código; ejecución completa,
  36/36 corridas completas, válidas y con soluciones idénticas entre repeticiones;
  19 figuras y exportaciones CSV/JSON/ZIP; cero celdas omitidas.
- Tres PNG seleccionados: layouts exactos de BS-3 sobre SMALL/MEDIUM/COMPLEX.
  Las 18 distribuciones y la comparación se generan en `results/figures/` y el ZIP.
- `validation-lock-windows.txt`: versiones instaladas durante la validación local.
- `pytest.txt`: **47 passed, 14 warnings in 33.70s**, cero fallos/omisiones.
  Las advertencias son deprecaciones de pyparsing usadas por matplotlib; no
  afectan las comprobaciones. Se sustituyó la ruta del equipo por `<repo>` en
  este log para no distribuir rutas personales; el contenido de resultados no cambia.

## Hallazgos acotados a estos fixtures

Todos los métodos colocan 3/3, 9/9 y 24/24 unidades respectivamente. No hay
faltantes geométricos ni unidades pendientes en las corridas seleccionadas.
BS-2/3/4 obtienen la misma calidad final en estas tres entradas, con costo
temporal creciente en MEDIUM y COMPLEX. Eso no garantiza igualdad en otras entradas.

| Caso | Métodos | Planchas / retazos | Aprovechada mm² | Merma mm² | Recuperable mm² | Aprovechamiento % |
|---|---|---:|---:|---:|---:|---:|
| SMALL | FF/BF/WF/BS-2/BS-3/BS-4 | 1 / 1 | 12,00 | 0,00 | 8 | 60,000 |
| MEDIUM | FF | 1 / 2 | 103,14 | 201,86 | 58 | 28,413 |
| MEDIUM | BF | 1 / 2 | 103,14 | 193,86 | 66 | 28,413 |
| MEDIUM | WF | 2 / 2 | 103,14 | 301,86 | 150 | 18,584 |
| MEDIUM | BS-2/BS-3/BS-4 | 1 / 2 | 103,14 | 197,86 | 62 | 28,413 |
| COMPLEX | FF/BF | 3 / 3 | 391,28 | 746,72 | 184 | 29,598 |
| COMPLEX | WF | 4 / 3 | 391,28 | 886,72 | 268 | 25,309 |
| COMPLEX | BS-2/BS-3/BS-4 | 3 / 3 | 391,28 | 655,72 | 275 | 29,598 |

M6 produce decisiones propias en COMPLEX y no invoca optimizadores base. Frente
a FF/BF en COMPLEX, mantiene fuentes y aprovechamiento, con 91 mm² menos de
merma y 91 mm² más de recuperable. En MEDIUM, su merma mejora en 4 mm² frente
a FF pero empeora en 4 mm² frente a BF. Frente a WF usa una plancha menos en
MEDIUM y COMPLEX. No domina a los tres métodos en todos los casos.

El tiempo y la memoria deben leerse en los CSV/JSON de la corrida, no extrapolarse
a NewGlass o Colab. La RSS es muestreada cada 10 ms y puede perder picos breves;
no es una medida del heap exclusivo del algoritmo. No se alcanzaron los límites
por defecto en ninguna de las 36 corridas. Los controles de límites se ejecutan
aparte con presupuestos reducidos, sin presentarlos como casos oficiales nuevos.

## Validación y límites de la conclusión

Las pruebas locales comparan las nueve combinaciones de los motores originales
contra sus copias portables, en procesos con imports distintos: igualdad de
placements y métricas. También comprueban hashes originales, inmutabilidad,
determinismo, geometría, prioridad/fallback de retazos, continuación después de
NO_FIT, independencia de M6 y límites de expansiones, consultas, estados, tiempo
y RSS. La auditoría de cada corrida comprueba todos sus placements y decisiones
de paso a planchas.

Las dependencias fijadas se instalaron en un venv separado; `pip check` no encontró
requisitos rotos. Se descargaron los cuatro wheels directos para Linux x86_64 /
Python 3.12 (numpy 2.2.6, pandas 2.2.3, matplotlib 3.10.1 y psutil 7.0.0).
Esto comprueba disponibilidad, no una ejecución Linux/Colab ni la estabilidad
de todas sus dependencias futuras. El lock Windows es evidencia, no un lock Linux.

La decisión de aceptar, ajustar o descartar M6 corresponde a Fabricio tras
revisar Colab y completar la plantilla. No hay certificación industrial, SLA
aprobado, benchmark productivo ni aprobación para integrar TA-053 T01/T02.

## Entrega Git

Rama independiente `spike/SP-006-m6-beam-search`, creada desde la integración
remota verificada `f9cfd4f`. Implementación experimental y notebook en el commit
local `9f7f420` (`feat(experiments): add portable SP-006 beam search Colab study`).
La evidencia se registra en un commit documental posterior. Todos los cambios
están bajo `experiments/sp-006-m6/`. La referencia
`chore/p0-functional-sanitization` se conserva en `d660ed7`.
No se hicieron push, merge, rebase ni despliegues.
