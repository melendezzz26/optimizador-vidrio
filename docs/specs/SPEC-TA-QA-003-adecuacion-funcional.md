# SPEC TA-QA-003 - Adecuacion funcional

Responsable: Andro Joseph Quispe Cesias (escenarios, pruebas, resultados y defectos); Fabricio Melendez Quezada: revision de motores y correcciones cuando corresponda. Base: integration-02. Estado: PENDIENTE DE REVIEW.

## Problema y objetivo
Demostrar mediante escenarios reproducibles que los seis metodos respetan sus politicas y restricciones geometricas; registrar diferencias observadas y defectos sin afirmar superioridad universal.

## Alcance
FF, BF, WF, HF/M4, M5/BRF y M6-BS; limites de fuente, solapamiento, margen, separacion y rotaciones permitidas. Vinculos con MF-01 (casos correctos), MF-02 (patrones validos) y MF-03 (politica) de [TA-QA-001](../quality/TA-QA-001-matriz-metricas-iso25023.md). Se informan numeradores, denominadores y exclusiones; cero denominador no es evaluable. Fuera de alcance: UX, compatibilidad, trazabilidad de material, optimizaciones no relacionadas y certificacion ISO.

## Criterios de aceptacion
- CA-01: ejecutar seis metodos en escenarios controlados.
- CA-02: sin superposicion en patrones aceptados.
- CA-03: piezas dentro de fuente.
- CA-04: margen respetado.
- CA-05: separacion respetada.
- CA-06: rotaciones permitidas.
- CA-07: cada politica contrastada con un caso controlado.
- CA-08: observar diferencias entre heuristicas en escenarios discriminantes.
- CA-09: registrar esperado, obtenido y evidencia.
- CA-10: clasificar cada defecto observado.
- CA-11: coordinar cambios profundos de motores con Melendez y validar su regresion.

Ver [plan](PLAN-TA-QA-003-adecuacion-funcional.md), [tareas](TASKS-TA-QA-003-adecuacion-funcional.md) y [auditoria](../evidence/sprint-02/TA-QA-003/README.md).
