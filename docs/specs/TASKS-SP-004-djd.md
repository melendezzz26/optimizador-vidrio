# TASKS-SP-004-DJD — Seguimiento

| ID | Tarea | Estado |
|---|---|---|
| SP004-DJD-01 | Renombrar rama local a `spike/S2-SP004-djd` sin eliminar commits de Filler. | Hecha |
| SP004-DJD-02 | Preservar documento, notebook, resultados y trazas Filler como candidato descartado. | Hecha |
| SP004-DJD-03 | Investigar algoritmo 1D, adaptación 2D, variantes y tolerancia `w`. | Hecha |
| SP004-DJD-04 | Crear SPEC/PLAN y registrar su revisión técnica. | Hecha |
| SP004-DJD-05 | Implementar DJD-1/3 experimental con validación geométrica por layouts temporales. | Hecha |
| SP004-DJD-06 | Crear caso discriminante independiente y comparar FF/BF/WF/DJD. | Hecha |
| SP004-DJD-07 | Cubrir poda, tolerancia, combinaciones, compatibilidad, geometría y determinismo con pruebas. | Hecha; 93 pruebas totales aprobadas junto con regresiones |
| SP004-DJD-08 | Ejecutar SMALL, MEDIUM, COMPLEX y caso didáctico; generar CSV/JSON. | Hecha |
| SP004-DJD-09 | Crear y ejecutar notebook `SP004-DJD.ipynb` con 36 secciones explicadas. | Hecha; 31 celdas Python ejecutadas localmente |
| SP004-DJD-10 | Actualizar evidencia, ejecutar regresiones FF/BF/WF y decidir viabilidad GO/NO-GO. | Hecha; NO-GO para TA-042 por costo de COMPLEX |
| SP004-DJD-11 | Crear commits coherentes; detenerse antes de push, PR y merge. | Hecha; commits locales creados y rama no publicada |

## Reevaluación Pair-Block v2

| ID | Tarea | Estado |
|---|---|---|
| SP004-PB2-01 | Auditar las rotaciones cardinales v1, el criterio de bloque y el tamaño de oportunidades antes de cambiar código. | Hecha; informe previo registrado en `SP-004-pair-block-v2-auditoria.md`. |
| SP004-PB2-02 | Usar la grilla común de 5°, preservar máscaras distintas, y medir pruning por compatibilidad, simetría, cotas, fase y offsets. | Hecha; los recortes heurísticos se declaran y contabilizan. |
| SP004-PB2-03 | Aceptar bloques por ahorro positivo de bounding box, manteniendo intactos Filler/DJD y los fixtures TA-027. | Hecha; sin cambios productivos ni modificaciones de fixture. |
| SP004-PB2-04 | Ejecutar FF/BF/WF/Pair-Block v2, casos congelados, determinismo ×3 y notebook con outputs. | Hecha; 6/6 casos deterministas, 12 pruebas Pair-Block aprobadas y 37 celdas notebook ejecutadas. |
| SP004-PB2-05 | Clasificar evidencia y decidir TA-042. | NO-GO; ningún fixture oficial colocó bloque y COMPLEX tardó 20.852× el baseline más rápido. |
| SP004-PB2-06 | Mantener cambios en commits locales; detenerse antes de push/PR/integración. | Hecha; commits de código y evidencia locales; sin push, PR, merge ni integración. |
