# SPEC-TA-046 — Ajustes UX de registro y revisión

| Campo | Valor |
|---|---|
| ID | TA-046 |
| Tareas | T01 — Enter/foco/teclado · T02 — Mostrar dimensiones originales del pedido en Optimización · T03 — Regresión UX/responsive/accesibilidad básica |
| Sprint | Sprint 2 |
| Estado | **Implemented** |
| Responsable original | Fabricio Danniel Aguilar Chavez |
| Correcciones de cierre | Andro Joseph Quispe Cesias |
| Revisor esperado | Andro Joseph Quispe Cesias (sin atribuir aprobación formal) |
| Rama | `feature/S2-TA046-ajustes-ux` |
| Base | `origin/integration/sprint-01` en `3f27cd7` |
| Fecha | 04/11/2026 |
| Referencias | Documento de Diseño UI/UX y Accesibilidad v1.0; Estrategia de Pruebas §16 y §19 |

## 1. Objetivo

Que el registro de pedidos se pueda completar solo con teclado, con un foco que avance de forma
predecible, y que en Optimización el resultado se pueda contrastar con las medidas que el usuario
ingresó, en mm, sin tener que abrir otra sección.

## 2. Alcance

**Incluye:** registro y edición de pedidos (`FormularioPedido`, `CustomPieceEditor`,
`BulkImportPanel`), la comparación de Optimización (`ComparisonWorkspace`) y el resultado de corrida individual (`OptimizationPage`).

**Fuera de alcance:** cambios de API o de base de datos; rediseño visual; Inventario, Usuarios,
Login y las pestañas de Optimización, que ya funcionan con teclado (ver §3).

## 3. Situación actual (auditoría con teclado, 04/11/2026)

Recorrido con Playwright usando solo el teclado sobre `integration/sprint-01` (`3f27cd7`).
No hay un registro escrito de la demostración; las fallas salen de esta auditoría.

| Flujo | Resultado |
|---|---|
| Login, búsqueda de cliente, formularios de Inventario y Usuarios | Enter funciona (usan `<form>`). |
| Pestañas de Inventario, Usuarios y Comparación | Flechas, Inicio y Fin funcionan. |
| Diálogos de confirmación | Foco inicial, Escape y retorno de foco funcionan. |
| **K-01** Registro de pedido | Enter en un campo no guarda: el pedido solo se guarda con clic. |
| **K-02** "Agregar pieza" | El foco queda en el botón; la pieza nueva no recibe el foco. |
| **K-03** "Agregar otro vidrio" | El foco queda en el botón; el grupo nuevo no recibe el foco. |
| **K-04** "Eliminar pieza" / "Eliminar vidrio" | El foco se pierde (vuelve a `body`). Consecuencia: Escape ya no cierra el diálogo del pedido, porque la tecla no llega a él. |
| **K-05** Corrección de filas importadas (HU-018) | Enter en el campo corregido no revalida. |
| **K-06** Editor de polígono | Los vértices solo se agregan con clic en el lienzo: no hay forma de crear un polígono con teclado. |
| **M-01** Medidas originales en Optimización | Están en "Piezas y medidas solicitadas", plegado y separado del resultado. |
| **M-02** Polígonos en ese bloque | No muestran ninguna medida: el pedido guarda solo vértices y el bloque solo imprime `dimensiones`. |

## 4. Reglas

### T01 — Teclado y foco

- **RN-01 (K-01):** en el registro y la edición de pedidos, Enter en un campo de texto o numérico
  de las piezas guarda el pedido **solo si el formulario es válido**; si no lo es, no hace nada.
  No aplica a los selectores (`select`), a los botones, al buscador de clientes (que ya busca con
  Enter) ni a los campos de la importación (RN-05).
- **RN-02 (K-02):** al agregar una pieza, el foco pasa al campo "Forma" de esa pieza.
- **RN-03 (K-03):** al agregar un vidrio, el foco pasa al campo "Tipo de vidrio" del grupo nuevo.
- **RN-04 (K-04):** al eliminar una pieza, el foco pasa a la pieza que ocupa su lugar o, si era la
  última, a la anterior; si el grupo queda sin piezas visibles, a "Agregar pieza". Al eliminar un
  vidrio, el foco pasa al encabezado del grupo anterior o, si no hay, al siguiente. El foco nunca
  queda en `body`.
- **RN-05 (K-05):** Enter en un campo de corrección de la importación ejecuta "Revalidar".
- **RN-06 (K-06):** el editor de polígono ofrece una alternativa al dibujo: debajo del lienzo, un
  campo "Número de lados" (3 a 128, texto con teclado numérico) y el botón "Crear boceto", que
  genera un polígono regular cerrado. Va debajo del lienzo para no desplazarlo mientras se dibuja.
  Desde ahí, las longitudes de los lados y los ángulos se escriben con teclado como hoy. El dibujo
  con mouse se mantiene sin cambios.

