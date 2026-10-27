# SP-003 — comparación angular y contrato operativo de Sprint 2

**Estado: lista para Cierre**. Smoke post-merge del PR #64 aprobado el 27/10/2026
sobre integration `2a76141`. Revisor / Scrum Master: Fabricio Melendez Quezada.
Periodo: 21/10/2026 – 28/10/2026. Pendiente decisión formal del revisor.
[Evidencia de reproducción y criterios finales](../evidence/sprint-02/TA-016/PR64-post-merge-smoke.md).

Responsable: Andro Quispe. Revisión experimental: 2026-10-26.
Base original POST-PR58 783aac8; nueva medición después de integrar 6f2a159.
Algoritmo fijo: FF. Desde raíz:
`.venv/Scripts/python experiments/raster/scripts/sp003_angles.py`.

Los resultados originales 90/45/15 se preservan íntegros en
docs/evidence/sprint-02/SP-003/results-historical-90-45-15.json.
results.json contiene una nueva ejecución completa 90/45/15/5, cinco tiempos
por paso y median_seconds. La función instance() permanece idéntica.
Tres piezas (incluido polígono diagonal), retazo 10×4, plancha 12×12,
resolución 1 mm, margen/separación 0, residual mínimo 1×1 mm y mismo orden.
Solo cambia angular_step_deg.

90° cubre cuartos de vuelta; 45° permite alinear la pieza diagonal; 15° aumenta
la exploración; 5° verifica la granularidad operacional acordada por el equipo.

| Paso | Orientaciones preparadas | Búsquedas posición | Candidatos | Colocadas | Uso % | Merma mm² | Recuperable mm² | Mediana ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
|90|6|3|3|3|20.652|78|68|1.671|
|45|12|9|3|3|20.652|16|130|3.585|
|15|32|18|3|3|20.652|16|130|11.514|
|5|68|24|3|3|20.652|22|124|34.008|

Preparadas = suma por unidad después de deduplicar. A 5° se enumeran 72 ángulos
por pieza antes de deduplicar; no confundir esa secuencia con 68 máscaras
entregadas en total para las tres piezas. Búsquedas = llamadas a first_position,
excluye rechazo bbox; candidatos = yields consumidos por FF, no todas las posiciones.
Tiempo solo del optimizador, cinco ejecuciones con cache fresca sin instrumentación;
se afirma igualdad de resultados en todas. Métricas fuera del cronómetro.
Memoria no medida: no existe instrumentación de memoria en este experimento.
Python 3.11.15, Windows; son mediciones locales pequeñas, no estimaciones industriales.

## Resultado experimental

45° tuvo la mejor relación calidad/costo de esta instancia; 15° no mejoró la calidad.
A 5° la mediana fue 2.954 veces la de 15° (+22.494 ms), preparó 36 orientaciones
adicionales y realizó seis búsquedas más. Merma +6 mm² y recuperable -6 mm².
El polígono entra a 130° en vez de 135°: la primera orientación factible cambia
el patrón. Mayor resolución angular NO garantiza mejorar la heurística voraz.
Aprovechamiento constante: piezas 38 mm² / material usado 184 mm².
Merma = material - piezas - recuperable; no equivale a todo el sobrante.

## Decisión de diseño

Sprint 2 usa **5° para FF/BF/WF** por regla explícita del equipo.
45° fue suficiente en este caso sintético, pero NO es la recomendación operativa.
Se acepta mayor costo de exploración fina sin prometer mejora de calidad.
No se busca el mejor ángulo dentro de una fuente: se mantiene primera orientación
y primera posición factibles, deduplicación por máscara y retazo antes que plancha.
