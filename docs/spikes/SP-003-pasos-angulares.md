# SP-003 — comparación angular POST-PR58

Responsable: Andro Quispe. Base: 783aac8. Algoritmo fijo: FF.
Reproducción desde raíz:
`.venv/Scripts/python experiments/raster/scripts/sp003_angles.py`.
Entrada completa versionada en instance() del script; resultados en
../evidence/sprint-02/SP-003/results.json.

Se eligen 90° (rectángulos/cuarto de vuelta), 45° (polígono diagonal),
15° (exploración más fina, incluye 45°). Misma instancia de tres piezas,
mismo retazo 10×4 y plancha 12×12, resolución 1 mm, margen/separación 0,
orden y umbral residual 1×1 mm. Solo cambia angular_step_deg.

| Paso | Orientaciones preparadas | Búsquedas de posición | Candidatos factibles | Colocadas | Uso % | Merma mm² | Recuperable mm² | Mediana ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
|90|6|3|3|3|20.652|78|68|1.827|
|45|12|9|3|3|20.652|16|130|3.449|
|15|32|18|3|3|20.652|16|130|16.789|

Orientaciones preparadas = suma por unidad después de deduplicar.
Búsquedas = llamadas reales a first_position, excluye orientaciones rechazadas
por bbox. Candidatos = yields consumidos por FF. No equivalen a todas las
posiciones raster ni a todas las fuentes potenciales.
Instrumentación local al experimento, retirada antes de medir cinco ejecuciones
con cache fresca. Se comprueba igualdad de resultados en las cinco.
Tiempo solo del optimizador, sin métricas ni instrumentación. Memoria no medida:
la infraestructura no tenía telemetría de memoria. Python 3.11.15, Windows;
datos temporales sujetos a variación del equipo, sin extrapolar a producción.

45° permite que el polígono entre en el retazo a 135°; las otras piezas van a
plancha. 90° usa plancha para el polígono y retazo para rectángulos.
Se usa la misma superficie total (184 mm²), por eso el aprovechamiento no cambia,
aunque mejora la superficie recuperable. Merma = material - piezas - recuperable.
No confundir merma con todo el sobrante.

Recomendación para esta instancia: 45°. 15° no aporta mejora y tarda más.
No cambiar el valor global: una instancia sintética no demuestra óptimo universal.
90° sigue siendo una base económica para piezas ortogonales; evaluar otras
instancias industriales antes de una recomendación general.

