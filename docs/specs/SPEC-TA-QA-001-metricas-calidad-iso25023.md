# SPEC TA-QA-001 - Metricas de calidad

Responsable: Andro Joseph Quispe Cesias. Reviewer: Fabricio Danniel Aguilar Chavez (fabrilar1). Sprint 2.

## Problema y objetivo
Las pruebas y mediciones estan dispersas y falta una matriz que indique como cuantificar la calidad. Definir metricas reproducibles, cuantificables y trazables.

## Alcance y exclusiones
Incluye adecuacion funcional, desempeno, interaccion, compatibilidad, flexibilidad, mantenibilidad, seguridad operacional y trazabilidad material. No incluye certificacion ISO, auditoria oficial, implementacion de todas las pruebas de las demas TA ni cambios de algoritmos.

## Definiciones
Caracteristica: propiedad amplia de calidad; subcaracteristica: aspecto mas especifico; metrica: regla de cuantificacion; medida: resultado de una ejecucion; meta: criterio de interpretacion; evidencia: registro verificable de datos y contexto.

## Criterios de aceptacion
- CA-01: existe matriz de calidad.
- CA-02: cada metrica tiene caracteristica, objetivo, calculo y unidad.
- CA-03: cada metrica tiene procedimiento reproducible.
- CA-04: cada metrica tiene herramienta y ambiente.
- CA-05: cada metrica tiene meta o criterio de interpretacion.
- CA-06: metas justificadas, sin atribuirlas a ISO.
- CA-07: vinculo con tareas QA del encargo, pendiente de cotejo con backlog oficial.
- CA-08: distincion entre definicion y medicion.
- CA-09: trazabilidad a evidencia esperada.
- CA-10: reviewer identificado y solicitud formal verificable en PR.

[Matriz](../quality/TA-QA-001-matriz-metricas-iso25023.md) - [Plan](PLAN-TA-QA-001-metricas-calidad-iso25023.md) - [Tareas](TASKS-TA-QA-001-metricas-calidad-iso25023.md)

## Flujo de integracion del bloque Sprint 2

`integration-02` es la rama actual de integracion y despliegue para este bloque. Las nuevas tareas TA-QA-003, TA-QA-008, HU-MAT-001, TA-QA-010 y las demas tareas nuevas del bloque deben partir de su HEAD actualizado y dirigir sus PR a ella. No modifica ramas historicas cerradas.
