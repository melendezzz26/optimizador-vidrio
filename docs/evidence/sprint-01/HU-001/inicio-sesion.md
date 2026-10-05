# Evidencia HU-001 — Inicio de sesión contra PostgreSQL

## Objetivo

Registrar la validación del inicio de sesión contra la tabla `usuarios`, según [SPEC-HU-001](../../../specs/SPEC-HU-001-inicio-login.md).

## Código validado

- Rama: `feature/HU-001-login`.
- Commit: `b54f3ee`.
- Cambios sin commit al ejecutar: `ninguno`.

Commits de la historia:

| Commit | Contenido |
|---|---|
| `608fc72` | Utilidades de seguridad en `shared/security` y `get_db` en `shared/database`. |
| `a67c27c` | Módulo `authentication` por capas; el login consulta `usuarios` y `roles`. |
| `3b6a7b2` | Formulario en `features/authentication` conectado a la API. |
| `b15004e` | Sincronización con `main` (PR #11 y #12). |
| `b54f3ee` | Adaptación de inventario a la autenticación nueva. |

## Pruebas automáticas

### Backend

- Directorio: `backend/`.
- Comando: `python -m pytest -q`.
- Entorno: Python `3.11.9`, Windows, sin binarios de PostgreSQL locales.
- Resultado observado: `504 passed, 185 skipped, 1 warning in 7.30s`.

Las pruebas omitidas son las de migraciones e integración que requieren un clúster PostgreSQL local. Ninguna prueba se conecta a la base compartida: `tests/conftest.py` fija una base SQLite en memoria antes de importar la aplicación.

Pruebas propias de la HU-001:

| Ubicación | Qué verifica |
|---|---|
| `tests/unit/shared/` | Hash de contraseñas, tokens JWT, arranque sin `SECRET_KEY`, sesión por petición. |
| `tests/unit/authentication/` | Formato del usuario, casos de uso y regla de dependencias entre capas. |
| `tests/integration/test_sqlalchemy_user_reader.py` | Lectura de `usuarios` y `roles` sobre una base de prueba. |
| `tests/api/test_auth_api.py` | Rutas `/api/auth/login` y `/api/auth/me`, códigos 200, 401, 403 y 422, y CORS. |

### Frontend

- Directorio: `frontend/`.
- Comandos: `npm run lint` y `npm run build`.
- Resultado observado de lint: `sin errores`.
- Resultado observado de build: `built in 347ms`.

El repositorio no tiene script `npm test`; no se ejecutaron pruebas de componentes (SPEC-HU-001, decisión D-06).

## Matriz de casos manuales (T03)

Ejecutados en el navegador con el backend y el frontend locales. Estado: PASS, FAIL o BLOCKED.

| ID | Caso | Resultado esperado | Resultado obtenido | Estado |
|---|---|---|---|---|
| CP-HU001-01 | Usuario activo con contraseña correcta | 200, token y datos; la interfaz muestra la sesión | No ejecutado: sin cuenta de prueba | BLOCKED |
| CP-HU001-02 | Mismo usuario escrito en minúsculas | 200, misma cuenta | No ejecutado: sin cuenta de prueba | BLOCKED |
| CP-HU001-03 | Usuario con formato inválido (admin) | Aviso de una letra y 8 dígitos | Aparece "El usuario debe tener una letra seguida de 8 dígitos | PASS |
| CP-HU001-04 | Contraseña incorrecta | "Usuario o contraseña incorrectos." | No ejecutado: sin cuenta de prueba | BLOCKED |
| CP-HU001-05 | Usuario inexistente (F70707070) | El mismo mensaje del caso anterior | Aparece "Usuario o contraseña incorrectos" | PASS |
| CP-HU001-06 | Cuenta inactiva | 403, sin sesión | No ejecutado: sin cuenta de prueba | BLOCKED |
| CP-HU001-07 | Campos vacíos | Mensaje en cada campo, sin llamada a la API | Aparecen: "Ingresa tu usuario" e "Ingresa tu contraseña" | PASS |
| CP-HU001-08 | GET /api/auth/me sin token | 401 | La API responde "Debes iniciar sesión" | PASS |
| CP-HU001-09 | Recarga con sesión iniciada | La sesión se conserva | No ejecutado: sin cuenta de prueba | BLOCKED |
| CP-HU001-10 | Cerrar sesión | Vuelve al formulario | No ejecutado: sin cuenta de prueba | BLOCKED |

Los casos 01, 02, 04, 06, 09 y 10 requieren una cuenta de prueba en la base compartida. Mientras no exista una autorizada por el equipo, se registran como BLOCKED; su comportamiento está cubierto por las pruebas automáticas de API.

## Capturas

En `capturas/`:

- `formulario.png`: formulario con etiquetas, ayuda y botón de mostrar contraseña.
- `campos-vacios.png`: mensajes de campos obligatorios.
- `formato-invalido.png`: aviso de formato del usuario.
- `credenciales-incorrectas.png`: mensaje único de credenciales.
- `api-docs.png`: rutas de autenticación en `/docs`.

Las capturas no muestran contraseñas, tokens ni datos personales.

## Limitaciones

- Sin PostgreSQL local, las pruebas de integración con clúster propio se omiten.
- Sin ejecutor de pruebas de frontend; la interfaz se validó de forma manual.
- Los casos 01, 02, 04, 06, 09 y 10 quedaron BLOCKED por falta de una cuenta de prueba en la base compartida.
