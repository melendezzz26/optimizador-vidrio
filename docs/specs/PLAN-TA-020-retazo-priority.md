# PLAN-TA-020 — Prioridad de retazos

## Información general

| Campo | Valor |
|---|---|
| Estado del PLAN | Revisado / autorizado para continuar |
| SPEC de referencia | [SPEC-TA-020](SPEC-TA-020-retazo-priority.md) |
| Responsable | Andro Quispe |
| Revisor | Fabricio Melendez Quezada |
| Estado de revisión | Revisado / autorizado para continuar — 27/10/2026 |
| Periodo | 21/10/2026 – 28/10/2026 |
| Rama | feature/S2-TA-020-retazo-priority |
| Base | 2a76141d38ca52045a5f5ee6000fea4eedb00885 |

## 1. Objetivo, autoridad y estado

Auditar la política existente y protegerla con pruebas, según instrucción directa
del Scrum Master transmitida por el usuario. SPEC y PLAN revisados por Fabricio Melendez Quezada el 27/10/2026,
según confirmación expresa del usuario. Autorizado continuar hasta crear PR;
review final del PR, merge, smoke y cierre permanecen pendientes.

## 2. Secuencia de trabajo y dependencias

1. Sincronizar origin; la rama anterior fue integrada por PR #64.
2. Crear SPEC y PLAN, registrar revisión previa realizada y los seis CA provisionales confirmados por el usuario.
3. Auditar en lectura; clasificar con evidencia real.
4. Añadir únicamente pruebas comunes si la política ya existe.
5. Ejecutar regresiones y slices; documentar CA y límites de verificación.
6. Verificar diff, commit y push solo a la rama autorizada. Crear el PR autorizado hacia integration/sprint-01 y dejarlo listo para Fabricio.

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
| Evidencia | Clasificación y tabla de los seis CA provisionales confirmados |
| Entrega | Commits, push feature y PR; sin merge del PR/rebase/cierre |

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

- Los criterios provisionales confirmados por el usuario permiten verificar los seis puntos sin esperar otra fuente; su revisión previa fue confirmada por el usuario; review del PR pendiente.
- Review final del PR por Fabricio pendiente; no declarar cierre.
- No alterar la rama paralela TA-021 ni los motores productivos.

## Historial de estado

- 27/10/2026 — Draft: plan de auditoría y pruebas; estado inicial anterior a la revisión confirmada.
- 27/10/2026 — Draft: aclaración del usuario incorporada. Los seis CA provisionales
  están cubiertos por las pruebas ejecutadas. Sin cambios de código/pruebas,
  se conserva la ejecución de 498 casos y se verifica el diff documental.

- 27/10/2026 — Revisado / autorizado para continuar: review previo de Fabricio confirmado por el usuario; lista para entrega mediante PR. No equivale a cierre.
