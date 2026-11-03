# Evidencia TA-042 — T01/T02

Autor y revisor académico designado: Andro Joseph Quispe Cesias. Revisión formal pendiente. Implementación: `backend/app/modules/optimization/domain/hole_filling.py`. Pruebas: `backend/tests/unit/optimization/test_hole_filling.py`. Las reglas, presupuesto y limitaciones están en la SPEC TA-042.

## Suite específica histórica (versión dc32a22f)

Desde `backend`:

```text
python -m pytest tests/unit/optimization/test_hole_filling.py -q -ra
23 passed, 0 failed, 0 skipped
```

Cubre fallback y rectángulos; pockets de los diagnósticos con círculo y polígonos de SP-004; diferenciación integrada 9/9 respecto a FF; 5°, margen, separación, material, espesor, retazo primero, determinismo, callbacks, presupuestos y no mutación. La protección de cobertura prueba un caso mixto independiente inspirado en HF-REALISTIC-003: la pasada exploratoria coloca 10/18, FF 11/18 y el resultado protegido devuelve exactamente FF con 11/18. Otro caso comprueba conservación de identidades incluso con igual cantidad.

Del spike se reutilizan los layouts presembrados `HF-DIAGNOSTIC-001/002/003` y su validación legal como pruebas de regla. Las mediciones y el orden pocket-first del prototipo son evidencia experimental, no código trasladado. El detector exhaustivo por todas las piezas/orientaciones y sus expectativas de conteo son obsoletos para el diseño acotado y no se copiaron. El caso integrado diferenciado y el caso de cobertura son fixtures nuevos, no resultados de SP-004 ni TA-027.

## Regresiones dirigidas históricas (versión dc32a22f)

Desde `backend`; los grupos son suites distintas y sus conteos no se presentan como un total aditivo.

```text
python -m pytest tests/unit/optimization/test_first_fit.py tests/unit/optimization/test_best_fit.py tests/unit/optimization/test_worst_fit.py tests/unit/optimization/test_retazo_priority.py -q -ra
102 passed, 0 failed, 0 skipped

python -m pytest tests/optimization/test_placement.py tests/optimization/test_raster_mask.py tests/optimization/test_rasterize_material.py tests/optimization/test_rasterize_polygon.py tests/optimization/test_rasterize_standard.py tests/unit/optimization/test_commercial_raster.py -q -ra
143 passed, 0 failed, 0 skipped

python -m pytest tests/unit/modules/orders/domain/test_domain_geometry.py tests/unit/optimization/test_rotation.py tests/unit/optimization/test_run_geometry.py tests/unit/optimization/test_sprint2_angles.py -q -ra
78 passed, 0 failed, 0 skipped

python -m pytest tests/unit/optimization/test_common_rules.py tests/unit/optimization/test_metrics.py tests/unit/optimization/test_preparation.py -q -ra
36 passed, 0 failed, 0 skipped

python -m pytest tests/unit/optimization/test_experimental_cases.py -q -ra
23 passed, 0 failed, 0 skipped
```

El primer intento de FF/BF/WF falló por un BOM UTF-8 en el archivo nuevo (101 passed, 1 failed); se retiró y la repetición completa produjo el resultado 102/0/0 anterior.

## Medición histórica (versión dc32a22f)

Desde la raíz: `python docs/evidence/sprint-02/TA-042/measure_hole_filling.py`. Python 3.11.15, una ejecución de calentamiento y mediana de cinco ejecuciones seriales por método y caso, sin callbacks. `measurements.json` contiene los datos. Se usa FF como baseline; no son umbrales de aceptación ni una comparación estadística general.

| Caso | HF ms | FF ms | HF/FF | Pocket final | Fallbacks | Mapas | Anclajes | Checks placement |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| Rectángulos, fallback | 0,474 | 0,482 | 0,98× | No | 3 | 0 | 0 | 0 |
| Mixto, pocket | 17,795 | 2,093 | 8,50× | Sí | 8 | 8 | 1.734 | 3.468 |
| EXP-SMALL-001 | 10,516 | 11,823 | 0,89× | No | 3 | 0 | 0 | 0 |
| EXP-MEDIUM-001 | 20,424 | 17,170 | 1,19× | No | 9 | 4 | 502 | 844 |
| EXP-COMPLEX-001 | 96,866 | 86,792 | 1,12× | No | 24 | 8 | 1.665 | 2.898 |

