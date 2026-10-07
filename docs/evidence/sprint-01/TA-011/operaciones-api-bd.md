# TA-011 — Operaciones API y alcance de evidencia de BD

Se registran las operaciones observadas en los logs y su relación con las
capturas del frontend. Se distinguen la respuesta inmediata de cada operación,
la consulta posterior al registro y el resultado visible en la interfaz.

| Operación observada | Respuesta inmediata de API | Consulta posterior | Visualización posterior en frontend | Evidencia |
| --- | --- | --- | --- | --- |
| GET `/api/inventory/tipos-vidrio` | 200 OK | No aplica: consulta inicial del catálogo. | Nombres Espejo e Incoloro visibles en los listados; el cuerpo de respuesta no se muestra en los logs. | TA011-03; TA011-01 y TA011-02. |
| GET `/api/inventory/planchas` | 200 OK | No aplica: consulta inicial del listado. | Listado de planchas con datos visibles. | TA011-03 y TA011-01. |
| GET `/api/inventory/retazos` | 200 OK | No aplica: consulta inicial del listado. | Listado de retazos con geometría y área legibles. | TA011-03 y TA011-02. |
| POST `/api/inventory/planchas` | 201 Created | GET `/api/inventory/planchas` → 200 OK. | Formulario cerrado, mensaje de éxito y plancha Espejo 6 mm, 1000 × 500 mm, cantidad 2, Activo. Actualización sin F5 informada por el usuario. | TA011-07 y TA011-06. |
| POST `/api/inventory/retazos` | 201 Created | GET `/api/inventory/retazos` → 200 OK. | Formulario cerrado, mensaje de éxito y RET-TA011-E2E-001, Espejo 6 mm, Rectángulo 1000 × 500 mm, área 500000 mm², Activo. Actualización sin F5 informada por el usuario. | TA011-10 y TA011-09. |
| POST `/api/inventory/retazos` con código duplicado | 409 Conflict | No se observó GET `/api/inventory/retazos` inmediatamente posterior en el tramo capturado. | Formulario abierto, datos conservados y un mensaje: "El código de retazo ya existe.". | TA011-12 y TA011-11. |

## Referencias

- [Consulta inicial: GET 200](capturas/TA011-03-endpoints-inventario-200.png), [Listado de planchas](capturas/TA011-01-listado-planchas-almacenero.png) y [Listado de retazos](capturas/TA011-02-listado-retazos-almacenero.png).
- [Registro de plancha: POST 201 y GET 200](capturas/TA011-07-post-plancha-201.png) y [Resultado en frontend](capturas/TA011-06-plancha-registrada-listado.png).
- [Registro de retazo: POST 201 y GET 200](capturas/TA011-10-post-retazo-201.png) y [Resultado en frontend](capturas/TA011-09-retazo-registrado-listado.png).
- [Código duplicado: POST 409](capturas/TA011-12-post-retazo-409.png) y [Conflicto en frontend](capturas/TA011-11-retazo-error-409.png).

## Alcance y límites

La captura TA011-07 contiene dos secuencias POST/GET de planchas. Según el
contexto aportado por el usuario, corresponden a dos registros intencionales
distintos. Los logs no muestran el cuerpo de las solicitudes y no permiten
atribuir visualmente un POST concreto a un material.

Para el registro válido del retazo, el usuario informó que el frontend no
envió el área y que el backend calculó 500000 mm². La evidencia visual
muestra el valor final; los logs muestran los estados HTTP.

PostgreSQL/Supabase es la persistencia declarada del entorno. No se dispone
de evidencia de consultas SQL directas y no se afirma haberlas ejecutado.
Las respuestas HTTP y los listados acreditan el flujo API/interfaz observado;
no constituyen por sí solos una inspección directa de la base de datos ni una
prueba de persistencia tras F5.

## Bloque 5 — Cambio de estado y permisos de gestión

### Respuesta API y consulta posterior

Referencia: [TA011-18-patch-estado-200.png](capturas/TA011-18-patch-estado-200.png).

Secuencia exacta de las operaciones PATCH/GET observadas:

| Orden | Operación | Respuesta | Etapa |
| --- | --- | --- | --- |
| 1 | PATCH `/api/inventory/planchas/2` | 200 OK | Respuesta inmediata de actualización. |
| 2 | GET `/api/inventory/planchas` | 200 OK | Consulta posterior del listado de planchas. |
| 3 | PATCH `/api/inventory/planchas/2` | 200 OK | Respuesta inmediata de actualización. |
| 4 | GET `/api/inventory/planchas` | 200 OK | Consulta posterior del listado de planchas. |
| 5 | PATCH `/api/inventory/retazos/2` | 200 OK | Respuesta inmediata de actualización. |
| 6 | GET `/api/inventory/retazos` | 200 OK | Consulta posterior del listado de retazos. |
| 7 | PATCH `/api/inventory/retazos/2` | 200 OK | Respuesta inmediata de actualización. |
| 8 | GET `/api/inventory/retazos` | 200 OK | Consulta posterior del listado de retazos. |

No se atribuye individualmente desde los logs qué PATCH activó o desactivó
la entidad: no se muestran los cuerpos de solicitud. Cada PATCH observado
va seguido de un GET 200 del listado de la misma entidad.

