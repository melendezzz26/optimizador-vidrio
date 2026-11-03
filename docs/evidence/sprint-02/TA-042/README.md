# Evidencia TA-042 — T01/T02

Autor y revisor académico designado: Andro Joseph Quispe Cesias. Revisión formal pendiente. Implementación: `backend/app/modules/optimization/domain/hole_filling.py`. Pruebas: `backend/tests/unit/optimization/test_hole_filling.py`. Las reglas, presupuesto y limitaciones están en la SPEC TA-042.

## Suite específica

Desde `backend`:

```text
python -m pytest tests/unit/optimization/test_hole_filling.py -q -ra
23 passed, 0 failed, 0 skipped
```

Cubre fallback y rectángulos; pockets de los diagnósticos con círculo y polígonos de SP-004; diferenciación integrada 9/9 respecto a FF; 5°, margen, separación, material, espesor, retazo primero, determinismo, callbacks, presupuestos y no mutación. La protección de cobertura prueba un caso mixto independiente inspirado en HF-REALISTIC-003: la pasada exploratoria coloca 10/18, FF 11/18 y el resultado protegido devuelve exactamente FF con 11/18. Otro caso comprueba conservación de identidades incluso con igual cantidad.

Del spike se reutilizan los layouts presembrados `HF-DIAGNOSTIC-001/002/003` y su validación legal como pruebas de regla. Las mediciones y el orden pocket-first del prototipo son evidencia experimental, no código trasladado. El detector exhaustivo por todas las piezas/orientaciones y sus expectativas de conteo son obsoletos para el diseño acotado y no se copiaron. El caso integrado diferenciado y el caso de cobertura son fixtures nuevos, no resultados de SP-004 ni TA-027.

## Regresiones dirigidas

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

## Medición descriptiva

Desde la raíz: `python docs/evidence/sprint-02/TA-042/measure_hole_filling.py`. Python 3.11.15, una ejecución de calentamiento y mediana de cinco ejecuciones seriales por método y caso, sin callbacks. `measurements.json` contiene los datos. Se usa FF como baseline; no son umbrales de aceptación ni una comparación estadística general.

| Caso | HF ms | FF ms | HF/FF | Pocket final | Fallbacks | Mapas | Anclajes | Checks placement |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| Rectángulos, fallback | 0,474 | 0,482 | 0,98× | No | 3 | 0 | 0 | 0 |
| Mixto, pocket | 17,795 | 2,093 | 8,50× | Sí | 8 | 8 | 1.734 | 3.468 |
| EXP-SMALL-001 | 10,516 | 11,823 | 0,89× | No | 3 | 0 | 0 | 0 |
| EXP-MEDIUM-001 | 20,424 | 17,170 | 1,19× | No | 9 | 4 | 502 | 844 |
| EXP-COMPLEX-001 | 96,866 | 86,792 | 1,12× | No | 24 | 8 | 1.665 | 2.898 |

El caso mixto colocó 9/9 en ambos métodos; SMALL 3/3, MEDIUM 9/9 y COMPLEX 24/24. En COMPLEX se agotó el máximo de ocho mapas y se continuó con FF. `placement_checks` cuenta llamadas a `SheetLayout.check`, no placements aceptados. El presupuesto limita operaciones de detección, pero no garantiza un ratio temporal máximo para toda entrada; FF adicional de cobertura y reproducción con callbacks tienen costo propio.
