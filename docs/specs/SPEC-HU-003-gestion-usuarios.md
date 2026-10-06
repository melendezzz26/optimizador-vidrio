# SPEC-HU-003 — Gestión de usuarios

## Información general

| Campo | Valor |
|---|---|
| Estado | Draft |
| PBI relacionado | HU-003 (T01, T02, T03) · HU-002 T02 · EN-003 Seguridad y acceso |
| Responsable | Fabricio A. |
| Reviewer | Por definir |

## 1. Objetivo

Que el Administrador pueda crear, consultar, editar y activar o desactivar
usuarios con un rol definido, desde una pantalla y una API, sobre la tabla
`usuarios` de la base compartida.

Se reutiliza la lógica de la rama anterior `feature/HU-003-gestion-usuarios`,
ubicada ahora en `modules/users` y `features/users` y ajustada a la
autenticación de HU-001 y al modelo de datos v1.1.

## 2. Alcance

### Incluye

- API de usuarios: listar roles, crear, listar, consultar y modificar
  (datos, rol, contraseña y estado).
- Generación automática del usuario de acceso a partir del nombre y el DNI.
- Restricción de la API al rol Administrador, reutilizando
  `require_permission`, que se traslada del módulo de inventario al de
  autenticación (parte de backend de HU-002 T02).
- Pantalla de gestión de usuarios, visible solo para el Administrador.
- Pruebas unitarias, de integración y de API, y matriz de casos.

### Fuera de alcance

- Eliminar usuarios.
- Cambios de esquema y migraciones.
- Creación del primer Administrador en la base compartida.
- Recuperación de contraseña y cambio de contraseña por el propio usuario.
- Paginación, búsqueda y filtros.
- Menú general de navegación y librería de rutas.
- Restricciones de interfaz por rol en otras pantallas (resto de HU-002 T02).

## 3. Actor y precondiciones

**Actor:** Administrador.

**Precondiciones:**

- HU-001 fusionada en `main`: login contra la base, `get_current_user` y
  utilidades de `shared/security`.
- Existe al menos una cuenta activa con rol Administrador en la base.
- Los roles Administrador, Almacenero y Operario existen en `roles`.
- La tabla `usuarios` sigue el modelo v1.1: `id_usuario`, `dni`, `nombres`,
  `apellidos`, `usuario`, `password_hash`, `estado`, `fecha_creacion` e
  `id_rol`.

## 4. Entradas y datos

| Campo / dato | Tipo / formato | Regla |
|---|---|---|
| `nombres` | Texto, 1 a 100 caracteres | Obligatorio. Se quitan los espacios sobrantes. Debe empezar con una letra. |
| `apellidos` | Texto, 1 a 100 caracteres | Obligatorio. Se quitan los espacios sobrantes. |
| `dni` | Texto, exactamente 8 dígitos | Obligatorio en el alta. Único. No editable. |
| `usuario` | Texto: una letra mayúscula y 8 dígitos | Lo genera el backend. El cliente no lo envía. No editable. |
| `password` | Texto, mínimo 8 caracteres y máximo 72 bytes UTF-8 | Obligatoria en el alta. Opcional al modificar: si se envía, reemplaza la anterior. |
| `id_rol` | Entero positivo | Obligatorio en el alta. Debe existir en `roles`. |
| `estado` | Booleano | Verdadero al crear. Se cambia al modificar. |
| `fecha_creacion` | Fecha y hora en UTC | La asigna el backend al crear. |
| Respuesta | JSON | `id_usuario`, `nombres`, `apellidos`, `dni`, `usuario`, `estado`, `id_rol`, `rol`. Nunca `password_hash`. |

Las peticiones con campos no previstos se rechazan con 422.

## 5. Reglas de negocio

- RN-01: Solo el rol Administrador gestiona usuarios (permiso
  `GESTIONAR_USUARIOS` de la matriz de permisos). La autorización se valida en
  el backend con el rol vigente en la base, aunque la interfaz oculte la
  pantalla.
- RN-02: El usuario de acceso es la inicial del primer nombre, sin tilde y en
  mayúscula, seguida del DNI. Ejemplo: "Álvaro" con DNI 71234567 genera
  `A71234567`.
- RN-03: No pueden existir dos usuarios con el mismo DNI. Como el usuario de
  acceso deriva del DNI, tampoco puede repetirse.
