# Intención previa — matriz DJD SP-004

Los siguientes casos se fijan antes de ejecutar FF/BF/WF/DJD. Todos llevan la etiqueta `DIAGNÓSTICO DJD — NO PERTENECE A TA-027`; sus dimensiones no se ajustarán tras observar resultados.

| Caso | Situación que motiva el caso | Campo que se observará |
|---|---|---|
| DJD-DIAGNOSTIC-001 | Pieza grande junto con dos rectángulos pequeños y un círculo; retazo compatible más plancha. | Si selección conjunta afecta continuidad del retazo o asignación posterior. |
| DJD-DIAGNOSTIC-002 | Dos triángulos convexos de misma familia y un rectángulo. | Si el grupo de dos cambia placements o stock frente a pieza individual. |
| DJD-DIAGNOSTIC-003 | Pieza grande más tres rectángulos 4×4; suma de áreas de la terna igual al área residual nominal tras el 12×6. | Si una terna aparece seleccionada y puede completar geométricamente la plancha. |
| DJD-DIAGNOSTIC-004 | Mezcla rectangular/circular con un retazo y dos planchas compatibles. | Diferencia de grupo elegido y prioridad de stock cuando hay varias fuentes. |

La matriz es diagnóstico dirigido, no una muestra estadística. Se conservan empates y empeoramientos. Clasificación posterior: A, decisiones distintas/métricas iguales; B, cambia métricas sin mejora; C, mejora alguna métrica funcional; D, empeora notablemente.

Regla fijada antes de las ejecuciones: se elige el mejor baseline lexicográfico por cobertura, planchas, aprovechamiento, merma y área recuperable. A indica empate funcional contra ese baseline cuando las decisiones difieren, o empate con todos los baselines; se informa por separado si la selección DJD difirió. B es un cambio sin mejora frente al mejor baseline; C es una mejora funcional frente al mejor baseline. D prevalece ante pérdida de cobertura, más planchas, caída de al menos 5 puntos porcentuales de aprovechamiento o aumento de merma superior al 5% frente al mejor baseline (piso de 1 mm²). El tiempo se compara aparte y no cambia la clase funcional.
