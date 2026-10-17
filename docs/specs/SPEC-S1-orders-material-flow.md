# SPEC-S1-ORDERS-MATERIAL-FLOW — Agrupación de Pedido por Material, Filas Lineales y Selección Directa de Vértice

## Información general

| Campo | Valor |
|---|---|
| Estado | Draft |
| PBI relacionado | S1-orders-material-flow |
| Responsable | Luis Anthony Ibañez Herrera[cite: 1] |
| Reviewer | Equipo NewGlass |

## 1. Objetivo

Refactorizar el formulario de creación y edición de pedidos (`FormularioPedido.jsx`) para agrupar las piezas bajo bloques de material (`Cliente -> Material -> Piezas`), evitando repetir la selección de material y espesor por cada pieza[cite: 7]. Además, implementar un diseño lineal para las filas de las piezas dentro del modal[cite: 4, 10], mejorar las etiquetas haciéndolas menos ambiguas (`Tipo de vidrio`, `Espesor del vidrio (mm)`, `Cantidad`)[cite: 7], garantizar la preservación de los datos originales al cancelar la edición[cite: 4, 7], y permitir la selección directa de vértices en `CustomPieceEditor.jsx` para fijar ángulos, eliminando selectores confusos como `S1/S2`[cite: 6].

## 2. Alcance

### Incluye

- Reestructuración de estado y UI en `FormularioPedido.jsx` para soportar la jerarquía `Cliente -> Material 1..N (Tipo de vidrio + Espesor del vidrio (mm)) -> Pieza 1..M`[cite: 7].
- Soporte para agregar múltiples piezas en un material y múltiples materiales en un pedido (`+ Agregar otro material`)[cite: 7].
- Diseño lineal para las filas de piezas (`RECTANGULO`, `CIRCUNFERENCIA` y `POLIGONO_CONVEXO`) en `FormularioPedido.jsx` y `NuevoPedido.css`[cite: 7, 10].
- Reemplazo de las etiquetas `Material`, `Espesor` y `Cant.` por `Tipo de vidrio`, `Espesor del vidrio (mm)` y `Cantidad`[cite: 7].
- Preservación estricta de los datos originales del pedido al cancelar la edición de un pedido `PENDIENTE`[cite: 4, 7].
- Selección interactiva haciendo clic directamente sobre el vértice (`V1..Vn`) en `CustomPieceEditor.jsx` y `CustomPieceEditor.css` para ingresar/fijar el ángulo interior, con recálculo y validación en tiempo real[cite: 6, 9, 12].
- Actualización de las suites de pruebas en `FormularioPedido.test.jsx` y `CustomPieceEditor.test.jsx`[cite: 13, 14].

### Fuera de alcance

- Alteraciones a la estructura de la base de datos o a los esquemas de backend en `schemas.py`[cite: 8].
- Cambios en las rutas y métodos de `ordersApi.js` (`/api/orders`, `/api/inventory/tipos-vidrio`)[cite: 5].
- Modificaciones al motor de optimización, RBAC, o repositorios de inventario (`ports.py`, `repository.py`)[cite: 2, 3].

## 3. Actor y precondiciones

**Actor:** Operario o usuario autenticado con permisos para gestionar pedidos[cite: 4, 5].

**Precondiciones:**

- El catálogo de tipos de vidrio (`/api/inventory/tipos-vidrio`) contiene registros activos (`estado !== false`) con sus respectivos espesores (`espesores_mm`)[cite: 5, 7].
- En la creación (`mode === 'create'`), se debe seleccionar un cliente a través de `OrderClientSelector` antes de guardar el pedido[cite: 7].
- En la edición (`mode === 'edit'`), el pedido debe encontrarse en estado `PENDIENTE`; de lo contrario, el formulario se renderiza en modo de solo lectura (`readOnly`)[cite: 4, 7].

## 4. Entradas y datos

