# PLAN-SP-005 — Cierre de evidencia M5

**PBI:** SP-005 / T01
**Responsable:** Luis Anthony Ibáñez Herrera
**Revisor asignado:** Andro Joseph Quispe Cesias
**Estado:** ejecución y documentación terminadas; revisión formal pendiente
**Rama / PR:** `spike/SP-005-heuristica-m5` / #93
**Fecha:** 02/11/2026

## Propósito

Dejar una única evidencia reproducible para FF/BF/WF/M5, explicar la discrepancia entre el notebook original y los artefactos CSV/JSON, y entregar el spike para revisión. El alcance permanece experimental; no incluye integración del selector a producción.

## Flujo ejecutado

| Paso | Evidencia | Estado |
|---|---|---|
| Auditar fuentes, fixtures, snapshots y salidas originales | Notebook, script, historial y fixtures TA-027 | Completado |
| Reemplazar runner duplicado por importaciones del loader y motor oficiales; añadir pruebas M5 | `experimento_m5.py`, `backend/tests/unit/optimization/test_sp005_m5.py` | Completado |
| Ejecutar tres repeticiones de FF/BF/WF/M5 en los tres casos | CSV de 36 filas y JSON con firmas | Completado; determinismo funcional PASS |
| Alinear SPEC, resultados, notebook, README e informe | Artefactos enlazados abajo | Completado |
| Revisión formal independiente | Andro Joseph Quispe Cesias | Pendiente |

## Evidencia de cierre

- [SPEC](SPEC-SP-005-heuristica-m5.md)
- [TASKS](TASKS-SP-005-heuristica-m5.md)
- [Informe](SP-005-informe-investigacion-m5.md)
- [Revisión técnica y discrepancia](REVIEW-SP-005-heuristica-m5.md)
- [CSV y JSON](resultados/)
- [README de evidencia](../../evidence/sprint-02/SP-005/README.md)

La decisión experimental es **GO CONDICIONADO**: M5 mejora el área recuperable frente a WF, pero consume más planchas y produce más merma que FF/BF en Medium y Complex. No se solicita merge hasta que la revisión formal pendiente se complete.
