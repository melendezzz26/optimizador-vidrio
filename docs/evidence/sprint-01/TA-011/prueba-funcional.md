# TA-011 — Prueba funcional

Casos de los bloques 2 a 7, con resultados y pendientes documentados con las capturas
oficiales y las confirmaciones manuales del usuario recogidas en
[Integración de inventario](integracion-inventario.md). Esta actualización
documental no implica una nueva ejecución de las pruebas.

| ID | Caso | Entrada | Esperado | Obtenido | Estado |
| --- | --- | --- | --- | --- | --- |
| TA011-PF-01 | Consulta de inventario autenticada | Sesión Almacenero; abrir Gestión de inventario y consultar Planchas y Retazos. | Catálogo y listados disponibles; HTTP 200; sidebar correspondiente al rol. | GET tipos-vidrio, planchas y retazos con 200 OK; registros y nombres de tipos visibles; sidebar con Inicio, Gestión de inventario y Consulta de resultados. | PASS |
| TA011-PF-02 | Registro válido de plancha | Espejo; id_tipo_vidrio 6; espesor 6 mm; ancho 1000 mm; alto 500 mm; cantidad 2. | POST 201, GET posterior 200, cierre del formulario, mensaje de éxito y nueva fila sin F5. | POST 201 Created y GET 200 OK; formulario cerrado; mensaje "Plancha registrada correctamente."; fila Espejo 6 mm, 1000 × 500 mm, cantidad 2, Activo, visible sin recarga manual según confirmación del usuario. | PASS |
| TA011-PF-03 | Registro válido de retazo RET-TA011-E2E-001 | Código RET-TA011-E2E-001; Espejo; id_tipo_vidrio 6; espesor 6 mm; RECTANGULO; ancho 1000 mm; alto 500 mm; área no enviada por frontend, según información de la prueba. | POST 201, área calculada por backend de 500000 mm², GET posterior 200, cierre del formulario y listado actualizado sin F5. | POST 201 Created, GET 200 OK; formulario cerrado; mensaje "Retazo registrado correctamente."; fila con área 500000 mm² y estado Activo. Cálculo en backend y actualización sin F5 confirmados por el usuario. | PASS |
| TA011-PF-04 | Código de retazo duplicado | Reintento de RET-TA011-E2E-001 ya existente; Espejo; 6 mm; Rectángulo; ancho 1233 mm y alto 1234 mm visibles en el formulario. | HTTP 409, mensaje visible, formulario permanece abierto, sin refresco GET. | HTTP 409 Conflict; mensaje único "El código de retazo ya existe."; formulario abierto y datos conservados; sin GET posterior observado en el tramo capturado. | PASS |

Referencias por caso:

- TA011-PF-01: [Planchas](capturas/TA011-01-listado-planchas-almacenero.png), [Retazos](capturas/TA011-02-listado-retazos-almacenero.png) y [GET 200](capturas/TA011-03-endpoints-inventario-200.png).
- TA011-PF-02: [Formulario de plancha](capturas/TA011-05-formulario-registro-plancha.png), [Listado actualizado](capturas/TA011-06-plancha-registrada-listado.png) y [POST/GET de plancha](capturas/TA011-07-post-plancha-201.png).
- TA011-PF-03: [Formulario de retazo](capturas/TA011-08-formulario-registro-retazo.png), [Listado actualizado](capturas/TA011-09-retazo-registrado-listado.png) y [POST/GET de retazo](capturas/TA011-10-post-retazo-201.png).
- TA011-PF-04: [Conflicto visible](capturas/TA011-11-retazo-error-409.png) y [HTTP 409](capturas/TA011-12-post-retazo-409.png).

No se afirma persistencia tras F5 ni se registran casos con entrada
insuficientemente identificada. Los logs no muestran cuerpos de solicitudes
ni consultas SQL directas.

## Bloque 5 — Cambio de estado y permisos de gestión

