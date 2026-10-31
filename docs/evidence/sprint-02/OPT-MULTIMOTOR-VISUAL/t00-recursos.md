# OPT-MULTIMOTOR-VISUAL — Medición agregada inicial

Autor: Fabricio Melendez Quezada.
Revisor asignado: Andro Quispe; revisión pendiente.
Fecha: 31/10/2026.
Estado: evidencia adicional de T00; presupuesto productivo pendiente.

## Reproducción

Código medido: `795c5881d0553d6aaf001cfa52200b995489dfc1`,
`test(optimization): medir recursos de tres motores concurrentes`.
Desde la raíz:

```text
PYTHONDONTWRITEBYTECODE=1 backend/.venv/bin/python -B experiments/optimization/probe_concurrency.py --resource-cases
```

Se conserva la barrera instrumentada, tres PID distintos, hash común y cotejo
de resultados/métricas/remanentes contra cada ejecución directa. Ahora se usa
el codec de entrada versionado y se mide el tamaño de resultados V2. No hay
conexiones DB ni escrituras de inventario.

Entorno: Linux, Python 3.11.9; cgroup `memory.max: 8589934592` (8 GiB),
`cpu.max: 200000 100000` (dos núcleos de cuota). No representa el despliegue.

## Resultados

La salida completa está en [t00-resources.json](t00-resources.json).
El agregado corresponde al supervisor y los tres trabajadores conocidos,
leídos desde `/proc/{pid}/statm`. Se exige observar los cuatro procesos; no se
usa un recorrido de descendientes que pueda omitirlos en un procfs restringido.

| Caso | Unidades | Máximo de sumas RSS muestreadas (MiB) | Muestras | Procesos observados | Entrada JSON (bytes) | Mayor resultado JSON (bytes) |
|---|---:|---:|---:|---:|---:|---:|
| EXP-SMALL-001 | 3 | 79.90 | 17 | 4 | 1044 | 2654 |
| EXP-MEDIUM-001 | 9 | 80.68 | 16 | 4 | 2341 | 6684 |
| EXP-COMPLEX-001 | 24 | 83.79 | 23 | 4 | 5445 | 17128 |
| T00-UNITS-150 | 150 | 85.22 | 53 | 4 | 33151 | 102865 |
| T00-STOCK-50 | 12 | 84.02 | 16 | 4 | 11158 | 16941 |
| T00-VERTICES-128 | 8 | 86.74 | 51 | 4 | 23046 | 68531 |
| T00-GRID-4M | 1 | 88.75 | 20 | 4 | 576 | 1319 |

En los siete casos los tres resultados coincidieron con su respectivo cálculo
directo. Los cuatro escenarios adicionales ejercitan, por separado, 150 unidades,
50 unidades físicas de stock, un polígono convexo de 128 vértices y una plancha
de 2000 × 2000 celdas. El stock repetido comparte bases según el comportamiento
real del motor. No modifica los casos congelados TA-027.

## Interpretación y pendientes

El intervalo solicitado es 10 ms. El mayor intervalo observado en esta corrida
fue 43.56 ms: el scheduler y las lecturas no garantizan periodicidad exacta.
La suma RSS incluye páginas compartidas varias veces y las lecturas de PID son
sucesivas. El máximo muestreado puede omitir picos y no es memoria física única
ni la suma de máximos independientes de `ru_maxrss`.

Se excluyen el proceso auxiliar `resource_tracker`, el servidor web, colas de
eventos/máscaras productivas y retención visual. Los límites se ejercitan por
separado; no se prueba el máximo de formas diferentes ni tres cachés/layouts
simultáneamente saturados. Los tiempos siguen incluyendo las barreras y no
sirven para ordenar motores.

Esta evidencia amplía la viabilidad, pero **no cierra T00**. Antes de conectar el
runner deben fijarse y probarse presupuesto total, colas, retención visual,
timeout global y rechazo/terminación ante excesos. No extrapolar los 88.75 MiB
observados a una garantía para cualquier lote permitido ni a capacidad remota.

Regresión de codecs, tres motores y casos congelados: **123 passed in 1.80s**.