- RN-04: El DNI y el usuario de acceso no cambian después del alta, aunque se
  modifiquen los nombres.
- RN-05: Todo usuario queda asociado a un rol existente.
- RN-06: No se eliminan usuarios; solo se activan o desactivan. Un usuario
  inactivo no puede iniciar sesión y sus sesiones abiertas dejan de valer en
  la siguiente petición (SPEC-HU-001).
- RN-07: Un Administrador no puede desactivar su propia cuenta ni cambiar su
  propio rol. Así siempre queda al menos un Administrador activo.
- RN-08: La contraseña se guarda solo como hash bcrypt. No se devuelve ni se
  registra en logs.
- RN-09: El DNI no se muestra en la tabla general de usuarios ni se incluye en
  logs o tokens. Solo aparece en el formulario de alta y edición.
- RN-10: Esta especificación no modifica el esquema de la base de datos.

## 6. Flujo principal

Alta de usuario:

1. El Administrador abre la pantalla; se cargan la lista de usuarios y las
   opciones de rol.
2. Completa nombres, apellidos, DNI, contraseña y rol, y envía el formulario.
3. El backend valida los datos, comprueba que el rol exista y que el DNI no
   esté registrado, genera el usuario de acceso y guarda el registro con la
   contraseña convertida en hash.
4. Responde 201 con los datos del usuario creado.
5. La pantalla muestra el usuario de acceso generado y actualiza la tabla.

Edición: el Administrador selecciona un usuario, modifica nombres, apellidos,
rol o contraseña, y el backend responde 200 con los datos actualizados. El DNI
y el usuario de acceso se muestran como solo lectura.

Cambio de estado: el Administrador activa o desactiva un usuario desde la
tabla y el backend responde 200 con el nuevo estado.

## 7. Flujos alternativos y errores

- Datos inválidos (DNI que no tiene 8 dígitos, campos vacíos, contraseña fuera
  de los límites, nombre que no empieza con letra, rol inexistente, campos no
  previstos): 422. La pantalla muestra el error junto al campo y conserva lo
  ingresado.
- DNI ya registrado: 409 "Ya existe un usuario con ese DNI.". No se crea el
  registro.
- El Administrador intenta desactivarse o cambiar su propio rol: 409. No se
  guardan cambios.
- Usuario inexistente al consultar o modificar: 404.
- Sin sesión o con sesión expirada: 401. La pantalla vuelve al inicio de
  sesión.
- Rol sin permiso (Almacenero u Operario): 403. La interfaz no ofrece la
  pantalla a esos roles.
- Backend no disponible: mensaje de conexión, sin perder lo ingresado.

## 8. Criterios de aceptación

- CA-01 (T01): La pantalla permite capturar nombres, apellidos, DNI,
  contraseña y rol; muestra el usuario de acceso como solo lectura y el
  estado; los campos obligatorios están indicados y las opciones de rol
  provienen de la API.
- CA-02 (T02): Un alta válida devuelve 201 y el usuario queda en PostgreSQL
  con el usuario de acceso generado según RN-02, estado activo, fecha de
  creación y la contraseña como hash.
- CA-03 (T02): Un alta con un DNI ya registrado devuelve 409 y no crea un
  segundo usuario.
- CA-04 (T02): Un alta o modificación con un rol inexistente devuelve 422 y
  no guarda cambios.
- CA-05 (T02): El listado y la consulta por id devuelven los datos del
  usuario con su rol; un id inexistente devuelve 404.
- CA-06 (T02): La modificación actualiza nombres, apellidos, rol y, si se
  envía, la contraseña, sin cambiar el DNI ni el usuario de acceso; enviar
  `dni` o `usuario` devuelve 422.
- CA-07 (T02): Al desactivar un usuario este ya no puede iniciar sesión; al
  reactivarlo puede hacerlo de nuevo.
- CA-08 (T02): Un Administrador no puede desactivarse ni cambiar su propio
  rol; la API devuelve 409.
- CA-09 (T02, HU-002 T02): Todas las rutas devuelven 403 a Almacenero y
  Operario, y 401 sin sesión. La interfaz solo ofrece la pantalla al
  Administrador.
- CA-10: Ninguna respuesta incluye `password_hash`, y la tabla de la pantalla
  no muestra el DNI.
- CA-11 (T03): La matriz de prueba incluye alta válida, usuario duplicado,
  edición y cambio de estado; cada caso registra resultado esperado, resultado
  obtenido y estado.
