# HU-004: matriz de prueba funcional API/BD

## Objetivo y procedencia

Registrar un caso válido y dos inválidos, con entrada, resultado esperado, resultado obtenido y estado, conforme a T04 y CA-12 a CA-14 de la [SPEC HU-004](../../../specs/SPEC-HU-004-registrar-plancha.md).

Los resultados fueron proporcionados por el usuario a partir de su ejecución manual real sobre la API existente y Supabase/PostgreSQL. El 05/10/2026 se verificaron T01, T02, T03 y T04 según su confirmación, incluyendo la revisión funcional y visual del formulario mediante montaje temporal. Se documentan los resultados reportados; no se volvieron a ejecutar durante esta tarea. No se dispone de un hash del despliegue.

Rama de documentación: `feature/HU-004-registrar-plancha`, con cambios sin commit. Se distinguen la matriz API/BD y las verificaciones del montaje temporal React; no se acredita una integración E2E entre ambos.

## Matriz de resultados

Los tres casos utilizan `POST /api/inventory/planchas`. El catálogo consultado permite para Espejo (`id_tipo_vidrio = 6`) los espesores 2, 3, 4 y 6 mm.

| Caso | Entrada | Esperado | Obtenido | Estado |
|---|---|---|---|---|
| 1. Alta válida | Espejo; `id_tipo_vidrio = 6`; `espesor_mm = 6`; `ancho_mm = 3210`; `alto_mm = 2250`; `cantidad = 2` | HTTP 201, persistencia y recuperación mediante consulta posterior. | HTTP 201; `id_plancha = 1`; recuperada por GET y confirmada directamente en Supabase. | PASS |
| 2. Ancho no positivo | Espejo; `id_tipo_vidrio = 6`; `espesor_mm = 6`; `ancho_mm = 0`; `alto_mm = 2250`; `cantidad = 2` | HTTP 422, sin registro. | HTTP 422; mensaje: `Input should be greater than 0`. La consulta final no mostró un registro adicional. | PASS |
| 3. Combinación inválida | Espejo; `id_tipo_vidrio = 6`; `espesor_mm = 8`; `ancho_mm = 3210`; `alto_mm = 2250`; `cantidad = 2` | HTTP 422, sin registro. | HTTP 422; mensaje: `La combinación de tipo de vidrio y espesor no está admitida.` La consulta final no mostró un registro adicional. | PASS |

## Consulta final

Después de los tres casos, `GET /api/inventory/planchas` devolvió solamente:

- `id_plancha = 1`.
- `Count = 1` (cantidad de elementos observados en la consulta; no se afirma que sea un campo de la respuesta HTTP).

La única plancha corresponde al caso válido. Por tanto, los dos casos inválidos no generaron persistencia.

## Verificaciones del formulario en montaje temporal

Resultados manuales reportados por el usuario el 05/10/2026:

| Caso | Entrada | Esperado | Obtenido | Estado |
|---|---|---|---|---|
| Formulario normal y catálogo | Catálogo local con tipos activos e inactivo | Cinco campos obligatorios y selección de espesores según tipo activo | Se observaron los cinco campos, tipos activos y espesores dependientes; cambiar el tipo limpió el espesor. | PASS |
| Errores, foco y navegación | Formulario en estado de error y navegación manual | Errores comprensibles, foco visible y controles semánticos | Mensajes próximos a los campos, no comunicados solo con color; foco visible y navegación comprobados. | PASS |
| Payload válido | `id_tipo_vidrio: 900001`, `espesor_mm: 6`, `ancho_mm: 3210`, `alto_mm: 2250`, `cantidad: 2` | `onSubmit` recibe los cinco valores como números, sin HTTP | Payload numérico verificado mediante el callback de consola. | PASS |
| Loading/disabled | `isSubmitting=true` | Bloqueo visual de envío y layout estable | Controles y botón deshabilitados, texto `Registrando...` y layout estable; prevención visual de doble envío. | PASS |
| Responsive | Anchura aproximada de 375 px | Una columna sin pérdida de uso | Controles utilizables, sin solapamientos ni pérdida funcional observada. | PASS |

Los IDs `900001–900004` eran exclusivamente fixtures locales. El montaje se retiró y se confirmó que `App.jsx` está restaurado, sin fixtures ni referencias temporales a HU-004. El payload de consola no se confunde con la plancha persistida mediante la API, cuyo tipo Espejo tiene ID 6.

La [captura del payload en consola](payload-on-submit.png) muestra los cinco valores numéricos del caso local; está descrita e insertada en [formulario-plancha.md](formulario-plancha.md). También se conservan capturas de [loading](formulario-loading.png), [errores y foco](formulario-validaciones-foco.png) y [disposición en una columna](formulario-responsive-columna.png). Estas imágenes complementan los casos manuales y no prueban la persistencia de la matriz API/BD ni la anchura exacta de 375 px.

## Alcance de la evidencia

El detalle del alta válida, su fecha devuelta y la comprobación directa en base de datos están en [registro-api-bd.md](registro-api-bd.md). Los PASS corresponden exclusivamente a los casos y resultados reportados.

No se incluyen JWT, credenciales ni secretos. La revisión visual y las comprobaciones manuales de foco/navegación constan como reportadas por el usuario; no se adjuntan capturas inexistentes ni se atribuye una auditoría exhaustiva. **Lighthouse no se ejecutó.** La integración E2E completa React → API → PostgreSQL permanece en TA-011.