### T02 — Medidas originales junto al resultado

- **RN-07 (M-01):** en la fase "Resultado" de cada motor y en la pestaña "Comparación" se muestra,
  visible y sin plegar, la tabla **"Medidas originales del pedido"**: pedido, pieza, forma,
  cantidad, vidrio y espesor, y medidas ingresadas.
- **RN-08 (M-02):** las medidas se muestran en mm: rectángulo `ancho × alto mm`; círculo
  `radio mm`; polígono `n lados: L1 · L2 · … mm`, con cada lado calculado desde los vértices
  guardados y redondeado a 0,1 mm.
- **RN-09:** la tabla aclara que las piezas colocadas pueden aparecer giradas y que las medidas son
  las ingresadas. El bloque plegado actual se conserva para ver la geometría dibujada.
- **RN-10:** ancho y alto del rectángulo y radio del círculo conservan la precisión numérica de
  la geometría guardada, sin ceros decimales innecesarios. El redondeo a 0,1 mm se limita a los
  lados calculados del polígono. En la corrida individual se utiliza la geometría original de las
  unidades solicitadas del resultado, no la geometría orientada de sus colocaciones.

## 5. Diseño técnico

Solo frontend; sin cambios de API, esquema ni migraciones.

| Archivo | Cambio |
|---|---|
| `features/orders/FormularioPedido.jsx` | RN-01 a RN-04: Enter para guardar y manejo de foco al agregar/eliminar. |
| `features/orders/BulkImportPanel.jsx` | RN-05. |
| `features/orders/CustomPieceEditor.jsx` | RN-06. |
| `features/optimization/originalMeasures.js` | Nuevo: función pura que describe las medidas de una pieza (RN-08). |
| `features/optimization/OriginalMeasuresTable.jsx` | Nuevo: tabla de RN-07 y RN-09, con `caption` y desplazamiento horizontal en móvil. |
| `features/optimization/ComparisonWorkspace.jsx` | Muestra la tabla en "Resultado" y "Comparación". |
| `features/orders/CustomPieceEditor.css`, `features/optimization/OriginalMeasuresTable.css` | Estilos de los controles nuevos, con los tokens de UI. |
| `features/optimization/__tests__/ComparisonWorkspace.test.jsx` | Ajuste de una línea: busca la tabla de métricas por su nombre, porque la pestaña Comparación ahora tiene dos tablas. |

## 6. Criterios de aceptación

| CA | Tarea | Criterio |
|---|---|---|
| CA-01 | T01 | Con un pedido válido, Enter en un campo de medidas o cantidad lo guarda una sola vez; con uno inválido, no envía nada. |
| CA-02 | T01 | Tras agregar una pieza o un vidrio, el foco queda en su primer campo. |
| CA-03 | T01 | Tras eliminar una pieza o un vidrio, el foco queda en un control visible del formulario y Escape sigue cerrando el diálogo. |
| CA-04 | T01 | Enter en una fila corregida de la importación revalida. |
| CA-05 | T01 | Un polígono se puede crear, medir y guardar en el pedido usando solo el teclado. |
| CA-06 | T02 | El resultado de cada motor y la comparación muestran las medidas originales visibles, en mm, incluidos los lados de los polígonos. |
| CA-07 | T03 | Un E2E registra un pedido con rectángulo y polígono usando solo teclado, en escritorio y móvil, sin desbordamiento horizontal. |
| CA-08 | T03 | Las suites existentes (unitarias, componentes, lint, build y E2E críticos) siguen en verde. |

## 7. Pruebas previstas

- **Regresión (T01):** una prueba de componentes por cada falla K-01 a K-06 que reproduce el
  defecto: falla sin el arreglo y pasa con él (Estrategia de Pruebas §16).
- **Unitarias (T02):** `originalMeasures` para rectángulo, círculo y polígono, con redondeo.
- **Componentes (T02):** la tabla aparece en "Resultado" y en "Comparación", con unidades.
- **E2E (T03):** `ta046-keyboard.spec.js`, agregado a `criticalSpecs.js` (TA-040).

## 8. Evidencia requerida

`docs/evidence/sprint-02/TA-046/`: resultado de la auditoría (§3), salida de las pruebas y checks
del PR.

## Historial de estado

| Fecha | Versión | Estado | Cambio |
|---|---|---|---|
| 04/11/2026 | 0.1 | Draft | Auditoría con teclado, reglas RN-01 a RN-09, diseño y criterios. |
| 04/11/2026 | 0.2 | Implemented | T01–T03 implementadas. K-01 a K-06 con pruebas de regresión que fallan sin el arreglo; tabla de medidas originales en resultado y comparación; E2E `ta046-keyboard.spec.js` en `criticalSpecs.js`. Regresión completa en verde. |
