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
