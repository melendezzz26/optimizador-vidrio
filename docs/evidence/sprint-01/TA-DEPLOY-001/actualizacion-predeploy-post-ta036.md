# TA-035-T1 — Actualización del predespliegue después de TA-036

## ESTADO VERIFICADO ACTUAL — cierre del 13/10/2026

**Completado y validado en Staging — versión final `293a2a9`.** Release
`v12 / 293a2a93`, upgrade a
`ta036a1b2c3d` e introspección `SCHEMA_PASS` confirmados mediante salidas
remotas aportadas por el usuario; smoke público por terminal conforme.
El usuario confirmó posteriormente el smoke autenticado de pedidos/inventario,
el POST 201 y GET 200 del retazo `RET-HU005-002`, su edición y su persistencia
directa en Supabase Staging. Estos resultados corresponden ya a `293a2a9`.
La evidencia manual se registra según la confirmación del usuario; Codex no
repitió operaciones remotas ni inspeccionó archivos de capturas en este cierre.

Esta sección reemplaza el estado operativo y los pendientes de la auditoría
histórica conservada abajo. El commit documental `900c995` permanece intacto.
Rama local comprobada: `feature/TA-035-T1-actualizacion-predeploy`, HEAD previo
al cierre `900c995`. Se conservaron los cambios documentales locales de la
continuación anterior. Este cierre actualiza únicamente los tres documentos
autorizados y los protege en un único commit documental. La sincronización con
integración queda para una fase posterior: sin push, PR ni merge en este cierre.

### Línea base autorizada y release Heroku

- **Base sobre la que se creó esta rama TA-035-T1:**
  `373dfc22f52ae46b01ea4dc059351daf06177352`, con PR #42 (TA-005/TA-006,
  rasterización) y PR #44 (TA-036, saneamiento funcional).
- Consulta pública GitHub, **21:32:35 UTC / 16:32:35 Lima**: la rama remota
  `integration/sprint-01` apunta a `293a2a930cdd398a678ff57b801bb7af9fad1bd4`.
