# SPEC-HU-001 — Inicio de sesión contra PostgreSQL

## Información general

| Campo | Valor |
|---|---|
| Estado | Draft |
| PBI relacionado | HU-001 (T01, T02, T03) · EN-003 Seguridad y acceso |
| Responsable | Fabricio A. |
| Reviewer | Por definir |

## 1. Objetivo

Que el inicio de sesión valide usuario y contraseña contra la tabla `usuarios`
de PostgreSQL (Supabase) en lugar de los usuarios temporales en memoria, que el
formulario de React use la API, y que el código de autenticación quede ubicado
en la estructura modular vigente.

Se parte del trabajo ya hecho en la rama `fix/integracion-login` (commit
`b189c73`), que se adapta a `main` en vez de reescribirse.

## 2. Alcance

### Incluye

- `POST /api/auth/login` y `GET /api/auth/me` contra las tablas reales
  `usuarios` y `roles`.
- Eliminación de los usuarios en memoria y de la clave JWT por defecto.
- Sesión de base de datos por petición (`get_db`).
- Dependencia reutilizable que entrega el usuario autenticado a otras rutas.
- Formulario de login conectado a la API: iniciar sesión, mostrar errores,
  conservar la sesión al recargar y cerrar sesión.
- Reubicación del código que se modifica en `modules/authentication`,
  `shared/security` y `features/authentication`.

### Fuera de alcance

- Alta, edición y activación de usuarios (SPEC-HU-003).
- Restricción de endpoints por permiso (HU-002 T02).
- Recuperación de contraseña, renovación de tokens y bloqueo por intentos.
- Navegación entre pantallas después del login.
- Cambios de esquema, migraciones Alembic o modificación de datos existentes.

## 3. Actor y precondiciones

**Actor:** usuario registrado con rol Administrador, Almacenero u Operario.

**Precondiciones:**

- Existe una cuenta en `usuarios` con `usuario` en minúsculas, `password_hash`
  generado con bcrypt, `estado` e `id_rol` de un rol existente.
- El backend tiene configuradas `DATABASE_URL` y `SECRET_KEY` en su entorno.
- El esquema compartido está en la revisión `c4e8a1f2b3d5` (columnas `usuario`
  y `dni` presentes).

## 4. Entradas y datos

| Campo / dato | Tipo / formato | Regla |
|---|---|---|
| `username` | Texto, 1 a 150 caracteres | Obligatorio. Se normaliza quitando espacios exteriores y pasando a minúsculas. Se compara con `usuarios.usuario`. |
| `password` | Texto, 1 a 128 caracteres | Obligatorio. Una contraseña de más de 72 bytes UTF-8 nunca autentica y no produce error 500. |
| `Authorization` | Cabecera `Bearer <JWT>` | Obligatoria en `GET /api/auth/me` y en toda ruta protegida. |
| `SECRET_KEY` | Variable de entorno | Obligatoria. Sin ella el backend no arranca. |
| `TOKEN_MINUTOS` | Entero positivo, en minutos | Opcional. Valor por defecto: 480. |
| `VITE_API_URL` | URL del backend | Opcional en desarrollo local. |
| Token emitido | JWT HS256 | Contiene `sub` (id de usuario), `username`, `rol` y `exp`. No contiene DNI ni correo. |

## 5. Reglas de negocio

- RN-01: La única credencial de acceso es `usuarios.usuario` más la contraseña.
  No se inicia sesión con correo ni con DNI.
- RN-02: El usuario ingresado se normaliza (sin espacios exteriores, en
  minúsculas) antes de buscarlo.
- RN-03: La contraseña se verifica con bcrypt contra `password_hash`. Nunca se
  guarda ni se compara en texto plano.
- RN-04: Usuario inexistente y contraseña incorrecta devuelven el mismo
  resultado: HTTP 401 con el mensaje "Usuario o contraseña incorrectos.".
- RN-05: Una cuenta inactiva con credenciales correctas recibe HTTP 403 y no
  obtiene token.
- RN-06: El token expira a los `TOKEN_MINUTOS` minutos de emitido.
- RN-07: En cada petición protegida se comprueba que el token sea válido y que
  la cuenta siga existiendo y activa. El rol vigente se toma de la base, no del
  token.
- RN-08: No existen usuarios en memoria ni claves por defecto en el código.
- RN-09: Ninguna respuesta expone `password_hash`, DNI, correo, SQL ni trazas
  internas.
- RN-10: Esta especificación solo lee `usuarios` y `roles`. No modifica el
  esquema ni requiere migraciones.

## 6. Flujo principal

1. El usuario abre el formulario e ingresa usuario y contraseña.
2. El frontend envía `POST /api/auth/login`.
3. El backend normaliza el usuario, lo busca junto con su rol y verifica la
   contraseña.
