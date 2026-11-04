# Evidencia TA-046 — Ajustes UX de registro y revisión

SPEC: [`docs/specs/SPEC-TA-046-ajustes-ux-registro-revision.md`](../../../specs/SPEC-TA-046-ajustes-ux-registro-revision.md)
Rama: `feature/S2-TA046-ajustes-ux`

Responsable original: Fabricio Danniel Aguilar Chavez. Correcciones de cierre: Andro Joseph Quispe Cesias.
Revisor esperado: Andro Joseph Quispe Cesias; no se atribuye aprobación formal antes de su registro.

La corrección de cierre conserva la precisión de rectángulos y círculos y extiende la tabla de
medidas originales al resultado individual. Los lados derivados de polígonos mantienen su regla
de redondeo. Las pruebas de precisión y de resultado individual complementan las siguientes.

## Auditoría con teclado (04/11/2026)

Recorrido con Playwright usando solo el teclado sobre `integration/sprint-01` (`3f27cd7`), antes de
los cambios. Detalle en la SPEC §3.

| ID | Antes | Después |
|---|---|---|
| K-01 | Enter en un campo del pedido no guardaba. | Enter guarda si el pedido es válido; si no, no envía nada. |
| K-02 | Tras "Agregar pieza" el foco quedaba en el botón. | El foco va a "Forma" de la pieza nueva. |
| K-03 | Tras "Agregar otro vidrio" el foco quedaba en el botón. | El foco va a "Tipo de vidrio" del grupo nuevo. |
| K-04 | Al eliminar una pieza o un vidrio el foco se perdía y Escape dejaba de cerrar el diálogo. | El foco va a la pieza o grupo vecino; Escape cierra el diálogo. |
| K-05 | Enter en una fila corregida de la importación no revalidaba. | Enter revalida. |
| K-06 | Los polígonos solo se podían crear con clics en el lienzo. | "Número de lados" + "Crear boceto" crea el polígono con teclado. |
| M-01/M-02 | Medidas originales plegadas y sin números para polígonos. | Tabla visible en el resultado de cada motor y en la comparación, con los lados del polígono en mm. |

## Pruebas

| Tipo | Archivo | Cubre |
|---|---|---|
| Regresión (componentes) | `frontend/src/features/orders/__tests__/KeyboardFocus.test.jsx` | K-01 a K-06. Cada prueba falla sin el arreglo y pasa con él. |
| Unitaria | `frontend/tests/unit/originalMeasures.test.js` | Medidas de rectángulo, círculo y polígono en mm, con redondeo a 0,1 mm. |
| Componentes | `frontend/src/features/optimization/__tests__/OriginalMeasures.test.jsx` | Tabla en el resultado de cada motor y en la comparación. |
| E2E | `frontend/tests/e2e/ta046-keyboard.spec.js` | Pedido con rectángulo y polígono solo con teclado; foco y Escape al eliminar un vidrio. Escritorio y móvil. |

Regresión completa: unitarias, componentes, lint, build y todos los E2E críticos en escritorio y
móvil, en verde (ver checks del PR).

## Cómo reproducir

Desde `frontend/`:

```bash
npm run test:unit
npx vitest run src/features/orders/__tests__/KeyboardFocus.test.jsx src/features/optimization/__tests__/OriginalMeasures.test.jsx
npx playwright test ta046-keyboard.spec.js
```

El E2E necesita PostgreSQL de pruebas; en el CI corre siempre.