- CA-12: `python -m pytest -q` pasa sin conectarse a Supabase; `npm run lint`
  y `npm run build` pasan; inventario sigue pasando sus pruebas.

## 9. Impacto técnico

### Módulos

Ubicación propuesta. Los nombres de archivo son orientativos y se confirman al
implementar contra el estado de `main` en ese momento.

- `backend/app/modules/users/domain/`: entidad de usuario, regla de
  generación del usuario de acceso y errores del módulo. Sin FastAPI ni
  SQLAlchemy.
- `backend/app/modules/users/application/`: casos de uso (crear, listar,
  consultar, modificar, listar roles) y contrato del repositorio.
- `backend/app/modules/users/infrastructure/`: repositorio SQLAlchemy sobre
  `usuarios` y `roles`.
- `backend/app/modules/users/presentation/`: router, esquemas HTTP y
  traducción de los errores del módulo a códigos HTTP.
- `backend/app/modules/authentication/presentation/`: recibe
  `require_permission`, hoy en `inventory/presentation/dependencies.py`.
  Inventario pasa a importarla desde ahí, sin cambiar su comportamiento.
- `backend/main.py`: registra el router de usuarios.
- Se reutilizan `get_current_user`, la sesión de base de datos por petición y
  `hash_password` de HU-001.
- La base y los modelos se importan al atender la petición, no al cargar el
  módulo, para respetar la regla de arranque sin conexión
  (`test_lazy_db_import`).
- `app/models.py` y `app/core/permissions.py` no se modifican.

Los identificadores de código van en inglés. Los nombres de los campos JSON
conservan el vocabulario del dominio en español.

### API

Todas las rutas requieren sesión y el permiso `GESTIONAR_USUARIOS`.

| Método y ruta | Uso | Respuestas |
|---|---|---|
| `GET /api/users/roles` | Opciones de rol | 200, 401, 403 |
| `POST /api/users` | Crear usuario | 201, 401, 403, 409, 422 |
| `GET /api/users` | Listar usuarios | 200, 401, 403 |
| `GET /api/users/{id_usuario}` | Consultar un usuario | 200, 401, 403, 404 |
| `PATCH /api/users/{id_usuario}` | Modificar nombres, apellidos, rol, contraseña o estado | 200, 401, 403, 404, 409, 422 |

### Base de datos / migración

- Sin cambios de esquema y sin migraciones.
- No se ejecuta `alembic upgrade`, `downgrade` ni `stamp`.
- Lectura y escritura en `usuarios`; lectura en `roles`.
- La base valida el formato del DNI y del usuario con sus restricciones
  CHECK, y la unicidad de ambos. La restricción del usuario admite mayúscula
  o minúscula; la mayúscula la garantiza el backend.

### UI

- `frontend/src/features/users/`: página de gestión de usuarios, formulario,
  tabla, estilos y cliente de la API de usuarios.
- El token se obtiene con `getAccessToken` de `features/authentication`.
- `App.jsx`: un conmutador de vista entre Pedidos y Usuarios, visible solo
  para el Administrador. No se agrega una librería de rutas.
- Tokens `--ng-*` definidos en `index.css` y componentes del Documento de
  UI/UX y Accesibilidad: tabla con encabezados y estado vacío, campos con
  etiqueta visible, selector de rol con opción inicial explícita, estado
  mostrado con texto y color, alertas en texto, indicador de carga, foco
  visible y controles de 40 a 44 px de alto.
- En anchos menores el formulario pasa a una columna.
- La pantalla no contiene reglas de negocio: el usuario de acceso lo genera
  el backend.

## 10. Pruebas previstas

- Unitarias (`backend/tests/unit/users/`): generación del usuario de acceso
  (inicial simple, con tilde, con ñ, en minúscula, con espacios, nombre que
  no empieza con letra); casos de uso con un repositorio simulado (DNI
  duplicado, rol inexistente, DNI y usuario inmutables, Administrador que
  intenta desactivarse o cambiar su rol); regla de dependencias entre capas.
- Integración (`backend/tests/integration/`): repositorio SQLAlchemy sobre la
  base SQLite de prueba; unicidad de DNI y usuario; lectura del rol.
