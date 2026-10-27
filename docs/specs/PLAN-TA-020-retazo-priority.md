# PLAN-TA-020 — Prioridad de retazos

## Información general

| Campo | Valor |
|---|---|
| Estado del PLAN | Draft |
| SPEC de referencia | [SPEC-TA-020](SPEC-TA-020-retazo-priority.md) |
| Responsable | Andro Quispe |
| Revisor | Fabricio Melendez Quezada |
| Estado de revisión | Pendiente |
| Periodo | 21/10/2026 – 28/10/2026 |
| Rama | feature/S2-TA-020-retazo-priority |
| Base | 2a76141d38ca52045a5f5ee6000fea4eedb00885 |

## 1. Objetivo, autoridad y estado

Auditar la política existente y protegerla con pruebas, según instrucción directa
del Scrum Master transmitida por el usuario. SPEC y PLAN permanecen pendientes
de revisión real; este trabajo de auditoría/pruebas no registra aprobación.

## 2. Secuencia de trabajo y dependencias

1. Sincronizar origin; la rama anterior fue integrada por PR #64.
2. Crear SPEC y PLAN, registrar revisión pendiente y referencia faltante del backlog.
3. Auditar en lectura; clasificar con evidencia real.
4. Añadir únicamente pruebas comunes si la política ya existe.
5. Ejecutar regresiones y slices; documentar CA y límites de verificación.
6. Verificar diff, commit y push solo a la rama autorizada. Andro abre el PR.

## 3. Estrategia técnica derivada de la SPEC

Reutilizar helpers existentes y parametrizar FirstFitOptimizer, BestFitOptimizer
y WorstFitOptimizer. Probar planchas al inicio de la entrada, scores tentadores,
fallback geométrico y agotamiento. Usar InventoryStockAdapter real para excluir
incompatibles (el helper problem filtra por material y no demuestra ese contrato).
Verificar snapshots de inventario y reutilizar slices SQLite existentes.

## 4. Tareas trazables

| Tarea | Salida |
|---|---|
| T01 auditoría | Recorrido stock → niveles → candidatos → selectores |
| Seis casos del usuario | Matriz FF/BF/WF y pruebas reutilizadas |
| Evidencia | Clasificación y tabla de CA; referencia literal pendiente |
| Entrega | Commits y push feature; sin PR/merge/rebase/cierre |

## 5. Coordinación y archivos de alcance

Solo nuevos documentos TA-020 y pruebas. Los cuatro archivos restringidos se
comparan contra la base. Fetch antes de cada lote de cambios; vigilar integration
y `origin/docs/TA-021-comparacion-metodos` (36d9c23 al inicio). No se implementa
ningún comparador u orquestador multimétodo.

## 6. Validación y evidencia reproducible

Python del entorno `.venv`, pytest desde backend. Ejecutar suite unitaria de
optimización, geometría, contrato y slices locales FF/BF/WF. Archivar salida,
verificar `git diff --check` y ausencia de cambios en backend/app.

## 7. Riesgos y pendientes

- CA literal del backlog no disponible: mantener GAP documental explícito.
- Revisión de Fabricio pendiente; no equivale a aprobación ni cierre.
- No alterar la rama paralela TA-021 ni los motores productivos.

## Historial de estado

- 27/10/2026 — Draft: plan de auditoría y pruebas; revisión Pendiente.
