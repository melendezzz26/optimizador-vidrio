# TA-011 — Integración de inventario

Estado vigente: ver [Cierre de la auditoría](#cierre-de-la-auditoría--8-de-octubre-de-2026).
Los bloques siguientes conservan sus resultados y pendientes históricos.

## Bloque 2 — Consulta E2E y navegación por permisos

### Objetivo

Verificar que la interfaz React consulte el inventario mediante FastAPI,
muestre los datos persistidos y respete la visibilidad correspondiente al rol
Almacenero.

### Entorno de prueba

- Rol utilizado: Almacenero.
- Frontend: React + Vite.
- Backend: FastAPI.
- Persistencia: PostgreSQL/Supabase, según el entorno declarado para la prueba.

Esta revisión comprende las cuatro capturas existentes y la ejecución manual
confirmada de las cuatro teclas descrita en la evidencia 4. Se observan datos
en la interfaz y respuestas exitosas de la API; las imágenes por sí solas no
verifican su persistencia en PostgreSQL/Supabase.

### Evidencia 1 — Listado de planchas

Referencia: [TA011-01-listado-planchas-almacenero.png](capturas/TA011-01-listado-planchas-almacenero.png).

Se observa una sesión identificada con el rol Almacenero, la pantalla
Gestión de Inventario y la pestaña Planchas activa. El listado muestra:

| Tipo de vidrio | Espesor | Dimensiones | Cantidad | Estado | Fecha de registro |
| --- | --- | --- | --- | --- | --- |
| Espejo | 6 mm | 3210 × 2250 mm | 2 | Activo | 5 oct. 2026 |

El sidebar muestra Inicio, Gestión de inventario y Consulta de resultados.
No aparecen Registro de pedidos, Panel de roles ni Configuración.
Esta evidencia comprueba la visibilidad del menú para la sesión mostrada;
no constituye una prueba de autorización de rutas o endpoints.

### Evidencia 2 — Listado de retazos

Referencia: [TA011-02-listado-retazos-almacenero.png](capturas/TA011-02-listado-retazos-almacenero.png).

Se observa la pestaña Retazos activa y los siguientes registros con geometría
y área legibles:

| Código | Tipo de vidrio | Espesor | Geometría | Área | Estado | Fecha de registro |
| --- | --- | --- | --- | --- | --- | --- |
| RET-HU005-001 | Incoloro | 6 mm | Rectángulo 850 × 420 mm | 357000 mm² | Activo | 6 oct. 2026 |
| RET-HU005-002 | Incoloro | 6 mm | Rectángulo 600 × 300 mm | 180000 mm² | Activo | 6 oct. 2026 |

### Evidencia 3 — Consulta API

Referencia: [TA011-03-endpoints-inventario-200.png](capturas/TA011-03-endpoints-inventario-200.png).

Los logs del backend muestran respuestas HTTP 200 OK para:

| Método | Endpoint | Resultado observado |
| --- | --- | --- |
| GET | `/api/inventory/tipos-vidrio` | 200 OK |
| GET | `/api/inventory/planchas` | 200 OK |
| GET | `/api/inventory/retazos` | 200 OK |

En conjunto con los listados visibles, esta evidencia documenta la
comunicación exitosa React/FastAPI durante la prueba. La captura muestra
solicitudes GET exitosas, no únicamente OPTIONS. No muestra los cuerpos de
respuesta ni prueba por sí sola la persistencia en PostgreSQL.

### Evidencia 4 — Accesibilidad de pestañas

Referencia: [TA011-04-tabs-accesibles-teclado.png](capturas/TA011-04-tabs-accesibles-teclado.png).

Se observa la pestaña Retazos activa y un contorno de foco visible sobre ella.

La captura demuestra visualmente el foco y la pestaña activa. El comportamiento
de las cuatro teclas se verificó mediante ejecución manual, confirmada por el
usuario, con los siguientes resultados:

| Tecla | Resultado | Comportamiento observado manualmente |
| --- | --- | --- |
| ArrowRight | PASS | Desde Planchas activa Retazos y mueve el foco. |
| ArrowLeft | PASS | Desde Retazos activa Planchas y mueve el foco. |
| Home | PASS | Activa la primera pestaña, Planchas, y mueve el foco. |
| End | PASS | Activa la última pestaña, Retazos, y mueve el foco. |

### Resultado del Bloque 2

Los siguientes resultados PASS corresponden a lo observado en las capturas
y a la ejecución manual confirmada de las cuatro teclas:

| Punto verificado | Resultado | Evidencia y alcance |
| --- | --- | --- |
| Consulta del catálogo | PASS | GET `/api/inventory/tipos-vidrio` con HTTP 200; evidencia 3. |
| Listado de planchas | PASS | Registro visible con sus datos; evidencia 1. |
| Listado de retazos | PASS | Dos registros visibles con sus datos; evidencia 2. |
| Resolución de nombre de tipo de vidrio | PASS | Se muestran los nombres Espejo e Incoloro; evidencias 1 y 2. Se verifica el resultado visible, no el mecanismo interno de resolución. |
| Representación legible de geometría | PASS | Forma y dimensiones legibles para ambos retazos; evidencia 2. |
| Visibilidad por rol Almacenero | PASS | Rol identificado y sidebar con las tres opciones indicadas; evidencia 1. |
| Respuestas HTTP 200 observadas | PASS | Los tres GET de inventario devuelven 200 OK; evidencia 3. |
| Navegación por teclado de pestañas | PASS | ArrowRight, ArrowLeft, Home y End verificados manualmente; evidencia 4 muestra el foco visible. |

**Resultado del Bloque 2: PASS.** La evidencia 4 confirma visualmente el foco
sobre Retazos activa; el comportamiento de las cuatro teclas se verificó
mediante ejecución manual.

No se declaran resultados de registro E2E, edición, cambio de estado, filtros
ni HU-008, que pertenecen a bloques posteriores.

### Privacidad

Las evidencias revisadas no muestran JWT, encabezados Authorization,
contraseñas, hashes ni secretos. La interfaz muestra identificadores de una
cuenta de prueba, que no se reproducen en este documento.

El usuario local y la ruta de Windows visibles en la terminal no se consideran
credenciales y tampoco se reproducen aquí.

## Bloque 3 — Registro E2E de plancha

### Objetivo

Verificar el flujo completo de registro de una plancha desde la interfaz
React hasta FastAPI y la actualización posterior del listado.

### Datos utilizados

- Tipo de vidrio: Espejo
- id_tipo_vidrio: 6
- Espesor: 6 mm
- Ancho: 1000 mm
- Alto: 500 mm
- Cantidad: 2

Según los datos de prueba proporcionados por el usuario, la combinación
Espejo + 6 mm pertenece al catálogo permitido y las dimensiones y la cantidad
cumplen las validaciones existentes. El id_tipo_vidrio se registra a partir
de esa información; no es visible en las capturas.

### Evidencia 5 — Formulario preparado

Referencia: [TA011-05-formulario-registro-plancha.png](capturas/TA011-05-formulario-registro-plancha.png).

Se observa el formulario Registrar plancha comercial con tipo Espejo,
espesor 6 mm, ancho 1000 mm, alto 500 mm, cantidad 2 y el botón Registrar
plancha. Está integrado dentro de Gestión de inventario, con el sidebar
correspondiente al Almacenero y sin AppShell duplicado visible.

La imagen documenta el estado preparado para la prueba. Por sí sola no
demuestra que posteriormente se enviaron exactamente esos datos.

### Evidencia 6 — Resultado visible

Referencia: [TA011-06-plancha-registrada-listado.png](capturas/TA011-06-plancha-registrada-listado.png).

Se observa el mensaje "Plancha registrada correctamente.", el formulario
cerrado, la pestaña Planchas activa y la siguiente fila en el listado de
Gestión de Inventario:

| Tipo de vidrio | Espesor | Ancho | Alto | Cantidad | Estado |
| --- | --- | --- | --- | --- | --- |
| Espejo | 6 mm | 1000 mm | 500 mm | 2 | Activo |

Según la ejecución manual informada por el usuario, el listado se actualizó
sin recarga manual inmediatamente después del registro. La captura muestra
el resultado visible; la ausencia de recarga manual se documenta a partir
de esa confirmación.

También aparece una plancha Catedral generada previamente durante otra
prueba intencional, según el contexto de la sesión proporcionado por el
usuario. No corresponde a un doble envío de la plancha Espejo.

### Evidencia 7 — Secuencia API

Referencia: [TA011-07-post-plancha-201.png](capturas/TA011-07-post-plancha-201.png).

Se observa la siguiente secuencia en los logs del backend:

| Orden | Método | Endpoint | Respuesta |
| --- | --- | --- | --- |
| 1 | POST | `/api/inventory/planchas` | 201 Created |
| 2 | GET | `/api/inventory/planchas` | 200 OK |

La captura contiene dos secuencias POST/GET. Según la información de la
sesión aportada por el usuario, hubo dos registros intencionales distintos:
una plancha Catedral previa y la plancha Espejo utilizada para este bloque.
Los logs no muestran el cuerpo de las solicitudes, por lo que no se atribuye
visualmente un POST concreto a un material determinado ni se interpretan
ambos POST como un mismo envío.

### Flujo verificado

Los resultados siguientes combinan lo observable en las evidencias 5 a 7
con el flujo manual informado por el usuario. La reutilización del formulario
de HU-004 se registra según la información de implementación proporcionada;
no se deduce de las capturas ni implica una revisión de código en esta tarea.

1. PASS — El usuario Almacenero abre Gestión de inventario.
2. PASS — Accede a Registrar plancha.
3. PASS — Se reutiliza el formulario existente de HU-004.
4. PASS — El registro se realiza mediante POST `/api/inventory/planchas`.
5. PASS — El backend responde 201 Created.
6. PASS — Después se consulta GET `/api/inventory/planchas`.
7. PASS — El GET responde 200 OK.
8. PASS — El formulario se cierra.
9. PASS — Se muestra el mensaje de éxito.
10. PASS — La nueva plancha aparece en el listado sin F5.

### Resultado del Bloque 3

| Punto verificado | Resultado |
| --- | --- |
| Formulario integrado sin AppShell duplicado | PASS |
| Registro desde React | PASS |
| POST /api/inventory/planchas | 201 Created |
| Refresco mediante GET /api/inventory/planchas | 200 OK |
| Cierre del formulario tras éxito | PASS |
| Mensaje de éxito | PASS |
| Nueva plancha visible sin recarga manual | PASS |
| Protección contra doble envío | Implementada, según la información proporcionada; sin evidencia directa de una prueba específica. |

No se declaran como terminados la edición, el cambio de estado, los filtros,
el registro de retazo mediante TA-011 ni HU-008.

### Privacidad

Las evidencias revisadas no muestran JWT, encabezados Authorization,
contraseñas, hashes, secretos ni credenciales de base de datos. El usuario
local y la ruta de Windows visibles en la terminal no son secretos y no se
reproducen en este documento.

## Bloque 4 — Registro E2E de retazo

### Datos de prueba

- Código: RET-TA011-E2E-001
- Tipo: Espejo
- id_tipo_vidrio: 6
- Espesor: 6 mm
- Geometría: RECTANGULO
- Ancho: 1000 mm
- Alto: 500 mm
- Área calculada por backend: 500000 mm²

Este bloque combina las capturas revisadas con los resultados de ejecución
y los detalles de implementación proporcionados por el usuario. El identificador
del tipo, el cálculo en backend, la omisión del área en el envío y la semántica
accesible no se deducen de una imagen estática.

### Evidencia 8 — Formulario

Referencia: [TA011-08-formulario-registro-retazo.png](capturas/TA011-08-formulario-registro-retazo.png).

Se observa el formulario Registrar retazo integrado dentro de Gestión de
Inventario, sin AppShell duplicado visible. Contiene el código RET-TA011-E2E-001,
tipo Espejo, espesor 6 mm, forma Rectángulo y dimensiones 1000 × 500 mm.

### Evidencia 9 — Registro exitoso

Referencia: [TA011-09-retazo-registrado-listado.png](capturas/TA011-09-retazo-registrado-listado.png).

Se observa la pestaña Retazos activa, el formulario cerrado y el mensaje
"Retazo registrado correctamente.". El listado contiene:

| Código | Tipo | Espesor | Geometría | Área | Estado |
| --- | --- | --- | --- | --- | --- |
| RET-TA011-E2E-001 | Espejo | 6 mm | Rectángulo 1000 × 500 mm | 500000 mm² | Activo |

El listado se actualizó sin recarga manual, según la ejecución informada por
el usuario. La captura documenta el resultado visible de esa operación.

### Evidencia 10 — Secuencia API

Referencia: [TA011-10-post-retazo-201.png](capturas/TA011-10-post-retazo-201.png).

Los logs muestran POST `/api/inventory/retazos` con respuesta 201 Created,
seguido de GET `/api/inventory/retazos` con respuesta 200 OK.

Según la información de la prueba proporcionada por el usuario, el área no
fue enviada por el frontend y fue calculada por el backend: 1000 × 500 =
500000 mm². Los logs no muestran el cuerpo de la solicitud; el valor final
se observa en la evidencia 9.

### Evidencia 11 — Conflicto por código duplicado

Referencia: [TA011-11-retazo-error-409.png](capturas/TA011-11-retazo-error-409.png).

Se reintentó registrar el código RET-TA011-E2E-001. Tras el conflicto, el
formulario permaneció abierto y conservó los datos ingresados. Se observa
un único mensaje de error: "El código de retazo ya existe.".

Los valores visibles en este reintento son RET-TA011-E2E-001, Espejo, 6 mm,
Rectángulo, ancho 1233 mm y alto 1234 mm. Estas dimensiones corresponden al
reintento duplicado, no al registro exitoso de 1000 × 500 mm.

### Evidencia 12 — HTTP 409

Referencia: [TA011-12-post-retazo-409.png](capturas/TA011-12-post-retazo-409.png).

Se observa POST `/api/inventory/retazos` con respuesta 409 Conflict. No se
observó un GET `/api/inventory/retazos` inmediatamente posterior como parte
de esa operación fallida, dentro del tramo de logs capturado.

### Evidencia 13 — Feedback visual

Referencia: [TA011-13-feedback-exito-inventario.png](capturas/TA011-13-feedback-exito-inventario.png).

El feedback de éxito de Inventario fue mejorado y se presenta como un bloque
visual diferenciado. La captura muestra el mensaje de éxito de una operación
de plancha; no corresponde al POST del retazo.

Según los detalles de implementación proporcionados por el usuario, el
feedback utiliza semántica accesible de status y el patrón es compartido por
las operaciones de planchas y retazos. La captura acredita su presentación
visual; no muestra por sí sola la semántica del DOM.

### Resultado Bloque 4

| Punto verificado | Resultado |
| --- | --- |
| RegistrarRetazoForm integrado | PASS |
| POST retazo 201 | PASS |
| GET posterior 200 | PASS |
| Actualización sin F5 | PASS |
| Área calculada por backend | PASS |
| Formulario cerrado después del éxito | PASS |
| Código duplicado devuelve 409 | PASS |
| Formulario permanece abierto tras 409 | PASS |
| Valores se conservan | PASS |
| Mensaje de conflicto visible | PASS |
| No se ejecuta refresco posterior al POST fallido | PASS — Sin GET posterior observado en el tramo capturado y según la ejecución informada. |
| Feedback visual accesible implementado | PASS — Presentación visual revisada y semántica status informada por el usuario. |

**Resultado del Bloque 4: PASS. Cierre documental completado** con el alcance
y las fuentes de verificación indicados. No se añaden resultados de edición,
cambio de estado, filtros ni HU-008.

### Privacidad

Las evidencias revisadas no muestran JWT, encabezados Authorization,
contraseñas, hashes, secretos ni credenciales de base de datos. No se
reproducen identificadores locales ni rutas de Windows.

## Bloque 5 — Cambio de estado y permisos de gestión

### Plancha

La entidad observada es una plancha Catedral, de 5 mm, dimensiones
3200 × 2000 mm y cantidad 12. No es la plancha Espejo E2E de 1000 × 500 mm.
Las capturas muestran una sesión con rol Almacenero y la pestaña Planchas.

| Evidencia | Cambio verificado | Resultado visible |
| --- | --- | --- |
| [TA011-14-plancha-desactivada.png](capturas/TA011-14-plancha-desactivada.png) | Activo → Inactivo; acción Desactivar → Activar. | Plancha Catedral Inactivo, acción Activar y mensaje "Plancha desactivada correctamente.". |
| [TA011-15-plancha-reactivada.png](capturas/TA011-15-plancha-reactivada.png) | Inactivo → Activo; acción Activar → Desactivar. | La misma plancha Catedral Activo, acción Desactivar y mensaje "Plancha activada correctamente.". |

### Retazo

La entidad observada es RET-HU005-002, tipo Incoloro, espesor 6 mm y
geometría Rectángulo 600 × 300 mm. Las capturas muestran la pestaña Retazos
y una sesión con rol Almacenero.

| Evidencia | Cambio verificado | Resultado visible |
| --- | --- | --- |
| [TA011-16-retazo-desactivado.png](capturas/TA011-16-retazo-desactivado.png) | Activo → Inactivo; acción Desactivar → Activar. | RET-HU005-002 Inactivo y acción Activar. No aparece un mensaje de desactivación en esta captura. |
| [TA011-17-retazo-reactivado.png](capturas/TA011-17-retazo-reactivado.png) | Inactivo → Activo; acción Activar → Desactivar. | RET-HU005-002 Activo, acción Desactivar y mensaje "Retazo activado correctamente.". |

TA011-16 se conserva sin reemplazo: la nueva captura revisada muestra una
activación, no una desactivación con mensaje. No se registra como observado
el mensaje "Retazo desactivado correctamente.".

### Secuencia API

Referencia: [TA011-18-patch-estado-200.png](capturas/TA011-18-patch-estado-200.png).

Se observan las siguientes operaciones, en este orden:

| Orden | Método | Endpoint | Respuesta |
| --- | --- | --- | --- |
| 1 | PATCH | `/api/inventory/planchas/2` | 200 OK |
| 2 | GET | `/api/inventory/planchas` | 200 OK |
| 3 | PATCH | `/api/inventory/planchas/2` | 200 OK |
| 4 | GET | `/api/inventory/planchas` | 200 OK |
| 5 | PATCH | `/api/inventory/retazos/2` | 200 OK |
| 6 | GET | `/api/inventory/retazos` | 200 OK |
| 7 | PATCH | `/api/inventory/retazos/2` | 200 OK |
| 8 | GET | `/api/inventory/retazos` | 200 OK |

Los logs no muestran el cuerpo de las solicitudes. No se atribuye
individualmente desde ellos qué PATCH fue activar o desactivar; los estados,
las acciones y los mensajes se verifican mediante las capturas de interfaz.

### Permisos Operario

Referencias:

- [TA011-19-operario-planchas-solo-consulta.png](capturas/TA011-19-operario-planchas-solo-consulta.png).
- [TA011-20-operario-retazos-solo-consulta.png](capturas/TA011-20-operario-retazos-solo-consulta.png).

La sesión identificada con rol Operario puede consultar los listados de
Planchas y Retazos en Gestión de inventario. No se ven Registrar plancha,
Registrar retazo, la columna Acciones ni botones Activar/Desactivar.

Estas capturas demuestran la restricción visual de acciones de gestión;
no demuestran una respuesta HTTP 403 del backend.

### Resultado del Bloque 5

| Punto verificado | Resultado |
| --- | --- |
| Permisos visuales por rol | PASS |
| Cambio de estado de plancha | PASS |
| Cambio de estado de retazo | PASS |
| PATCH 200 | PASS |
| GET posterior 200 | PASS |
| Actualización de badge y acción | PASS |
| Feedback visible observado | PASS — Desactivación y activación de plancha; activación de retazo. No se acredita el mensaje de desactivación del retazo. |

**Resultado del Bloque 5: PASS**, limitado a los cambios de estado y permisos
visuales documentados. Casos asociados: TA011-PF-05 a TA011-PF-09 en
[Prueba funcional](prueba-funcional.md).

Quedan explícitamente pendientes:

- Edición de campos de plancha.
- Edición de campos y geometría de retazo.
- Prueba backend 403.
- Filtros.
- Pruebas 401/422.
- HU-008.

### Privacidad

Las capturas revisadas no muestran JWT, encabezados Authorization,
contraseñas, hashes ni secretos. Los nombres e identificadores de cuenta
visibles no se reproducen en el texto.

## Bloque 6 — Edición de plancha

### Flujo y alcance

La edición reutiliza RegistrarPlanchaForm, con mode=create para registro y
mode=edit para edición. Precarga id_tipo_vidrio, espesor_mm, ancho_mm,
alto_mm y cantidad. El formulario no permite editar estado; este continúa
gestionándose mediante Activar/Desactivar.

La acción Editar está restringida a Administrador y Almacenero según la
lógica revisada. La sesión de prueba informada es Almacenero; Operario
conserva solo consulta. No se declara una prueba E2E con Administrador ni
una prueba backend 403 a partir de las imágenes.

### PATCH parcial

InventoryPage compara los valores numéricos con la plancha seleccionada y
envía únicamente los campos modificados entre id_tipo_vidrio, espesor_mm,
ancho_mm, alto_mm y cantidad. El formulario no envía estado, id_plancha ni
fecha_registro en el cuerpo. El identificador se utiliza en la ruta PATCH.
Esta descripción corresponde a la lógica revisada, no a un payload visible
en los logs.

### Evidencia 21 — Precarga

Referencia: [TA011-21-editar-plancha-precarga.png](capturas/TA011-21-editar-plancha-precarga.png).

Se observa Editar plancha con Espejo, 6 mm, ancho 1000.00 mm, alto 500.00 mm
y cantidad 2 correctamente cargados; están disponibles Guardar cambios y
Cancelar. La captura muestra el sidebar correspondiente al contexto de la
prueba, pero el encabezado con el rol queda fuera del encuadre. El rol
Almacenero se registra por el contexto de la sesión informada, no como texto
visible en esta imagen. No se utiliza la captura con "Seleccionar espesor"
como evidencia de precarga correcta.

### Evidencias 22 y 23 — Edición de cantidad

Referencias:

- [TA011-22-plancha-editada-cantidad.png](capturas/TA011-22-plancha-editada-cantidad.png).
- [TA011-23-patch-edicion-plancha-200.png](capturas/TA011-23-patch-edicion-plancha-200.png).

La prueba informada cambió cantidad de 2 a 3. La interfaz muestra
"Plancha actualizada correctamente." y la fila Espejo, 6 mm, 1000 × 500 mm,
cantidad 3, Activo, con Editar disponible. El encabezado de sesión no está
visible en TA011-22; el rol de ejecución corresponde al contexto informado.

El backend muestra PATCH `/api/inventory/planchas/3` → 200 OK, seguido por
GET `/api/inventory/planchas` → 200 OK. El listado se actualizó sin F5 según
la ejecución E2E informada por el usuario. TA011-23 no muestra el payload y
no permite identificar por sí sola qué campo cambió.

### Evidencia 24 — Cantidad cero

Referencia: [TA011-24-plancha-cantidad-cero.png](capturas/TA011-24-plancha-cantidad-cero.png).

Tras el cambio informado de 3 a 0, se observa el mensaje
"Plancha actualizada correctamente." y la fila Espejo, 6 mm,
1000 × 500 mm, cantidad 0, todavía Activo. La actualización fue aceptada;
cantidad cero no desactiva automáticamente la plancha.

La regla de registro exige cantidad > 0; edición/PATCH permite cantidad
entera >= 0. La regla de create se registra por la lógica revisada, sin
atribuirle una nueva prueba E2E en este bloque.

### Restauración de la entidad de prueba

La captura adicional
[Captura de pantalla 2026-10-07 005114.png](capturas/Captura%20de%20pantalla%202026-10-07%20005114.png)
muestra el mensaje de actualización correcta y la plancha Espejo, 6 mm,
1000 × 500 mm, cantidad 2, Activo. Respalda la restauración posterior
informada en la secuencia de prueba. TA011-26 también muestra ese estado
en una consulta posterior. Se conserva el nombre original de la captura
adicional.

### Evidencia 25 — Guardar sin cambios

Referencia: [TA011-25-edicion-plancha-sin-cambios.png](capturas/TA011-25-edicion-plancha-sin-cambios.png).

Se observa el formulario Editar plancha abierto, con Espejo, 6 mm,
1000 × 500 mm, cantidad 2, y el mensaje "No hay cambios para guardar.".

No debe enviarse un PATCH vacío ni ejecutarse una actualización sin cambios.
La lógica revisada retorna antes de updatePlancha y del GET de refresco
cuando no hay diferencias. El feedback usa el warning existente con
role=status y aria-live=polite, sin cerrar ni reiniciar el formulario.

La imagen por sí sola no demuestra ausencia de HTTP. El log ampliado
[Captura de pantalla 2026-10-07 005859.png](capturas/Captura%20de%20pantalla%202026-10-07%20005859.png)
muestra tres pares PATCH/GET de planchas y después operaciones de sesión y
consulta, sin otro PATCH en el tramo final visible. Es consistente con la
lógica descrita, pero no delimita por sí solo el instante del clic sin cambios.

### Cancelación

El usuario confirmó explícitamente haber pulsado Cancelar, vuelto al listado
y comprobado que no se envió PATCH. Se registra PASS manual sin captura;
no se inventa evidencia visual. La revisión estática también muestra que
Cancelar cierra el formulario y limpia la selección sin llamar a la API.

### Evidencia 26 — Operario sin edición

Referencia: [TA011-26-operario-sin-editar-plancha.png](capturas/TA011-26-operario-sin-editar-plancha.png).

Se observa sesión con rol Operario, Gestión de inventario, Planchas activa
y listado visible. No aparecen Registrar plancha, columna Acciones, Editar
ni Activar/Desactivar. Demuestra restricción visual por rol, no HTTP 403.

### Resultado del Bloque 6

| Punto verificado | Resultado | Sustento |
| --- | --- | --- |
| Precarga de plancha | PASS | TA011-21; encabezado de rol fuera del encuadre. |
| Edición de cantidad 2 → 3 | PASS | TA011-22 y TA011-23; actualización sin F5 informada por el usuario. |
| PATCH 200 y GET posterior 200 | PASS | TA011-23. |
| Cantidad 0 aceptada sin desactivación | PASS | TA011-24. |
| Restauración a cantidad 2, Activo | PASS | Captura adicional 005114 y consulta TA011-26. |
| Guardar sin modificaciones | PASS | TA011-25, revisión de lógica y alcance del log ampliado indicado. |
| Cancelación sin PATCH | PASS | Confirmación manual explícita del usuario, sin captura. |
| Operario sin acción Editar | PASS | TA011-26; solo restricción visual. |

**Bloque 6: PASS en el alcance documentado. TA-011 no está completamente
terminada.** El rol no es visible en TA011-21; para acreditarlo en esa misma
imagen sería necesaria una captura con el encabezado de sesión incluido.

Continúan pendientes edición de retazo, filtros tipo/espesor/estado,
validaciones generales 401, 403 backend, 422 formal, los estados
loading/empty/error aún no acreditados y HU-008 como PBI separado.

### Capturas adicionales y privacidad

Se revisaron las once capturas nuevas. Se conservaron sin renombrar:

- 004938: edición con "Seleccionar espesor"; excluida de evidencia de éxito.
- 005055: recorte mínimo sin contenido legible; no acredita una prueba.
- 005114: evidencia adicional de restauración de cantidad a 2.
- 005325: Operario en Retazos; no corresponde a TA011-26 de Planchas.
- 005859: logs ampliados; evidencia complementaria con los límites indicados.

Los identificadores anteriores son las horas del nombre original
"Captura de pantalla 2026-10-07 HHMMSS.png". No se eliminaron imágenes.
No se observan JWT, Authorization, contraseñas, hashes, secretos,
credenciales de Supabase ni variables sensibles. Los nombres e
identificadores de cuenta visibles son datos identificativos y no se
reproducen innecesariamente en este documento.

## Bloque 7 — Edición de retazo

### Implementación y fuentes de verificación

La revisión estática confirma la reutilización de RegistrarRetazoForm en
create/edit y la precarga de código, material, espesor y geometría mediante
initialValues. InventoryPage construye el PATCH parcial con las diferencias
de codigo, id_tipo_vidrio, espesor_mm y geometria. Si cambia la geometría,
envía el objeto completo de la forma, no un campo aislado como height_mm.
El estado queda fuera del formulario y se gestiona con Activar/Desactivar.
area_mm2 no es editable ni enviada por el frontend; tampoco se envían estado,
id_retazo, fecha_registro ni id_ejecucion_origen en este PATCH de edición.

El backend recalcula area_mm2 cuando recibe geometria modificada. Después
del PATCH exitoso, el frontend consulta únicamente GET del listado de retazos
y muestra el área devuelta por backend. Estas afirmaciones proceden del código
revisado; el log disponible no muestra cuerpos de solicitud ni respuesta.

### PF-16 — Precarga de edición verificada manualmente

Precondición: RET-TA011-E2E-001 existente.

Esperado:

- código RET-TA011-E2E-001;
- tipo Espejo;
- espesor 6 mm;
- Rectángulo;
- ancho 1000 mm;
- alto 500 mm.

Resultado obtenido: **PASS**. La comprobación manual posterior mostró todos
los valores precargados correctamente. No se conserva una captura adicional
para este caso y no se asigna una referencia de imagen inexistente.

Durante la primera ejecución se detectó que el select no reconocía
correctamente valores equivalentes "6.0" y "6". Se normalizó el valor inicial
y posteriormente se repitió la comprobación manual, mostrando correctamente
6 mm.

### Evidencias 28 a 30 — Edición rectangular y restauración

Entidad de prueba informada: RET-TA011-E2E-001, Espejo, 6 mm, RECTANGULO,
1000 × 500 mm, área inicial 500000 mm² y estado Activo.

| Evidencia | Resultado observado |
| --- | --- |
| [TA011-28-retazo-geometria-editada.png](capturas/TA011-28-retazo-geometria-editada.png) | Mensaje "Retazo actualizado correctamente."; RET-TA011-E2E-001, Espejo, 6 mm, Rectángulo 1000 × 400 mm, área 400000 mm² y Activo. |
| [TA011-29-patch-edicion-retazo-200.png](capturas/TA011-29-patch-edicion-retazo-200.png) | PATCH /api/inventory/retazos/3 → 200 OK, seguido de GET /api/inventory/retazos → 200 OK. El log no muestra el payload exacto. |
| [TA011-30-retazo-restaurado.png](capturas/TA011-30-retazo-restaurado.png) | La misma entidad vuelve a Rectángulo 1000 × 500 mm, área 500000 mm² y Activo; mensaje de actualización correcta visible. |

La secuencia manual informada es 1000 × 500 → 1000 × 400 → 1000 × 500 mm.
El recálculo del área lo realiza backend, confirmado por la revisión de
update_retazo y sus resultados visibles. No se afirma una consulta SQL directa
ni persistencia tras F5. TA011-29 acredita un par PATCH/GET, no un segundo
par correspondiente a la restauración.

### Evidencia 31 — Guardar sin cambios

Referencia: [TA011-31-edicion-retazo-sin-cambios.png](capturas/TA011-31-edicion-retazo-sin-cambios.png).

La entidad de esta prueba es RET-HU005-001, Incoloro, Rectángulo 850 × 420 mm,
no RET-TA011-E2E-001. El formulario Editar retazo permanece abierto y muestra
"No hay cambios para guardar."; código, material y dimensiones siguen visibles.
Guardar sin modificar no debe enviar PATCH vacío ni ejecutar el GET asociado.
La revisión estática confirma que changes vacío produce el warning y retorna
antes de ambas llamadas, sin cerrar ni reiniciar el formulario. La captura
acredita el feedback y el formulario abierto; por sí sola no prueba ausencia
de tráfico HTTP. PF-20 se limita a ese resultado visible y la lógica revisada.

### Evidencia 32 — Operario solo consulta

Referencia: [TA011-32-operario-sin-editar-retazo.png](capturas/TA011-32-operario-sin-editar-retazo.png).

Se observa rol Operario, Gestión de Inventario, pestaña Retazos y listado
visible, sin Registrar retazo, columna Acciones, Editar ni Activar/Desactivar.
Es evidencia de restricción visual; no demuestra un 403 backend.

### Resultado del Bloque 7 y pendientes

| Punto | Resultado | Sustento |
| --- | --- | --- |
| Precarga completa de edición | PASS | Verificación manual posterior: código, Espejo, 6 mm, Rectángulo y 1000 × 500 mm correctamente precargados. |
| Edición rectangular | PASS | TA011-28 y TA011-29. |
| Recálculo de área por backend | PASS | TA011-28 y revisión estática del servicio. |
| Restauración de geometría | PASS | TA011-30. |
| Guardar sin cambios | PASS en el alcance indicado | TA011-31 y retorno previo a PATCH/GET comprobado estáticamente; no acredita precarga de espesor. |
| Operario sin gestión | PASS | TA011-32; restricción visual. |

**Bloque 7: PASS.** PF-16 se sustenta en verificación manual posterior sin
captura adicional. Los pendientes de edición de retazo citados en bloques
anteriores quedan actualizados por los resultados de esta sección.

E2E se ejecutó con RECTANGULO. CIRCUNFERENCIA y POLIGONO_CONVEXO quedaron
verificados estáticamente en precarga, validación, construcción y comparación
de geometría; no se afirma E2E de esas formas. No se implementó editor visual
de polígonos. La mejora visual y reutilización del editor geométrico de Pedidos
se tratará después como mejora UI/UX. Siguen pendientes filtros, pruebas
generales 401/403/422, estados loading/empty/error aún no acreditados y HU-008.

### Capturas adicionales y privacidad

Se revisaron las capturas nuevas y se conservaron las evidencias oficiales
TA011-28 a TA011-32. La captura 021018 queda fuera del conjunto oficial como
evidencia diagnóstica de la primera ejecución, porque mostraba el espesor sin
seleccionar. TA011-01 a TA011-26 se conservaron intactas.
Las nuevas capturas no muestran JWT, Authorization, contraseñas, hashes,
secretos ni credenciales Supabase. TA011-32 muestra nombre e identificador
de cuenta; son datos identificativos que no se reproducen en este documento.

## Bloque 8A — Mejora UI/UX y filtros de Inventario

### Entorno y alcance

Validación E2E del 7 de octubre de 2026 con datos reales, React/Vite y FastAPI,
en sesiones Almacenero y Operario. Implementación versionada en
`fac938c feat(TA-011): mejorar interfaz y filtros de inventario`.

Se documentan la ejecución E2E ya confirmada y ocho capturas seleccionadas
de las doce originales externas, copiadas sin alterar sus originales.
Las capturas acreditan estados visibles; la ausencia de HTTP adicional,
las respuestas PATCH/GET, la limpieza, la restauración y la navegación por
teclado proceden de la ejecución confirmada, no de una imagen aislada.

### Evidencias 33 a 40

| Evidencia | Original externo | Contenido visible |
| --- | --- | --- |
| [TA011-33](capturas/TA011-33-planchas-filtros.png) | 02-filtros-planchas.png | Espejo + 6 mm, Estado Todos, 2 de 4 planchas, Limpiar filtros y foco en Espesor. |
| [TA011-34](capturas/TA011-34-planchas-sin-resultados.png) | 03-sin-resultados-planchas.png | Espejo + 6 mm + Inactivo: 0 de 4 y mensaje de filtros sin coincidencias. |
| [TA011-35](capturas/TA011-35-retazos-filtros.png) | 05-filtros-retazos.png | Incoloro + 6 mm + Activo: 2 de 3 retazos; geometría, área y acciones. La tabla está desplazada horizontalmente y recorta el inicio de los códigos. |
| [TA011-36](capturas/TA011-36-retazos-sin-resultados.png) | 10-sin-resultados-retazos.png | Incoloro + 6 mm + Inactivo: 0 de 3 y Limpiar filtros. |
| [TA011-37](capturas/TA011-37-operacion-con-filtro-activo.png) | 11-operacion-filtro-activo.png | Catedral + Activo: 1 de 4 y mensaje "Plancha desactivada correctamente.". |
| [TA011-38](capturas/TA011-38-operario-filtros-solo-consulta.png) | 06-operario-solo-consulta.png | Operario consulta Retazos con filtros; sin Registrar retazo, Acciones, Editar ni Activar/Desactivar. |
| [TA011-39](capturas/TA011-39-responsive-400.png) | 08-responsive-400.png | Vista a 400 px: filtros apilados, códigos legibles y tabla dentro del contenedor. |
| [TA011-40](capturas/TA011-40-responsive-375-acciones-foco.png) | 12-responsive-375-acciones-foco.png | Vista a 375 px: tabla desplazada hasta Acciones y foco visible en Desactivar. |

### Comportamiento y resultados E2E

Filtros locales Tipo / Espesor / Estado, independientes por pestaña, con
contador de coincidencias respecto del total y Limpiar filtros solo cuando
hay filtros activos. Las tablas presentan geometría compacta, área alineada
y acciones agrupadas, con desplazamiento horizontal dentro del contenedor.

| Caso | Resultado | Observación confirmada |
| --- | --- | --- |
| Carga Planchas | PASS | 4 registros visibles. |
| Filtros Planchas | PASS | Espejo + 6 mm: 2 de 4; sin HTTP adicional. Cambiar a un tipo incompatible limpia Espesor. |
| Limpiar filtros Planchas | PASS | Vuelve a 4 de 4 y desaparece Limpiar filtros. |
| No-results Planchas | PASS | 0 de 4 y "No hay resultados para los filtros seleccionados.". |
| Carga Retazos | PASS | 3 registros visibles. |
| Filtros Retazos | PASS | Incoloro + 6 mm: 2 de 3; sin HTTP adicional. |
| Limpiar filtros Retazos | PASS | Vuelve a 3 de 3 y desaparece Limpiar filtros. |
| No-results Retazos | PASS | 0 de 3; Limpiar filtros recupera los datos. |
| Operación con filtros activos | PASS | PATCH 200 + GET 200; el registro sale del filtro Activo y el contador se actualiza. |
| Operario | PASS | Consulta y filtra ambos listados, sin acciones de gestión. |
| 1366 × 768 | PASS | Sin overflow horizontal global; Retazos utiliza scroll interno. |
| 768 px | PASS | Controles utilizables y tabla con scroll interno. |
| 400 px | PASS | Filtros apilados, etiquetas visibles y botones sin superposición. |
| 375 px | PASS | Sin overflow global; acciones alcanzables desplazando la tabla. |
| Teclado/foco | PASS | Tab alcanza filtros, tabla y acciones; ArrowRight, ArrowLeft, Home y End cambian la pestaña y el foco. Foco visible y tabla desplazable con teclado. |
| Regresión create/edit/state | PASS | Registro y edición abren/cancelan en ambas entidades; cambio de estado de plancha ejecutado y restaurado. No se probaron nuevas altas. |

No-results identifica cero coincidencias sobre un inventario existente
(0 de 4 / 0 de 3), distinto de inventario vacío (sin registros). No se vació
la base ni se acredita aquí una nueva ejecución E2E de empty, loading o error.
Los estados muestran texto Activo/Inactivo y no dependen únicamente del color.
Las capturas 39 y 40 son de página completa: la altura de la imagen no representa
la altura del viewport. Los cuatro tamaños se verificaron durante el E2E.
La captura 38 muestra Retazos; la comprobación de Operario también incluyó
Planchas. No constituye una prueba de 403 backend.

### Operación y restauración del dato de prueba

Se utilizó la plancha Catedral, 5 mm, 3200 × 2000 mm, cantidad 12
(`id_plancha=2`). Con Tipo Catedral y Estado Activo, había 2 de 4 planchas.
Al desactivarla, PATCH `/api/inventory/planchas/2` → 200 seguido de
GET `/api/inventory/planchas` → 200 dejó 1 de 4. Al seleccionar Inactivo,
la misma plancha seguía disponible: desapareció del filtro, no fue eliminada.

Se reactivó con otro PATCH 200 y GET 200; el filtro Catedral + Activo volvió
a 2 de 4. **La plancha quedó Activa**, con sus dimensiones y cantidad originales.
No se insertaron registros nuevos durante esta validación. TA011-37 muestra
el resultado de desactivación; la red y la restauración fueron comprobadas
durante el E2E, sin una captura específica de esas operaciones.

### Resultado y pendientes

**Bloque 8A = PASS. TA-011 todavía no está finalizada.**
Casos asociados: TA011-PF-22 a TA011-PF-28 en [Prueba funcional](prueba-funcional.md).
Los pendientes de filtros y mejora general de Inventario de los bloques
anteriores quedan actualizados por este cierre; se mantienen pendientes:

- Editor visual/reutilizable para POLIGONO_CONVEXO.
- 401 y 403 backend.
- Validación formal restante de 422 de TA-011.
- Cierre documental final de TA-011 y PR.

No se afirma integración de HU-007 a main; HU-008 queda fuera de este cierre.

### Privacidad

Las doce capturas revisadas no muestran JWT, Authorization, contraseñas,
hashes, tokens ni secretos. Algunas muestran nombres e identificadores de
cuentas, que no se transcriben. Ninguna se excluyó por privacidad; las cuatro
no seleccionadas se conservan fuera del repositorio por menor aporte frente
a la selección. No se modificaron capturas anteriores ni código.

## Cierre de la auditoría — 8 de octubre de 2026

La [matriz T01–T11](prueba-funcional.md#auditoría-y-cierre--8-de-octubre-de-2026)
consolida PF-01–28 sin repetirlos. Añade las confirmaciones manuales previas
401/403/422 y persistencia aportadas por el usuario, cuatro casos componente
de Inventario y la inspección del código y pruebas backend existentes.

El archivo InventoryPage había sido eliminado localmente: se restauró desde
HEAD y se recuperó el mensaje de sesión inválida del callback 401. El test 403
conserva su lógica; el único 422 cubre feedback de formulario. Solo dos casos
nuevos cubren loading, inventario vacío y error de carga, que no estaban
acreditados por PF-25 (filtros sin coincidencias).

Los pendientes históricos de HTTP y estados UI quedan resueltos con las
fuentes y límites indicados en la matriz. T11 incorpora la confirmación manual
de persistencia en [Operaciones API/BD](operaciones-api-bd.md#ampliación-de-evidencia--8-de-octubre-de-2026).
HU-008 y un editor visual de polígonos no son requisitos de este cierre.
Commit, push y PR no se realizan en esta intervención.