4. Si la cuenta está activa, responde 200 con `access_token`, `token_type` y
   `usuario` (`id_usuario`, `username`, `nombre`, `rol`).
5. El frontend guarda la sesión en `sessionStorage` y muestra nombre, usuario
   y rol.
6. Al recargar, el frontend valida la sesión guardada con `GET /api/auth/me`.
7. Al cerrar sesión, el frontend elimina la sesión guardada.

## 7. Flujos alternativos y errores

- Campo vacío en el formulario: se muestra un mensaje y no se llama a la API.
  Si la petición llega incompleta al backend, responde 422.
- Usuario inexistente o contraseña incorrecta: 401 con el mensaje único de
  RN-04.
- Cuenta inactiva con credenciales correctas: 403.
- Petición protegida sin token: 401.
- Token alterado, expirado, incompleto o con firma incorrecta: 401, nunca 500.
- Cuenta desactivada o eliminada después de emitir el token: 401 en la
  siguiente petición protegida; el frontend descarta la sesión.
- Backend no disponible: el formulario muestra un mensaje de conexión y
  conserva lo ingresado.

## 8. Criterios de aceptación

- CA-01 (T01): El formulario solicita usuario y contraseña con etiquetas
  visibles; al enviar con un campo vacío muestra un mensaje y no llama a la API.
- CA-02 (T02): Con un usuario activo almacenado en PostgreSQL y su contraseña
  correcta, `POST /api/auth/login` devuelve 200, un JWT y los datos
  `id_usuario`, `username`, `nombre` y `rol`.
- CA-03 (T02): Con usuario inexistente o contraseña incorrecta devuelve 401
  con el mismo mensaje en ambos casos.
- CA-04 (T02): Con una cuenta inactiva y credenciales correctas devuelve 403 y
  no emite token.
- CA-05 (T02): `GET /api/auth/me` con token válido devuelve 200 con
  `id_usuario`, `username` y el `rol` vigente en la base; sin token o con
  token inválido devuelve 401.
- CA-06 (T02): La contraseña solo existe como `password_hash`; ninguna
  respuesta incluye `password_hash`, DNI ni correo.
- CA-07 (T01): Tras iniciar sesión, la interfaz muestra nombre, usuario y rol;
  la sesión se conserva al recargar y desaparece al cerrar sesión.
- CA-08 (T02): El código no contiene usuarios en memoria ni clave JWT por
  defecto; el backend no arranca sin `SECRET_KEY`.
- CA-09 (T03): La matriz de prueba registra al menos un caso válido y uno
  inválido, cada uno con entrada, resultado esperado, resultado obtenido y
  estado.
- CA-10: `python -m pytest -q` pasa sin conectarse a Supabase; `npm run lint`
  y `npm run build` pasan.

## 9. Impacto técnico

### Módulos

Ubicación propuesta. Los nombres de archivo son orientativos y se confirman al
implementar.

- `backend/app/modules/authentication/domain/`: entidad del usuario
  autenticado, sin dependencias de FastAPI ni SQLAlchemy.
- `backend/app/modules/authentication/application/`: caso de uso de
  autenticación y contrato de lectura de usuarios (por usuario y por id).
- `backend/app/modules/authentication/infrastructure/`: lector de usuarios con
  SQL parametrizado sobre `usuarios` y `roles`.
- `backend/app/modules/authentication/presentation/`: router `/api/auth`,
  esquemas HTTP y dependencia del usuario autenticado.
- `backend/app/shared/security/`: hash y verificación de contraseñas, creación
  y validación de JWT. Se traslada desde `app/core/security.py`.
- `backend/app/shared/database/`: se agrega y exporta `get_db`.
- `backend/main.py`: registra el router desde su nueva ubicación y restringe
  CORS a los orígenes locales del frontend.
- Se retiran `app/routers/auth.py`, `app/schemas/auth.py`,
  `app/services/usuarios.py` y `app/core/security.py` una vez actualizados sus
  consumidores.
- `app/core/permissions.py` no se modifica (pertenece a HU-002).
- El script de cuenta de prueba pasa a `backend/scripts/` y se ejecuta solo
  con autorización del equipo, porque inserta un registro en la base compartida.
- La guía `AUTENTICACION.md` pasa a `docs/seguridad/autenticacion.md`.

Los identificadores de código que se toquen pasan a inglés. El contrato HTTP
no cambia.

### API

| Método y ruta | Entrada | Respuestas |
|---|---|---|
| `POST /api/auth/login` | `username`, `password` | 200, 401, 403, 422 |
| `GET /api/auth/me` | Cabecera `Authorization` | 200, 401 |

### Base de datos / migración

