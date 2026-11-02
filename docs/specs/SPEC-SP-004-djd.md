# SPEC-SP-004-DJD — Evaluación experimental de Djang and Finch

## Estado

Spike experimental completado. DJD-1/3 se evaluó aislado y no queda aprobado para implementación productiva en TA-042: aunque mostró elecciones conjuntas distintas, el costo observado en COMPLEX fue desproporcionado frente a FF sin cambiar las métricas finales. El candidato no se registra en NewGlass productivo.

## Contexto

La evaluación inicial de Filler mostró coincidencia práctica con FF en los tres fixtures TA-027 y confirmó que FF ya ordena piezas por área descendente. Filler queda como candidato evaluado y descartado como principal, con su notebook, trazas, resultados y commits preservados. DJD-1/3 ofrece una pregunta de investigación diferente: después de una fase inicial de llenado, evalúa grupos ordenados de una, dos y tres piezas con la capacidad residual y la tolerancia de desperdicio.

## Objetivo

Implementar y medir DJD-1/3 en un módulo experimental aislado, emparejado con la colocación geométrica real de NewGlass. Comparar sus decisiones, calidad, determinismo y costo con FF/BF/WF sobre EXP-SMALL-001, EXP-MEDIUM-001 y EXP-COMPLEX-001, más un caso discriminante explícitamente no oficial.

## Definición experimental

1. Dentro de cada grupo material-espesor, ordenar piezas por área descendente y por identidad estable.
2. Activar unidades de stock compatibles con la prioridad actual: retazo antes de plancha, desempate por inventario estable.
3. Llenar la fuente activa colocando piezas individuales hasta que la suma de áreas oficiales alcance al menos un tercio del área nominal total de la fuente, o no haya pieza individual factible.
4. Inicializar `w = 0`. El incremento será `delta_w = stock.area_mm2 / 20`, el incremento relativo de 1/20 del área del objeto descrito por López-Camacho et al. Tanto el umbral inicial como el paso usan el área nominal total de la fuente; el margen, la forma irregular y la separación se aplican después mediante validación geométrica.
5. Buscar secuencialmente secuencias geométricas factibles de tamaño 1, 2 y 3. Los subconjuntos se enumeran por orden determinista de piezas y se prueban sus permutaciones, pues el orden de colocación puede cambiar la factibilidad 2D.
6. Podar antes de rasterizar cuando la suma de áreas oficiales exceda el área nominal residual (`área de fuente - áreas oficiales ya colocadas`) o cuando el residuo estimado supere `w`. Para todo candidato restante, probar cada pieza sobre un layout inmutable temporal y validar el grupo completo.
7. Aceptar el primer grupo completo que deje residuo estimado dentro de `w`; publicar los layouts y placements solo si todas las piezas de la secuencia entran. Tras aceptar, reiniciar el proceso de selección en el mismo objeto con `w = 0`.
8. Si no se encuentra un grupo, aumentar `w` por `delta_w` mientras `w` sea menor que el área nominal residual actual. Si se agota esa progresión sin grupo factible aceptable, avanzar a la siguiente fuente.

La búsqueda de combinaciones se inspira en la adaptación 2D de la referencia primaria. El área nominal residual solo sirve como cota superior para podar; nunca certifica cabida geométrica. Las reglas de orden de combinaciones y desempates son decisiones explícitas de esta adaptación a NewGlass.

## Invariantes

- Resolución 1 mm, paso angular 5°, materiales, espesores, inventario, margen y separación permanecen iguales a TA-027.
- No se cambia la implementación productiva de FF/BF/WF ni se registra DJD en la aplicación.
- Los grupos se validan en una copia inmutable del `SheetLayout`; ningún candidato incompleto modifica el estado activo.
- Los placements aceptados deben respetar `PieceUnit.material_key`, margen, separación, rotación y colisión del motor.
- Se reutilizan `RasterCache`, `PreparedRunGeometry`, `_feasible_candidates`, `SheetLayout` y `calculate_metrics`.
- No se almacena un listado completo de combinaciones geométricas; se generan como iterador determinista.