- La comparación pública de las 21:32:50 UTC confirma 8 commits posteriores,
  0 detrás, con TA-007 (PR #43). Incluye `373dfc2`; la lista de cambios no
  modifica frontend, migraciones ni inventario, pero sí código de optimización.
- **El usuario autorizó actualizar la línea base a `293a2a9`**, con TA-036 y
  TA-007. No se cambió la rama local ni se hizo merge para documentarlo.
- El usuario informó que ejecutó `git fetch origin --prune`. En este cierre,
  `git rev-parse origin/integration/sprint-01` confirmó localmente
  `293a2a930cdd398a678ff57b801bb7af9fad1bd4`, sin repetir fetch.
  La eliminación remota de `feature/TA-007-validacion-geometrica` después del
  merge es normal y no representa un problema.
- **Versión final de Staging verificada: `293a2a9`**, que incluye PR #42,
  PR #44 y PR #43. TA-007 se incorporó después de la base inicial; no estuvo
  presente desde el inicio de TA-035-T1. `origin/integration/sprint-01` y el
  Staging verificado coinciden en `293a2a9`; la rama documental aún no se fusionó.

Los ocho commits incorporados por PR #43, del más reciente al más antiguo:

```text
293a2a9 Merge pull request #43 from melendezzz26/feature/TA-007-validacion-geometrica
e8ec42d docs(TA-007): completar README de evidencia y estado de la SPEC
aa92c7d docs(TA-007): agregar evidencia de validación geométrica y actualizar SPEC
dccbbd8 feat(TA-007): aplicar separación y margen configurados
4265542 feat(TA-007): validar limites y superposicion de colocaciones
439cefa test(TA-007): agregar pruebas de rasterización del material
6a8b595 feat(TA-007): rasterizar el material con regla interior
74129a4 docs(TA-007): especificar validación geométrica
```

Comprobaciones y despliegue de la continuación previa:

- `heroku --version` y `heroku auth:whoami`: ambos fallaron localmente con
  `CommandNotFoundException`. No se encontró el CLI en PATH ni en las rutas
  habituales de Program Files, LocalAppData o npm global comprobadas. Esto
  no demuestra falta de permisos de la cuenta ni un fallo de Heroku.
- `apps:info`, `releases`, metadatos del slug y one-off dynos por CLI no se
  ejecutaron. No se leyó `heroku config` ni `.env`.
- Al no poder demostrar el SHA remoto, el backend se marcó inicialmente
  **NEEDS DEPLOYMENT** y se entregó el procedimiento GitHub → Heroku existente.
- Posteriormente el usuario ejecutó Manual Deploy y compartió el resultado:

  ```text
  Procfile declares types -> web
  Compressing... Done: 93.2M
  Launching... Released v12
  https://newglass-api-staging-5f52e8e9b00c.herokuapp.com/ deployed to Heroku
  ```

  **App:** `newglass-api-staging`. **Release:** `v12`. **Estado:** despliegue
  exitoso según log aportado por el usuario. El fragmento también identifica
  Heroku-24; no se cambió el stack. **Confirmación posterior de Activity aportada
  por el usuario:** `Deployed 293a2a93`, `Today at 4:35 PM · v12`, el 13/10/2026
  (16:35 según la hora mostrada en el panel; el fragmento no indica zona).
  [Diff del release](https://github.com/melendezzz26/optimizador-vidrio/compare/b7a01755...293a2a93).
  El prefijo desplegado coincide con la línea base autorizada `293a2a9`.
  Se omite la identidad del operador. Verificación por evidencia del usuario,
  no por consulta CLI de Codex; no se dispone de listado de releases anteriores.
- Auto Deploy debe permanecer desactivado; estado indicado por el usuario y
  procedimiento existente, no verificado directamente con CLI en esta sesión.

Procedimiento entregado y ejecutado por el usuario:

**Heroku → newglass-api-staging → Deploy → Manual deploy → seleccionar
integration/sprint-01 → Deploy Branch**, con SHA esperado `293a2a9`.
No hace falta otro deploy: v12 y su SHA ya fueron corroborados por el usuario.
Si la rama vuelve a avanzar, revisar el SHA antes de una nueva publicación.

### Disponibilidad pública y Pages

El usuario confirmó visualmente la raíz del backend y su mensaje. Se añade
verificación independiente por terminal: GET sin credenciales con PowerShell
`Invoke-WebRequest -UseBasicParsing -TimeoutSec 25`.

| URL/ruta | 21:32:10 UTC, antes de confirmar v12 | Después de confirmar v12 | Body no sensible |
| --- | --- | --- | --- |
| Heroku `/` | 200 | 200, 21:36:41 UTC | `{"mensaje":"Backend del optimizador de vidrio funcionando"}` |
| Heroku `/health/live` | 200 | 200, 21:36:41 UTC | `{"status":"ok"}` |
| Heroku `/health/ready` | 200 | 200, 21:36:41 UTC | `{"status":"ready"}` |
| Pages `/optimizador-vidrio/` | 200 | 200, 21:36:42 UTC | HTML recibido; sin interacción autenticada |

Fecha: 13/10/2026; 21:36 UTC equivale a 16:36 en Lima. El sandbox rechazó
la conexión inicial; la reejecución con red autorizada produjo estos 200.
Ese rechazo local no es un fallo health ni un 503 remoto.

**Smoke posterior a la migración:** el 13/10/2026 a las **21:42:03 UTC /
16:42:03 Lima**, `/`, `/health/live` y `/health/ready` volvieron a responder
**200** con los mismos tres bodies no sensibles de la tabla.

La API pública de GitHub confirmó el workflow Pages más reciente:
[run 38443828520](https://github.com/melendezzz26/optimizador-vidrio/actions/runs/38443828520),
SHA `293a2a930cdd398a678ff57b801bb7af9fad1bd4`, `completed / success`, creado
18:04:43 UTC y actualizado 18:09:34 UTC. El run de `373dfc2` que aparece abajo
es histórico. No se volvió a publicar Pages ni se repitió la comparación del
bundle en esta continuación. Un workflow Pages exitoso no identifica el release
backend ni prueba la UI autenticada.

Fuentes públicas consultadas: [rama remota](https://api.github.com/repos/melendezzz26/optimizador-vidrio/branches/integration/sprint-01)
y [comparación de SHAs](https://github.com/melendezzz26/optimizador-vidrio/compare/373dfc22f52ae46b01ea4dc059351daf06177352...293a2a930cdd398a678ff57b801bb7af9fad1bd4).

### Alembic remoto: upgrade a ta036a1b2c3d confirmado

El repo contiene `backend/alembic.ini`; el `cd backend` del Procfile solo
aplica al proceso web. Por ello, el one-off debe indicar también ese directorio.
Con CLI disponible y autenticado, después de corroborar el código del release:

```sh
heroku apps:info -a newglass-api-staging
heroku releases -a newglass-api-staging
heroku run "cd backend && python -m alembic heads" -a newglass-api-staging
heroku run "cd backend && python -m alembic current" -a newglass-api-staging
```

Como el CLI local no está disponible, se pidió al usuario ejecutar en
**Heroku → newglass-api-staging → More → Run console**:

```sh
cd backend && python -m alembic heads && python -m alembic current
```

Registrar por separado `heads` (código disponible) y `current` (BD real).
El head esperado es único: `ta036a1b2c3d`. No confundirlo con la revisión de BD.

**Salida remota aportada por el usuario tras v12:**

```text
ta036a1b2c3d (head)
INFO [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO [alembic.runtime.migration] Will assume transactional DDL.
fa014e1a2b3c
```

En esa lectura previa, el código contenía la migración y la BD seguía en su padre directo.
Es el escenario B autorizado; se entregó al usuario el comando de upgrade y
current posterior. **El usuario confirmó su ejecución exitosa** con:

```text
INFO [alembic.runtime.migration] Running upgrade fa014e1a2b3c -> ta036a1b2c3d, TA-036: cantidades auditables y bajas parciales de plancha.
ta036a1b2c3d (head)
```

Revisión previa: `fa014e1a2b3c`. Revisión posterior: **`ta036a1b2c3d`**.
Evidencia aportada desde consola remota por el usuario; Codex no ejecutó el
one-off mediante CLI. No repetir upgrade: la BD ya está en el head esperado.

| Resultado de `current` | Acción autorizada |
| --- | --- |
| `ta036a1b2c3d` | Correcto; no ejecutar upgrade |
| `fa014e1a2b3c`, con head remoto `ta036a1b2c3d` | Ejecutar upgrade y volver a consultar current |
| Otra revisión, varias revisiones o error real de Alembic | `BLOCKED`: registrar salida sanitizada y detener migración |

Solo para el segundo caso:

```sh
heroku run "cd backend && python -m alembic upgrade head" -a newglass-api-staging
heroku run "cd backend && python -m alembic current" -a newglass-api-staging
```

Equivalente dentro de Run console:

```sh
cd backend && python -m alembic upgrade head && python -m alembic current
```

El destino debe ser el Staging existente autorizado. No ejecutar downgrade,
stamp, bootstrap ni DDL manual. El runbook se actualiza con la salida remota
confirmada, no a partir del head local.

### Esquema: SCHEMA_PASS confirmado desde Heroku

Después del upgrade, el usuario ejecutó en Run console de
`newglass-api-staging` la siguiente variante compacta de introspección
SQLAlchemy, usando el engine del backend. Solo consulta metadata; su manejador
de errores imprime el tipo de excepción sin mensajes de conexión:

```sh
cd backend && python -c "import sys; sys.excepthook=lambda t,v,b: print('SCHEMA_CHECK_ERROR',t.__name__); from sqlalchemy import inspect; from app.shared.database import engine; i=inspect(engine); c=next((c for c in i.get_columns('movimientos_inventario',schema='public') if c['name']=='cantidad_afectada'),None); checks={x['name'] for x in i.get_check_constraints('movimientos_inventario',schema='public')}; required={'ck_movimientos_cantidad_positiva','ck_movimientos_retazo_unitario'}; old=any(x['name']=='uq_movimientos_baja_manual_plancha' for x in i.get_indexes('movimientos_inventario',schema='public')); print('cantidad_afectada:',None if c is None else (str(c['type']),c['nullable'])); print('checks_ta036:',sorted(required & checks)); print('old_plancha_index_absent:',not old); ok=c is not None and str(c['type'])=='INTEGER' and c['nullable'] and required<=checks and not old; print('SCHEMA_PASS' if ok else 'SCHEMA_FAIL'); sys.exit(0 if ok else 1)"
```

**Salida real aportada por el usuario, apta para captura:**

```text
cantidad_afectada: ('INTEGER', True)
checks_ta036: ['ck_movimientos_cantidad_positiva', 'ck_movimientos_retazo_unitario']
old_plancha_index_absent: True
SCHEMA_PASS
```

Confirma columna entera nullable, presencia de ambos checks TA-036 y ausencia
del índice antiguo `uq_movimientos_baja_manual_plancha` en la BD usada por el
backend. No se modificaron datos en esta consulta. La confirmación posterior
del usuario añadió la consulta directa en Supabase Staging y el registro
funcional creado por la UI, detallados abajo.

**Alternativa preparada, no ejecutada:** el bloque siguiente combina revisión
y esquema en una transacción explícita de solo lectura; no es necesario
repetirlo para dar por válida la salida compacta anterior.

Después de Alembic, abrir una consola `bash` en un one-off de la misma app
(`heroku run bash -a newglass-api-staging` con CLI, o Run console del dashboard).
Ejecutar este bloque desde la raíz del slug. Usa la configuración real del
backend, transacción de solo lectura y salida acotada; no muestra URL ni
mensajes de excepción que puedan contener datos de conexión:

```sh
cd backend
python - <<'PY'
import json
import sys
try:
    from sqlalchemy import inspect, text
    from app.shared.database import engine
    with engine.connect() as conn:
        conn.execute(text('SET TRANSACTION READ ONLY'))
        revisions = list(conn.execute(text('SELECT version_num FROM alembic_version')).scalars())
        inspector = inspect(conn)
        columns = inspector.get_columns('movimientos_inventario', schema='public')
        column = next((c for c in columns if c['name'] == 'cantidad_afectada'), None)
        checks = {c['name'] for c in inspector.get_check_constraints('movimientos_inventario', schema='public')}
        indexes = {i['name'] for i in inspector.get_indexes('movimientos_inventario', schema='public')}
        required = {'ck_movimientos_cantidad_positiva', 'ck_movimientos_retazo_unitario'}
        ok = (revisions == ['ta036a1b2c3d'] and column is not None
              and str(column['type']) == 'INTEGER' and column['nullable']
              and required <= checks and 'uq_movimientos_baja_manual_plancha' not in indexes)
        print(json.dumps({'app': 'newglass-api-staging', 'revisions': revisions,
              'cantidad_afectada': None if column is None else {
                  'type': str(column['type']), 'nullable': column['nullable']},
              'checks_ta036': sorted(required & checks),
              'old_plancha_index_absent': 'uq_movimientos_baja_manual_plancha' not in indexes,
              'result': 'PASS' if ok else 'FAIL'}))
        conn.rollback()
    sys.exit(0 if ok else 1)
except Exception as exc:
    print('SCHEMA_CHECK_ERROR ' + type(exc).__name__)
    sys.exit(1)
PY
```

Un `FAIL` de estructura sería BD incompatible; un error requiere revisar el
diagnóstico sanitizado. Este bloque alternativo fue preparado a partir de la
migración y los imports del repo; solo se validó su sintaxis. La evidencia
remota real es la salida de la variante compacta anterior junto con Alembic.

### Smoke autenticado manual confirmado en Pages — 293a2a9

El usuario confirmó el smoke realizado desde
<https://melendezzz26.github.io/optimizador-vidrio/> contra el backend Staging
ya desplegado en `293a2a9`. Se registran los resultados comunicados, sin
inventar status adicionales de login o `/api/auth/me` no aportados al cierre.

| Verificación confirmada | Request / operación | Resultado observado |
| --- | --- | --- |
| [x] Backend | `/`, `/health/live`, `/health/ready` | **200** en los tres endpoints |
| [x] Pedido creado | `POST /api/orders` | **201** |
| [x] Lectura del pedido | Lectura posterior | **200**, pedido visible en UI; no se especificó ruta/ID en la confirmación |
| [x] Planchas | `GET /api/inventory/planchas` | **200** |
| [x] Retazos | `GET /api/inventory/retazos` | **200** |
| [x] Retazo personalizado creado | `POST /api/inventory/retazos` | **201 Created**, código `RET-HU005-002`; Headers con Method POST y Status 201 |
| [x] Lectura posterior del retazo | `GET /api/inventory/retazos` | **200**, mismo registro visible en UI |
| [x] Edición del mismo recurso | Actualización de `RET-HU005-002` | **200**; de polígono convexo de 3 vértices a 4 vértices; área final **5705.55 mm²** |

El registro real sustituye al código de ejemplo de la preparación. No se
crearon nuevos datos durante este cierre documental ni se repitió el smoke.
La confirmación no aporta el método/ruta exactos de actualización; se registra
su status 200 sin inventarlos.

Capturar **Method, URL, Status y Response no sensible** para POST/GET de
inventario. No compartir Authorization completo, access token, cookies,
contraseñas, HAR sin sanitizar ni “Copy as cURL” con credenciales. Login se
documenta con metadatos; su response contiene un token y debe omitirse.

### Evidencia directa confirmada en Supabase Staging

El usuario confirmó consultas SQL de solo lectura en **Supabase Staging**,
no Development. La consulta del retazo ejecutada fue:

```sql
SELECT id_retazo, codigo, geometria, area_mm2, estado
FROM public.retazos
WHERE codigo = 'RET-HU005-002';
```

| Campo | Resultado observado |
| --- | --- |
| `id_retazo` | `2` |
| `codigo` | `RET-HU005-002` |
| `geometria.type` | `POLIGONO_CONVEXO` |
| `geometria.vertices_mm` | Presente; la UI confirmó edición de 3 a 4 vértices |
| `area_mm2` | `5705.55` |
| `estado` | `true` |

`SELECT version_num FROM alembic_version;` devolvió **`ta036a1b2c3d`**.
La metadata confirmó `movimientos_inventario.cantidad_afectada` con
`data_type = integer`, `is_nullable = YES` y ambos constraints:
`ck_movimientos_cantidad_positiva` y `ck_movimientos_retazo_unitario`.

Se conserva el bloque de consultas seguras de referencia, con el código real;
no es una instrucción para repetir operaciones en este cierre:

```sql
BEGIN TRANSACTION READ ONLY;
SELECT version_num FROM public.alembic_version;
SELECT table_name, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'movimientos_inventario'
  AND column_name = 'cantidad_afectada';
SELECT conname, pg_get_constraintdef(oid) AS definition
FROM pg_constraint
WHERE conrelid = 'public.movimientos_inventario'::regclass
  AND conname IN ('ck_movimientos_cantidad_positiva', 'ck_movimientos_retazo_unitario');
SELECT id_retazo, codigo, geometria, area_mm2, estado
FROM public.retazos WHERE codigo = 'RET-HU005-002';
COMMIT;
```

No se afirma que crear el retazo genere un movimiento de baja; esta evidencia
demuestra esquema y registro sin introducir otra operación de inventario.

### Correctivo real demostrado: Decimal JSON 500 → resuelto

**Antes, evidencia histórica:** `POST /api/inventory/retazos → 500 Internal
Server Error`, con `TypeError: Object of type Decimal is not JSON serializable`.
El [correctivo angular y JSON](../TA-036/correctivo-angular-json.md) documenta
el diagnóstico de Decimal dentro de tuplas de `vertices_mm` y la normalización
JSON-safe en Infrastructure.

**Después, Staging `293a2a9`:** `POST /api/inventory/retazos → 201 Created`,
GET posterior **200**, `RET-HU005-002` visible en UI y persistido directamente
en `public.retazos` de Supabase Staging como `id_retazo = 2`. La edición también
respondió 200 y dejó el área final de 5705.55 mm². El caso validado demuestra
la corrección del defecto; no se recreó el error histórico.

Trazabilidad: **hallazgo → diagnóstico → corrección → despliegue → API →
persistencia BD → lectura posterior**.

### Checklist de evidencia disponible para presentación y cierre

Disponibilidad confirmada por el usuario y resultados técnicos ya registrados.
Este índice describe el contenido de la evidencia; no inventa archivos de
imagen ni afirma una inspección de capturas por Codex. Las capas distintas
deben mostrarse explícitamente; no presentar únicamente varias capturas del
mismo render. Conservar la sanitización de datos sensibles indicada arriba.

| Disponible | Contenido concreto | Capa / origen |
| --- | --- | --- |
| [x] 1. CÓDIGO (A) | Migración `ta036a1b2c3d_baja_parcial.py` e implementación JSON-safe | Código |
| [x] 2. TERMINAL (B) | v12 / `293a2a93`, Alembic `ta036a1b2c3d`, health 200 y resultados técnicos registrados | Release/runtime |
| [x] 3. API PEDIDOS (C) | `POST /api/orders → 201`, lectura posterior 200 | Contrato de pedidos |
| [x] 4. API INVENTARIO (C) | GET planchas/retazos → 200 | Lectura de inventario |
| [x] 5. API RETAZO PERSONALIZADO (C/G) | POST retazo → **201 Created**, Headers con Request Method POST y Status 201 | Creación autenticada |
| [x] 6. BASE DE DATOS (D) | Alembic `ta036a1b2c3d`, cantidad_afectada INTEGER nullable y ambos checks | Esquema Supabase Staging |
| [x] 7. PERSISTENCIA (D) | Fila `RET-HU005-002`, ID 2, POLIGONO_CONVEXO, vertices_mm, área 5705.55 | Datos PostgreSQL |
| [x] 8. UI (E) | Pages mostrando pedidos/inventario reales y el retazo registrado/editado | Frontend publicado |
| [x] 9. ERROR HISTÓRICO (F) | Decimal → 500, [correctivo documentado](../TA-036/correctivo-angular-json.md) | Hallazgo histórico; no atribuir un screenshot original si solo se conserva texto |
| [x] 10. CORRECCIÓN (G) | POST 201 + GET 200 + fila PostgreSQL de `RET-HU005-002` | Validación funcional entre capas |
| [x] 11. PRUEBAS (H) | Run `38443828520` exitoso en `293a2a9`; tests/build/smoke ya registrados | CI y validación técnica; suites no repetidas |

**TA-035-T1 completado y validado en Staging `293a2a9`.** El estado previo
`READY FOR USER STAGING SMOKE` queda superado por el smoke y la evidencia SQL
confirmados. Este cierre es exclusivamente documental: no repite despliegues,
publicación Pages, Alembic upgrade, consultas/escrituras remotas ni suites.
No modifica producto ni los estados de las SPEC históricas.

Próximo paso, después de proteger estos documentos en el commit solicitado y
comprobar working tree limpio: **READY TO SYNC WITH INTEGRATION**. La
sincronización de la rama local con integración no se ejecuta en este cierre.

Validación documental de la continuación previa: `git diff --check` sin errores;
sintaxis del bloque Python revisada con `ast.parse`, enlaces locales existentes
y cuerpo histórico desde «Objetivo y línea base» idéntico al commit `900c995`.
No se ejecutó ese bloque contra una BD local ni remota para esta validación.
En el cierre se conserva ese contenido histórico y se identifica su resumen
para Notion como histórico; se añade al final el resumen vigente. La revisión
del cierre usa `git diff --check`, `git status` y `git diff`, sin repetir suites.

## ESTADO HISTÓRICO — auditoría conservada del commit 900c995

Lo que sigue se conserva como evidencia anterior. Sus referencias a la última
publicación, necesidad de navegador, estados pendientes y resumen para Notion
describen aquel momento; quedan sustituidas operativamente por la sección
actual anterior. Los tests y build aquí consignados no se repitieron en esta
continuación, limitada a documentación y consultas remotas de solo lectura.

Fecha: 13/10/2026. Estado histórico: **pendiente de acceso operativo autenticado**.

## Objetivo y línea base

Actualizar y validar el Staging existente, conservando Heroku, GitHub Pages y
Supabase Staging separados de desarrollo. Sin cambios funcionales ni de
proveedor, recreación de recursos, rotación de secretos o despliegue a producción.

- Base comprobada: `integration/sprint-01`,
  `373dfc22f52ae46b01ea4dc059351daf06177352`, inicialmente limpia.
- Rama de actualización: `feature/TA-035-T1-actualizacion-predeploy`.
- PR #42: TA-005/TA-006 rasterización, merge `cff3db6`.
- PR #44: TA-036 saneamiento funcional, merge `373dfc2`.
- No se modifican código, tests, migraciones ni SPEC de TA-036; esta conserva
  Draft y CA-09 PARTIAL.

## Auditoría de la preparación existente y del historial

La implementación existente se encuentra bajo TA-DEPLOY-001. T01–T06 aportan
Procfile raíz, Python 3.11, dependencias backend desde raíz, configuración
externa, CORS, health checks, bootstrap manual, build Pages y CI.

El checklist original correspondía al estado previo a la ejecución remota.
El usuario confirmó que Staging ya estaba creado y utilizado. Ahora se
verificaron endpoints públicos operativos; no se infiere de ello qué SHA
ejecuta Heroku ni qué revisión Alembic tiene Supabase. Las notas históricas
se conservan y no se usan para negar la existencia del entorno.

El procedimiento documentado sigue siendo GitHub → Heroku manual, app
`newglass-api-staging`, Auto Deploy desactivado según el usuario y el runbook.
El estado actual de ese interruptor aún no se ha consultado autenticadamente.
No se realizó un deploy backend durante esta actualización.

Pages usa `.github/workflows/deploy-pages.yml`: push a integración o ejecución
manual en esa misma rama; primero ejecuta CI y después publica `frontend/dist`.
No publica PR ni migra Supabase. `VITE_API_URL` se suministra al build y la base
es `/optimizador-vidrio/`. No hace falta un segundo workflow.

## Estado remoto observado

Consultas públicas HTTPS de solo lectura el 13/10/2026; comprobación de Actions
y segunda lectura health registrada a las 17:26:41 UTC. No se usaron secretos.

| Comprobación | Resultado observado | Límite |
| --- | --- | --- |
| Heroku `/health/live` | Primera consulta 503; reconsulta 200; confirmación posterior `200 {"status":"ok"}` | Causa del 503 sin determinar; no se atribuye a Decimal ni a PostgreSQL |
| Heroku `/health/ready` | Primera consulta 503; reconsulta 200; confirmación posterior `200 {"status":"ready"}` | Prueba disponibilidad de la conexión usada por el backend; no certifica esquema/revisión o aislamiento del proyecto |
| `/db-test` | 404; ausente de OpenAPI | Sin acceso público al diagnóstico antiguo |
| CORS desde `https://melendezzz26.github.io` | OPTIONS `/api/auth/me`: 200, allow-origin coincide | Sin token |
| CORS desde `https://unapproved.example.test` | OPTIONS: 400, sin allow-origin | Origen no autorizado rechazado |
| Pages | GET raíz publicada: 200 | No sustituye interacción visual autenticada |
| Última publicación Pages | Run `38436063048`, success, SHA `373dfc2` | Workflow consultado vía API pública GitHub |
| Jobs del mismo run | backend, frontend, e2e y pages: success | No se inventan conteos a partir del estado del job |
| Destino API del JS público | URL HTTPS Heroku esperada presente; sin `http://localhost` ni `http://127.0.0.1` | Inspección del bundle, no captura de red de una sesión autenticada |
| Bundle publicado | `index-CTlfiOXa.js`, idéntico por comparación completa de texto al build local de `373dfc2` | Mismo API público al construir |
| CSS publicado | `index-DXKAtT4E.css`, mismo nombre que build local | No se comparó su contenido completo |
| Geometría publicada | `vertices_mm` presente en el JS | Editor pendiente de retest visual remoto |
| SHA/release backend | Pendiente | Requiere panel Heroku autenticado |
| Alembic Staging antes/después | Pendiente / no ejecutado | No se aplicó upgrade |
| Login, `/me`, pedidos e inventario | Pendientes | No hay sesión/cuenta operativa disponible en las herramientas |
| Retazo personalizado remoto | Pendiente | No se crearon datos de prueba |

Destinos y evidencia pública:

- Backend: <https://newglass-api-staging-5f52e8e9b00c.herokuapp.com>.
- Frontend: <https://melendezzz26.github.io/optimizador-vidrio/>.
- [Run Pages de la línea base](https://github.com/melendezzz26/optimizador-vidrio/actions/runs/38436063048),
  iniciado 17:07:13 UTC; job Pages terminado 17:10:53 UTC.

El primer intento de HTTP desde el sandbox no tuvo conectividad. Las consultas
posteriores con acceso de red autorizado produjeron los resultados anteriores.
No se confunde esa limitación local con los 503 remotos realmente observados.

## Alembic y Supabase

`python -m alembic heads` y `python -m alembic history` locales confirmaron
head único `ta036a1b2c3d`, parent `fa014e1a2b3c`; once revisiones en la cadena.
No son lecturas de Staging. La migración agrega `cantidad_afectada` nullable,
rellena únicamente bajas manuales históricas de retazo con 1, agrega checks
de cantidad positiva/retazo unitario y retira el índice que impedía varias
bajas manuales de una plancha. Conserva NULL histórico de cantidad desconocida.

No se consultó ni reutilizó `.env` de desarrollo para conectar con Staging.
No se actualizará el head operativo del runbook hasta verificar la BD real.

Pendiente, desde el runtime de **newglass-api-staging**, con configuración
existente protegida, sin imprimirla:

```sh
cd backend
python -m alembic current
```

- Si devuelve `ta036a1b2c3d`: no ejecutar upgrade.
- Si devuelve `fa014e1a2b3c`: confirmar destino aislado, recuperación y datos a
  preservar; con el código nuevo disponible, comprobar heads/history y ejecutar
  el upgrade manual autorizado. Registrar current posterior.
- Si devuelve otra revisión: detener y reportar antes de modificar.

La secuencia para poner el código nuevo a disposición de Alembic debe acordarse
con el release real observado; no se afirma que el slug actual incluya TA-036.
No se ejecutan downgrade, stamp, bootstrap repetido ni DDL manual.

Consultas seguras previstas en la conexión aprobada de Staging:

```sql
SELECT version_num FROM alembic_version;
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'movimientos_inventario'
  AND column_name = 'cantidad_afectada';
SELECT conname, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = 'public.movimientos_inventario'::regclass AND contype = 'c';
```

Estas consultas aún no se ejecutaron. No demuestran conservación de datos sin
comparar los registros acordados antes/después. No insertar fixtures por SQL.

## Validaciones locales ejecutadas ahora

No se modificó producto ni configuración de deployment. Se aplicó validación
proporcional; las suites completas ya están registradas históricamente y el CI
del SHA integrado figura aprobado.

| Comando / conjunto | Resultado |
| --- | --- |
| `python -m alembic heads` / `history` | head único y cadena local confirmados |
| pytest focalizado indicado abajo | 75 passed, 0 skipped, 1 warning Starlette/httpx, 21.46 s |
| `node --test tests/unit/staging.test.js` | 17 passed, 0 failed, 0 skipped |
| `npm run test:component -- src/shared/__tests__/stagingNavigation.test.jsx` | 1 passed, 3.12 s |
| `npm run build:staging` con la API HTTPS aprobada | OK, 1945 módulos, 764 ms |
| `npm run check:staging` | PASS: base, assets y escaneo de patrones de secretos/localhost/DSN |

Backend ejecutado desde `backend/` con Python del venv 3.11,
`PYTHON_DOTENV_DISABLED=1`, `NEWGLASS_REQUIRE_POSTGRES=1`, `PGCTLTIMEOUT=85`:

```text
python -m pytest tests/unit/shared/test_config.py
  tests/unit/shared/test_alembic_config.py tests/api/test_health_api.py
  tests/integration/test_health_database.py
  tests/integration/test_staging_bootstrap.py
  tests/integration/test_ta036_migration.py -q -ra
```

Las líneas anteriores representan un único comando. El PostgreSQL del ensayo
es aislado local, no Supabase. El bootstrap ejecutado por el test es local.
No se ejecutó bootstrap ni migración remotos.

## TA-036, rasterización y error histórico

La [regresión integrada TA-036](../TA-036/regresion-post-integracion-ta005-ta006.md)
registra 1397 backend, 124 unitarias, 223 componentes y E2E 45 passed / 1 skipped
de 46, con el único skip móvil HU-014 preexistente. Son resultados históricos
reportados por el usuario, no nuevas ejecuciones de esta actualización.

El contrato inspeccionado en `backend/app/modules/optimization/domain/rasterizer.py`
continúa siendo `geometria.vertices_mm → rasterize_geometry() →
rasterize_convex_polygon() → RasterMask`. No existe necesidad de inventar una
interfaz de rasterización para el smoke. No se cambió su algoritmo.

El [correctivo angular y JSON](../TA-036/correctivo-angular-json.md) documenta:
hallazgo de 500, diagnóstico de `Decimal` dentro de tuplas de `vertices_mm`,
normalización JSON-safe en Infrastructure y regresión HTTP/PostgreSQL.
Los números se persisten como números, no strings. No se provocó ese defecto
en Staging. Falta obtener la evidencia remota POST + lectura corregidos;
no se presenta el E2E local como prueba de persistencia remota.

## Checklist exacta de capturas reales para presentación

No se generaron ni fabricaron screenshots. Ocultar Authorization, cookies,
contraseñas, DSN, tokens y datos personales antes de cualquier captura.

1. **Git/código:** terminal en el repo con `git log --oneline -8 integration/sprint-01`
   y `git rev-parse integration/sprint-01`; al lado, abrir
   `backend/alembic/versions/ta036a1b2c3d_baja_parcial.py` mostrando revision,
   down_revision y cantidad_afectada. Aún no rotular ese SHA «backend desplegado».
2. **Terminal/runtime:** en el runtime de la app Heroku aprobada, capturar
   `cd backend && python -m alembic current`, sin mostrar Config Vars. Si
   procede upgrade, conservar antes, salida del upgrade y current después.
   Si ya está en head, mostrar current y explicar que no fue necesaria migración.
3. **API:** en Network/Postman, registrar método, URL, status y body sanitizado
   de login (ocultar token) y de un GET autorizado de inventario. Para retazo,
   mostrar POST exitoso y lectura posterior del mismo ID con coordenadas numéricas.
   Usar un solo registro controlado e identificable si el flujo lo permite;
   no inventar un campo de etiqueta ni borrar físicamente el registro.
4. **BD:** en el proyecto Staging confirmado, mostrar salida de las consultas
   de revisión, columna y checks de este documento. Si hubo retazo de prueba,
   consultar solo su ID y geometría; ocultar datos ajenos. No mostrar conexión.
5. **Frontend publicado:** abrir la URL Pages; tras login, capturar sidebar,
   identidad/rol/sesión y editor personalizado con lados independientes,
   contador de ángulos fijados y preview. Probar recarga bajo el subpath.
   Pedidos, Inventario y Roles son los módulos implementados; no crear pantallas
   nuevas de Inicio/Resultados/Configuración para esta demostración.
6. **Error y corrección:** mostrar el fragmento histórico del documento del
   Decimal junto al POST/GET remoto correcto obtenido en el punto 3. Identificar
   el primero como evidencia histórica textual; no llamarlo screenshot original
   de un traceback si no se conserva tal captura. No recrear el error en Staging.
7. **Pruebas/deployment:** abrir el run `38436063048` con SHA y jobs verdes;
   expandir sus resultados reales cuando se necesiten conteos. Capturar también
   el build/check Staging local o los 75 tests focalizados, indicando «local».
   Panel Heroku Activity/Deploy: capturar release/SHA real cuando se habilite acceso.

## Pendientes y criterio de cierre

- Habilitar navegador conectado con sesiones Heroku/aplicación Staging.
  La herramienta de navegador no detectó superficies disponibles; `gh` y
  `heroku` tampoco están en PATH. No se solicitan secretos por el chat.
- Consultar SHA/release y Auto Deploy; comprobar proyecto Staging aislado,
  current, esquema, recuperación y ausencia de errores de bootstrap.
- Desplegar backend mediante el mecanismo manual existente si está atrasado;
  no publicar otra vez Pages si ya corresponde a la línea base.
- Completar login, `/me`, pedidos, tipos de vidrio, planchas y retazos; un
  retazo personalizado controlado con lectura posterior si es seguro.
- Validar visualmente editor compartido, geometría y navegación publicada.
- Investigar logs sanitizados del 503 transitorio; no clasificarlo como
  defecto funcional sin diagnóstico.
- Actualizar el runbook operativo solo después de verificar Alembic remoto.

**No se declara READY FOR MANUAL STAGING REVIEW todavía.** Readiness 200 no
reemplaza la verificación de release, migración y smoke autenticado.

## Resumen histórico para Notion — auditoría parcial

- **TA-035-T1 / Estado:** en curso, pendiente de acceso autenticado a Staging.
- **Objetivo:** actualizar el predespliegue existente tras PR #42 y #44.
- **Qué se actualizó:** evidencia histórica contextualizada; auditoría remota y
  validaciones locales focalizadas. Sin cambios de producto ni deploy nuevo.
- **Línea base:** integración `373dfc2`.
- **Backend:** live/ready 200 tras 503 transitorio; release/SHA pendiente.
- **Frontend:** Pages publicado en `373dfc2`, workflow success y bundle idéntico
  al build local con API HTTPS correcta.
- **BD:** conectividad por readiness; revisión/esquema Staging pendientes.
- **Pruebas:** 75 backend focalizadas, 17 unit Staging, 1 componente, build/check OK.
- **Evidencias:** este documento, run Actions enlazado y checklist de siete tipos
  de capturas reales; corrección Decimal histórica enlazada.
- **Errores/correctivos:** 503 transitorio sin causa confirmada; no hubo fix funcional.
- **Pendientes:** current/release, actualización backend si aplica, smoke autenticado,
  POST/lectura de retazo y validación visual. Sin push, PR, merge ni producción.

## Resumen final para Notion

**TA-035-T1 — Actualización de predespliegue**

- **Estado:** Completado y validado en Staging.
- **Versión final verificada:** `293a2a9`; base inicial de esta rama: `373dfc2`.
- **Incluye:** PR #42, PR #44 y PR #43.
- **Backend:** Heroku operativo, release v12 / `293a2a93`.
- **Frontend:** GitHub Pages operativo, publicación de `293a2a9`.
- **BD:** Supabase Staging en `ta036a1b2c3d`; esquema TA-036 confirmado.
- **API:** Pedidos e inventario validados.
- **Retazo personalizado:** POST 201 + GET 200 + persistencia PostgreSQL;
  `RET-HU005-002`, ID 2; edición 200, área final 5705.55 mm².
- **Correctivo:** Decimal JSON 500 → resuelto en el caso validado.
- **Evidencias:** código, terminal, API, BD, UI, error/corrección y pruebas.
- **Siguiente etapa Git:** READY TO SYNC WITH INTEGRATION; sin push, PR ni merge
  en este cierre documental.