| Campo / dato | Tipo / formato | Regla |
|---|---|---|
| `id_cliente` | `int` (`PositiveId`) | Requerido por `CreateOrderRequest` (`gt=0`) al registrar un pedido nuevo[cite: 7, 8]. |
| `id_tipo_vidrio` | `int` (`PositiveId`) | Seleccionado a nivel de bloque (`Tipo de vidrio`) e inyectado a cada pieza del bloque en el payload plano[cite: 7, 8]. |
| `espesor_mm` | `float` (`PositiveNumber`) | Seleccionado a nivel de bloque (`Espesor del vidrio (mm)`) a partir de la lista `espesores_mm` del vidrio elegido[cite: 7, 8]. |
| `tipo_forma` | `Literal["RECTANGULO", "CIRCUNFERENCIA", "POLIGONO_CONVEXO"]` | Determina los campos de dimensiones visibles en la fila lineal de la pieza[cite: 7, 8]. |
| `cantidad` | `int` (`PositiveId`) | Número entero mayor que `0` (`Cantidad`)[cite: 7, 8]. |
| `width_mm`, `height_mm` | `float` (`PositiveNumber`) | Requeridos para `RECTANGULO`; deben ser mayores que `0`[cite: 7, 8]. |
| `radius_mm` | `float` (`PositiveNumber`) | Requerido para `CIRCUNFERENCIA`; debe ser mayor que `0`[cite: 7, 8]. |
| `vertices_mm` | `list[list[Coordinate]]` | Requerido para `POLIGONO_CONVEXO`, mínimo `3` vértices y debe validarse con `validateConvexPolygon`[cite: 7, 8, 12]. |
| `constraints` (Ángulo) | `Array<{ vertex: int, angle: string }>` | Capturado al hacer clic en el vértice `Vi`; el ángulo debe ser mayor a `0` y menor a `180` grados, y se pueden fijar hasta `n - 3` vértices[cite: 6, 12]. |

## 5. Reglas de negocio

- RN-01 (Agrupación por Material): En la interfaz de `FormularioPedido.jsx`, las piezas se organizan dentro de bloques (`Tipo de vidrio` y `Espesor del vidrio (mm)`), pero la función `buildPayload` debe aplanar (flatten) esta estructura para enviar un arreglo de `piezas` compatible con `CreateOrderRequest` y `UpdateOrderRequest` de `schemas.py`[cite: 7, 8].
- RN-02 (Hidratación en Edición): Al abrir un pedido mediante `getOrder(idPedido)`, las piezas que llegan planas desde el backend se agruparán dinámicamente en bloques basándose en la combinación de `id_tipo_vidrio` y `espesor_mm`[cite: 5, 7, 8].
- RN-03 (Reinicio de Espesor): Si se cambia el `Tipo de vidrio` en un bloque, el valor de `Espesor del vidrio (mm)` de ese bloque debe reiniciarse a vacío[cite: 7].
- RN-04 (Diseño Lineal y Etiquetas): Cada pieza se presenta en una fila horizontal:
  - `RECTANGULO`: `Rectángulo | Ancho (mm) [ ] | Alto (mm) [ ] | Cantidad [ ]`[cite: 7, 10].
  - `CIRCUNFERENCIA`: `Círculo | Radio (mm) [ ] | Cantidad [ ]`[cite: 7, 10].
  - `POLIGONO_CONVEXO`: `Polígono convexo | Figura configurada | Cantidad [ ] | [Editar figura]`[cite: 7, 10].
- RN-05 (Inmutabilidad al Cancelar): Al hacer clic en `Cancelar` o cerrar el modal durante una edición (`mode === 'edit'`), se descartan todas las mutaciones locales y se restauran los valores originales obtenidos del backend al abrir el modal[cite: 4, 7].
- RN-06 (Selección Directa de Vértice): En `CustomPieceEditor.jsx`, una vez que el polígono esté cerrado (`isClosed === true`) y tenga al menos `3` vértices, el usuario podrá hacer clic directamente sobre un vértice (`V1..Vn`) en el lienzo SVG para seleccionarlo y fijar/liberar su ángulo interior, sin depender de menús tipo `S1/S2`[cite: 6, 12].

## 6. Flujo principal

1. El operario abre el formulario de pedidos en modo `create` (`NuevoPedido.jsx`) o en modo `edit` para un pedido en estado `PENDIENTE`[cite: 4, 7, 11].
2. `FormularioPedido.jsx` carga el catálogo de vidrios (`listOrderMaterials`) y, si es edición, carga los datos del pedido (`getOrder`)[cite: 5, 7].
3. En modo de creación, el operario selecciona al cliente mediante `OrderClientSelector`[cite: 7].
4. En el primer bloque de material, el operario elige el `Tipo de vidrio` y el `Espesor del vidrio (mm)`, y luego configura la forma (`Rectángulo`, `Círculo` o `Polígono convexo`), las medidas y la `Cantidad` en las filas de las piezas[cite: 7].
5. Si se requiere otro material, el operario hace clic en `+ Agregar otro material`, lo que genera un nuevo bloque independiente[cite: 7].
6. Si la pieza es un `Polígono convexo`, el operario hace clic en `Editar figura`, dibuja el contorno en `CustomPieceEditor.jsx`, cierra la figura, ingresa las longitudes y hace clic sobre un vértice en el dibujo para fijar su ángulo interior antes de guardar la pieza[cite: 6, 7, 12].
7. El operario hace clic en `Guardar pedido` o `Guardar cambios`; el sistema aplana los bloques de material y envía la petición a través de `createOrder` o `updateOrder`[cite: 5, 7, 8].

## 7. Flujos alternativos y errores