## Métricas

Se reutilizan requested/placed/unplaced, retazos y planchas usados, aprovechamiento, merma, área recuperable y runtime oficiales. Los diagnósticos incluyen ratio de llenado inicial, subconjuntos evaluados por tamaño, pruning de área, secuencias geométricas probadas, secuencias factibles, pasos de tolerancia, tamaños seleccionados y cambios de fuente.

## Criterios de aceptación y verificación

| ID | Criterio | Verificación y estado |
|---|---|---|
| CA-01 | Renombrar la rama sin perder commits; preservar la investigación, notebook, trazas y resultados de Filler como candidato descartado. | Historial desde `f7b8861`, archivos archivados y evidencia Filler: PASS. |
| CA-02 | Documentar DJD 1D, adaptación irregular 2D, placement separado, variantes iniciales y fuentes académicas verificables. | Investigación del Spike y notebook, referencias Ross et al. y López-Camacho et al.: PASS. |
| CA-03 | Usar DJD-1/3 con umbral nominal 1/3 y `delta_w = stock.area_mm2 / 20`, ambos visibles y trazables. | Implementación, prueba discriminante con tolerancia 5 mm² y lectura de código: PASS. |
| CA-04 | Evaluar combinaciones deterministas de 1/2/3 de forma perezosa, podar por área y registrar costo de búsqueda. | Traza CSV/JSON y prueba de generación/pruning: PASS. |
| CA-05 | Validar cada orden geométricamente con layouts experimentales sin mutación; conservar material, espesor, retazo→plancha, margen, separación y rotación. | Pruebas aisladas DJD y fixtures COMPLEX: PASS. |
| CA-06 | Comparar FF/BF/WF/DJD en los tres fixtures TA-027 sin alterarlos y usar las métricas oficiales. | CSV/JSON actualizado y comprobación de archivos productivos/fixtures sin cambios: PASS. |
| CA-07 | Mostrar un caso discriminante separado de TA-027, sin presentarlo como mejora de rendimiento. | `DJD-DISCRIMINANT-001`: DJD elige el par `[2, 3]`; resultados marcados no oficiales: PASS. |
| CA-08 | Entregar notebook con 36 secciones, comentarios en español, interpretación de resultados y outputs ejecutados. | 98 celdas, 31 celdas Python ejecutadas, sin errores; salida local, no kernel remoto de Colab: PASS. |
| CA-09 | Ejecutar pruebas DJD y regresiones FF/BF/WF, incluyendo determinismo. | 93 pruebas aprobadas; determinismo ×3 PASS en SMALL/MEDIUM/COMPLEX. |
| CA-10 | Evaluar GO/NO-GO con decisiones, calidad y costo medidos; detenerse antes de push/PR/merge. | NO-GO productivo por costo 7,694 ms en COMPLEX frente a 154 ms FF, sin mejora de calidad; commits locales, sin publicación. |

## Criterio de evaluación

El resultado es GO para un diseño productivo posterior solo si la política produce una decisión operacional distinguible, respeta geometría e inventario, es determinista, puede implementarse sin duplicar el motor y su costo medido permanece razonable para la carga de evaluación. No necesita ganar todos los fixtures. Se registra NO-GO si equivale en la práctica, el costo es desproporcionado, necesita alterar reglas centrales o no conserva determinismo. La evidencia satisface los requisitos de distinción, geometría, reglas compartidas y determinismo, pero el factor de costo cercano a 50× FF en COMPLEX decide NO-GO para TA-042 con esta implementación.

## Fuera de alcance

Integración productiva, cambios en API, interfaz, base de datos, inventario, fixtures TA-027, TA-042, publicación de la rama, PR y merge.
