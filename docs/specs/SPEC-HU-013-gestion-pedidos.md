# SPEC-013 — Gestionar pedidos

## Información general

| Campo | Valor |
|---|---|
| Estado | Draft |
| PBI relacionado | HU-013 |
| Responsable | Luis Anthony Ibañez Herrera |
| Reviewer | Equipo de Desarrollo |

## 1. Objetivo

Permitir a los operarios buscar, listar y filtrar los pedidos existentes en el sistema para facilitar su localización. Además, establecer un control de concurrencia e integridad (máquina de estados) que permita la visualización y edición segura de los pedidos y sus piezas, restringiendo las modificaciones exclusivamente a aquellos en estado "PENDIENTE".

## 2. Alcance

### Incluye

- Pantalla de listado de pedidos con soporte para paginación.
- Controles de búsqueda y filtros por cliente, fecha y estado.
- Visualización detallada de las piezas de un pedido seleccionado.
- Edición y eliminación de piezas (material, espesor, forma, medidas) para pedidos en estado `PENDIENTE`.
- Bloqueo de UI (solo lectura) para estados avanzados.

### Fuera de alcance

- Motor de cálculo algorítmico o visualización del plano de corte (corresponde a HU de Optimización).
- Facturación, gestión de cobros o reportes financieros del pedido.
- Creación de pedidos nuevos (ya abordado en HU-006).

## 3. Actor y precondiciones

**Actor:** Operario / Administrador

**Precondiciones:**

- El usuario debe estar autenticado en el sistema con un token JWT válido.
- La base de datos debe contener registros de pedidos generados previamente y el catálogo de vidrios activo.
- El modelo `Pedido` en base de datos debe contemplar los campos de `estado` y `cliente`.

## 4. Entradas y datos

| Campo / dato | Tipo / formato | Regla |
|---|---|---|
| Filtro: `estado` | String (Enum) | PENDIENTE, EN_OPTIMIZACION, OPTIMIZADO, CONFIRMADO, CANCELADO |
| Filtro: `fecha` | Date (YYYY-MM-DD) | Búsqueda por coincidencia exacta o rango según implementación. |
| Filtro: `cliente` | String | Búsqueda parcial (ILIKE) o ID si es llave foránea. |
| Payload Edición | JSON Object | Misma estructura estricta anidada de piezas validada en HU-006. |

## 5. Reglas de negocio

- RN-01: **Máquina de estados estricta.** Un pedido solo puede ser modificado (PUT) si su estado actual en la base de datos es `PENDIENTE`. 
- RN-02: **Solo lectura.** Los estados `EN_OPTIMIZACION`, `OPTIMIZADO`, `CONFIRMADO` y `CANCELADO` hacen que el pedido sea inmutable. La interfaz debe deshabilitar los controles y el backend rechazar peticiones de cambio.
- RN-03: **Validación integral.** Al editar o retirar piezas, se debe aplicar la misma validación geométrica de Pydantic utilizada en la creación. No se permiten actualizaciones parciales que dejen un pedido sin piezas o con datos inconsistentes.

## 6. Flujo principal

1. El operario inicia sesión y navega a la vista de "Gestión de pedidos".
2. El sistema carga la tabla con la primera página de pedidos ordenados descendentemente por fecha.
3. El operario utiliza la barra de búsqueda o filtros para localizar un pedido y hace clic en él.
4. El sistema abre la vista de detalle del pedido (modal o nueva ruta).
5. El sistema evalúa el estado: al ser `PENDIENTE`, habilita los inputs y botones de edición.
6. El operario modifica el espesor o retira una de las piezas y hace clic en "Guardar cambios".
7. El backend recibe el PUT, verifica el estado actual en BD, valida el payload y actualiza el registro.
8. El sistema confirma el éxito de la operación y actualiza la tabla de la vista principal.

## 7. Flujos alternativos y errores

- **Intento de edición en estado no válido:** Si la UI falla o hay concurrencia (otro usuario cambió el estado segundos antes), el operario envía el PUT pero el backend detecta un estado distinto a `PENDIENTE`. El sistema aborta la transacción y devuelve un error HTTP 400/403.
- **Validación de esquema fallida:** Si la edición incluye medidas negativas o faltan vértices en un polígono, la API retorna HTTP 422 y se muestra el feedback en la interfaz.

## 8. Criterios de aceptación

- CA-01 (T01): La pantalla muestra listado paginable o acotado, búsqueda y filtros por cliente, estado y fecha; el botón "Nuevo pedido" abre el formulario correctamente.
- CA-02 (T02): El estado PENDIENTE permite edición; EN_OPTIMIZACION, OPTIMIZADO, CONFIRMADO y CANCELADO son solo lectura. Los cambios conservan integridad y permisos.
- CA-03 (T03): Desde un pedido PENDIENTE se puede editar o retirar una pieza de forma individual; la validación se repite y el pedido queda consistente o se revierte sin cambios parciales.

## 9. Impacto técnico

### Módulos

- `orders/application`: Casos de uso de listado y actualización.
- `orders/infrastructure`: Repositorios de lectura/escritura con filtrado.

### API

- `GET /api/orders/`: Endpoint con Query Params (`page`, `limit`, `estado`, `cliente`, `fecha`).
- `GET /api/orders/{id}`: Endpoint para obtener el detalle de un pedido específico.
- `PUT /api/orders/{id}`: Endpoint idempotente para sobreescribir las piezas de un pedido existente.

### Base de datos / migración

- Revisión del modelo SQLAlchemy `Pedido` para garantizar la existencia y tipado de los campos `estado` (Enum), `cliente` y `fecha_creacion`. Generación de migración en Alembic si están ausentes.

### UI

- Creación de componente `GestionPedidos.jsx` (tabla y filtros).
- Refactorización de `NuevoPedido.jsx` o creación de `DetallePedido.jsx` preparado para inyectar datos existentes y aceptar modo "solo lectura" (props `disabled`).

## 10. Pruebas previstas

- Pruebas unitarias/integración en Pytest para `PUT /api/orders/{id}` evaluando el rechazo por estado no permitido (RN-01).
- Pruebas E2E comprobando la correcta renderización de la tabla con filtros activos.
- Verificación manual del bloqueo de UI para un pedido en estado "CANCELADO".

## 11. Evidencias requeridas

- Capturas de pantalla de la tabla paginada funcionando con y sin filtros.
- Capturas de la vista de detalle en modo edición (PENDIENTE) y modo bloqueado.
- Ejecución de la suite de `pytest` validando reglas de negocio en verde.

## Historial de estado

- Draft