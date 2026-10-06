# Evidencia HU-003 — Gestión de usuarios

## Objetivo

Registrar la validación de la gestión de usuarios (API y pantalla), según
[SPEC-HU-003](../../../specs/SPEC-HU-003-gestion-usuarios.md).

## Código validado

- Rama: `feature/HU-003-modulo-usuarios`.
- Commit: `dba14dc`.
- Cambios sin commit al ejecutar: `ninguno`.

Commits de la historia:

| Commit | Contenido |
|---|---|
| `88da233` | SPEC de gestión de usuarios. |
| `f2077c3` | Dominio y casos de uso de usuarios; `require_permission` pasa a autenticación. |
| `b3dfb22` | Repositorio SQLAlchemy y rutas `/api/users`. |
| `f9b8f26` | Sincronización con `main` (base visual compartida, PR #16). |
| `dba14dc` | Pantalla de gestión de usuarios sobre la base visual compartida. |

## Pruebas automáticas

### Backend

- Directorio: `backend/`.
- Comando: `python -m pytest -q`.
- Entorno: Python `3.11.9`, Windows, sin binarios de PostgreSQL locales.
- Resultado observado: `654 passed, 185 skipped, 1 warning in 14.41s`.

Las pruebas omitidas son las de migraciones e integración que requieren un
clúster PostgreSQL local. Ninguna prueba se conecta a la base compartida:
`tests/conftest.py` fija una base SQLite en memoria antes de importar la
aplicación.

Pruebas propias de la HU-003 (150 casos nuevos):

| Ubicación | Qué verifica |
|---|---|
| `tests/unit/users/test_rules.py` | Generación del usuario de acceso, DNI, nombres y contraseña. |
| `tests/unit/users/test_use_cases.py` | Alta, consulta y modificación con un repositorio en memoria; regla RN-07. |
| `tests/unit/users/test_layer_dependencies.py` | Dominio y aplicación sin FastAPI ni SQLAlchemy. |
| `tests/integration/test_sqlalchemy_user_repository.py` | Lectura y escritura en `usuarios` y `roles` sobre una base de prueba. |
| `tests/api/test_users_api.py` | Rutas `/api/users`: 200, 201, 401, 403, 404, 409 y 422; login del usuario creado; desactivación. |
| `tests/api/test_require_permission.py` | Restricción por permiso con el rol vigente en la base (HU-002 T02). |

### Frontend

- Directorio: `frontend/`.
- Comandos: `npm run lint` y `npm run build`.
- Resultado observado de lint: `sin errores`.
- Resultado observado de build: `built in 348ms`.

El repositorio no tiene script `npm test`; no se ejecutaron pruebas de
componentes.

## Matriz de casos manuales (T03)

Ejecutados en el navegador con el backend y el frontend locales. El backend
se conectó a una base SQLite local y desechable, con las tablas `usuarios` y
`roles` creadas a partir del modelo y una cuenta de Administrador de prueba.
No se usó la base compartida. Estado: PASS, FAIL o BLOCKED.

| ID | Caso | Resultado esperado | Resultado obtenido | Estado |
|---|---|---|---|---|
| CP-HU003-01 | Alta válida | 201; usuario de acceso generado; aparece en la tabla | Aparece el aviso con el usuario de acceso generado y la fila nueva en la tabla | PASS |
| CP-HU003-02 | Alta con DNI ya registrado | 409; no se crea el usuario | Aparece "Ya existe un usuario con ese DNI." junto al campo y no se agrega ninguna fila | PASS |
| CP-HU003-03 | Edición de nombres y rol | 200; DNI y usuario de acceso sin cambios | Se guardan los cambios; el DNI y el usuario de acceso no se modifican | PASS |
| CP-HU003-04 | Desactivar usuario | 200; el usuario no puede iniciar sesión | El usuario queda Inactivo y el login lo rechaza | PASS |
| CP-HU003-05 | Reactivar usuario | 200; el usuario vuelve a iniciar sesión | El usuario queda Activo e inicia sesión | PASS |
| CP-HU003-06 | DNI con formato inválido | Mensaje junto al campo | Aparece el aviso de 8 dígitos junto al campo DNI | PASS |
| CP-HU003-07 | Rol inexistente | 422 | No ejecutado: el selector solo ofrece roles existentes. Cubierto por `tests/api/test_users_api.py`. | BLOCKED |
| CP-HU003-08 | Administrador intenta desactivarse | No puede; sigue activo | Su fila muestra "Tu cuenta" y no ofrece el botón Desactivar | PASS |
| CP-HU003-09 | Operario intenta acceder a usuarios | La interfaz no le ofrece la pantalla | Con una sesión de Operario no aparece la opción Panel de roles | PASS |
| CP-HU003-10 | Petición sin sesión | 401 | La API responde "Debes iniciar sesión." | PASS |

## Capturas

En `capturas/`:

- `pantalla.png`: formulario y tabla dentro de la base visual, con *Panel de roles* resaltado.
- `alta-usuario.png`: aviso con el usuario de acceso generado.
- `dni-duplicado.png`: mensaje junto al campo DNI.
- `edicion.png`: DNI y usuario de acceso como solo lectura.
- `usuario-desactivado.png`: estado Inactivo en la tabla.
- `cuenta-propia.png`: fila propia con "Tu cuenta".

Los DNI y usuarios son ficticios. Las capturas no muestran contraseñas ni tokens.

## Limitaciones

- Los casos manuales se ejecutaron sobre SQLite local, que no aplica las
  restricciones CHECK ni los límites de longitud de PostgreSQL. Falta
  repetirlos contra la base compartida cuando exista una cuenta de
  Administrador autorizada.
- Sin PostgreSQL local, las pruebas de integración con clúster propio se omiten.
- Sin ejecutor de pruebas de frontend; la interfaz se validó de forma manual.
- El acceso a la pantalla usa un cambio de sección provisional en `App.jsx`,
  porque la barra lateral compartida aún no tiene navegación.
