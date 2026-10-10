# HU-012 T02 — Consulta y alta de clientes

Fecha de validación: 09/10/2026. Rama: `feature/HU-012-T02-api-clientes`.
Base exacta: `9f605bf` de `feature/HU-012-gestion-clientes`.
SPEC Reviewed: [SPEC-HU-012](../../../specs/SPEC-HU-012-gestion-clientes.md).

## Archivos de la entrega

Único archivo existente modificado: `backend/main.py` (registro del router).
Archivos creados:

```text
backend/app/modules/clients/
  __init__.py
  domain/__init__.py
  domain/client.py
  domain/errors.py
  domain/rules.py
  application/__init__.py
  application/dto.py
  application/ports.py
  application/use_cases.py
  infrastructure/__init__.py
  infrastructure/sqlalchemy_client_repository.py
  presentation/__init__.py
  presentation/dependencies.py
  presentation/schemas.py
  presentation/router.py
backend/tests/
  clients_support.py
  unit/clients/__init__.py
  unit/clients/test_use_cases.py
  unit/clients/test_layer_dependencies.py
  integration/clients/__init__.py
  integration/clients/conftest.py
  integration/clients/test_repository.py
  api/clients/__init__.py
  api/clients/conftest.py
  api/clients/test_clients_api.py
docs/evidence/sprint-01/HU-012/t02-api-clientes.md
```

## Implementación y decisiones de alcance

`clients` mantiene Presentation → Application → Domain. Infrastructure implementa
`ClientRepository` usando el único ORM `Cliente` y la sesión existente. Sigue el
patrón de Orders: cada alta hace flush, captura un DTO, confirma y revierte si
falla; no consulta de nuevo después del commit. No se modifica la migración T01.

- Alta con nombre obligatorio, texto no vacío y recorte de espacios exteriores.
- Documento y teléfono opcionales. Texto vacío opcional se convierte en NULL.
- No se exige una pareja documental completa ni un catálogo o longitud legal.
  Se conserva la decisión de la SPEC/T01, que prevalece para esta entrega sobre
  la propuesta general de campos NOT NULL del documento de evolución v1.3.
- Tipo y número se conservan como texto, incluidos ceros iniciales y mayúsculas.
- `estado=true` y fecha UTC se generan en backend. El HTTP rechaza campos extra,
  incluidos ID, fecha, estado, roles, usuario, password y credenciales.
- PostgreSQL decide la unicidad de `(tipo_documento, numero_documento)`, también
  ante altas concurrentes y para clientes inactivos. Solo esa restricción con
  SQLSTATE `23505` se traduce a duplicado. Como en T01, las parejas con NULL no
  quedan protegidas contra duplicados por la restricción única.
- Listado ordenado por ID, con activos e inactivos, siguiendo los listados de
  Users e Inventory. Se devuelve `estado`; no se añade filtro de estado.
- `document` busca número exacto; `query` busca una parte literal del nombre,
  sin distinguir mayúsculas. Juntos aplican AND. Se recortan espacios exteriores;
  filtros vacíos se rechazan. `%`, `_`, `/` y `\` se tratan como texto literal.
- Ambos endpoints requieren sesión activa y `GESTIONAR_PEDIDOS`, el permiso ya
  usado por Orders: Operario y Administrador tienen acceso; Almacenero recibe 403.
  No hay permisos, roles ni credenciales propios del cliente.

## Contrato HTTP

| Operación | Resultado |
|---|---|
| `POST /api/clients` | 201, cliente creado |
| `GET /api/clients` | 200, lista; `[]` si no hay resultados |
| `GET /api/clients?document=DEMO-001` | 200, coincidencias exactas por número |
| `GET /api/clients?query=norte` | 200, coincidencias parciales por nombre |
| Documento duplicado | 409, mensaje comprensible |
| Entrada o filtro inválido | 422 |
| Sesión ausente, inválida, expirada o cuenta inactiva | 401 |
| Rol sin el permiso existente | 403 |
| Fallo inesperado | 500, mensaje genérico sin SQL ni traceback |

Solicitud de ejemplo:

```json
{
  "nombre_razon_social": "Vidrios Norte Demo",
  "tipo_documento": "TEST",
  "numero_documento": "DEMO-001",
  "telefono": "+51 900 000 001"
}
```

Respuesta real del smoke local, con ID y fecha generados por backend:

```json
{
  "id_cliente": 1,
  "tipo_documento": "TEST",
  "numero_documento": "DEMO-001",
  "nombre_razon_social": "Vidrios Norte Demo",
  "telefono": "+51 900 000 001",
  "estado": true,
  "fecha_registro": "2026-10-09T10:10:23.536279Z"
}
```

Duplicado:

```json
{"detail":"Ya existe un cliente con ese tipo y número de documento."}
```

## Pruebas y validaciones

Entorno usado: Windows, Python 3.14.7, pytest 9.1.1. No se instalaron dependencias
ni se cambiaron versiones. Los tests de BD usan PostgreSQL temporal en loopback.
No se accedió a Supabase ni se aplicaron migraciones sobre una BD remota.

Se agregaron 102 casos: 38 unitarios/arquitectura, 20 de repositorio PostgreSQL y
44 de API con persistencia y autenticación reales. Cubren validación, reloj UTC,
campos opcionales, contratos de salida, búsquedas, duplicado concurrente,
rollback/reutilización de sesión, errores inesperados y permisos vigentes.

Resultados:

- Clients: **102 passed**, 1 warning, 46,64 s.
- Regresión focalizada: **478 passed**, 1 warning, 256,89 s.
- Suite completa: **1067 passed**, 1 warning, 296,38 s (965 anteriores + 102 T02).
- Las tres ejecuciones finales terminaron con 0 failed, 0 errors y 0 skipped.
- Smoke HTTP local: `/docs` y `/openapi.json` 200; alta 201; listado y ambas
  búsquedas 200; duplicado 409. Servidor y PostgreSQL detenidos al terminar.
- `compileall` y `git diff --check`: correctos.
- No hay una herramienta de lint/formato backend configurada en el repositorio.
- Warning existente: Starlette informa que el uso de `httpx` en TestClient está
  deprecado. No se modifican dependencias fuera del alcance de T02.

La primera colección focalizada detectó nombres de módulos de test coincidentes
con Orders. Se resolvió agregando `__init__.py` en los nuevos paquetes Clients;
no se modificaron ni debilitaron los tests anteriores.

Desde `backend/`, en PowerShell:

```powershell
$env:NEWGLASS_TEST_PG_BIN='C:/Users/Andro/.cache/tooling/hu007-postgres/server/pgsql/bin'
python -m pytest tests/unit/clients tests/integration/clients tests/api/clients -v