- API (`backend/tests/api/`): alta válida; DNI duplicado; formatos inválidos;
  rol inexistente; campos no previstos; listado y consulta; modificación;
  cambio de estado seguido de intento de login; 401 sin sesión; 403 para
  Almacenero y Operario; respuesta sin `password_hash`; arranque sin importar
  la base.
- Inventario: sus pruebas existentes siguen pasando tras el traslado de
  `require_permission`.
- Frontend: `npm run lint`, `npm run build` y lista de comprobación manual de
  accesibilidad (teclado, foco, etiquetas, errores).
- Limitación: sin PostgreSQL local, las restricciones propias de la base se
  verifican en SQLite, que no aplica los CHECK ni los límites de longitud.

Casos de la matriz manual (T03):

| ID | Caso | Resultado esperado |
|---|---|---|
| CP-HU003-01 | Alta válida | 201; usuario de acceso generado; aparece en la tabla |
| CP-HU003-02 | Alta con DNI ya registrado | 409; no se crea el usuario |
| CP-HU003-03 | Edición de nombres y rol | 200; DNI y usuario de acceso sin cambios |
| CP-HU003-04 | Desactivar usuario | 200; el usuario no puede iniciar sesión |
| CP-HU003-05 | Reactivar usuario | 200; el usuario vuelve a iniciar sesión |
| CP-HU003-06 | DNI con formato inválido | 422; mensaje junto al campo |
| CP-HU003-07 | Rol inexistente | 422 |
| CP-HU003-08 | Administrador intenta desactivarse | 409; sigue activo |
| CP-HU003-09 | Operario intenta listar usuarios | 403; la interfaz no le ofrece la pantalla |
| CP-HU003-10 | Petición sin sesión | 401 |

## 11. Evidencias requeridas

En `docs/evidence/sprint-01/HU-003/`:

- Archivo de evidencia con rama, commit, comandos, directorio de ejecución y
  salida de `pytest`, `npm run lint` y `npm run build`.
- Matriz de casos con resultado obtenido y estado (PASS, FAIL o BLOCKED).
- Capturas: formulario con validaciones, usuario registrado, vista de
  edición, cambio de estado y respuesta 403.
- Lista de comprobación de accesibilidad con PASS, FAIL o NA.
- Los DNI y usuarios usados son ficticios; no se incluyen tokens completos.

## 12. Decisiones y notas

- D-01: El usuario de acceso se genera en mayúscula, igual que en
  SPEC-HU-001. El ejemplo del Documento de Diseño de Base de Datos
  (`w75811779`) está en minúscula y debe corregirse.
- D-02: El criterio T01 del backlog dice "capturar usuario". Se interpreta
  como mostrar el usuario generado, porque el Documento de Diseño de Base de
  Datos propone generarlo y no ingresarlo.
- D-03: El DNI se añade al formulario aunque el criterio T01 no lo mencione,
  porque la tabla lo exige y de él deriva el usuario de acceso.
- D-04: Contraseña de mínimo 8 caracteres y máximo 72 bytes. El máximo es el
  límite de bcrypt; el mínimo conserva el de la rama anterior.
- D-05: Rutas bajo `/api/users` y modificación con `PATCH`, siguiendo la
  convención que ya usa inventario (`/api/inventory/...`). La rama anterior
  usaba `/api/usuarios`, `PUT` y una ruta aparte para el estado.
- D-06: El rol inexistente responde 422, igual que los errores de validación
  de inventario. La rama anterior respondía 400.
- D-07: RN-07 es una propuesta para el reviewer. El backlog no define si un
  Administrador puede desactivarse; permitirlo podría dejar el sistema sin
  administradores.
- D-08: `require_permission` se traslada a autenticación porque la usarán
  varios módulos. Se coordina con el responsable de inventario.
- D-09: El acceso a la pantalla se resuelve con un conmutador en `App.jsx`.
  Una navegación completa queda para una tarea propia.
- D-10: Desactivar no pide confirmación, porque es reversible.
- N-01: Crear el primer Administrador en la base compartida corresponde al
  equipo. Con uno disponible, esta pantalla permite crear las cuentas de
  prueba que dejaron casos bloqueados en la evidencia de HU-001.
- N-02: En el backlog la HU-003 y la HU-002 T02 aún figuran a nombre de
  Fabricio M. Falta actualizar el responsable.

## Historial de estado

- Draft: 05/10/2026, redacción sobre el modelo de datos v1.1 y HU-001.
- Reviewed
- Implemented
- Verified