### Visualización en frontend

| Entidad observada | Resultado visible | Evidencia |
| --- | --- | --- |
| Plancha Catedral, 5 mm, 3200 × 2000 mm, cantidad 12 | Inactivo, acción Activar y mensaje "Plancha desactivada correctamente.". | [TA011-14](capturas/TA011-14-plancha-desactivada.png). |
| La misma plancha Catedral | Activo, acción Desactivar y mensaje "Plancha activada correctamente.". | [TA011-15](capturas/TA011-15-plancha-reactivada.png). |
| RET-HU005-002, Incoloro, 6 mm, Rectángulo 600 × 300 mm | Inactivo y acción Activar; no se observa mensaje de desactivación. | [TA011-16](capturas/TA011-16-retazo-desactivado.png). |
| El mismo retazo RET-HU005-002 | Activo, acción Desactivar y mensaje "Retazo activado correctamente.". | [TA011-17](capturas/TA011-17-retazo-reactivado.png). |

La prueba de plancha corresponde a Catedral, no a la plancha Espejo E2E de
1000 × 500 mm. No se afirman consultas SQL directas ni persistencia tras F5
a partir de estas evidencias.

### Permisos y alcance del cierre

[TA011-19](capturas/TA011-19-operario-planchas-solo-consulta.png) y
[TA011-20](capturas/TA011-20-operario-retazos-solo-consulta.png) muestran al
Operario consultando Planchas y Retazos sin botones de registro, columna
Acciones ni Activar/Desactivar. Acreditan restricción visual, no HTTP 403.

Bloque 5: PASS para cambio de estado, PATCH 200, GET posterior 200,
actualización de badge/acción, permisos visuales y feedback efectivamente
visible. Quedan pendientes edición de campos de plancha, edición de
campos/geometría de retazo, prueba backend 403, filtros, pruebas 401/422
y HU-008.

## Bloque 6 — Edición de plancha

### Operaciones observadas

| Etapa | Observación | Evidencia |
| --- | --- | --- |
| Actualización API | PATCH `/api/inventory/planchas/3` → 200 OK. | [TA011-23](capturas/TA011-23-patch-edicion-plancha-200.png). |
| Consulta posterior | GET `/api/inventory/planchas` → 200 OK, después del PATCH. | [TA011-23](capturas/TA011-23-patch-edicion-plancha-200.png). |
| Resultado en interfaz | Espejo 6 mm, 1000 × 500 mm, cantidad 3 y Activo; mensaje "Plancha actualizada correctamente.". Cambio informado: 2 → 3; listado sin F5 según ejecución del usuario. | [TA011-22](capturas/TA011-22-plancha-editada-cantidad.png). |
| Cantidad cero | Actualización aceptada; cantidad 0 y estado Activo, con mensaje de éxito. | [TA011-24](capturas/TA011-24-plancha-cantidad-cero.png). |
| Restauración | Cantidad 2 y Activo con mensaje de actualización; también visible en consulta posterior. | [Adicional 005114](capturas/Captura%20de%20pantalla%202026-10-07%20005114.png) y [TA011-26](capturas/TA011-26-operario-sin-editar-plancha.png). |

La secuencia API pertenece a la prueba de edición informada. El log no
muestra el cuerpo de la solicitud: no identifica por sí solo el campo
modificado ni sus valores. El
[log ampliado 005859](capturas/Captura%20de%20pantalla%202026-10-07%20005859.png)
contiene tres pares PATCH `/api/inventory/planchas/3` y GET del listado,
todos con 200 OK; no se asigna a cada par un payload específico.

### Contrato y operaciones sin envío

Según la lógica revisada, InventoryPage construye un PATCH parcial con
los campos modificados entre id_tipo_vidrio, espesor_mm, ancho_mm, alto_mm
y cantidad. No incluye estado, id_plancha ni fecha_registro en el cuerpo
del formulario de edición. El estado se gestiona con Activar/Desactivar.
Create exige cantidad > 0; edit/PATCH permite cantidad entera >= 0.

Guardar sin cambios no debe enviar un PATCH vacío ni actualizar la entidad.
La lógica retorna antes de PATCH y GET; [TA011-25](capturas/TA011-25-edicion-plancha-sin-cambios.png)
muestra el formulario abierto y el mensaje correspondiente. La revisión del
log ampliado no encuentra otro PATCH en el tramo final visible, pero la
captura no delimita el instante del clic. No se presenta una imagen como
prueba suficiente de ausencia de HTTP.

Cancelar no llama a la API según la revisión estática. El usuario confirmó
manualmente cierre, retorno al listado y ausencia de PATCH; sin captura.

### Alcance de BD y permisos

La evidencia corresponde a API y consulta/listado frontend. No se afirma
consulta SQL directa ni inspección directa de PostgreSQL/Supabase.
[TA011-26](capturas/TA011-26-operario-sin-editar-plancha.png) muestra al
Operario sin acciones de gestión; no demuestra HTTP 403.

La edición de plancha queda documentada en este bloque. Siguen pendientes
edición de retazo, filtros tipo/espesor/estado, validaciones generales 401,
403 backend, 422 formal, estados loading/empty/error aún no acreditados y
HU-008 como PBI separado. TA-011 no se declara completamente terminada.