$targets = @(
  'tests/unit/clients', 'tests/integration/clients', 'tests/api/clients',
  'tests/unit/modules/orders', 'tests/integration/modules/orders', 'tests/api/orders',
  'tests/integration/test_clients_migration.py',
  'tests/integration/test_orders_multimaterial_migration.py',
  'tests/integration/test_r1_migration.py', 'tests/integration/test_r2_migration.py',
  'tests/integration/test_r3_migration.py', 'tests/integration/test_r4_migration.py',
  'tests/integration/inventory/test_catalog.py',
  'tests/api/test_auth_api.py', 'tests/api/test_require_permission.py',
  'tests/test_permissions.py', 'tests/unit/authentication',
  'tests/api/inventory/test_lazy_db_import.py'
)
python -m pytest @targets -q
python -m pytest
```

## Servidor local para capturas Swagger

Se reutiliza `tests.e2e_server`, sin modificar Orders. El helper crea su propio
PostgreSQL temporal, aplica el head y carga una cuenta Operario sintética.
Genera la URL local y la clave de firma; no usa la BD del archivo `.env`.
Requiere el puerto 8017 libre. Los datos son temporales y cada arranque comienza
con una base nueva.

```powershell
Set-Location C:\Users\Andro\optimizador-vidrio\backend
$env:NEWGLASS_TEST_PG_BIN='C:/Users/Andro/.cache/tooling/hu007-postgres/server/pgsql/bin'
python -m tests.e2e_server
```

1. Abrir `http://127.0.0.1:8017/docs`.
2. Ejecutar `POST /api/auth/login` con la cuenta sintética del helper:
   `{"username":"O70000001","password":"Orders-test-2026!"}`.
3. Copiar `access_token`, pulsar **Authorize** y pegar el token en HTTPBearer.
4. En **Clientes**, ejecutar `POST /api/clients` con el JSON de ejemplo.
5. Ejecutar `GET /api/clients` sin filtros.
6. Ejecutarlo con `document=DEMO-001` y sin `query`.
7. Ejecutarlo con `query=norte` y sin `document`.
8. Repetir el POST original: debe devolver 409.

Para cerrar: Ctrl+C en la terminal del servidor. Si Windows dejó el clúster
del helper abierto, ejecutar desde `backend/`:

```powershell
python -m tests.e2e_server --stop
```

## Capturas manuales solicitadas

No se generan capturas automáticamente. Guardarlas en esta carpeta o en su
subcarpeta `capturas/t02/`:

1. Árbol `backend/app/modules/clients/`, mostrando las cuatro capas.
2. Swagger: solicitud de alta y respuesta 201 con los siete campos de cliente.
3. Swagger: listado y respuesta 200.
4. Swagger: filtro `document=DEMO-001` y respuesta 200.
5. Swagger: filtro `query=norte` y respuesta 200.
6. Swagger: repetición del alta, respuesta 409 y mensaje.
7. Terminal: resumen de las pruebas específicas T02.
8. Terminal: resumen de la suite completa.
9. Terminal: `git log -3 --oneline` con los commits T02.
10. Terminal: rama correcta, árbol limpio y sincronización `0 0`:

```powershell
git branch --show-current
git status
git status --short
git rev-list --left-right --count HEAD...origin/feature/HU-012-T02-api-clientes
```

## Pendientes fuera de T02

Siguen pendientes de decisión del equipo el catálogo documental, obligatoriedad
del documento/teléfono y tratamiento definitivo de pedidos históricos. T03
incorporará la selección/alta de cliente desde Nuevo Pedido y su asociación en
ese flujo. No se implementan edición, DELETE, frontend, HU-013 ni rasterización.
La revisión por otro integrante y las capturas manuales quedan por realizar.
