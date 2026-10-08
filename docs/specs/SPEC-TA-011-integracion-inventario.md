# SPEC-TA-011 - Integración de stock

## 1. Información general

| Campo | Valor |
|---|---|
| Estado | Verified |
| PBI relacionado | TA-011 — Integración de stock |
| Responsable | Fabricio A. / Fabricio M. |
| Reviewer | Pendiente |
| Épica | EP-001 — Módulo de gestión de inventario de vidrio |
| Sprint | Sprint 1 |

## 2. Objetivo

Completar el flujo de planchas y retazos desde React hasta PostgreSQL, conectando la interfaz de stock con la API existente.

La integración debe permitir crear, listar y editar inventario mediante la API, comprobar la persistencia en PostgreSQL y mostrar al usuario los errores de validación. Debe usar la autenticación/JWT vigente y conservar desacoplados los formularios existentes.

## 3. Dependencias

- TA-003.
- HU-004.
- HU-005.

## 3. Alcance

- Construcción de la pantalla principal de Gestión de Inventario.
- Incorporación de dos vistas o pestañas: **Planchas** y **Retazos**.
- Creación de la capa frontend `inventoryApi.js` para centralizar las solicitudes de inventario.
- Obtención del catálogo real de tipos de vidrio y espesores mediante `GET /api/inventory/tipos-vidrio`.
- Listado de planchas mediante `GET /api/inventory/planchas`.
- Registro de planchas mediante `POST /api/inventory/planchas`.
- Edición y cambio de estado de planchas mediante `PATCH /api/inventory/planchas/{id_plancha}`.
- Listado de retazos mediante `GET /api/inventory/retazos`.
- Registro de retazos mediante `POST /api/inventory/retazos`.
- Edición y cambio de estado de retazos mediante `PATCH /api/inventory/retazos/{id_retazo}`.
- Refresco de los listados después de operaciones exitosas.
- Búsqueda y filtros básicos por tipo, espesor y estado sobre los datos disponibles, sin inventar parámetros de consulta no soportados por el backend.
- Estados visibles de carga, vacío, error y éxito.
- Manejo visible de respuestas HTTP `401`, `403`, `409` y `422`.
- Verificación de los flujos React → API → PostgreSQL/Supabase → consulta/listado.
- Disponibilización de los datos de planchas y retazos mediante la API integrada para su consumo posterior por HU-008.

La capa `inventoryApi.js` será responsable de las solicitudes HTTP y del contrato de transporte. `RegistrarPlanchaForm` y `RegistrarRetazoForm` continuarán recibiendo datos y callbacks por props, sin realizar llamadas HTTP directamente.

## 4. Fuera de alcance

- Dashboard general.
- Kardex.
- Costos.
- Historial de movimientos.
- CRUD administrativo del catálogo.
- Pedidos.
- Rasterización.
- FF/BF/WF.
- Resultados de optimización.
- Implementación de HU-008 — Stock compatible.
- Cambios al backend no requeridos por los contratos ya disponibles.

## 5. Actor y precondiciones

- **Actores de consulta:** Administrador, Almacenero y Operario, con permiso `CONSULTAR_STOCK`.
- **Actores de gestión:** Administrador y Almacenero, con `GESTIONAR_PLANCHAS` o `GESTIONAR_RETAZOS` según la entidad.
- **Precondiciones:**
  - El usuario debe autenticarse mediante `POST /api/auth/login`.
  - El cliente debe enviar `Authorization: Bearer <access_token>` en las solicitudes protegidas.
  - El catálogo debe estar disponible para seleccionar un tipo activo y una combinación de espesor válida.
  - El usuario debe conservar una sesión válida durante la operación.

## 6. Estado actual inspeccionado

La SPEC se basa en los contratos observados en el backend y frontend actuales, sin inventar endpoints ni campos.

### 6.1 Backend disponible

