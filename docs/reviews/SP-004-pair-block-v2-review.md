# Revisión técnica local — Pair-Block v2

## Alcance

Revisión de la reevaluación experimental v2 de SP-004. No es una aprobación para TA-042 ni una revisión externa. Filler y DJD, incluida su evidencia previa, permanecen sin cambios.

## Hallazgos

1. **Contrato angular:** PASS. Las orientaciones provienen de `discrete_angles` y de la caché de rotación/rasterización común; se usa `0°, 5°, …, 355°`. La equivalencia elimina máscaras solo si coinciden ancho, alto y todas las filas binarias.
2. **Compatibilidad e identidad:** PASS. Las parejas se generan dentro de grupos de igual material y espesor. El bloque es una máscara temporal y cada resultado conserva dos placements con identidad, giro y coordenadas individuales.
3. **Separación y colisión:** PASS. La comprobación raster de separación reproduce la dilatación cuadrada de `SheetLayout`; los placements finales usan layouts comunes y el fallback vuelve a las piezas individuales.
4. **Criterio:** PASS con limitación. El bloque requiere ahorro positivo del bounding box frente a las cajas separadas. Es una adaptación local; la literatura consultada respalda la complementariedad, no esta fórmula.
5. **Pruning:** PASS en trazabilidad; limitación aceptada. Compatibilidad, máscaras equivalentes, cotas, selección de fase y offsets se cuentan. La selección de fase y la grilla inicial de offsets son heurísticas y pueden omitir combinaciones válidas dependientes de la rasterización.
6. **Fixtures:** PASS. No se modificaron los tres fixtures oficiales TA-027. Los dos diagnósticos tienen intención y geometría congeladas antes de ejecutar métodos.
7. **Determinismo:** PASS. SMALL, MEDIUM, COMPLEX, discriminante y ambos diagnósticos pasaron tres ejecuciones cada uno.
8. **Aislamiento:** PASS. El código nuevo está bajo `experiments/optimization/block_packing`; no hubo cambios productivos, push, PR, merge ni integración de TA-042.

## Verificación de resultados

- Pruebas específicas: **12/12 PASS**, incluyendo material/espesor, ángulos de 5°, máscaras diferentes con la misma caja, separación, fallback, identidad, fixture no mutado, clasificación A–E y regresiones FF/BF/WF.
- Notebook `SP004-Block-Packing.ipynb`: **37 celdas de código ejecutadas, cero errores**, outputs del benchmark v2 y tres figuras generadas desde el CSV real.
- Ningún fixture oficial colocó un bloque. SMALL se clasificó D; MEDIUM y COMPLEX, E. COMPLEX terminó 24/24 con métricas iguales a FF/BF, pero tardó 1,957.860 ms frente a 93.891 ms del baseline más rápido (20.852×).
- El discriminante colocó el bloque triangular 0°/180° y cambió el patrón con métricas empatadas, pero se clasificó E por costo (10.602×). El diagnóstico oblicuo colocó bloques a 60° y redujo merma; aun así, 37.027× lo clasifica E. Triángulo+círculo empeoró merma/recuperable y también es E.

## Decisión

**NO-GO para implementar Pair-Block v2 en TA-042 con esta evidencia.** El mecanismo geométrico está demostrado en diagnósticos, pero no produjo bloques oficiales; MEDIUM perdió calidad frente a BF y COMPLEX excedió el umbral de costo predeclarado sin mejora funcional. La evidencia está en [auditoría v2](../spikes/SP-004-pair-block-v2-auditoria.md), [CSV](../evidence/sprint-02/SP-004/benchmark-results/sp004_block_v2_results.csv), [JSON](../evidence/sprint-02/SP-004/benchmark-results/sp004_block_v2_trace.json) y el [notebook ejecutado](../../experiments/optimization/colab/SP004-Block-Packing.ipynb).