- Cancelación de edición: Si el usuario cancela la edición de un pedido `PENDIENTE`, el formulario se restablece a su estado original o se cierra sin mutar los datos guardados[cite: 4, 7].
- Error de validación de campos: Si falta seleccionar el `Tipo de vidrio`, el `Espesor del vidrio (mm)`, o si las dimensiones (`width_mm`, `height_mm`, `radius_mm`) o la `Cantidad` son inválidas, se muestra un `FieldError` y el botón de guardado se deshabilita[cite: 7, 13].
- Error de geometría (Polígono): Si el ángulo introducido en un vértice no está entre `0` y `180` grados, excede el límite de `n - 3` vértices fijados, o no permite cerrar una figura convexa, `buildConstrainedGeometry` muestra un error y bloquea la adición de la pieza[cite: 6, 12, 14].
- Error de API: Si `createOrder` o `updateOrder` fallan (ej. 422, 500), se despliega un `FeedbackMessage` de error y los datos introducidos en los bloques se mantienen para permitir un reintento[cite: 5, 7].

## 8. Criterios de aceptación

- CA-01: Un bloque de material permite agrupar y gestionar múltiples piezas que comparten el mismo `Tipo de vidrio` y `Espesor del vidrio (mm)`[cite: 7].
- CA-02: Se pueden agregar múltiples bloques de material dentro de un mismo pedido utilizando el botón `+ Agregar otro material`[cite: 7].
- CA-03: Las piezas se renderizan en una estructura lineal donde los campos cambian instantáneamente al cambiar la `Forma` (`Rectángulo`, `Círculo`, `Polígono convexo`)[cite: 7, 10].
- CA-04: Las etiquetas mostradas al usuario son estrictamente `Tipo de vidrio`, `Espesor del vidrio (mm)`, `Cantidad`, `Figura configurada` y `Editar figura`[cite: 7].
- CA-05: Las peticiones `POST /api/orders` y `PUT /api/orders/:id` mantienen la compatibilidad enviando la estructura plana exigida por `ordersApi.js` y `schemas.py`[cite: 5, 7, 8].
- CA-06: Cancelar una modificación en curso (`mode === 'edit'`) restaura de inmediato los valores originales del pedido sin afectar la persistencia[cite: 4, 7].
- CA-07: Dentro de `CustomPieceEditor.jsx`, el usuario puede hacer clic sobre un vértice en el SVG para asignar o liberar su ángulo interior, forzando un recálculo geométrico sin usar selectores `S1/S2`[cite: 6, 12].

## 9. Impacto técnico

### Módulos

- `frontend/src/features/orders/FormularioPedido.jsx`[cite: 7]
- `frontend/src/features/orders/NuevoPedido.css`[cite: 10]
- `frontend/src/features/orders/CustomPieceEditor.jsx`[cite: 6]
- `frontend/src/features/orders/CustomPieceEditor.css`[cite: 9]
- `frontend/src/features/orders/__tests__/FormularioPedido.test.jsx` y `CustomPieceEditor.test.jsx`[cite: 13, 14]

### API

- Ninguno. Se reutliza la integración actual de `listOrderMaterials`, `createOrder`, `getOrder` y `updateOrder` en `ordersApi.js`[cite: 5].

### Base de datos / migración

- Ninguno. Se respeta la estructura y validaciones de `schemas.py`[cite: 8].

### UI

- Reorganización total en bloques de material, vista lineal para las piezas en el modal[cite: 4, 7, 10], y SVG interactivo (vértices clicables) en `CustomPieceEditor.jsx`[cite: 6, 9].

## 10. Pruebas previstas

- Validación de estado con un material y varias piezas (`FormularioPedido.test.jsx`)[cite: 7, 13].
- Validación de estado con varios materiales en un pedido (`FormularioPedido.test.jsx`)[cite: 7, 13].
- Limpieza de datos al cambiar la forma geométrica en la fila lineal (`RECTANGULO`, `CIRCUNFERENCIA`, `POLIGONO_CONVEXO`)[cite: 7, 13].
- Completitud del flujo de creación de pedido (`POST /api/orders`)[cite: 5, 7, 13].
- Completitud del flujo de edición de pedido (`PUT /api/orders/:id`)[cite: 5, 7, 13].
- Restauración segura del estado original al cancelar la edición[cite: 4, 7, 13].
- Validaciones estrictas de campos y geometría por material y pieza[cite: 7, 13].
- Interacción por clics en vértices dentro del canvas del `CustomPieceEditor.test.jsx` para modificar ángulos[cite: 6, 12, 14].

## 11. Evidencias requeridas

- Aprobación del 100% de las pruebas automatizadas en `vitest` para los módulos modificados[cite: 13, 14].
- Código fusionado en la rama `feature/S1-orders-material-flow` respetando las restricciones de no modificar base de datos ni contratos de API.

## Historial de estado

- Draft
- Reviewed
- Implemented
- Verified