| Recurso | Método y endpoint | Permiso | Respuesta observada |
|---|---|---|---|
| Catálogo | `GET /api/inventory/tipos-vidrio` | `CONSULTAR_TIPOS_VIDRIO` | `200`, lista de tipos con `id_tipo_vidrio`, `nombre`, `descripcion`, `estado` y `espesores_mm` |
| Planchas | `GET /api/inventory/planchas` | `CONSULTAR_STOCK` | `200`, lista de `PlanchaResponse` |
| Planchas | `POST /api/inventory/planchas` | `GESTIONAR_PLANCHAS` | `201`, `PlanchaResponse` |
| Planchas | `PATCH /api/inventory/planchas/{id_plancha}` | `GESTIONAR_PLANCHAS` | `200`, `PlanchaResponse` |
| Retazos | `GET /api/inventory/retazos` | `CONSULTAR_STOCK` | `200`, lista de `RetazoResponse` |
| Retazos | `POST /api/inventory/retazos` | `GESTIONAR_RETAZOS` | `201`, `RetazoResponse` |
| Retazos | `PATCH /api/inventory/retazos/{id_retazo}` | `GESTIONAR_RETAZOS` | `200`, `RetazoResponse` |

Los endpoints de actualización aceptan campos parciales y permiten `estado: true | false`. Un PATCH vacío o con valores `null` explícitos se rechaza con `422`.

### 6.2 Catálogo real

La respuesta de `GET /api/inventory/tipos-vidrio` tiene esta forma:

```json
{
  "id_tipo_vidrio": 1,
  "nombre": "Incoloro",
  "descripcion": null,
  "estado": true,
  "espesores_mm": [3, 4, 5.5, 6, 8, 10, 12]
}
```

El frontend debe filtrar tipos activos para la selección y derivar los espesores de `espesores_mm` del tipo seleccionado. No debe asumir IDs ni espesores fijos.

### 6.3 Contratos de creación

Plancha:

```json
{
  "ancho_mm": 1000,
  "alto_mm": 500,
  "espesor_mm": 5.5,
  "cantidad": 10,
  "id_tipo_vidrio": 1
}
```

La respuesta agrega `id_plancha`, `estado` y `fecha_registro`.

Retazo:

```json
{
  "codigo": "RET-001",
  "espesor_mm": 4,
  "geometria": {
    "type": "RECTANGULO",
    "width_mm": 100,
    "height_mm": 50
  },
  "id_tipo_vidrio": 1
}
```

La respuesta agrega `id_retazo`, `area_mm2`, `estado`, `fecha_registro` e `id_ejecucion_origen`. El área es calculada por backend y no se envía desde React; en registros manuales `id_ejecucion_origen` queda en `null`.

Las geometrías admitidas para retazos son `RECTANGULO`, `CIRCUNFERENCIA` y `POLIGONO_CONVEXO`.

### 6.4 Autenticación y permisos

El login actual es `POST /api/auth/login` y entrega un `access_token` Bearer junto con los datos del usuario. El frontend debe reutilizar el mecanismo de sesión existente y no duplicar la lógica de autenticación.

| Operación | Administrador | Almacenero | Operario |
|---|---:|---:|---:|
| Consultar catálogo | Sí | Sí | Sí |
| Consultar stock | Sí | Sí | Sí |
| Crear/editar planchas | Sí | Sí | No |
| Crear/editar retazos | Sí | Sí | No |

### 6.5 Contratos frontend existentes

Los formularios existentes permanecen desacoplados de HTTP:

- `RegistrarPlanchaForm({ catalogo, onSubmit, isSubmitting, onCancel })` emite dimensiones, cantidad, espesor e `id_tipo_vidrio` mediante `onSubmit`.
- `RegistrarRetazoForm({ catalogo, onSubmit, isSubmitting, onCancel })` emite código, espesor, geometría e `id_tipo_vidrio` mediante `onSubmit`.
- `RegistrarPlanchaPage` y `RegistrarRetazoPage` componen el formulario correspondiente dentro de `AppShell`.
- `AppShell`, `Sidebar` y `PageLayout` deben reutilizarse para conservar la línea visual y la navegación establecida.

Actualmente `App.jsx` no monta estas páginas para una integración de inventario y no existe `inventoryApi.js`.

## 7. Diseño funcional propuesto

### 7.1 Pantalla principal

La pantalla de Gestión de Inventario debe:

1. Usar `AppShell` y `PageLayout`.
2. Mostrar un encabezado contextual y acciones compatibles con los permisos de la sesión.
3. Presentar las pestañas **Planchas** y **Retazos**.
4. Mantener estable la navegación y el contenido principal al cambiar de pestaña.
5. Cargar catálogo y listado con la sesión autenticada.
6. Mostrar acciones de registrar, editar y cambiar estado solo cuando correspondan al permiso del usuario.

### 7.2 Listados

Cada pestaña debe mostrar los campos relevantes de su respuesta:

