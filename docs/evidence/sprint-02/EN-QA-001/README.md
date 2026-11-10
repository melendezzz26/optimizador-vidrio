# Evidencia EN-QA-001 — Modelo de calidad ISO/IEC 25010:2023

| Campo | Valor |
|---|---|
| Tarea | EN-QA-001 (1 SP, Alta) |
| SPEC | [SPEC-EN-QA-001](../../../specs/SPEC-EN-QA-001-modelo-calidad-iso25010.md) |
| Entregable | [Modelo de calidad](../../../quality/ISO-25010-modelo-calidad.md) |
| Rama | `enabler/S2-ENQA001-modelo-calidad-iso25010`, desde `integration-02` en `f46d96d` |
| Responsable | Fabricio Danniel Aguilar Chavez (`fabrilar1`) |
| Reviewer | Andro Joseph Quispe Cesias |
| Fecha | 10/11/2026 |

## Qué se entregó

- **Modelo de calidad** de NewGlass con las nueve características de la ISO/IEC 25010:2023:
  matriz resumen y una matriz por característica (definición, subcaracterísticas, módulos,
  riesgos, evaluación, tarea QA y evidencia existente con ruta).
- **Validación de TA-QA-001**: cobertura por característica y vacíos V-01 a V-18, cada uno
  con su tarea QA. La matriz de TA-QA-001 no se modificó.
- **Prioridades** de calidad y **nota de alineación** ISO/IEC 25023:2016 ↔ 25010:2011/2023.
- **Corrección de SPEC-TA-037** (V-17): L-03 de 300 a 800 unidades según
  SPEC-ACADEMIC-800 (PR #108), con línea de historial v1.5. Ningún otro cambio en esa SPEC.

Solo documentación: sin cambios en `backend/`, `frontend/`, migraciones ni workflows.

## Verificación de criterios de aceptación

| CA | Criterio | Cómo se verificó | Resultado |
|---|---|---|---|
| CA-01 | Matriz de las 9 características con definiciones | Revisión: §3 (resumen) y §4.1 a §4.9 del modelo, una definición parafraseada por característica. | Cumple |
| CA-02 | Cada atributo se vincula a módulos y riesgos | Revisión: filas "Módulos" y "Riesgos" completas en §4.1 a §4.9, con los módulos reales (incluidos `results` y `dashboard`). | Cumple |
| CA-03 | Se identifica cómo se evaluará cada atributo | Revisión: fila "Evaluación" (prueba, medición o revisión) y "Tarea QA" en §4.1 a §4.9; vacíos asignados en §5.2. | Cumple |
| CA-04 | SPEC revisada por un integrante distinto del autor | Solicitud de revisión a Andro en el PR. | **Pendiente** |

Verificaciones adicionales:

- Todas las rutas citadas en el modelo (enlaces, archivos de código y pruebas) se comprobaron
  contra la base auditada: ninguna falta.
- `git diff --check` sin errores en cada commit de la rama.

## Estado de la revisión

La revisión de Andro Joseph Quispe Cesias (CA-04) está **solicitada en el PR y pendiente**.
No se atribuye aprobación antes de que conste en GitHub. Tras su aprobación y el merge,
la SPEC pasa a **Verified** en un PR `docs/...` aparte.

## Cómo reproducir la verificación

Desde la raíz del repositorio, en la rama de la tarea:

```powershell
git diff --stat integration-02...HEAD
git diff --check integration-02...HEAD
```

Resultado esperado: solo cambian los cuatro archivos de documentación de esta tarea y
`git diff --check` no muestra salida.