| ID | Caso | Entrada/precondición | Esperado | Obtenido | Estado | Evidencia |
| --- | --- | --- | --- | --- | --- | --- |
| TA011-PF-05 | Desactivar plancha | Rol Almacenero; plancha Catedral 5 mm, 3200 × 2000 mm, cantidad 12, activa; seleccionar Desactivar. | Estado Inactivo, acción Activar y feedback de éxito; PATCH 200 y GET posterior 200. | Catedral Inactivo y acción Activar; mensaje "Plancha desactivada correctamente.". Los logs muestran dos pares PATCH/GET de planchas con 200, sin identificar el estado enviado en cada PATCH. | PASS | [TA011-14](capturas/TA011-14-plancha-desactivada.png) y [TA011-18](capturas/TA011-18-patch-estado-200.png). |
| TA011-PF-06 | Reactivar plancha | Rol Almacenero; la misma plancha Catedral inactiva; seleccionar Activar. | Estado Activo, acción Desactivar y feedback de éxito; PATCH 200 y GET posterior 200. | Catedral Activo y acción Desactivar; mensaje "Plancha activada correctamente.". Secuencias API de planchas con 200 observadas en conjunto. | PASS | [TA011-14](capturas/TA011-14-plancha-desactivada.png), [TA011-15](capturas/TA011-15-plancha-reactivada.png) y [TA011-18](capturas/TA011-18-patch-estado-200.png). |
| TA011-PF-07 | Desactivar retazo | Rol Almacenero; RET-HU005-002, Incoloro, 6 mm, Rectángulo 600 × 300 mm, activo; seleccionar Desactivar. | Estado Inactivo y acción Activar; PATCH 200 y GET posterior 200. | RET-HU005-002 Inactivo y acción Activar. No se observa mensaje de desactivación. Los logs muestran dos pares PATCH/GET de retazos con 200, sin identificar el estado enviado en cada PATCH. | PASS | [TA011-16](capturas/TA011-16-retazo-desactivado.png) y [TA011-18](capturas/TA011-18-patch-estado-200.png). |
| TA011-PF-08 | Reactivar retazo | Rol Almacenero; RET-HU005-002 inactivo; seleccionar Activar. | Estado Activo, acción Desactivar y feedback de éxito; PATCH 200 y GET posterior 200. | RET-HU005-002 Activo y acción Desactivar; mensaje "Retazo activado correctamente.". Secuencias API de retazos con 200 observadas en conjunto. | PASS | [TA011-16](capturas/TA011-16-retazo-desactivado.png), [TA011-17](capturas/TA011-17-retazo-reactivado.png) y [TA011-18](capturas/TA011-18-patch-estado-200.png). |
| TA011-PF-09 | Operario consulta inventario sin acciones de gestión | Sesión con rol Operario; abrir Gestión de inventario y consultar Planchas y Retazos. | Ambos listados visibles; sin Registrar plancha/retazo, columna Acciones ni Activar/Desactivar. | Ambos listados visibles y acciones de gestión ausentes en las capturas. No se acredita un 403 backend. | PASS | [TA011-19](capturas/TA011-19-operario-planchas-solo-consulta.png) y [TA011-20](capturas/TA011-20-operario-retazos-solo-consulta.png). |

Los PASS se limitan al alcance descrito en cada caso. TA011-PF-07 acredita
el cambio de estado y acción; no acredita el mensaje de desactivación del
retazo. Las operaciones PATCH individuales no se clasifican como activar
o desactivar a partir de los logs, que no muestran el cuerpo enviado.

Pendientes: edición de campos de plancha; edición de campos/geometría de
retazo; prueba backend 403; filtros; pruebas 401/422; HU-008.

## Bloque 6 — Edición de plancha

Entidad de prueba: Espejo, 6 mm, 1000 × 500 mm, cantidad inicial 2, Activo.
La sesión de edición es Almacenero según el contexto informado; TA011-21
muestra los valores pero no incluye el encabezado con el rol. Los resultados
combinan capturas, revisión estática y confirmaciones manuales, sin presentar
estas fuentes como equivalentes.