- **Planchas:** dimensiones, espesor, cantidad, tipo, estado y fecha de registro.
- **Retazos:** código, tipo, espesor, geometría resumida, área, estado, fecha de registro e `id_ejecucion_origen` cuando corresponda.

Los filtros básicos por tipo, espesor y estado se aplicarán sobre los datos disponibles en frontend, porque los endpoints actuales de listado no exponen parámetros de filtro documentados. La búsqueda no debe modificar el contrato API sin una brecha aprobada.

### 7.3 Registro y edición

Las páginas y formularios existentes se reutilizarán. La capa contenedora debe:

- cargar y entregar el catálogo real mediante `catalogo`;
- traducir `onSubmit` a la solicitud de `inventoryApi.js`;
- pasar `isSubmitting` durante la operación;
- mostrar éxito o error sin trasladar HTTP al formulario;
- refrescar el listado tras una creación o edición exitosa;
- usar PATCH para editar campos permitidos y para cambiar `estado`.

### 7.4 Estados de interfaz

La pantalla debe contemplar de forma visible:

- carga inicial de catálogo y listados;
- listado vacío sin tratarlo como error;
- éxito después de crear, editar o cambiar estado;
- error de red o de servidor con opción de reintento cuando corresponda;
- sesión expirada o respuesta `401` con solicitud de autenticación nuevamente;
- respuesta `403` con mensaje de permisos insuficientes;
- respuesta `409` con mensaje de conflicto, por ejemplo código duplicado;
- respuesta `422` con errores de validación cercanos al formulario o al campo correspondiente.

## 8. Relación con HU-008 — Stock compatible

- HU-008 pertenece también a EP-001.
- HU-008 es un PBI independiente de TA-011.
- HU-008 filtrará planchas y retazos por `id_tipo_vidrio` y `espesor_mm`.
- TA-011 solo debe asegurar que esos datos estén correctamente disponibles mediante la API integrada.
- HU-008 tendrá su propia SPEC e implementación.
- Reserva, consumo y descuento de inventario no corresponden a HU-008.

## 9. Reglas de negocio y errores

1. El catálogo debe provenir de `GET /api/inventory/tipos-vidrio` y las combinaciones tipo/espesor deben validarse contra `espesores_mm`.
2. Las validaciones de dimensiones, cantidad, espesor y geometría son responsabilidad compartida: feedback local en los formularios y validación definitiva en backend.
3. El cliente no debe enviar campos calculados o asignados por backend, como `area_mm2` de retazos.
4. Las operaciones de gestión requieren el permiso específico de la entidad.
5. Toda respuesta exitosa de creación, edición o cambio de estado debe actualizar el listado visible.
6. Las respuestas `401`, `403`, `409` y `422` deben producir mensajes visibles y accionables sin ocultar el error en consola.
7. El frontend no debe asumir que una respuesta exitosa implica persistencia sin verificar el flujo mediante consulta/listado en la prueba de aceptación.

## 10. Impacto técnico

### Frontend

- Crear `frontend/src/features/inventory/inventoryApi.js`.
- Integrar la sesión/JWT actual en las solicitudes.
- Incorporar la pantalla, pestañas, listados, filtros y estados de inventario.
- Integrar `RegistrarPlanchaPage` y `RegistrarRetazoPage` sin mover HTTP a los formularios.
- Reutilizar `AppShell`, `Sidebar`, `PageLayout` y tokens/estilos compartidos.
- Mantener labels visibles, foco, mensajes próximos al campo y navegación estable.

### Backend y persistencia

No se prevén cambios de backend para consumir los endpoints ya disponibles. Si la verificación de HU-008 demuestra una brecha de contrato para stock transaccional, esta debe documentarse y aprobarse antes de cualquier cambio backend.

La persistencia de las operaciones se verificará contra PostgreSQL/Supabase mediante consultas posteriores y no solo mediante la respuesta inmediata de la API.

## 11. Criterios de aceptación

