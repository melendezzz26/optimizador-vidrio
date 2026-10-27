# HU-016 T03 — Aislar respuestas por visita a Inicio

Fecha: 27/10/2026, America/Lima. Corrección autorizada por Fabricio Melendez:
estabilizar el E2E del Dashboard. Base `4bcf54d`, `integration/sprint-01`.
Rama original reutilizada: `feature/HU-016-dashboard-inicial`.
[SPEC vigente](../../../specs/SPEC-HU-016-dashboard-inicial.md), en particular
su validación E2E de navegación y permisos. No cambia sus 22 CA ni su estado
formal; la regularización de cierres queda con Aguilar según la indicación del
responsable. Esta entrega y sus commits permanecen exclusivamente locales.

## Defecto y reproducción

El observador atendía todas las respuestas GET de Inventory/Orders/Clients.
Vaciar el arreglo al regresar a Inicio no impedía que una petición comenzada
en el módulo anterior terminase después y se sumara a las seis fuentes nuevas.
El mismo URL puede pertenecer a cualquiera de las dos visitas.

En `c941ada` se extrae el observador conservando su comportamiento y se añaden
regresiones antes de corregirlo:

```bash
cd frontend
node tests/unit/dashboardResponses.test.js
# 6 tests: 3 pass, 3 fail. Casos: 7 != 6, 4 != 2 y 1 != 0.
```

El caso navegador retiene la entrega de una respuesta obtenida con `route.fetch`
contra la API real y el token del login sintético real. Vuelve a Inicio, espera
sus seis fuentes y después libera la respuesta anterior. No reemplaza el payload
del backend. Con el comportamiento original falla tanto en escritorio como en
móvil: **expected length 6, received length 7**.

```bash
PATH="/workspace/optimizador-vidrio/backend/.venv/bin:$PATH" NEWGLASS_TEST_PG_BIN=/tmp/hu016-tools/root/usr/lib/postgresql/17/bin NEWGLASS_REQUIRE_POSTGRES=1 PYTHON_DOTENV_DISABLED=1 PLAYWRIGHT_CHANNEL=chromium PLAYWRIGHT_BROWSERS_PATH=/tmp/hu016-tools/browsers npm run test:e2e -- ta-dashboard.spec.js --grep 'ciclo anterior'
# 2 failed: la respuesta real retenida se convierte en la séptima fuente.
```

## Corrección

`tests/e2e/dashboardResponses.js` registra las peticiones al comenzar, conserva
su identidad en un `WeakSet` y solo incorpora respuestas de peticiones observadas
en el ciclo vigente. `beginCycle()` sustituye ese conjunto y vacía las respuestas.
Las visitas anteriores no aportan respuestas a la nueva, incluso con URL idéntico.

Se conserva el mismo filtro de origen, método y recursos; las respuestas actuales
403/503 siguen registrándose para que las aserciones las detecten. Permanecen los
conteos exactos de seis/dos, los permisos por rol, cero accesos restringidos para
la sesión sin permisos, refresh/logout, navegación, responsive y error parcial.
No se añaden reintentos, esperas artificiales ni tolerancia a peticiones extra.
La corrección se limita al observador de pruebas: no cambia la aplicación ni API.

## Validación local posterior

Node 24.19.0, Python 3.11.9, PostgreSQL 17 temporal exclusivo y Chromium local
154. El backend y la aplicación Vite son reales; no se usa una base compartida.
No se necesitan credenciales del usuario.

```bash
node tests/unit/dashboardResponses.test.js
# 6 passed, 0 failed.
npm run test:unit
# 167 passed, 0 failed, 0 skipped.
npm run lint
# Exit 0.
npm run build
# Exit 0; 1988 módulos; 887 ms.

PATH="/workspace/optimizador-vidrio/backend/.venv/bin:$PATH" NEWGLASS_TEST_PG_BIN=/tmp/hu016-tools/root/usr/lib/postgresql/17/bin NEWGLASS_REQUIRE_POSTGRES=1 PYTHON_DOTENV_DISABLED=1 PLAYWRIGHT_CHANNEL=chromium PLAYWRIGHT_BROWSERS_PATH=/tmp/hu016-tools/browsers npm run test:e2e -- ta-dashboard.spec.js --repeat-each=3
# 72 passed (2.9m), sin skips y con retries: 0.
```

Son 24 casos por repetición: los 22 existentes y dos nuevos de latencia controlada
con respuesta de la API real. Tres repeticiones producen 72 ejecuciones; no son
72 escenarios distintos. Los casos previos de fallo HTTP controlado se conservan
identificados por su propio nombre y no acreditan una avería natural del backend.

La instrucción posterior del responsable prohíbe publicar, crear PRs o realizar
merges: no se ejecuta CI remota ni se despliega esta corrección. Los resultados
anteriores son locales. TA-040 y los seis skips históricos de HU-015 mantienen
su alcance separado; no se declaran resueltos desde este trabajo.
