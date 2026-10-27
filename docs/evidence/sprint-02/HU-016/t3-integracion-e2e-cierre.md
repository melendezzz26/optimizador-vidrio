# HU-016 T03 — integración real y evidencia de cierre

Fecha: 27/10/2026, America/Lima. Rama: `feature/HU-016-dashboard-inicial`.
PR: [#72 → integration/sprint-01](https://github.com/melendezzz26/optimizador-vidrio/pull/72).
SPEC: [SPEC-HU-016](../../../specs/SPEC-HU-016-dashboard-inicial.md).

T01/T02: Luis Anthony Ibañez Herrera (`imthonyyy`), integradas en PR #63.
Regularización T03: Fabricio Melendez Quezada con asistencia de Codex,
commit de pruebas `32dd7156a0dbc081c3684ed05c9127d1bc9f5eaa`, sobre
`2094b2d` de Luis y `9cf6dc8` de integración. Revisión humana del PR pendiente;
no se atribuye a Aguilar la aprobación del cierre ni se modifica Notion.

La ejecución anterior no acreditaba T03: eliminar la suite simulada no ejecutaba
la suite real, que omitía 14 casos por falta de credenciales. Esta evidencia
sustituye las afirmaciones anteriores de cierre, conservadas en Git.

## Qué se verifica

Se reutilizan la aplicación Vite, la API FastAPI y el PostgreSQL temporal de
`tests.e2e_server` con migraciones Alembic reales. Los tres roles usan las
cuentas sintéticas ya preparadas; se añade una cuarta cuenta con un rol sin
filas en `rol_permisos`. Login y `/api/auth/me` consultan el backend real.
No se inyectan tokens, respuestas HTTP ni permisos del cliente para los flujos
que acreditan CA-20. No se necesitan credenciales ni variables secretas externas.

- Login → Inicio → Inventario/Optimización → Inicio para los tres roles.
- Pedidos para Administrador/Operario y Usuarios para Administrador.
- Almacenero consulta Optimización sin controles de cálculo/confirmación.
- Totales de pedidos y unidades/registros de planchas comparados con las
  respuestas HTTP recibidas; no se fijan cifras para aparentar datos reales.
- Sesión sin permisos: Inicio, identidad, refresh y logout; cero solicitudes
  del navegador a módulos restringidos. Llamadas API directas con ese token
  reciben 403 en Inventario, Pedidos, Clientes y Usuarios.
- Responsive 1440/1024/800/390 px: sin overflow horizontal, Sidebar sin
  intersección con contenido, accesos utilizables con scroll y retorno a Inicio.
- Logout elimina `sessionStorage.optimizador.auth` y la superficie protegida.

El escenario **CONTROLLED FAILURE SCENARIO — NOT REAL BACKEND FAILURE**
intercepta una respuesta 503 de planchas para comprobar error parcial y luego
retira la intercepción: el reintento obtiene las seis fuentes de la API real.
Son **2 casos de fallo controlado** (uno por proyecto), separados de los
**20 casos de integración real**. No se presentan como una avería natural del
backend ni sustituyen los flujos reales de CA-20. Los estados loading, empty,
error, success, permisos revocados y respuestas tardías también tienen pruebas
de componentes específicas.

## Resultados observados

| Comprobación | Resultado |
|---|---|
| Dashboard/Authentication, componentes focalizados | 86 passed, 6 archivos; 9.56 s |
| Dashboard E2E focalizado, escritorio y móvil | 22 passed, 0 skipped; 1.3 min |
| Componentes frontend completos | 483 passed, 43 archivos; 244.02 s |
| Unitarias frontend, Node 24.19.0 | 9 archivos aprobados, 0 fallos; el reporter local resume por archivo |
| ESLint | Exit 0, sin errores ni advertencias |
| Build Vite 8.3.1 | Exit 0; 1988 módulos; 1.24 s |
| Regresión E2E completa, Chromium local 154 | 99 passed, 6 skipped de HU-015, 1 fallo en TA-036 móvil; 7.1 min. Los 22 casos Dashboard pasan dentro de esta ejecución. |
| Backend completo con PostgreSQL obligatorio | 2146 passed, 1 warning; 518.76 s |
| CI del commit de pruebas | [Run 138](https://github.com/melendezzz26/optimizador-vidrio/actions/runs/40527868191): frontend aprobado (161 unitarias, 483 componentes, lint/build) y E2E aprobado (100 passed, 6 skipped de HU-015, incluidos los 22 Dashboard sin skips); backend en ejecución al preparar este reporte |

Contexto local: Linux, Python 3.11.9 (venv del backend), Node 24.19.0,
PostgreSQL 17.11 temporal y Chromium 154.0.8037.57 del entorno. Los comandos se ejecutaron
sobre `32dd715`; solo la documentación estaba sin commit al preparar el reporte.
CI usa su Node 22, Python 3.11, PostgreSQL y Chromium administrados del workflow.
Los resultados locales y de CI se distinguen; no se copian cifras históricas.

### Límite observado en la regresión local

`ta036-retazo-personalizado.spec.js` falla en el proyecto móvil al pulsar
«Registrar retazo»: el formulario/footer intercepta el puntero. Se repitió
el caso aislado y volvió a fallar con Chromium 154 local. Ese test y todo el
código de producción son idénticos a la base `9cf6dc8`; no se modifica TA-036
para declarar verde HU-016. El mismo caso aprueba en escritorio y móvil con Chromium administrado de CI
(run 138: 100 passed, 6 skipped, 0 failed). No se declara que toda la regresión
local haya pasado ni se atribuye a HU-016 un cambio en esa interfaz.
Los seis skips corresponden a tres escenarios antiguos HU-015 por proyecto,
fuera de los 22 E2E Dashboard; no se presentan como pruebas ejecutadas.

## Reproducción

Con dependencias backend/frontend preparadas según los README y binarios
`initdb`/`pg_ctl` disponibles:

```bash
# Activar primero el venv de backend para que Playwright encuentre python.
# Linux: ajustar únicamente NEWGLASS_TEST_PG_BIN a los binarios instalados.
export NEWGLASS_TEST_PG_BIN=/ruta/a/postgresql/bin
export NEWGLASS_REQUIRE_POSTGRES=1
export PYTHON_DOTENV_DISABLED=1
export PLAYWRIGHT_CHANNEL=chromium
cd frontend
npm run test:component -- src/features/dashboard src/features/authentication
npm run test:e2e -- ta-dashboard.spec.js
npm run test:unit
npm run test:component
npm run test:e2e
npm run lint
npm run build
cd ../backend
python -m pytest tests -q -ra
```

Playwright inicia y detiene sus servidores; la base se crea en loopback bajo
un directorio temporal propio. `DATABASE_URL` compartida no es un requisito.
El CI existente establece `NEWGLASS_REQUIRE_POSTGRES=1` y deshabilita dotenv.
La suite Dashboard no usa `test.skip` por credenciales. No se crea un endpoint
agregado, ni se cambian producción, migraciones o lógica del optimizador.

Para exportar capturas fuera del directorio ignorado de Playwright, configurar
`NEWGLASS_HU016_EVIDENCE_DIR` antes del comando focalizado. Sin esa variable,
los artefactos van a `frontend/test-results/`; los proyectos se separan y no
sobrescriben la evidencia histórica de Sprint 1. La exportación de esta sesión
usó `/tmp/hu016-tools/evidence`; se conservan cinco capturas seleccionadas en
[t3/real/](t3/real/). Son capturas nuevas contra PostgreSQL real. Las imágenes
anteriores de `t3/screenshots/` son históricas y no acreditan esta ejecución.

## Matriz de los 22 criterios

Se mantiene el texto funcional de la SPEC. CA-20 recupera su exigencia original:
Login → Inicio → módulo autorizado con navegador, API y datos controlados reales,
incluyendo retorno a Inicio, refresh y logout.

| CA | Evidencia actual |
|---|---|
| CA-01 | E2E real para los tres roles y rol sin permisos; login HTTP 200 y saludo con identidad de la respuesta. |
| CA-02 | E2E real: navegación desde accesos rápidos y retorno mediante Sidebar con aria-current=page. |
| CA-03 | E2E real: rol sin filas en rol_permisos; Inicio, mensaje, refresh y logout; cero solicitudes del navegador a módulos restringidos. |
| CA-04 | E2E real: fuentes y accesos por rol; ausencia de Pedidos/Usuarios donde corresponde. Componentes para permisos efectivos y revocados. |
| CA-05 | E2E real: llamadas directas con token sin permisos reciben 403 en Inventario, Pedidos, Clientes y Usuarios; controles backend existentes. |
| CA-06 | E2E compara unidades/registros de planchas y totales de pedidos con las respuestas HTTP reales. Componentes verifican las otras transformaciones. |
| CA-07 | E2E distingue estado=PENDIENTE y compara total; sin consulta ni tarjeta para Almacenero. |
| CA-08 | E2E distingue estado=EN_OPTIMIZACION y compara total; componentes comprueban el rotulado sin métricas de ejecución. |
| CA-09 | E2E compara unidades/registros de planchas; dashboardModel/DashboardPage prueban retazos y advertencias de compatibilidad. |
| CA-10 | E2E real: Inventario y Optimización para tres roles; Pedidos para Administrador/Operario; Usuarios para Administrador; retorno a Inicio. |
| CA-11 | E2E Almacenero: acceso neutral a Optimización, consulta visible, sin controles de cálculo ni confirmación. |
| CA-12 | E2E sin Administración para Operario/Almacenero; pruebas de permisos y componentes para pestañas independientes. |
| CA-13 | Componentes: loading/empty/error/success, disabled y parciales. E2E: datos vacíos reales y fallo 503 controlado seguido de reintento contra API real. |
| CA-14 | useDashboard y DashboardNavigation: cancelación/aislamiento por sesión y permisos; E2E controlado conserva fuentes exitosas. |
| CA-15 | Contrato y pruebas de componentes: Inicio no incorpora indicadores ni comparativas del optimizador. |
| CA-16 | DashboardNavigation: teclado, foco y semántica. E2E: accesos y Sidebar utilizables; no se afirma certificación WCAG. |
| CA-17 | E2E parametrizado en 1440/1024/800/390: scrollWidth <= innerWidth, controles accesibles al hacer scroll y Sidebar sin solapamiento. |
| CA-18 | E2E real: reload en URL base, GET /api/auth/me 200 y sesión recuperada; componentes conservan navegación en subpath. |
| CA-19 | E2E real: desaparecen Inicio y sus datos, sessionStorage.optimizador.auth queda vacío y se presenta Login. |
| CA-20 | ta-dashboard.spec.js: navegador, API y PostgreSQL temporal reales; login, módulos, retorno a Inicio, refresh/logout. El fallo 503 controlado no acredita este CA. |
| CA-21 | 86 pruebas de permisos/componentes de Dashboard y Authentication, incluyendo permisos revocados y sesión sin fuentes. |
| CA-22 | E2E real navega a los cuatro módulos autorizados; regresión completa registrada en la evidencia. Sin cambios en HU-015 ni código de producción. |

La validación técnica se completa con los resultados anteriores; la revisión y
el merge del PR se registran separadamente. El estado de Notion no se cambia
automáticamente ni se declara una aprobación humana que no haya ocurrido.
