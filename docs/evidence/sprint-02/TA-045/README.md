# Evidencia TA-045 — Separación de corte

Base: `7556a700496673d00fe41b6036d69d91d0939959`. Valores de prueba, no comerciales: resolución 1 mm, separación 0 o 1 mm.

## Demostración reproducible

`python -m pytest -q tests/unit/optimization/test_ta045_separation.py`

Dos cuadrados de 2 × 2 mm en una fuente rectangular de 4 × 2 mm: con separación 0 caben los dos adyacentes; con separación 1 mm solo cabe uno. El caso se ejecuta para FF, BF, WF, M4, M5 y M6, tanto con retazo como con plancha. El test también comprueba máscaras mixtas, margen independiente, repetición, una orientación de 5° y comprobación independiente de celdas. El techo de la distancia se prueba con valores pequeños y fracciones.

## Resultados locales

| Suite no solapada | Passed | Failed | Skipped |
|---|---:|---:|---:|
| TA-045 transversal | 20 | 0 | 0 |
| FF/BF/WF | 76 | 0 | 0 |
| M4/M5/M6 | 80 | 0 | 0 |
| Placement, raster, rotación, geometría, reglas, métricas y casos experimentales | 219 | 0 | 0 |
| Comparación, ángulos Sprint 2, raster comercial, preparación y SP-005 M5 | 105 | 0 | 0 |
| Integración FF/BF/WF | 4 | 0 | 1 |

La prueba de integración omitida requiere binarios locales `initdb`/`pg_ctl` de PostgreSQL para un clúster aislado. La ejecución de cada suite es independiente y no se suman selecciones solapadas. TA-043 no estaba integrada en la base auditada; T03 queda pendiente.