| ID | Caso | Entrada/precondición | Esperado | Obtenido | Estado | Evidencia |
| --- | --- | --- | --- | --- | --- | --- |
| TA011-PF-10 | Abrir edición y precargar plancha | Abrir Editar para la plancha de prueba con cantidad 2. | Formulario edit y valores actuales precargados. | Editar plancha muestra Espejo, 6 mm, 1000.00, 500.00 y cantidad 2. | PASS | [TA011-21](capturas/TA011-21-editar-plancha-precarga.png); rol por contexto de sesión. |
| TA011-PF-11 | Editar cantidad de plancha | Cantidad 2 → 3. | PATCH exitoso, GET posterior y fila actualizada sin recarga manual. | PATCH /planchas/3 con 200 y GET /planchas con 200; cantidad 3, Activo y mensaje "Plancha actualizada correctamente.". Sin F5 según ejecución informada. El log no muestra el payload. | PASS | [TA011-22](capturas/TA011-22-plancha-editada-cantidad.png) y [TA011-23](capturas/TA011-23-patch-edicion-plancha-200.png). |
| TA011-PF-12 | Cantidad cero en edición | Cantidad 3 → 0. | Actualización aceptada, cantidad 0 y sin cambio automático de estado. | Mensaje de actualización correcta; Espejo 6 mm, 1000 × 500 mm, cantidad 0 y Activo. | PASS | [TA011-24](capturas/TA011-24-plancha-cantidad-cero.png). |
| TA011-PF-13 | Guardar plancha sin modificaciones | Formulario precargado con Espejo, 6 mm, 1000 × 500 mm y cantidad restaurada a 2; guardar sin cambios. | No PATCH vacío ni actualización; formulario abierto y mensaje "No hay cambios para guardar.". | Formulario y valores conservados, mensaje visible. La lógica retorna antes de PATCH/GET; el log ampliado no muestra otro PATCH en su tramo final, sin correlación temporal exacta con el clic. | PASS | [TA011-25](capturas/TA011-25-edicion-plancha-sin-cambios.png), revisión estática y [log ampliado](capturas/Captura%20de%20pantalla%202026-10-07%20005859.png). |
| TA011-PF-14 | Cancelar edición de plancha | Formulario de edición abierto; pulsar Cancelar. | Volver al listado, sin actualizar la entidad ni enviar PATCH. | El usuario confirmó explícitamente cierre del formulario, vuelta al listado y comprobación de ausencia de PATCH. | PASS | Verificación manual confirmada, sin captura. |
| TA011-PF-15 | Operario sin acción Editar | Sesión Operario; consultar Planchas. | Listado visible sin acciones de gestión. | Planchas activa y registros visibles; sin Registrar plancha, columna Acciones, Editar ni Activar/Desactivar. No acredita HTTP 403. | PASS | [TA011-26](capturas/TA011-26-operario-sin-editar-plancha.png). |

La restauración a cantidad 2 y estado Activo se respalda con la
[captura adicional 005114](capturas/Captura%20de%20pantalla%202026-10-07%20005114.png)
y con TA011-26.

Create exige cantidad > 0; edit/PATCH admite cantidad entera >= 0, según
la lógica revisada. El PATCH parcial incluye solo diferencias entre
id_tipo_vidrio, espesor_mm, ancho_mm, alto_mm y cantidad. TA011-23 no muestra
los valores enviados. TA011-25 por sí sola no demuestra ausencia de HTTP.

Bloque 6: PASS con los límites de evidencia indicados. Pendientes restantes:
edición de retazo; filtros tipo/espesor/estado; validaciones generales 401;
403 backend; 422 formal; estados loading/empty/error que falten; HU-008
separado. No se declara TA-011 terminada.

## Bloque 7 — Edición de retazo

Resultados documentados mediante las capturas oficiales TA011-28 a TA011-32,
la ejecución rectangular informada, la verificación manual de precarga y la
revisión estática. No se conserva una captura adicional para PF-16.

| ID | Caso | Entrada/precondición | Esperado | Obtenido | Estado | Evidencia |
| --- | --- | --- | --- | --- | --- | --- |
| TA011-PF-16 | Precargar edición de retazo | RET-TA011-E2E-001 existente. | Código RET-TA011-E2E-001, Espejo, 6 mm, Rectángulo, ancho 1000 y alto 500 precargados. | Todos los valores precargados correctamente después de normalizar el espesor. Verificación manual E2E sin captura adicional. | PASS | Verificación manual posterior; sin captura oficial. |
| TA011-PF-17 | Editar geometría rectangular | RET-TA011-E2E-001 activo; cambiar alto 500 → 400, conservar ancho 1000 mm. | PATCH 200, GET de retazos 200, geometría actualizada y feedback de éxito. | PATCH /api/inventory/retazos/3 y GET /api/inventory/retazos con 200; fila 1000 × 400 mm, Activo y "Retazo actualizado correctamente.". Log sin payload. | PASS | [TA011-28](capturas/TA011-28-retazo-geometria-editada.png) y [TA011-29](capturas/TA011-29-patch-edicion-retazo-200.png). |
| TA011-PF-18 | Recalcular área por cambio geométrico | Mismo cambio rectangular de PF-17; área inicial 500000 mm² según la prueba informada. | Backend recalcula 400000 mm²; frontend muestra el valor del GET. | Área visible 400000 mm². Revisión estática confirma cálculo en backend y visualización de area_mm2 recibido, sin enviarlo desde el formulario. | PASS | [TA011-28](capturas/TA011-28-retazo-geometria-editada.png), [TA011-29](capturas/TA011-29-patch-edicion-retazo-200.png) y revisión estática. |
| TA011-PF-19 | Restaurar geometría original | RET-TA011-E2E-001 en 1000 × 400 mm; restaurar alto a 500 mm. | Geometría 1000 × 500 mm, área 500000 mm², Activo. | Fila restaurada con esos valores y mensaje de actualización correcta. No se dispone de log específico de este segundo PATCH. | PASS | [TA011-30](capturas/TA011-30-retazo-restaurado.png). |
| TA011-PF-20 | Guardar retazo sin cambios | Editar RET-HU005-001, Incoloro, Rectángulo 850 × 420 mm; guardar sin modificaciones. | Sin PATCH vacío ni GET asociado; formulario abierto y mensaje "No hay cambios para guardar.". | Formulario abierto, código/material/dimensiones visibles y mensaje esperado. Ausencia de PATCH/GET confirmada estáticamente por retorno anticipado, no por captura de red. | PASS en este alcance | [TA011-31](capturas/TA011-31-edicion-retazo-sin-cambios.png) y revisión estática. |
| TA011-PF-21 | Operario sin acción Editar retazo | Sesión Operario; consultar Retazos. | Listado visible sin registro ni gestión. | Rol Operario y listado visibles; sin Registrar retazo, Acciones, Editar ni Activar/Desactivar. No acredita HTTP 403. | PASS | [TA011-32](capturas/TA011-32-operario-sin-editar-retazo.png). |

