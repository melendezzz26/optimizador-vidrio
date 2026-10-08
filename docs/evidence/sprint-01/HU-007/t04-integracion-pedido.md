# HU-007 T04 — Integración de pieza personalizada y pedido

Fecha: 2026-10-07. Rama: `feature/HU-007-lienzo-pieza-personalizada`.
Punto de partida: `74d550584b648921a1918abbe4f1a0c6e757660f`.

## Alcance y resultado

Se continuó el WIP de T04, reutilizando el editor y la validación de T01–T03.
El editor entrega una pieza `POLIGONO_CONVEXO` al estado local de NuevoPedido
solo con geometría VALID y material/espesor seleccionados. Reinicia el lienzo
después de agregar y permite varias piezas. Guardar envía un único POST con
todas ellas; `isSubmitting` y una guarda síncrona bloquean envíos simultáneos.
El éxito muestra el ID devuelto y vacía las piezas ya guardadas. Un error
mantiene material, espesor y piezas para corregir o reintentar.

La SPEC pasó de Reviewed a Implemented. Se mantiene fuera de Verified: la revisión formal del responsable
y las capturas manuales del usuario no se sustituyen por estas pruebas.

## Qué faltaba o fallaba en el WIP

- NuevoPedido agregaba filas vacías; no recibía vértices, no llamaba a la API
  y usaba un catálogo escrito a mano sin IDs reales.
- El editor mantenía Agregar deshabilitado y los textos temporales obsoletos.
- La ruta usaba `user.id_usuario`, pero `AuthenticatedUser` expone `user_id`.
- La inyección importaba la conexión al cargar `main`, rompiendo el arranque
  diferido existente y acoplando el módulo a la configuración de la BD.
- Las pruebas API importaban `app.main` y sustituían autenticación; las de
  repositorio usaban una fixture SQLite sin tablas de pedidos ni catálogo.
- El catálogo no descartaba tipos inactivos. Los esquemas aceptaban coerciones
  y campos extra; faltaban comprobaciones numéricas y de rango de almacenamiento.
- Un polígono cruzado con área firmada cero fallaba antes de detectar el cruce.
- Acceder al ID después del commit podía disparar una lectura adicional sobre
  atributos expirados. `None` en JSONB no garantizaba SQL NULL en dimensiones.
- Había BOM, trailing whitespace y caracteres de control/fences rotos en la SPEC.

## Backend y persistencia

Presentation traduce esquemas discriminados a datos de aplicación; Application
usa su puerto y el dominio geométrico sin importar Presentation, FastAPI,
Pydantic o SQLAlchemy. Infrastructure reutiliza exclusivamente `Pedido`,
`Pieza`, `TipoVidrio` y `TipoVidrioEspesor` de `app.models`.

La ruta usa `require_permission("GESTIONAR_PEDIDOS")`, que a su vez ejecuta
`get_current_user`, valida JWT y consulta el usuario/rol vigente. Operario y
Administrador pueden registrar; Almacenero recibe 403. El cliente no elige
`id_usuario_registro`.

Se vuelve a validar convexidad, simplicidad, coordenadas numéricas finitas,
área positiva y rango compatible con `NUMERIC(18,2)`. La cantidad debe ser un
entero positivo compatible con INTEGER. El backend calcula todas las áreas.
Un material inactivo o una combinación ajena al catálogo produce 422.

Una sesión guarda cabecera e hijos con un único commit. Se captura el ID antes
del commit, y cualquier excepción en cabecera, piezas o commit hace rollback.
Las pruebas consultan con otra sesión para comprobar persistencia o ausencia
de todas las filas, incluyendo SQL NULL real en `dimensiones` del polígono.

## Contrato HTTP

`POST /api/orders`, `Authorization: Bearer <JWT>`, `Content-Type: application/json`.
Materiales: `GET /api/inventory/tipos-vidrio`; usar sus IDs y `espesores_mm` activos.

