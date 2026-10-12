# T06 — CI y workflow Pages

Fecha local: 12/10/2026. Rama `feature/TA-DEPLOY-001-staging`.
Base de esta tarea: `208d5fc`. SPEC Reviewed, releída antes de implementar.

Estado: **IMPLEMENTADA / VALIDACIÓN LOCAL**. Publicación y controles remotos pendientes.

## Implementación

CI en PR, pushes main/integration y llamada reutilizable: Python 3.11, Node 22,
PostgreSQL temporal en loopback, pytest completo, npm ci, unit/component,
lint/build y Playwright con Chromium administrado. No usa secretos Staging.
La ausencia de binarios PostgreSQL es un fallo con NEWGLASS_REQUIRE_POSTGRES=1
o CI=true; dos pruebas verifican ambos casos, sin omitirlos silenciosamente.

Pages solo desde integration/sprint-01, después de CI del mismo commit;
artefacto frontend/dist, environment github-pages, permisos mínimos y
concurrency sin cancelación. VITE_API_URL llega de vars GitHub, se valida en
build:staging y se inspecciona el bundle antes de publicarlo. No se ejecutó
el workflow remoto ni se configuraron protecciones, environments o servicios.
El runbook documenta aprobación humana y checks de rama pendientes.

## Verificaciones locales ejecutadas

Entorno Windows, Python 3.11.9 del venv existente, Node 22.23.2 / npm 10.9.8.

| Comando / comprobación | Resultado |
|---|---|
| python -m pytest tests/unit/test_ci_contract.py -q | 4 passed, 0.50 s |
| NEWGLASS_REQUIRE_POSTGRES=1; python -m pytest tests -q -ra | 1284 passed, 0 skipped, 1 warning, 308.31 s (5:08) |
| npm ci | exit 0; 221 paquetes instalados, 222 auditados; 1 aviso high |
| npm run test:unit | 101 passed, 0 fail, 0 skipped, 164.2407 ms |
| npm run test:component | 20 archivos / 206 passed, 45.18 s |
| npm run lint | exit 0 |
| npm run build | exit 0; 1941 módulos, 985 ms |
| npx playwright install chromium | exit 0; Chromium v1243, FFmpeg y componentes descargados |
| npm run test:e2e | 31 passed, 1 skipped, 43.2 s |
| npm run build:staging con VITE_API_URL=https://api.example.test | exit 0; 1941 módulos, 840 ms |
| npm run check:staging | PASS: base, assets, ausencia de localhost/DSN/nombres de secretos/patrones de tokens privados |
| git diff --check | exit 0, sin observaciones |

E2E usó PATH del venv, PLAYWRIGHT_CHANNEL=chromium,
NEWGLASS_REQUIRE_POSTGRES=1 y PYTHON_DOTENV_DISABLED=1, con backend/BD sintéticos.
La URL example.test es sintética y solo se compiló; no hubo petición a ella.
YAML se parseó con PyYAML y se comprobaron contratos de triggers, dependencias,
permisos, artefacto y gates. No se ejecutó actionlint ni un runner Linux/Actions.

## Avisos y omisiones

- Backend: StarletteDeprecationWarning sobre httpx en TestClient; aviso existente,
  sin cambio de dependencias.
- Playwright: omisión preexistente y explícita en
  `frontend/tests/e2e/hu014-inventory-writeoff.spec.js`, caso de baja de inventario
  en chromium-mobile: «La mutación usa un recurso de baja única.» El caso desktop
  pasó. No es falta de PostgreSQL o navegador.
- Node advierte que NO_COLOR se ignora porque FORCE_COLOR está definido.
- npm audit (consulta sin cambios) reportó una vulnerabilidad high transitiva
  en source-map-js, rango 1.0.0–1.2.1, con corrección disponible:
  [GHSA-68fv-2mgg-jv7q](https://github.com/advisories/GHSA-68fv-2mgg-jv7q).
  No se ejecutó npm audit fix ni se cambió el lockfile. Requiere evaluación
  antes de aprobar el release; npm ci terminó con exit 0.
- Dos intentos anteriores de lanzar las suites fueron rechazados por límite
  de uso de revisión automática de permisos; no se ejecutaron. Tras la orden
  de continuar se pudieron lanzar; no se contabilizan como ejecuciones fallidas.

CA-12: implementación y validación local; pendientes run Linux/Actions y checks
requeridos de rama. CA-13: workflow preparado, publicación real pendiente.
CA-09/10/11: artefacto sintético comprobado. CA-14/15/16/17 remotos pendientes.
Sin push, Supabase Staging, deploy Heroku, publicación Pages o migraciones nuevas.
