# T07 — Checklist para ejecución humana de Staging

**T07 NO COMPLETADA. No se ejecutó ninguna acción remota.**
SPEC Reviewed; runbook: [staging.md](../../../infrastructure/staging.md).
Preparación local sobre `a95d92f`, 12/10/2026. Los checks siguientes requieren
responsable, autorización operativa y evidencia sanitizada. No confundir este
documento con permiso para migrar/publicar ni con resultados de Staging.

## Gate previo al release

- [x] Resolver el aviso high transitivo de `source-map-js@1.2.1` con la
  actualización mínima del lockfile a 1.2.2. El audit posterior reportó 0
  vulnerabilidades. Ver [evidencia de seguridad](test-results/security-source-map-js.md).
- [x] Validar E2E después del cambio de lockfile: `npm run test:e2e`, 32 casos
  descubiertos, 31 passed, 1 skipped, 0 failed, 34.8 s. Python 3.11.9 se
  localizó primero en `backend/venv/Scripts/python.exe`. El único skip es
  “HU-014 Almacenero registra una baja” en chromium-mobile; el escenario
  equivalente desktop y el caso de permisos HU-014 pasaron. Esta ejecución
  manual válida reemplaza la limitación anterior del entorno Codex.
- [ ] Revisar e integrar el SHA aprobado en `integration/sprint-01`; esta sesión
  no hizo push. Registrar SHA integrado y resultado real de Actions en Linux.
- [ ] Configurar checks requeridos backend/frontend/e2e y protección de rama.
  Confirmar que faltas de PostgreSQL fallan explícitamente, sin skips silenciosos.
- [ ] Configurar aprobación humana del environment `github-pages` antes de un
  push integrado: ese push dispara el workflow de Pages. Restringirlo a la rama
  aprobada; no aprobar publicación hasta completar los pasos siguientes.
- [ ] Confirmar regresión local/CI del SHA integrado que se desplegará y que
  Actions pasó para ese mismo SHA. La ejecución manual E2E post-seguridad y el
  skip conocido están registrados en [evidencia de seguridad](test-results/security-source-map-js.md).

## 1. Configurar Supabase Staging

- [ ] Seleccionar/provisionar destino aislado autorizado; confirmar proyecto,
  región, BD y dueño por canal privado. No copiar DSN/contraseñas a evidencia.
- [ ] Decidir direct vs Session Pooler según IPv4/IPv6, disponibilidad desde
  Heroku, TLS y límites reales. No asumir compatibilidad de transaction pooling.
- [ ] Revisar exposición Data API, grants y RLS para evitar accesos alternativos.
- [ ] Acordar presupuesto de conexiones (dynos/procesos, pool y overflow,
  migración/admin/readiness) y timeouts finitos; registrar razones sin secretos.
- [ ] Confirmar backup/restauración o recuperación aprobada y precondiciones
  de todas las revisiones según el runbook, incluidos datos/tablas existentes.

## 2. Configurar Config Vars Heroku

- [ ] App `newglass-api-staging`, GitHub conectado, automatic deploy desactivado.
  Build desde raíz, Python 3.11, único proceso web del Procfile. Sin workers,
  Redis, scheduler o Heroku Postgres.
- [ ] Inyectar DATABASE_URL con TLS y SECRET_KEY propia por canal protegido;
  TOKEN_MINUTOS positivo, CORS_ORIGINS con el origen HTTPS Pages aprobado
  (sin `/optimizador-vidrio/`), DB_POOL_SIZE, DB_MAX_OVERFLOW,
  DB_POOL_TIMEOUT y DB_CONNECT_TIMEOUT según presupuesto revisado.
- [ ] Heroku proporciona PORT; no crear `.env` ni usar placeholders funcionales.
- [ ] Verificar DNS, red y TLS desde runtime autorizado, sin revelar la conexión.

## 3. Migrar la BD real (manual y autorizadamente)

- [ ] Confirmar destino y SHA nuevamente; detenerse ante discrepancias.
  Registrar `alembic current`, head único `fa014e1a2b3c`, historial,
  precondiciones, backup y registros concretos que se preservarán.
- [ ] Confirmar ensayo local de la cadena existente. Con entorno protegido,
  desde backend ejecutar `python -m alembic upgrade head` solo después de la
  autorización; registrar `python -m alembic current` posterior.
- [ ] Verificar current `fa014e1a2b3c`, catálogo de tipos/espesores y comparación
  acordada de datos. No crear revisiones, DDL manual ni usar `alembic stamp`
  para ocultar divergencias. Fallo implica detener el release.

## 4. Bootstrap controlado

- [ ] Tras migrar, ejecutar `python seed.py` una vez, sin concurrencia; comprobar
  roles Administrador, Almacenero y Operario.
- [ ] Ejecutar `python -m scripts.create_first_admin` interactivamente, con datos
  controlados de Staging y contraseña gestionada fuera de Git. Revisar si ya
  existe administrador activo. No usar identidades personales reales.
- [ ] Acordar gestión/cambio de credencial inicial y datos mínimos de smoke.
  Sanitizar host/BD que muestra el script; no conservar tokens ni contraseñas.

## 5. Deploy manual Heroku

- [ ] Elegir SHA integrado/aprobado por GitHub en Heroku; ejecutar deploy manual.
  Mantener automatic deploy apagado. Registrar SHA, release, runtime y fecha.
- [ ] Comprobar build limpio, detección Python/dependencias raíz, arranque con
  PORT de plataforma y funcionamiento sin `.env` local.
- [ ] Verificar live/ready y logs sanitizados. Detenerse ante error antes de Pages.

## 6. Configurar y publicar Pages

- [ ] Pages source = GitHub Actions, environment github-pages con aprobación y
  rama restringida. Configurar `VITE_API_URL` como variable pública GitHub con
  la API HTTPS real aprobada; ninguna variable VITE contiene secretos.