```json
{
  "id_tipo_vidrio": 7,
  "espesor_mm": 5.5,
  "piezas": [
    {
      "tipo_forma": "POLIGONO_CONVEXO",
      "cantidad": 1,
      "vertices_mm": [[0, 0], [500, 0], [500, 300], [0, 300]]
    },
    {
      "tipo_forma": "RECTANGULO",
      "cantidad": 2,
      "width_mm": 100,
      "height_mm": 200
    },
    {
      "tipo_forma": "CIRCUNFERENCIA",
      "cantidad": 1,
      "radius_mm": 10
    }
  ]
}
```

El ID 7 es del entorno sintético de esta evidencia, no una constante productiva.
Se rechazan campos adicionales, incluyendo usuario, área o geometría derivada.
Respuesta 201:

```json
{"id_pedido": 1, "estado": "PENDIENTE"}
```

El ID es generado por BD. Errores: 401 sin sesión válida, 403 sin permiso,
422 por esquema/catálogo/geometría y 500 con mensaje público sin detalles internos.
El polígono del ejemplo persiste con `dimensiones = NULL`,
`geometria = {"type":"POLIGONO_CONVEXO","vertices_mm":[...]}` y `area_mm2 = 150000.00`.

## Entorno seguro de pruebas

- Python 3.14.7; pytest 9.1.1. Frontend: scripts existentes de Node, Vitest,
  Playwright/Chrome, ESLint y Vite. No se cambiaron dependencias del proyecto.