El caso mixto colocó 9/9 en ambos métodos; SMALL 3/3, MEDIUM 9/9 y COMPLEX 24/24. En COMPLEX se agotó el máximo de ocho mapas y se continuó con FF. `placement_checks` cuenta llamadas a `SheetLayout.check`, no placements aceptados. El presupuesto limita operaciones de detección, pero no garantiza un ratio temporal máximo para toda entrada; FF adicional de cobertura y reproducción con callbacks tienen costo propio.

## Auditoría anterior: REQUERÍA AJUSTE (commit 1cff0aa2)

La revisión anterior encontró dos bloqueos conceptuales: el diseño de filtros y mapa global excluye el caso de capacidad de SP-004 a escala, y la protección por identidad permite usar más planchas con igual cobertura. En esa auditoría no se cambió el motor ni se repitieron benchmarks. El ajuste posterior se documenta más abajo; la revisión formal de Andro permanece pendiente.

En el commit histórico `1cff0aa2`, desde `backend`, se ejecutó la versión anterior del archivo de caracterización:

```text
python -m pytest ../docs/evidence/sprint-02/TA-042/test_final_audit.py -q -ra
14 passed, 0 failed, 0 skipped
```

Eran **pruebas de caracterización de la implementación anterior**, no una aprobación de sus limitaciones; el archivo actual fue convertido a regresiones del ajuste. Cubren el límite exacto de 1.024 anclajes/mapa, 8 mapas y 8.192 anclajes; presupuesto agotado; fronteras de fuente circular y poligonal; 0° frente a pocket a 5°; cambio de resolución; eventos y no mutación; determinismo en tres caminos; y el contraejemplo de planchas.

| Evidencia | Resultado actual |
| --- | --- |
| HF-CAPABILITY-001 P11, 32 × 32 mm, 1 mm/celda | 1.024 celdas y 32 filas: excluido por límites 64 y 16. Subirlos no basta: el mapa tiene 60.507 anclajes y supera 1.024. |
| Misma pieza 8 × 8 mm y fuente 24 × 24 mm | A 0,5 mm no activa; a 1 y 2 mm sí activa. |
| SP-004 HF-REALISTIC-001 / 002 / 003 | Áreas mínimas de pieza de 1.050 / 2.200 / 2.000 mm²; tamaños de fixtures, no requisitos comerciales. |
| Subconjunto de HF-DIAGNOSTIC-001, semillas 1, 4, 5 y 6 | A 0° FF permanece en fila 0, columna 0; el pocket legal de 5° está en fila 13, columna 7 y no se explora por la política actual. |
| Caso sintético, retazo 14 × 14 mm, planchas 18 × 18 mm, 13 piezas | HF y FF 13/13; HF 1 plancha y FF 0. Merma 61,74 vs 27,74 mm²; recuperable 294 vs 4 mm². |

Para igual conjunto de identidades, se recomienda estudiar un guard que rechace más planchas nuevas sin elegir automáticamente por merma. Cuando HF añade piezas respecto de FF, la prioridad de cobertura y el costo de planchas adicionales deben evaluarse explícitamente. La solución del problema de escala requiere una búsqueda acotada que no dependa de construir el mapa global; cambiar solo 64 a un porcentaje no resuelve el límite de mapa. Ver SPEC y review.


## Resultado vigente después del ajuste

Autor: Andro Joseph Quispe Cesias. Revisión académica de Andro pendiente. T01/T02 están listas para revisión técnica previa al PR. La implementación, criterios y límites vigentes están en SPEC TA-042. Los resultados históricos anteriores y `measurements.json` se conservan sin sobrescribir.

Desde `backend`:

```text
python -m pytest tests/unit/optimization/test_hole_filling.py -q -ra
43 passed, 0 failed, 0 skipped
python -m pytest ../docs/evidence/sprint-02/TA-042/test_final_audit.py -q -ra
7 passed, 0 failed, 0 skipped

python -m pytest tests/unit/optimization/test_first_fit.py tests/unit/optimization/test_best_fit.py tests/unit/optimization/test_worst_fit.py tests/unit/optimization/test_retazo_priority.py -q -ra
102 passed, 0 failed, 0 skipped
python -m pytest tests/optimization/test_placement.py tests/optimization/test_raster_mask.py tests/optimization/test_rasterize_material.py tests/optimization/test_rasterize_polygon.py tests/optimization/test_rasterize_standard.py tests/unit/optimization/test_commercial_raster.py -q -ra
143 passed, 0 failed, 0 skipped
python -m pytest tests/unit/modules/orders/domain/test_domain_geometry.py tests/unit/optimization/test_rotation.py tests/unit/optimization/test_run_geometry.py tests/unit/optimization/test_sprint2_angles.py -q -ra
78 passed, 0 failed, 0 skipped
python -m pytest tests/unit/optimization/test_common_rules.py tests/unit/optimization/test_metrics.py tests/unit/optimization/test_preparation.py -q -ra
36 passed, 0 failed, 0 skipped
python -m pytest tests/unit/optimization/test_experimental_cases.py -q -ra
23 passed, 0 failed, 0 skipped
```

