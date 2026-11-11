"""Regenera gráficos documentales; no ejecuta pruebas ni benchmarks del producto."""
import collections
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent
def read(name):
    return json.loads((ROOT / name).read_text(encoding='utf-8'))

plt.rcParams.update({'font.size': 11, 'axes.spines.top': False,
                     'axes.spines.right': False, 'figure.facecolor': 'white'})
BLUE = '#176b91'
ORANGE = '#d97924'
def save(name, note):
    plt.figtext(.02, .015, note, fontsize=9, color='#465260')
    plt.tight_layout(rect=(0, .07, 1, 1))
    plt.savefig(ROOT / name, dpi=180, facecolor='white')
    plt.close()

metrics = read('metricas-consolidadas.json')
counts = collections.Counter(m['estado'] for m in metrics)
states = ['CUMPLE META', 'NO CUMPLE META', 'PENDIENTE DE BASELINE',
          'RESULTADO PARCIAL', 'NO MEDIDA']
fig, ax = plt.subplots(figsize=(11, 5.5))
bars = ax.barh(states[::-1], [counts[s] for s in states[::-1]], color=BLUE)
ax.bar_label(bars, padding=4)
ax.set_xlim(0, 14)
ax.set_xlabel('Número de métricas (26 en total)')
ax.set_title('TA-QA-010 · Estado de las métricas', loc='left', fontweight='bold')
save('01_Resumen_metricas.png', 'Fuente: matriz consolidada. 20 tienen algún resultado, incluidos parciales; no equivale a 20 mediciones completas.')

fig, ax = plt.subplots(figsize=(11, 5.5))
labels = ['TA-QA-003\nJUnit dirigido', 'TA-QA-008\nCompatibilidad',
          'E2E por fases\nReporte QA-008', 'TA-QA-006\nLocal Windows']
passed = [50, 72, 148, 306]
skipped = [0, 0, 0, 3]
bars = ax.bar(labels, passed, color=BLUE, label='PASS reportados/verificados según fuente')
ax.bar(labels, skipped, bottom=passed, color=ORANGE, label='Omitidos')
ax.bar_label(bars, padding=4)
ax.set_ylim(0, 360)
ax.set_ylabel('Casos por suite (sin total acumulado)')
ax.set_title('Resultados de suites independientes', loc='left', fontweight='bold')
ax.legend(loc='upper left', fontsize=9)
save('02_Resultados_calidad.png', 'Fuentes E02/E04/E09. FAIL: 0 en estas corridas. E2E y seguridad: resúmenes documentales; suites pueden solaparse.')

compat = read('compatibilidad-consolidada.json')
fig, ax = plt.subplots(figsize=(11, 6))
bars = ax.barh(list(compat), list(compat.values()), color=BLUE)
ax.bar_label(bars, padding=4)
ax.set_xlim(0, 11)
ax.set_xlabel('Pruebas aprobadas por combinación')
ax.set_title('Compatibilidad · Chrome y Edge (72/72)', loc='left', fontweight='bold')
save('03_Compatibilidad.png', 'Fuente E03: JSON del frontend independiente. Viewports móviles/tablet emulados; no dispositivos físicos.')

perf = read('rendimiento-consolidado.json')
methods = ['FF', 'BF', 'WF', 'HF', 'M5', 'M6-BS']
sizes = [10, 25, 50, 100, 150, 200]
lookup = {(p['motor'], p['piezas']): p for p in perf}
fig, ax = plt.subplots(figsize=(11, 6))
for method in methods:
    ax.plot(sizes, [lookup[method, n]['p50_s'] for n in sizes], marker='o', label=method)
ax.axhline(120, color='#777777', linestyle='--', linewidth=1, label='Checkpoint declarado 120 s')
ax.set_xticks(sizes)
ax.set_xlabel('Piezas del dataset de Luis')
ax.set_ylabel('Tiempo hasta terminación · p50 (s), n=3')
ax.set_title('Duración por carga · incluye terminaciones parciales', loc='left', fontweight='bold')
ax.legend(ncols=4, fontsize=9)
save('04_Tiempos_por_carga.png', 'Fuente E05. No representa latencia E2E ni p95. M6/150 tuvo máximo 272,906 s; ver causas y tabla del informe.')

fig, ax = plt.subplots(figsize=(11, 6))
for method in methods:
    ax.plot(sizes, [lookup[method, n]['rss_proceso_mib'] for n in sizes], marker='o', label=method)
ax.set_xticks(sizes)
ax.set_xlabel('Piezas del dataset de Luis')
ax.set_ylabel('Pico máximo de RSS del proceso (MiB)')
ax.set_title('Memoria observada por carga y motor', loc='left', fontweight='bold')
ax.legend(ncols=3)
save('05_Memoria_por_carga.png', 'Fuente E05. Máximo de tres corridas; sondeo declarado 40 ms. No incluye suma sincronizada de descendientes (MP-04).')

fig, ax = plt.subplots(figsize=(10, 6))
grid = np.array([[lookup[m, n]['completas_reportadas'] for n in sizes] for m in methods])
ax.imshow(grid, cmap='Blues', vmin=0, vmax=3, aspect='auto')
for i in range(len(methods)):
    for j in range(len(sizes)):
        ax.text(j, i, f'{grid[i,j]}/3', ha='center', va='center',
                color='white' if grid[i,j] > 1 else '#222222', fontsize=14)
ax.set_xticks(range(len(sizes)), sizes)
ax.set_yticks(range(len(methods)), methods)
ax.set_xlabel('Piezas del dataset de Luis')
ax.set_title('Finalización reportada · COMPLETED y todas las piezas', loc='left', fontweight='bold')
save('06_Finalizacion_por_carga.png', 'Fuente E05. No sustituye validación geométrica independiente de MP-05/06; ningún motor completa 200 en este dataset.')

raw = read('rendimiento-fuente.json')
reasons = collections.Counter(r['reason'] for group in raw.values() for v in group.values() for r in v['raw_runs'])
fig, ax = plt.subplots(figsize=(11, 5.5))
bars = ax.barh(list(reasons), list(reasons.values()), color=[BLUE, ORANGE, ORANGE, ORANGE])
ax.bar_label(bars, padding=4)
ax.set_xlim(0, 95)
ax.set_xlabel('Ejecuciones (108 en total)')
ax.set_title('Terminaciones reales · 27 interrupciones', loc='left', fontweight='bold')
save('07_Motivos_terminacion.png', 'Fuente E05, raw_runs. 81 COMPLETED, 19 TIME_BUDGET_EXCEEDED, 5 TIME_LIMIT y 3 STATE_MEMORY_LIMIT.')