- **T01:** La pantalla de Gestión de Inventario se integra con la navegación existente, reutiliza `AppShell`, `Sidebar` y `PageLayout`, y ofrece las pestañas Planchas y Retazos sin rediseñar innecesariamente los formularios existentes.
- **T02:** `inventoryApi.js` obtiene el catálogo real mediante `GET /api/inventory/tipos-vidrio` y entrega a ambos formularios tipos activos con sus espesores reales, sin hardcodear IDs ni espesores.
- **T03:** Un usuario autorizado puede listar planchas y retazos desde la API autenticada y visualizar estados vacío, loading, error y éxito de forma visible.
- **T04:** Un usuario autorizado puede registrar una plancha desde React; la solicitud usa `POST /api/inventory/planchas`, respeta el contrato actual y el listado se refresca tras HTTP 201.
- **T05:** Un usuario autorizado puede editar una plancha y cambiar su estado mediante `PATCH /api/inventory/planchas/{id_plancha}`; tras HTTP 200 el listado muestra los datos actualizados.
- **T06:** Un usuario autorizado puede registrar un retazo desde React; la solicitud usa `POST /api/inventory/retazos`, conserva el cálculo de `area_mm2` en backend y el listado se refresca tras HTTP 201.
- **T07:** Un usuario autorizado puede editar un retazo y cambiar su estado mediante `PATCH /api/inventory/retazos/{id_retazo}`; tras HTTP 200 el listado muestra los datos actualizados.
- **T08:** La interfaz ofrece filtros o búsqueda básica por tipo, espesor y estado sobre los datos cargados, sin afirmar que el backend soporte parámetros de consulta inexistentes.
- **T09:** Las respuestas HTTP 401, 403, 409 y 422 se presentan mediante mensajes visibles y comprensibles; no se exponen secretos, contraseñas, hashes ni JWT.
- **T10:** Los formularios `RegistrarPlanchaForm` y `RegistrarRetazoForm` no realizan HTTP directamente y continúan funcionando mediante props y callbacks.
- **T11:** Se verifica al menos un flujo completo de plancha y uno de retazo: React → API autenticada → PostgreSQL/Supabase → consulta/listado posterior, con evidencia de los datos persistidos.
## 12. Pruebas planificadas

- Pruebas de la capa `inventoryApi.js` para catálogo, listados, creación, edición, cambio de estado y propagación de errores.
- Pruebas de integración de la pantalla con sesión autenticada y permisos de Administrador, Almacenero y Operario.
- Verificación manual o automatizada de estados loading, vacío, éxito y error.
- Verificación de respuestas `401`, `403`, `409` y `422` con mensajes visibles.
- Verificación de filtros por tipo, espesor y estado.
- Flujo completo de creación de una plancha y un retazo, consulta posterior y comprobación en PostgreSQL/Supabase.
- Flujo de edición y cambio de estado para ambas entidades.

## 13. Evidencias esperadas

Directorio previsto: `docs/evidence/sprint-01/TA-011/`.

| Archivo | Contenido previsto |
|---|---|
| `integracion-inventario.md` | Pantalla, pestañas, navegación, catálogo, listados y estados de interfaz |
| `operaciones-api-bd.md` | Solicitudes autenticadas, respuestas, consultas posteriores y persistencia de planchas y retazos |
| `prueba-funcional.md` | Casos válidos, permisos, errores HTTP, filtros, refresco y flujo completo |

No se deben inventar capturas, respuestas, consultas de base de datos ni resultados de pruebas. Las credenciales, contraseñas, hashes y JWT deben excluirse de cualquier evidencia.

## 14. Historial de estado

- **Draft — 06/10/2026:** Especificación creada después de inspeccionar los contratos actuales de inventario, autenticación, permisos y componentes React. Se identificaron las brechas de integración frontend y navegación. HU-008 queda como trabajo posterior e independiente dentro de EP-001. Implementación pendiente.
- **Specified — 06/10/2026:** Especificación revisada y alineada con el backlog v3.2. Se aprueba el alcance de integración E2E del módulo de inventario para planchas y retazos mediante React → FastAPI → PostgreSQL/Supabase. HU-008 permanece como PBI independiente para stock compatible por tipo y espesor.
- **Verified — 08/10/2026:** Cierre técnico T01–T11 según la [auditoría final](../evidence/sprint-01/TA-011/prueba-funcional.md#auditoría-y-cierre--8-de-octubre-de-2026): PF-01–28 existentes, confirmaciones manuales previas del usuario para 401/403/422 y persistencia, revisión de cobertura backend y cuatro casos componente de Inventario PASS. Lint y build PASS. Las fuentes manuales, estáticas y automatizadas se distinguen en la matriz; no se repitieron altas ni se modificó la BD. Reviewer pendiente; sin commit, push ni PR en esta intervención.