Durante la primera ejecución se detectó que el select no reconocía
correctamente valores equivalentes "6.0" y "6". Se normalizó el valor inicial
y posteriormente se repitió la comprobación manual, mostrando correctamente
6 mm. La captura antigua 021018 se conserva como evidencia diagnóstica/no
oficial y no se usa para aprobar PF-16. Sin secretos visibles;
la captura de Operario contiene datos identificativos que no se transcriben.

Bloque 7: **PASS**.

E2E limitado a RECTANGULO; CIRCUNFERENCIA y POLIGONO_CONVEXO solo verificadas
estáticamente. No se implementó editor visual de polígonos; la reutilización
del editor geométrico de Pedidos queda como mejora UI/UX posterior. Pendientes
posteriores: mejora UI/UX de Inventario, filtros, mejora UX del editor de
geometrías/polígonos, 401, 403 backend, 422 formal y estados UI restantes.
HU-008 permanece fuera de este cierre.

## Bloque 8A — Mejora UI/UX y filtros de Inventario

Validación E2E confirmada del 7 de octubre de 2026 con datos reales,
Almacenero y Operario; implementación `fac938c`. Capturas TA011-33 a TA011-40.
Las acciones, ausencia de solicitudes al filtrar, HTTP, restauración y teclas
se sustentan en la ejecución confirmada; las capturas muestran estados visibles.

