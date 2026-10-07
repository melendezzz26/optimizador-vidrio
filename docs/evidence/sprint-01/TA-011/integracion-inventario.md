# TA-011 — Integración de inventario

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