- [ ] Ejecutar/aprobar workflow desde `integration/sprint-01`, con CI aprobado
  para el mismo commit. Revisar build:staging, check:staging y frontend/dist.
- [ ] Confirmar base `/optimizador-vidrio/`, assets presentes, ausencia de
  localhost/DSN/secretos/tokens privados; registrar commit, run y artefacto.

## 7. Smoke desplegado

- [ ] `/health/live`: 200 y `{"status":"ok"}`; independencia de BD cubierta
  localmente, no provocar una caída real sin procedimiento autorizado.
- [ ] `/health/ready`: 200 y `{"status":"ready"}`; fallo controlado 503 genérico
  con plazo finito, sin información de PostgreSQL, según prueba autorizada.
- [ ] `/db-test`: 404 y ausente de OpenAPI.
- [ ] Login de cuenta controlada, `/api/auth/me` y lectura de inventario con
  permisos; no hace falta mutación para el smoke.
- [ ] Preflight desde origen Pages permitido; origen no autorizado sin permiso.
- [ ] Carga/recarga de URL Pages bajo `/optimizador-vidrio/`, navegación interna
  al editor sin 404 y sin peticiones localhost. No usar editor-pieza como ruta
  profunda física. Comprobar desktop y móvil.

## 8. Evidencias finales y recuperación

- [ ] Registrar PASS/FAIL de cada smoke, SHA backend/frontend, revisión Alembic,
  fecha, entorno, responsable y links de Actions/deployment sin datos sensibles.
- [ ] Guardar capturas/logs sanitizados en smoke/ y deployment/; eliminar
  Authorization, cookies, tokens, contraseñas y DSN antes de conservarlos.
- [ ] Fallo: detener release; rollback de app al SHA/artefacto anterior compatible.
  Recuperación de BD es independiente: usar procedimiento aprobado, no
  downgrades improvisados ni stamp. Documentar resultado y revisión.
- [ ] Solo después de revisión humana actualizar CA y estado de la SPEC/T07.

## Evidencia local de preflight (no es evidencia de deployment)

Comandos backend desde backend con venv existente; frontend desde frontend.
Variables de prueba: NEWGLASS_REQUIRE_POSTGRES=1, PYTHON_DOTENV_DISABLED=1;
E2E además PLAYWRIGHT_CHANNEL=chromium y PATH del venv.

| Verificación | Resultado observado |
|---|---|
| python -m pytest tests -q -ra | 1284 passed, 0 skipped, 1 warning, 282.21 s (4:42) |
| python -m alembic heads | fa014e1a2b3c (head), único |
| npm run test:unit | 101 passed, 0 skipped, 191.493 ms |
| npm run test:component | 20 archivos / 206 passed, 48.30 s |
| npm run lint | exit 0 |
| npm run build | exit 0, 1941 módulos, 933 ms |
| npm run test:e2e | 31 passed, 1 skipped, 43.4 s |
| git diff --check | exit 0, sin observaciones |

E2E omitió únicamente el caso móvil de baja de inventario que consume un recurso
único; desktop pasó. Aviso Node: NO_COLOR ignorado por FORCE_COLOR. El primer
intento de regresión backend del preflight no se ejecutó por límite de uso de
revisión automática de permisos; tras la instrucción de continuar se reintentó
y pasó. Backend conserva el aviso StarletteDeprecationWarning sobre httpx en
TestClient. No se modificaron dependencias para ocultarlo.

### Validación manual post-seguridad

Python se localizó primero en `backend/venv/Scripts/python.exe` y reportó
Python 3.11.9. En esta ejecución manual se registraron:

| Verificación | Resultado observado |
|---|---|
| `npm run test:unit` | 101 passed |
| `npm run test:component` | 206 passed |
| `npm run lint` | PASS |
| `npm run build` | PASS |
| Build Staging / check Staging | PASS |
| `npm run test:e2e` | 32 descubiertos: 31 passed, 1 skipped, 0 failed; 34.8 s |

El único skip fue “HU-014 Almacenero registra una baja” en chromium-mobile.
El escenario equivalente desktop pasó y el caso de permisos HU-014 pasó en las
plataformas ejecutadas. La imposibilidad previa de iniciar E2E correspondía al
entorno de Codex y queda reemplazada por esta ejecución manual válida. La
recomendación del preflight es **READY FOR HUMAN STAGING DEPLOY**; T07 continúa
pendiente y no se declara deployment realizado.

Siguen pendientes para T07: conexión con Supabase real, Config Vars de Heroku,
migración real, bootstrap real, deploy manual de Heroku, publicación de Pages y
smoke Staging. El SHA integrado y la aprobación de Actions aún deben confirmarse
para el despliegue.

Escaneo local por patrones sobre los 526 archivos de `git ls-files`: sin `.env`
real ni archivos de claves versionados; sin coincidencias de clave privada,
tokens de proveedor/JWT literales o asignaciones literales de secretos revisadas.
Tres archivos contenían DSN sintéticos: backend/.env.example,
backend/tests/unit/shared/test_alembic_config.py y test_config.py. Se comprobó
que usan destinos sintéticos/locales; no se imprimieron sus URLs. No se hallaron
credenciales reales Supabase/Heroku en los patrones examinados. Este escaneo
del árbol versionado no certifica servicios remotos ni todo el historial Git.

CA-01/02/03/04/08/09/10/11: aportes locales, confirmación remota pendiente.
CA-05/06/07: contratos comprobados localmente, smoke remoto pendiente.
CA-12/13: implementación validada localmente, ejecución/protecciones/publicación
real pendientes. CA-14/15/16/17: pendientes de despliegue y smoke humanos.
