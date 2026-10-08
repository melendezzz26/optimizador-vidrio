# SPEC-HU-006 — Registrar pedido

## Información general

| Campo | Valor |
|---|---|
| Estado | Reviewed |
| PBI relacionado | HU-006 (Incluye T01, T02, T03, T04) |
| Responsable | Luis Anthony Ibañez Herrera |
| Reviewer | Andro Joseph Quispe Cesias |

## 1. Objetivo

Permitir a un Operario crear un pedido definiendo el tipo de vidrio y el espesor, agregando múltiples piezas con formas estándar (indicando sus medidas y cantidades) de manera estructurada antes de confirmar y persistir la operación en la base de datos.

## 2. Alcance

### Incluye

- Diseño y validación del formulario frontend por secciones (datos del pedido → piezas → guardar).
- Construcción del endpoint y casos de uso en el módulo `orders`.
- Registro en PostgreSQL preservando las medidas estándar y geometría normalizada en formato JSONB.
- Verificación y validación de tipos, medidas y campos obligatorios.

### Fuera de alcance

- Ejecución del motor de optimización (First Fit / Best Fit / Worst Fit) sobre el pedido, ya que corresponde a una etapa posterior del flujo.

## 3. Actor y precondiciones

**Actor:** Operario.

**Precondiciones:**

- El usuario debe poseer una sesión activa.
- El usuario debe presentar un token JWT válido verificado por el backend.

## 4. Entradas y datos

| Campo / dato | Tipo / formato | Regla |
|---|---|---|
| Tipo de vidrio | FK (TIPO_VIDRIO) | Debe existir en el catálogo y estar activo. |
| Espesor | NUMERIC(4,1) | Limitado al dominio permitido (3, 4, 5.5, 6, 8). |
| Tipo de forma | VARCHAR | RECTANGULO, CIRCUNFERENCIA o POLIGONO_CONVEXO. |
| Cantidad | INTEGER | Estrictamente mayor a 0. |
| Dimensiones | Estructura / JSONB | Evaluadas y almacenadas en milímetros (mm). |

## 5. Reglas de negocio

- RN-01: El espesor seleccionado debe pertenecer estrictamente al dominio permitido: 3, 4, 5.5, 6, 8 mm.
- RN-02: El pedido creado recibirá por defecto el estado `PENDIENTE`.
- RN-03: Las longitudes deben evaluarse y almacenarse en milímetros (mm), y las áreas en mm².
- RN-04: La cantidad de una pieza solicitada debe ser estrictamente mayor a 0 (`CHECK > 0`).
- RN-05: Todo control interactivo del formulario debe mostrar un estado de foco visible y mensajes de error específicos en texto, sin depender únicamente del color para indicar fallas (cumplimiento WCAG 2.2 AA).

## 6. Flujo principal

1. El Operario navega a la pantalla "Nuevo pedido".
2. Selecciona el tipo de vidrio y el espesor en la sección "Datos del pedido".
3. Utiliza la sección "Piezas del pedido" para ingresar el tipo de forma, dimensiones y cantidad.
4. El sistema valida los datos de la pieza y la añade a la lista local (estado de la UI).
5. El Operario hace clic en "Guardar pedido".
6. El frontend previene envíos duplicados activando un estado `loading` o `disabled`.
7. El backend valida el payload y persiste la cabecera `PEDIDO` y sus registros relacionados en `PIEZA` de forma transaccional.

## 7. Flujos alternativos y errores

- Si el formulario carece de tipo de vidrio o espesor, el botón de "Agregar pieza" explicará visiblemente por qué se encuentra deshabilitado.
- Si se ingresan medidas negativas o valores nulos, los campos de Input presentarán el estado de `Error` y un mensaje explícito cerca del control.
- Si el payload recibido por la API incumple el contrato o los esquemas, el backend retornará `422 Unprocessable Entity` sin exponer el stack trace al cliente.

## 8. Criterios de aceptación

- CA-01 (T01): El formulario solicita tipo y espesor del vidrio y permite añadir más de una pieza al mismo pedido antes de guardarlo en la base de datos.
- CA-02 (T02): El backend crea un pedido con sus piezas relacionadas en PostgreSQL y permite recuperar el pedido completo mientras se encuentre en edición.
- CA-03 (T03): Se pueden registrar las formas estándar aprobadas con sus medidas y cantidad; cada pieza almacenada conserva tipo de forma, dimensiones originales en JSONB, cantidad y referencia al pedido.
- CA-04 (T04): Las pruebas unitarias y de integración de la API garantizan que cantidades no positivas, medidas no válidas y campos obligatorios faltantes sean rechazados correctamente, conservando el resultado de cada caso.

## 9. Impacto técnico

### Módulos

- Módulo funcional `orders` (aplicando las capas de Presentation, Application, Domain e Infrastructure).

### API

- Creación de rutas `POST /api/orders` exponiendo schemas de transporte formales.

### Base de datos / migración

- Inserción sobre las tablas `PEDIDO` y `PIEZA`.
- No requiere nueva migración si la v1.1 ya está implementada.

### UI

- Adaptación visual de la pantalla "Nuevo pedido" para reducir la competencia del fondo.
- Implementación de Empty State ("No hay piezas agregadas") y estados correctos de botones.

## 10. Pruebas previstas

- Unitarias (Caja Blanca): Reglas de validación de piezas, schemas y geometrías en la capa `Domain`.
- API (Caja Negra): Validación HTTP, 422 para errores de entrada y 403 en caso de violación de permisos de rol.
- Frontend: Pruebas de componente para garantizar renderizado de validaciones visibles y estados `loading`.

## 11. Evidencias requeridas

- Logs de salida de CI (GitHub Actions) demostrando ejecución exitosa de pruebas automatizadas (pytest y frontend).
- Reporte Lighthouse demostrando cumplimiento de los criterios prioritarios (contraste mínimo, asociación de labels).
- Capturas de pantalla de la interfaz con los estados `default`, `focus`, `error` y `disabled` gestionados.

## Historial de estado

- Draft (Completado)
- Reviewed (Actual)
- Implemented
- Verified