- PostgreSQL 18.6 portátil descargado desde los
  [binarios oficiales distribuidos por EDB](https://www.enterprisedb.com/download-postgresql-binaries).
- Binarios locales usados: `C:/Users/Andro/.cache/tooling/hu007-postgres/server/pgsql/bin`.
  No están dentro del repositorio.
- `tests/conftest.py` fija una URL SQLite y una clave JWT sintética antes de
  importar la aplicación. Las pruebas PostgreSQL crean clústeres propios en
  TEMP, escuchan solo en `127.0.0.1` y usan bases aleatorias `r1_*`.
- El servidor E2E reutiliza ese soporte, aplica solamente las migraciones ya
  existentes a una base vacía temporal y crea un usuario/material sintéticos.
  Login, JWT, permisos, catálogo y POST se ejecutan contra FastAPI real.
- La fixture fija UTC para evitar dependencia de la zona horaria del equipo.
  El teardown de Playwright detiene el clúster propio también en Windows.
- No se ejecutó seed, upgrade, downgrade, borrado ni escritura sobre Supabase.
  No se crearon migraciones ni se editó `app/models.py`.

## Resultados

| Comando | Resultado final |
|---|---|
| `python -m pytest` | **920 passed, 1 warning in 195.21s (0:03:15)**; 0 failed, 0 skipped; exit 0 |
| `npm.cmd run test:unit` | 84 passed, 0 failed |
| `npm.cmd run test:component` | 36 passed, 0 failed (28 heredadas + 8 T04) |
| `npm.cmd run test:e2e` | **24 passed (47.7s)**; 0 failed; 20 heredadas + 4 T04; exit 0 |
| `npm.cmd run lint` | Exit 0 |
| `npm.cmd run build` | Exit 0; 1917 módulos; Vite 8.3.1 |
| `python -m alembic heads` | `1c8754481a08 (head)` |
| `python -m alembic current` | `1c8754481a08 (head)` en PostgreSQL temporal |
| `git diff --check` | Sin errores |

La comprobación de Alembic current se refiere exclusivamente a la base temporal
de pruebas. No certifica el estado de una base remota compartida.

El warning backend es `StarletteDeprecationWarning`: el TestClient heredado usa
httpx, deprecado por esta versión de Starlette. No hay fallos ni pruebas omitidas.
Las 132 pruebas frontend heredadas siguen presentes y pasan; T04 suma 12.
La suite backend completa supera el baseline de 669 passed indicado por el usuario
e incluye las integraciones de PostgreSQL local y 69 casos del módulo Orders.

En las iteraciones previas se corrigieron: extracción incompleta de PostgreSQL,
atributo incorrecto del usuario autenticado, causa de error requerida por ESLint,
zona horaria de la fixture heredada, cierre del clúster E2E en Windows y respuesta
422 serializable para coordenadas JSON no finitas (incluido `1e400`).
Los resultados anteriores con errores no son la evidencia final.

## Pasos exactos para capturas

### 1. Pytest backend

En una terminal PowerShell de VS Code:

```powershell
Set-Location C:\Users\Andro\optimizador-vidrio\backend
$env:NEWGLASS_TEST_PG_BIN = 'C:/Users/Andro/.cache/tooling/hu007-postgres/server/pgsql/bin'
python -m pytest
```

Esperar el resumen completo y capturar comando, ruta y total passed, sin ocultar
failures/skips/warnings si los hubiera. Todas las integraciones usan PostgreSQL
temporal propio. No establecer DATABASE_URL con Supabase para estas pruebas.

### 2. Tests frontend

```powershell
Set-Location C:\Users\Andro\optimizador-vidrio\frontend
$env:NEWGLASS_TEST_PG_BIN = 'C:/Users/Andro/.cache/tooling/hu007-postgres/server/pgsql/bin'
npm.cmd run test:unit
npm.cmd run test:component
npm.cmd run test:e2e
```

Capturar el resumen de cada comando: 84, 36 y 24 pruebas respectivamente.
Los puertos 5173 y 8017 deben estar libres: Playwright inicia ambos servidores
y no reutiliza una aplicación que pudiera apuntar a servicios compartidos.

### 3. Lint y build

En la misma carpeta frontend:

```powershell
npm.cmd run lint
npm.cmd run build
```

Capturar ambos comandos y la salida de build; ESLint no imprime hallazgos cuando pasa.

### 4. Preparar la demostración manual aislada

Terminar primero Playwright. En una terminal A:

```powershell
Set-Location C:\Users\Andro\optimizador-vidrio\backend
$env:NEWGLASS_TEST_PG_BIN = 'C:/Users/Andro/.cache/tooling/hu007-postgres/server/pgsql/bin'
python -m tests.e2e_server
```

Esperar los resultados Alembic y `Synthetic local database: ...`. Mantener A abierta.
En otra terminal B:

```powershell
Set-Location C:\Users\Andro\optimizador-vidrio\frontend
$env:VITE_API_URL = 'http://127.0.0.1:8017'
npm.cmd run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Abrir `http://127.0.0.1:5173/`, iniciar sesión con `O70000001` y
`Orders-test-2026!`. Esta cuenta solo existe en la base temporal recién creada.
Seleccionar **Material de prueba**, espesor **5.5 mm**.

### 5. Polígono VALID con Agregar habilitado

En el lienzo, hacer cuatro clics formando un rectángulo, en orden alrededor
del borde (superior izquierdo, superior derecho, inferior derecho, inferior
izquierdo). Pulsar **Cerrar polígono**. Completar S1=300, S2=200, S3=300,
S4=200 mm. Capturar **Geometría convexa validada.**, la vista completa y
**Agregar pieza al pedido** habilitado. El motivo interno es `VALID`.

Las E2E reproducen el dibujo con puntos exactos del viewBox:
`[100,100], [400,100], [400,300], [100,300]`, sin inyectar estado del componente.

### 6. Pieza agregada

Pulsar **Agregar pieza al pedido**. Subir a **Piezas del pedido** y capturar
**Pieza 1**, polígono convexo, 4 vértices, cantidad 1 y estado **Sin guardar**.
El lienzo debe mostrar 0 vértices. Se puede repetir el dibujo para Pieza 2.
En Network no debe existir POST `/api/orders` antes de guardar.

### 7. Pedido guardado con ID

Pulsar **Guardar pedido**. Capturar el mensaje **Pedido guardado correctamente.
ID del pedido: …** con el ID real de esa ejecución. En DevTools Network se puede
capturar el POST con estado 201 y su JSON de respuesta, sin mostrar el JWT.
El listado queda vacío y Guardar deshabilitado hasta agregar otras piezas.

### 8. Swagger POST /api/orders

Abrir `http://127.0.0.1:8017/docs` y desplegar **Pedidos → POST /api/orders**.
Capturar ruta, esquema discriminado y respuesta 201. Para ejecutar en Swagger:

1. Ejecutar `POST /api/auth/login` con
   `{"username":"O70000001","password":"Orders-test-2026!"}`.
2. Copiar `access_token` y pegarlo en **Authorize → HTTPBearer** (sin publicarlo
   ni incluirlo en capturas).
3. En POST `/api/orders`, pulsar **Try it out**, usar el JSON de esta evidencia
   con material 7 y espesor 5.5, y pulsar **Execute**.
4. Capturar 201 y `id_pedido`. Este registro solo modifica la base temporal.

### 9. Alembic head/current

Con la terminal A aún abierta, en una tercera terminal:

```powershell
Set-Location C:\Users\Andro\optimizador-vidrio\backend
$testState = Get-Content "$env:TEMP/newglass-orders-e2e-8017.json" | ConvertFrom-Json
$env:DATABASE_URL = $testState.database_url
python -m alembic heads
python -m alembic current
```

Capturar ambos comandos y `1c8754481a08 (head)` en ambas salidas. Esta variable
apunta al PostgreSQL temporal local. No ejecutar migraciones contra una BD real.

Al terminar la demostración, detener A y B con Ctrl+C. Si Windows interrumpe
el cierre de PostgreSQL, ejecutar desde backend:

```powershell
python -m tests.e2e_server --stop
```

Las capturas automáticas de VALID, piezas locales y guardado se generan en
`frontend/test-results/hu007-order-integration-*/` para escritorio y móvil.
`test-results`, `playwright-report`, `dist`, `node_modules` y `.env` no se versionan.

## Git y archivos

Commit de entrega: `feat(HU-007): completar integracion T04 de pedidos`.
Su identificador se obtiene con `git log -1 --format="%H %s"` en esta entrega.
Publicación autorizada: `git push origin feature/HU-007-lienzo-pieza-personalizada`.
La confirmación del hash remoto se realiza con
`git ls-remote --heads origin feature/HU-007-lienzo-pieza-personalizada`.
No se cambió de rama ni se ejecutó merge, rebase, cherry-pick o force push.

Archivos modificados o creados respecto al WIP:

- `backend/app/modules/orders/application/ports.py`
- `backend/app/modules/orders/application/use_cases.py`
- `backend/app/modules/orders/domain/exceptions.py`
- `backend/app/modules/orders/domain/geometry.py`
- `backend/app/modules/orders/infrastructure/dependencies.py`
- `backend/app/modules/orders/infrastructure/repositories.py`
- `backend/app/modules/orders/presentation/router.py`
- `backend/app/modules/orders/presentation/schemas.py`
- `backend/main.py`
- `backend/tests/api/orders/conftest.py`
- `backend/tests/api/orders/test_orders_api.py`
- `backend/tests/e2e_server.py`
- `backend/tests/integration/modules/orders/conftest.py`
- `backend/tests/integration/modules/orders/infrastructure/test_repositories.py`
- `backend/tests/integration/postgres_support.py`
- `backend/tests/orders_support.py`
- `backend/tests/unit/modules/orders/application/test_use_cases.py`
- `backend/tests/unit/modules/orders/domain/test_domain_geometry.py`
- `backend/tests/unit/modules/orders/test_layer_dependencies.py`
- `docs/evidence/sprint-01/HU-007/t04-integracion-pedido.md`
- `docs/specs/SPEC-HU-007-T04-integrar-pedido.md`
- `frontend/playwright.config.js`
- `frontend/src/features/orders/CustomPieceEditor.css`
- `frontend/src/features/orders/CustomPieceEditor.jsx`
- `frontend/src/features/orders/__tests__/CustomPieceEditor.test.jsx`
- `frontend/src/features/orders/__tests__/NuevoPedido.test.jsx`
- `frontend/src/features/orders/ordersApi.js`
- `frontend/src/pages/NuevoPedido.css`
- `frontend/src/pages/NuevoPedido.jsx`
- `frontend/tests/e2e/globalTeardown.js`
- `frontend/tests/e2e/hu007-custom-piece.spec.js`
- `frontend/tests/e2e/hu007-order-integration.spec.js`