| ID | Caso | Precondición | Acción | Esperado | Obtenido | Evidencia | Resultado |
| --- | --- | --- | --- | --- | --- | --- | --- |
| TA011-PF-22 | Filtrar planchas por tipo, espesor y estado | Almacenero; 4 planchas cargadas; filtros en Todos. | Seleccionar Espejo, 6 mm, Activo/Inactivo; cambiar tipo a Catedral. | Reducir resultados, contador correcto, sin HTTP adicional; limpiar espesor incompatible. | Espejo + 6 mm: 2 de 4; Activo mantiene 2 e Inactivo da 0. Sin solicitudes adicionales; cambiar a Catedral limpia Espesor. | [TA011-33](capturas/TA011-33-planchas-filtros.png), [TA011-34](capturas/TA011-34-planchas-sin-resultados.png) y ejecución E2E. | PASS |
| TA011-PF-23 | Filtrar retazos por tipo, espesor y estado | Almacenero; 3 retazos cargados. | Seleccionar Incoloro, 6 mm y Activo; después Inactivo. | Coincidencias y contador correctos, sin HTTP adicional. | Incoloro + 6 mm + Activo: 2 de 3; Inactivo: 0 de 3. Sin HTTP adicional. | [TA011-35](capturas/TA011-35-retazos-filtros.png), [TA011-36](capturas/TA011-36-retazos-sin-resultados.png) y ejecución E2E. | PASS |
| TA011-PF-24 | Limpiar filtros | Filtros activos en cada listado. | Pulsar Limpiar filtros en Planchas y Retazos. | Restablecer Todos, recuperar el total y ocultar el botón. | Planchas vuelve a 4 de 4; Retazos a 3 de 3; botón ausente sin filtros activos. | Ejecución E2E; [TA011-33](capturas/TA011-33-planchas-filtros.png)/[TA011-35](capturas/TA011-35-retazos-filtros.png) muestran el botón antes y [TA011-38](capturas/TA011-38-operario-filtros-solo-consulta.png) muestra Retazos sin filtros. | PASS |
| TA011-PF-25 | Mostrar estado sin resultados | Inventario existente: 4 planchas y 3 retazos. | Combinar Espejo + 6 mm + Inactivo en Planchas e Incoloro + 6 mm + Inactivo en Retazos; limpiar. | Mensaje de cero coincidencias, distinto de inventario vacío; limpieza recupera datos. | 0 de 4 y 0 de 3 con "No hay resultados para los filtros seleccionados."; limpiar recupera ambos listados. No se eliminaron datos para probar empty. | [TA011-34](capturas/TA011-34-planchas-sin-resultados.png), [TA011-36](capturas/TA011-36-retazos-sin-resultados.png) y ejecución E2E. | PASS |
| TA011-PF-26 | Actualizar inventario con filtros activos | Catedral, 5 mm, 3200 × 2000 mm, cantidad 12, Activo; filtro Catedral + Activo con 2 de 4. | Desactivar, consultar Inactivo, reactivar y volver a Activo. | PATCH 200 + GET 200; excluir del filtro al dejar de coincidir, actualizar contador y restaurar el estado original. | Al desactivar queda 1 de 4; la plancha aparece bajo Inactivo. Cada PATCH /planchas/2 y GET /planchas devuelve 200. Reactivada: 2 de 4; dato final Activo, sin altas nuevas. | [TA011-37](capturas/TA011-37-operacion-con-filtro-activo.png) muestra la desactivación; red y restauración por ejecución E2E confirmada. | PASS |
| TA011-PF-27 | Operario conserva consulta y filtros sin acciones | Sesión Operario con datos existentes. | Consultar, filtrar y limpiar Planchas y Retazos. | Listados y filtros disponibles; sin Registrar, Acciones, Editar ni Activar/Desactivar. | Planchas 4 → 2 → 4; Retazos 3 → 2 → 3, sin acciones de gestión ni HTTP adicional al filtrar. No se forzó un 403. | [TA011-38](capturas/TA011-38-operario-filtros-solo-consulta.png) muestra Retazos; ambos listados comprobados en el E2E. | PASS |
| TA011-PF-28 | Responsive y navegación por teclado | Sesión Almacenero; listados cargados. | Revisar 1366 × 768, 768, 400 y 375 px; usar Tab, ArrowRight, ArrowLeft, Home y End; desplazar la tabla con teclado. | Sin overflow global, filtros/etiquetas utilizables, acciones accesibles mediante scroll interno y foco visible. | Los cuatro tamaños pasan; filtros apilados en móvil, botones sin superposición, tabs operables, tabla y acciones alcanzables por teclado. Estados con texto además del color. | [TA011-39](capturas/TA011-39-responsive-400.png), [TA011-40](capturas/TA011-40-responsive-375-acciones-foco.png), foco en [TA011-33](capturas/TA011-33-planchas-filtros.png) y ejecución E2E para tamaños/teclas. | PASS |

Regresión create/edit/state: **PASS** en el alcance de abrir/cancelar registro
y edición de ambas entidades, más cambio de estado reversible de plancha.
No se insertaron registros nuevos; la Catedral de 5 mm, 3200 × 2000 mm,
cantidad 12 quedó Activa.

Los filtros locales Tipo / Espesor / Estado son independientes por pestaña.
El contador y Limpiar filtros distinguen coincidencias del total; las tablas
mantienen geometría compacta, área legible y acciones dentro del scroll interno.
No-results no equivale a inventario vacío: no se acredita una nueva prueba
E2E de empty sin registros.

**Bloque 8A = PASS. TA-011 todavía no está finalizada.** Los pendientes de
filtros/mejora general citados en bloques anteriores quedan actualizados.
Siguen pendientes editor visual/reutilizable para POLIGONO_CONVEXO, 401,
403 backend, validación formal restante de 422 de TA-011, cierre documental
final y PR. No se afirma que HU-007 esté integrado a main; HU-008 queda fuera.

Las capturas revisadas no exponen JWT, Authorization, contraseñas, hashes,
tokens ni secretos; no se transcriben los datos identificativos de las cuentas.
