# SPEC-HU-004 — Registrar plancha comercial

## Información general

| Campo | Valor |
|---|---|
| Estado | Verified |
| PBI relacionado | HU-004 |
| Épica | EP-002 — Inventario |
| Sprint | Sprint 1 |
| Responsable principal | Fabricio A. |
| Colaborador | Fabricio M. |
| Dependencias | TA-003 y TA-013 |
| Integración E2E posterior | TA-011 |

## 1. Objetivo

Permitir al almacenero registrar una plancha comercial para incorporarla al stock de NewGlass. HU-004 comprende el formulario, sus validaciones y la comprobación de creación, consulta y persistencia mediante la API existente.

**Historia de usuario:**

> Como almacenero, quiero registrar una plancha comercial para incorporarla al stock.

La comprobación API/BD se realiza de forma independiente del formulario. La integración E2E completa React → API → PostgreSQL corresponde a TA-011.

## 2. Alcance

### Incluye

- Formulario de registro de plancha con tipo de vidrio, espesor, ancho en mm, alto en mm y cantidad.
- Identificación de campos obligatorios y validación de campos vacíos y valores positivos.
- Validación de cantidad entera y compatibilidad tipo–espesor según TA-013.
- Comprobación de creación y consulta mediante la API existente.
- Comprobación de persistencia en PostgreSQL/Supabase en el entorno de verificación acordado.
- Un caso funcional válido y al menos dos inválidos, con sus resultados y evidencias de HU-004.

### Fuera de alcance

- React Router y navegación definitiva.
- CRUD completo de inventario desde React, incluido listado y edición E2E.
- Gestión de retazos y administración dinámica del catálogo.
- Nuevas migraciones y cambios de esquema de base de datos.
- Lógica de optimización.
- Integración E2E completa React → API → PostgreSQL, correspondiente a TA-011.
- Incorporación de una nueva librería global de estado para esta HU.

## 3. Actor y precondiciones

**Actor:** Almacenero.

**Precondiciones:**

- TA-003 y TA-013 están implementadas y disponibles en el entorno de verificación.
- Existe un catálogo persistido de tipos de vidrio y combinaciones tipo–espesor.
- La API de inventario y PostgreSQL/Supabase están disponibles para las comprobaciones previstas.
- Las comprobaciones API utilizan la autenticación y los permisos existentes para registrar y consultar planchas.

## 4. Entradas y datos

| Campo / dato | Tipo / formato | Obligatorio | Regla |
|---|---|---|---|
| Tipo de vidrio / `id_tipo_vidrio` | Selector; identificador entero | Sí | Tipo existente y activo del catálogo |
| Espesor / `espesor_mm` | Selector; valor decimal en mm | Sí | Compatible con el tipo seleccionado |
| Ancho / `ancho_mm` | Decimal en mm | Sí | Mayor que 0 |
| Alto / `alto_mm` | Decimal en mm | Sí | Mayor que 0 |
| Cantidad / `cantidad` | Entero | Sí | Mayor que 0 |

El catálogo procede de TA-013. El frontend no debe duplicar ni hardcodear las combinaciones tipo–espesor ni asumir identificadores fijos.

## 5. Reglas de negocio

- **RN-01:** El ancho debe ser mayor que cero.
- **RN-02:** El alto debe ser mayor que cero.
- **RN-03:** La cantidad debe ser un entero mayor que cero.
- **RN-04:** El tipo de vidrio es obligatorio.
- **RN-05:** El espesor es obligatorio y debe ser compatible con el tipo seleccionado.
- **RN-06:** Al cambiar el tipo de vidrio, debe limpiarse el espesor seleccionado previamente.
- **RN-07:** El formulario no debe procesarse ni invocar la función de envío si existen errores de validación.
- **RN-08:** Backend y base de datos mantienen la validación final; la validación del formulario no sustituye sus reglas de integridad.

## 6. Flujo principal

1. El almacenero visualiza el formulario y los campos obligatorios.
2. Selecciona un tipo de vidrio del catálogo recibido.
3. Selecciona un espesor admitido para ese tipo.
4. Ingresa ancho y alto en mm y una cantidad entera positiva.
5. Solicita el registro y el formulario valida los datos.
6. Si los datos son válidos, el formulario invoca la función de envío recibida con los datos de la plancha.
7. Como comprobación independiente de T02, se envía un alta válida mediante la API existente.
8. Se consulta el registro mediante la API y se comprueba su persistencia en PostgreSQL/Supabase.

Los pasos de comprobación API/BD no implican cerrar la integración E2E desde React en esta HU; dicha conexión completa corresponde a TA-011.

## 7. Flujos alternativos y errores

- Campo obligatorio vacío: mostrar el error y bloquear el procesamiento.
- Ancho o alto menor o igual a cero: rechazar el valor.
- Cantidad no entera o menor o igual a cero: rechazar el valor.
- Cambio de tipo: limpiar el espesor y exigir una selección compatible.
- Tipo inexistente o inactivo, o combinación tipo–espesor inválida: rechazar el registro conforme al catálogo y la validación backend.
- Error del servidor durante la comprobación API: registrar el resultado y no asumir que la plancha fue persistida.

## 8. Criterios de aceptación

### T01 — Diseñar formulario

- **CA-01:** Contiene ancho, alto, tipo de vidrio, espesor y cantidad.
- **CA-02:** Los campos obligatorios están identificados.
- **CA-03:** No procesa el formulario con campos obligatorios vacíos.

### T02 — Integrar registro con API y BD

