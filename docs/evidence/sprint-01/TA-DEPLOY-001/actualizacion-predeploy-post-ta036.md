# TA-035-T1 — Actualización del predespliegue después de TA-036

Fecha: 13/10/2026. Estado: **pendiente de acceso operativo autenticado**.

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

## Resumen para Notion

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
