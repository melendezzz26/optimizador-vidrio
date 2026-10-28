# SPEC-TA-041 — Sanitización de errores de autenticación

## Información general

| Campo | Valor |
|---|---|
| ID | TA-041 |
| Nombre | Sanitización de errores de autenticación |
| Tarea | T01 — Evitar eco de contraseña |
| Sprint | Sprint 2 |
| Épica | EN-003 / Seguridad |
| Prioridad / estimación | Alta / 0,5 SP |
| Versión | **1.1**: alternativa A implementada |
| Estado | **Verified**: CI en verde, revisado e integrado en el PR #85 |
| Responsable | Fabricio Aguilar |
| Reviewer | Por asignar (distinto del autor) |
| Rama | `fix/TA-041-sin-eco-de-contrasena` |
| Base | `origin/integration/sprint-01` en `b4a2ce6` (después del PR #84) |
| Fecha | 28/10/2026 |
| Dependencia | HU-001 (login) y el manejo de errores actual; HU-003 (gestión de usuarios) |
| Evidencia | [docs/evidence/sprint-02/TA-041](../evidence/sprint-02/TA-041/README.md) |

## 1. Objetivo

Que **ninguna respuesta del backend devuelva la contraseña** (ni otro dato enviado
por el usuario) cuando la validación de una petición falla, sin cambiar los mensajes
que hoy muestra el frontend.

**Criterio del PBI:** los errores de autenticación y validación no incluyen
credenciales sensibles, y las respuestas siguen siendo comprensibles y compatibles
con el frontend.

## 2. Situación actual (evidencia)

Cuando el cuerpo de una petición no cumple el esquema de Pydantic, FastAPI responde
`422` con su formato por defecto, que incluye el campo `input`: **el valor recibido,
tal cual**. Si el error es de un campo que falta, `input` es **el cuerpo completo**.

Reproducción del 28/10/2026 sobre `ffb5a04` (estos módulos no cambian hasta `b4a2ce6`), con valores de ejemplo:

| Petición | Respuesta 422 (resumida) | ¿Eco de la contraseña? |
|---|---|---|
| `POST /api/auth/login` con contraseña de 130+ caracteres | `"loc":["body","password"], … "input":"S3cr3to-AAAA…"` | **Sí, completa** |
| `POST /api/auth/login` sin `username` | `"loc":["body","username"], … "input":{"password":"MiClaveSecreta1"}` | **Sí, todo el cuerpo** |
| `POST /api/users` (administrador) sin `dni` | `"input":{"nombres":…, "password":"ClaveSecreta-…", "id_rol":3}` | **Sí, todo el cuerpo** |
| `PATCH /api/users/{id}` con `password` numérica | `"loc":["body","password"], … "input":1234567890` | **Sí** |
| `POST /api/users` con `dni` numérico | `"input":123` | No (pero expone el dato enviado) |

`orders`, `clients` y `optimization` ya resuelven esto con una clase `APIRoute`
propia que conserva solo `loc`, `msg` y `type`. `authentication`, `users`,
`inventory` y `roles` usan el formato por defecto.

**Compatibilidad con el frontend.** `authApi.js` y `usersApi.js` solo leen `detail`
cuando es un texto (los mensajes de negocio). Si `detail` es una lista, como en el
422 de Pydantic, muestran un mensaje fijo ("Revisa el usuario y la contraseña
ingresados." / "Revisa los datos ingresados."). Ningún código del frontend ni prueba
del backend lee `input` ni `ctx`.

## 3. Alcance

### Incluye

- Un manejador de `RequestValidationError` que responde con `detail` como lista de
  `{loc, msg, type}`, sin `input`, `ctx` ni `url`.
- Registrarlo en la aplicación (`main.py`).
- Pruebas de regresión del login y de usuarios con contraseñas centinela.

### Fuera de alcance

- Los mensajes de negocio (401, 403, 409 y los 422 con texto de las reglas de dominio):
  no cambian. Ya no incluyen la contraseña (por ejemplo, "La contraseña debe tener
  al menos 8 caracteres.").
- Las clases `APIRoute` de `orders`, `clients` y `optimization`: siguen igual.
- El frontend: no necesita cambios.
- Logs del servidor: hoy los módulos `authentication` y `users` no registran
  cuerpos de petición. No se agrega ni se quita ningún log.

## 4. Alternativas evaluadas

| # | Alternativa | Evaluación |
|---|---|---|
| A | **Manejador global en `main.py` (recomendada)** | Una sola regla para toda la API: protege login, usuarios y cualquier endpoint futuro que reciba datos sensibles. No toca los módulos de otros compañeros: sus routers con `APIRoute` propia siguen igual y los demás solo pierden `input`/`ctx`, que nadie usa. |
| B | Clase `APIRoute` propia en `authentication` y `users`, como en `orders` | Sigue el patrón existente, pero duplica código por tercera vez y un módulo nuevo podría olvidarla. |
| C | Quitar solo el campo `password` de `input` | Más fino, pero frágil: hay que listar nombres de campos sensibles y el resto de los datos (DNI, nombres) seguiría volviendo. |

## 5. Reglas

- **R-01** Un `422` por validación del esquema responde `{"detail": [{"loc": …, "msg": …, "type": …}]}`.
  Nunca incluye `input`, `ctx` ni `url`.
- **R-02** Se conservan `loc`, `msg` y `type`: indican qué campo falló y por qué, sin el valor.
  Es el mismo formato que ya usan `orders`, `clients` y `optimization`.
- **R-03** El código sigue siendo `422` y la forma de `detail` (lista) no cambia, así el
  frontend sigue mostrando sus mensajes de siempre.
- **R-04** Los errores que ya se convierten en `HTTPException` (mensajes de negocio y las
  `APIRoute` existentes) no pasan por este manejador y no cambian.
- **R-05** Sin cambios de esquema, migraciones ni dependencias nuevas.

## 6. Diseño técnico

- **Archivo nuevo:** `backend/app/shared/security/validation_errors.py` (capa compartida de
  seguridad) con `sanitized_validation_handler(request, error)`.
- **`main.py`:** `app.add_exception_handler(RequestValidationError, sanitized_validation_handler)`.
- Presentación pura: no importa dominio ni base de datos.

**Prototipo validado (28/10/2026):** con el manejador registrado, la suite completa del
backend con PostgreSQL pasa sin cambiar ninguna prueba existente: **2245 passed**.

## 7. Criterios de aceptación

| CA | Criterio |
|---|---|
| CA-01 | Un 422 del login (contraseña demasiado larga, campo faltante, tipo inválido) no contiene la contraseña enviada en ninguna parte del cuerpo. |
| CA-02 | Un 422 de `POST /api/users` y `PATCH /api/users/{id}` no contiene la contraseña enviada, incluso cuando el error es de otro campo. |
| CA-03 | Cada error conserva `loc`, `msg` y `type`; no aparecen `input`, `ctx` ni `url`. |
| CA-04 | Los códigos no cambian (422, 401, 403, 409) y los mensajes de negocio con texto siguen iguales. |
| CA-05 | El frontend sigue mostrando "Revisa el usuario y la contraseña ingresados." / "Revisa los datos ingresados." ante un 422 (pruebas existentes en verde). |
| CA-06 | Las suites de backend, frontend y E2E pasan sin cambiar sus aserciones. |

## 8. Pruebas previstas

- **API** (`backend/tests/api/test_validation_errors_sanitized.py`, nueva): contraseñas
  centinela en login y usuarios; se verifica que el texto de la respuesta no las contenga,
  que las claves sean exactamente `loc`, `msg` y `type`, y el código 422. Primero en rojo.
- **Regresión:** suite completa de backend con PostgreSQL; frontend y E2E por CI (con el
  gate de TA-040).

## 9. Evidencia requerida

`docs/evidence/sprint-02/TA-041/README.md` con la salida en rojo antes y en verde
después, la tabla CA → prueba y el resultado de la suite completa.

## 10. Decisiones y preguntas abiertas

- **P-01 (decidida, 28/10/2026):** se adopta la alternativa A (manejador global).
- **P-02 (decidida, 28/10/2026):** al ser global, el 422 de `inventory` y `roles` también deja de incluir `input`.
  Nadie lo usa, pero es un cambio visible para esos módulos: se avisa al equipo en el PR.

## 11. Verificación de criterios de aceptación

| CA | Resultado | Prueba (`tests/api/test_validation_errors_sanitized.py`) |
|---|---|---|
| CA-01 | PASS | `test_login_validation_error_never_echoes_the_password` (contraseña larga, usuario faltante, tipo inválido) y `test_malformed_login_json_is_sanitized` |
| CA-02 | PASS | `test_user_creation_error_in_another_field_does_not_echo_the_password` y `test_user_update_error_never_echoes_the_password` (contraseña con tipo inválido, error en `estado`, campo `usuario` no permitido) |
| CA-03 | PASS | `assert_sanitized`: cada error tiene exactamente `loc`, `msg` y `type` |
| CA-04 | PASS | `test_business_messages_and_codes_do_not_change`; además, `test_auth_api.py` y `test_users_api.py` sin cambios en sus aserciones |
| CA-05 | PASS | El frontend no se modificó; solo lee `detail` cuando es texto y muestra un mensaje fijo ante un 422 con lista. Ninguna prueba ni código lee `input` o `ctx`. |
| CA-06 | PASS | CI del PR #85: backend con PostgreSQL, frontend (unitarias, componentes, lint y build) y E2E con el gate de TA-040, los 3 jobs en verde sin cambiar aserciones. Local: 2254 pruebas backend sin fallos. |

Antes de la corrección, 8 de las 9 pruebas nuevas fallaban; solo pasaba la de
mensajes de negocio (CA-04), que ya funcionaba. Detalle en la evidencia.

## Historial de estado

| Fecha | Versión | Estado | Cambio |
|---|---|---|---|
| 28/10/2026 | 0.1 | Draft | Borrador: reproducción del eco en login y usuarios, alternativas y reglas. |
| 28/10/2026 | 1.0 | Draft | P-01 (alternativa A) y P-02 decididas. Pendiente: revisión en el PR. |
| 28/10/2026 | 1.1 | Implemented | Manejador global implementado; 8 pruebas en rojo antes y 9 en verde después; suite backend 2254 PASS. Pendiente: CI del PR y revisión para Verified. |
| 28/10/2026 | 1.1 | Verified | PR #85 revisado e integrado en `integration/sprint-01` con los 3 checks del CI en verde (CA-06 en PASS). |