- Sin cambios de esquema y sin migraciones.
- Solo lectura de `usuarios` y `roles`.
- No se ejecuta `alembic upgrade`, `downgrade` ni `stamp`.

### UI

- `frontend/src/features/authentication/`: formulario de login, estilos y
  cliente de la API de autenticación.
- La sesión se guarda en `sessionStorage` con una única clave, que las demás
  features leen a través de esta feature.
- Etiquetas visibles "Usuario" y "Contraseña"; el placeholder no las reemplaza.
- Error en texto junto al formulario; botón deshabilitado mientras se envía.
- Sin enlace de recuperación de contraseña.
- Se retiran `frontend/src/components/Login.jsx` y `Login.css` al trasladarlos.

## 10. Pruebas previstas

- API (`backend/tests/api/`): login válido; usuario con mayúsculas y espacios;
  contraseña incorrecta; usuario inexistente con el mismo mensaje; cuenta
  inactiva; campos vacíos; ruta protegida sin token; token alterado, expirado,
  incompleto y con firma incorrecta; `/me` con cuenta revocada; `/me` con rol
  actualizado; rechazo de correo y DNI como identificador; contraseña mayor a
  72 bytes; CORS permitido y no permitido.
- Unitarias (`backend/tests/unit/authentication/`): hash y verificación de
  contraseña; creación y validación de token; arranque sin `SECRET_KEY`.
- Integración (`backend/tests/integration/`): lector de usuarios sobre una
  base SQLite en memoria que reproduce `usuarios` y `roles`; entrada con
  caracteres de SQL tratada como dato.
- Las pruebas fijan `DATABASE_URL` y `SECRET_KEY` de prueba antes de importar
  la aplicación, para no conectarse a Supabase.
- `backend/tests/test_auth.py` se reemplaza por las pruebas anteriores al
  migrar el código que cubre.
- Frontend: `npm run lint`, `npm run build` y lista de comprobación manual
  (teclado, foco, etiquetas, mensajes de error).

Casos de la matriz manual (T03):

| ID | Caso | Resultado esperado |
|---|---|---|
| CP-HU001-01 | Usuario activo con contraseña correcta | 200, token y datos del usuario; la interfaz muestra la sesión |
| CP-HU001-02 | Contraseña incorrecta | 401 con el mensaje único |
| CP-HU001-03 | Usuario inexistente | 401 con el mismo mensaje |
| CP-HU001-04 | Cuenta inactiva | 403, sin token |
| CP-HU001-05 | Campos vacíos en el formulario | Mensaje visible, sin llamada a la API |
| CP-HU001-06 | `/me` sin token | 401 |
| CP-HU001-07 | Recarga con sesión iniciada | La sesión se conserva |
| CP-HU001-08 | Cerrar sesión | La sesión se elimina |

## 11. Evidencias requeridas

En `docs/evidence/sprint-01/HU-001/`:

- `README.md` con rama, commit, comandos, directorio de ejecución y salida de
  `pytest`, `npm run lint` y `npm run build`.
- Matriz de casos con resultado obtenido y estado (PASS, FAIL o BLOCKED).
- Capturas del formulario, de un error de credenciales y de la sesión iniciada.
- Respuesta de la API registrada sin el token completo ni datos personales.

## 12. Decisiones y notas

- D-01: El usuario se compara en minúsculas, igual que el ejemplo del
  Documento de Diseño de Base de Datos. Un registro con `usuario` en mayúsculas
  no podrá iniciar sesión; esta SPEC no modifica datos, así que se informa al
  equipo si existe alguno.
- D-02: `get_db` se ubica en `shared/database`. Ese bloque figura como cerrado
  en `CONTRIBUTING.md`, por lo que el cambio requiere acuerdo de su
  responsable. La prueba de estructura existente sigue pasando.
- D-03: Se reutiliza el commit `b189c73` como base y se adapta a la estructura
  nueva.
- D-04: `main` no tiene script `npm test`. Las pruebas de componentes con
  Vitest y React Testing Library quedan para una tarea aparte.
- D-05: La cuenta inactiva responde 403 solo después de verificar la
  contraseña, de modo que no revela la existencia de un usuario a quien no
  conoce su contraseña.
- N-01: La base compartida está en la revisión `c4e8a1f2b3d5` y `main` solo
  contiene `9b9f04eb67f6`. Esta SPEC no depende de Alembic; la incorporación
  del archivo se trata en SPEC-HU-003.
- N-02: La contraseña de desarrollo que estuvo escrita en
  `app/services/usuarios.py` permanece en el historial de Git y no debe
  reutilizarse en ninguna cuenta.

## Historial de estado

- Draft: 04/10/2026, redacción inicial.
- Reviewed
- Implemented
- Verified
