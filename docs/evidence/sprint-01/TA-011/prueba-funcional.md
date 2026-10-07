# TA-011 — Prueba funcional

Casos ejecutados de los bloques 2, 3, 4 y 5, documentados con las capturas
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