Los grupos son selecciones distintas; no se presentan como un total aditivo. La cobertura degradada 10/18 frente a FF 11/18 sigue protegida. El contraejemplo de 13/13 con plancha adicional se fuerza usando `max_regions=24` sobre el mismo fixture; la protección devuelve FF. Con 8 regiones predeterminadas ese fixture retorna FF sin proponer el pocket. La prueba de superconjunto estricto verifica que una plancha adicional no descarta cobertura superior.

En HF-CAPABILITY-001 se cargan las 16 semillas originales validadas y se ejecuta el recorrido productivo sobre las dos piezas pendientes. El resultado es 18/18 para ambos, M4 con 0 planchas y FF con 1; P11 32 × 32 mm se ubica en (x=51, y=191). La detección aislada de P11 revisa 121 anclajes frente a 60.507 del dominio global. En el caso integrado de siete piezas sobre plancha 80 × 80 mm y paso 5°, M4 y FF completan 7/7 con una plancha: el círculo de diámetro 10 mm se coloca en (47, 24) con M4 y (66, 0) con FF. Es un caso construido y seleccionado entre candidatos deterministas, no una muestra estadística comercial.

### Rendimiento y sensibilidad

`python docs/evidence/sprint-02/TA-042/measure_adjustment.py` desde la raíz; Python 3.11.15, calentamiento y mediana de cinco ejecuciones seriales sin callbacks. Los resultados completos están en `measurements_adjustment.json`. Capability mide solo las dos piezas pendientes y el guard FF desde el mismo layout presembrado, con preparación y cachés calentados fuera del cronómetro; no es comparable como ejecución completa con los demás casos.

| Caso | HF ms | FF ms | Ratio | Pocket final | Fallbacks | Anclajes | Regiones |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Rectángulos, fallback | 0,668 | 0,550 | 1,22× | No | 3 | 0 | 0 |
| Productivo, pocket | 55,411 | 2,238 | 24,76× | Sí | 6 | 4.243 | 8 |
| Mixto anterior | 4,862 | 2,031 | 2,39× | No | 9 | 345 | 8 |
| EXP-SMALL-001 | 10,236 | 10,050 | 1,02× | No | 3 | 0 | 0 |
| EXP-MEDIUM-001 | 18,768 | 16,888 | 1,11× | No | 9 | 205 | 4 |
| EXP-COMPLEX-001 | 87,416 | 86,953 | 1,01× | No | 24 | 257 | 8 |
| HF-CAPABILITY-001, presembrado | 11,592 | 2,502 | 4,63× | Sí | 1 | 377 | 1 |

El caso productivo alcanzó 512 anclajes y 512 comprobaciones nuevas en su región más costosa; el total de 4.243 comprobaciones equivale a 59.431 filas de máscara. En capability se certificaron 60 anclajes del pocket y se hicieron 377 comprobaciones para las dos piezas pendientes. El indicador de presupuesto quedó activo en ambos: no invalida un pocket ya certificado y refleja que otras exploraciones fueron limitadas. Las llamadas finales de `SheetLayout.place`, el FF de protección y una eventual reproducción de eventos no integran ese contador.

En sensibilidad, denominadores 4 y 8 detectaron ambos casos con 8 regiones y 4.243 anclajes en el integrado; 16, 32 y 64 también detectaron ambos con 2 regiones y 487 anclajes; 128 no detectó ninguno. El 1/8 predeterminado mantiene además elegible el rectángulo 8 × 8 mm en fuente 24 × 24 mm (relación 1/9) en las resoluciones 0,5, 1 y 2 ensayadas. Es un parámetro técnico conservador, no un valor comercial u óptimo demostrado.

En un caso sintético distinto, con 15/15 piezas y 2 planchas en ambos métodos, M4 tuvo 2.243,58 mm² de merma y 5.578 mm² recuperables, frente a 2.181,58 y 5.640 mm² de FF. Se deja visible esta dominancia en esas métricas; no se añade una regla rígida por merma para no convertir M4 en selector de métodos. El costo de 24,76× en el caso integrado y las oportunidades perdidas por muestreo y presupuesto siguen siendo limitaciones reales.