- **CA-04:** Un registro válido enviado mediante la API existente crea una plancha en PostgreSQL.
- **CA-05:** Una consulta posterior devuelve el registro creado.
- **CA-06:** Se respetan las combinaciones tipo–espesor de TA-013.

La aceptación de T02 verifica API y persistencia; la integración E2E completa del formulario React corresponde a TA-011.

### T03 — Validar datos

- **CA-07:** Rechaza ancho no positivo.
- **CA-08:** Rechaza alto no positivo.
- **CA-09:** Rechaza cantidad no positiva o no entera.
- **CA-10:** Rechaza campos obligatorios faltantes.
- **CA-11:** Rechaza combinaciones tipo–espesor inválidas y limpia el espesor seleccionado al cambiar el tipo.

### T04 — Prueba funcional

- **CA-12:** Se documenta al menos un caso válido.
- **CA-13:** Se documentan al menos dos casos inválidos.
- **CA-14:** Cada caso registra entrada, resultado esperado, resultado obtenido y estado.

## 9. Impacto técnico

### Módulos

- Nuevo código de inventario en `frontend/src/features/inventory/`, siguiendo la organización por funcionalidades del repositorio.
- No añadir lógica de inventario a `frontend/src/pages/NuevoPedido.jsx`.
- Reutilizar el módulo backend de inventario existente de TA-003 y el catálogo de TA-013.

### API

| Método y ruta | Uso |
|---|---|
| `GET /api/inventory/tipos-vidrio` | Consultar tipos y sus `espesores_mm` admitidos |
| `POST /api/inventory/planchas` | Crear una plancha |
| `GET /api/inventory/planchas` | Consultar las planchas y verificar el registro creado |

Ejemplo conceptual de creación:

```json
{
  "ancho_mm": 3210,
  "alto_mm": 2250,
  "espesor_mm": 6,
  "cantidad": 2,
  "id_tipo_vidrio": 1
}
```

El identificador `1` es ilustrativo: debe utilizarse un tipo real del catálogo que admita 6 mm. No se requieren nuevos endpoints.

### Base de datos / migración

- Comprobar la persistencia de la plancha mediante la API y una consulta a PostgreSQL/Supabase en el entorno de verificación acordado.
- Utilizar la integridad tipo–espesor introducida por TA-013.
- No crear migraciones ni modificar el esquema de base de datos.

### UI

- El formulario debe quedar desacoplado para recibir catálogo, función de envío y estado de carga.
- Los espesores disponibles dependen del tipo seleccionado y del catálogo recibido.
- No duplicar ni hardcodear el catálogo.
- No agregar React Router ni una nueva librería global de estado.
- La navegación definitiva, la conexión E2E con autenticación/API y la actualización del inventario en la interfaz corresponden a TA-011.

## 10. Pruebas previstas

### Formulario

- Validación manual de los cinco campos y de la identificación de obligatorios.
- Comprobar rechazo de campos vacíos, dimensiones no positivas y cantidad no positiva o no entera.
- Comprobar que el cambio de tipo limpia el espesor y actualiza las opciones compatibles.
- Comprobar que los errores impiden invocar la función de envío y que se utiliza el estado de carga recibido.
- Ejecutar desde `frontend/`:

```sh
npm run lint
npm run build
```

No se incorporará un framework de pruebas frontend únicamente por esta HU si el repositorio no dispone de uno.

### API, persistencia y prueba funcional

| Caso previsto | Entrada | Resultado esperado |
|---|---|---|
| Válido | Tipo existente y activo que admita 6 mm, ancho 3210 mm, alto 2250 mm y cantidad 2 | Alta aceptada, registro persistido y recuperable mediante consulta posterior |
| Inválido: valor no positivo | Datos válidos salvo `ancho_mm: 0` | Alta rechazada; no se crea una plancha |
| Inválido: combinación | Tipo Espejo obtenido del catálogo con `espesor_mm: 8` y demás campos válidos | Alta rechazada por incompatibilidad; no se crea una plancha |

La consulta posterior utiliza `GET /api/inventory/planchas` y contrasta el registro con PostgreSQL/Supabase. Las verificaciones funcionales y visuales reportadas por el usuario quedaron completadas el 05/10/2026; los resultados obtenidos y estados se documentan en las evidencias de HU-004. La comprobación del formulario utilizó un montaje temporal sin HTTP, separado de los casos API/BD. Lighthouse no se ejecutó y la integración E2E completa sigue fuera del alcance, en TA-011.

## 11. Evidencias requeridas

Directorio previsto: `docs/evidence/sprint-01/HU-004/`.

| Archivo | Contenido previsto |
|---|---|
| `formulario-plancha.md` | Campos, obligatorios, comportamiento del formulario y capturas pertinentes |
| `registro-api-bd.md` | Solicitud de alta, respuesta, consulta posterior y comprobación de persistencia |
| `validaciones-plancha.md` | Reglas verificadas, errores y resultados de lint/build |
| `prueba-funcional.md` | Al menos un caso válido y dos inválidos, cada uno con entrada, resultado esperado, resultado obtenido y estado |

## Historial de estado

- **Draft:** Especificación de HU-004 normalizada; implementación y verificación pendientes.
- **Verified — 05/10/2026:** T01, T02, T03 y T04 verificadas según los resultados reportados: formulario y validaciones, comprobación API/BD y prueba funcional. Se comprobaron manualmente los estados normal, error y loading/disabled, el payload numérico, foco/navegación y responsive aproximadamente a 375 px. El montaje temporal fue retirado y `App.jsx` está restaurado. Evidencias en [HU-004](../evidence/sprint-01/HU-004/formulario-plancha.md). Lighthouse no ejecutado; TA-011 permanece fuera del alcance.
