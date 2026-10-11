# Evidencia TA-034: Patrón de gestión y feedback compartido

| Dato | Valor |
|---|---|
| PBI / tarea | EN-006 / TA-034 (T01 y T02) |
| SPEC | docs/specs/SPEC-EN-006-ui-componentes-compartidos.md |
| Responsable | Fabricio Aguilar |
| Rol en el sprint | Scrum Master / Developer |
| Fecha | 2026-10-09 |
| Entorno | Local, Windows (frontend con Vite y Vitest; backend con Python y pytest) |
| Rama / commit | feature/TA-034-patron-gestion-feedback / 69e7455 |

## 1. Qué se entrega

- **T01:** componentes de feedback compartidos en `frontend/src/shared/components/feedback/` (`FeedbackMessage`, `FieldError`, `LoadingState`, `EmptyState`, `ConfirmDialog`), aplicados en Users, Inventory y Orders (registro de pedidos).
- **T02:** hook `frontend/src/shared/hooks/useManagementView.js` con el patrón "listado primero y formulario bajo acción". Su aplicación completa corresponde a HU-003 T05 (Users) y HU-013 T01 (Orders), según la opción A acordada por el equipo.
- No es un módulo nuevo: son piezas compartidas de la interfaz. No hay cambios de backend ni de BD.

## 2. Pruebas automatizadas

| Procedimiento | Resultado esperado | Resultado obtenido | Archivo |
|---|---|---|---|
| `npx vitest run --reporter=verbose src/shared src/features/users src/features/inventory src/features/orders/__tests__/NuevoPedidoFeedback.test.jsx` | Todas pasan | 37 passed (8 archivos) | test-results/vitest-ta034.txt |
| `npm run lint` | Sin errores | Pass | test-results/lint.txt |
| `npm run build` | Build correcto | Pass (built in 603 ms) | test-results/build.txt |
| `python -m pytest -q` (backend) | Sin fallos | 741 passed, 326 skipped, 0 failed | test-results/pytest.txt |
| `npx vitest run` (suite completa) | Ver observación | 14 failed / 63 passed (77) | test-results/vitest-suite-completa.txt |

**Observación:** las 14 pruebas que fallan en la suite completa están en `features/orders/__tests__/NuevoPedido.test.jsx` (12) y `CustomPieceEditor.test.jsx` (2). Corresponden a HU-006 y HU-007, ya fallaban en `integration/sprint-01` antes de esta rama y no prueban código de la TA-034. Se informó al responsable de Orders.

## 3. Casos manuales

| ID | Caso | Esperado | Obtenido | Evidencia |
|---|---|---|---|---|
| CP-TA034-01 | Crear un usuario | Mensaje de éxito con rol status | Pass | screenshots/01-users-exito.png |
| CP-TA034-02 | Campo obligatorio vacío | Error junto al campo, aria-invalid | Pendiente | screenshots/02-users-error-campo.png |
| CP-TA034-03 | Carga de la lista (Slow 4G) | LoadingState visible | Pendiente | screenshots/03-users-cargando.png |
| CP-TA034-04 | Búsqueda sin coincidencias | EmptyState "sin resultados" | Pendiente | screenshots/04-users-sin-resultados.png |
| CP-TA034-05 | Desactivar usuario | ConfirmDialog antes de ejecutar | Pendiente | screenshots/05-users-dialogo-desactivar.png |
| CP-TA034-06 | Registrar plancha | Mensaje de éxito | Pendiente | screenshots/06-inventario-exito.png |
| CP-TA034-07 | Dato inválido en inventario | Error de campo | Pendiente | screenshots/07-inventario-error.png |
| CP-TA034-08 | Pedido sin piezas | EmptyState | Pendiente | screenshots/08-pedidos-vacio.png |
| CP-TA034-09 | Cancelar pedido | ConfirmDialog; no limpia si se elige Cancelar | Pendiente | screenshots/09-pedidos-dialogo-cancelar.png |
| CP-TA034-10 | Teclado en el diálogo | Foco inicial en Cancelar; Tab atrapado; Escape cierra; el foco vuelve | Pendiente | Manual |

Las capturas no muestran tokens, contraseñas ni DNI reales.

## 4. Referencias

- WCAG 2.2: 1.4.1, 3.3.1, 3.3.3, 4.1.3.
- WAI-ARIA APG: Alert and Message Dialogs Pattern.