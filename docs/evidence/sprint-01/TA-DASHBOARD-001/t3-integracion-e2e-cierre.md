# TA-DASHBOARD-001 — T3 integración, E2E y cierre

## Resultado

T3 completada en la rama feature/TA-DASHBOARD-001. Los siete escenarios E2E pasaron contra el frontend local, el backend ya iniciado por el usuario y la instancia Supabase de desarrollo configurada. La SPEC queda Verified; el PLAN se mantiene Approved. No se creó PR ni se hizo push, merge o deploy.

## Secuencia de entorno

1. **Intento inicial del agente:** no pudo crear el proceso Python del backend desde su contexto porque el intérprete base del venv resolvía a WindowsApps. Ese intento no reinició ni dañó el backend; el resumen histórico se conserva en t3/logs/backend-agent-start-block-summary.txt.
2. **Comprobación del entorno real:** el usuario inició el backend desde su PowerShell con el venv activo. El agente no intentó iniciarlo de nuevo. El servidor existente en http://127.0.0.1:8000 respondió HTTP 200 en /openapi.json, /health/live y /health/ready; el último devolvió status ready. Vite respondió HTTP 200 en http://127.0.0.1:5173/. La salida saneada está en t3/logs/backend-health-recheck-summary.txt.
3. **Segundo bloqueo:** la spec E2E no disponía de cuentas de prueba. Una ejecución inicial descubrió siete tests pero los omitió por ausencia explícita de configuración; no se contó como prueba exitosa. El resumen conserva 0 passed y 7 skipped en t3/logs/e2e-initial-skips-summary.txt.
4. **Cuentas sintéticas autorizadas:** se crearon mediante el caso de uso/repositorio existente y el helper de hash de contraseña real del backend. No se modificaron tablas ni se añadieron migraciones. Se verificaron login y sesión (/api/auth/me) para las tres cuentas sin imprimir ni guardar sus valores en este documento.

| Rol | Resultado | Identificador de base de datos |
|---|---|---:|
| Administrador | Creada, activa | 18 |
| Operario | Creada, activa | 19 |
| Almacenero | Creada, activa | 20 |

Las credenciales se conservan solo en frontend/.env.e2e.local, archivo local ignorado por frontend/.gitignore (regla *.local). git check-ignore confirmó la exclusión. No se incluyeron en contenido versionado las credenciales, nombres de inicio de sesión, contraseñas, tokens, cookies o estado de autenticación.

Las cuentas permanecen activas por solicitud expresa y no se eliminaron. No se crearon pedidos, clientes, piezas ni otros datos operativos.

## E2E real

Comando ejecutado desde frontend:

npm.cmd run test:e2e -- --config=./playwright.dashboard.config.js tests/e2e/ta-dashboard.spec.js

Resultado final: **7 passed, 0 failed, 0 skipped, 0 flaky**, Playwright 1.63.0, Chromium 153.0.8010.12, un worker. La spec usa Vite, backend y Supabase reales en los happy paths. No usa route.fulfill para autenticación, inventario, pedidos ni clientes. El escenario parcial es una excepción controlada y etiquetada.

| Caso | Resultado y comprobación observable |
|---|---|
| Administrador | Login real, Inicio, datos reales permitidos, acceso a Gestión de inventario y módulo real con respuesta HTTP 200. |
| Operario | Login real, Inicio, datos reales permitidos, acceso a Gestión de inventario y módulo real con respuesta HTTP 200. |
| Almacenero | Login real, Inicio, resumen limitado a inventario y navegación real a Gestión de inventario; no consulta pedidos/clientes ni ofrece accesos a pedidos o Panel de roles. |
| Refresh | Recarga conserva la sesión; GET /api/auth/me responde HTTP 200 y el Dashboard termina de cargar todas las fuentes esperadas. |
| Logout | Cerrar sesión elimina el estado de sesión del navegador y vuelve a Login. |
| Responsive | Viewports 1366 y 390 px; se comprueba que documentElement.scrollWidth no supera innerWidth y que las acciones esenciales siguen visibles. |
| Error parcial controlado | CONTROLLED FAILURE SCENARIO — NOT REAL BACKEND FAILURE. Playwright intercepta únicamente GET /api/inventory/planchas con 503; las otras fuentes llegan al backend real y conservan datos. Se verifica alerta y datos parciales. |

La ejecución presentó problemas únicamente en aserciones del harness: el manejador global de rutas debía dejar continuar al handler específico de 503 y la aserción debía comprobar el mensaje accesible dentro de role=alert, que es la semántica implementada por la UI. Se corrigió el E2E, sin modificar producto, quitar validaciones del flujo real, añadir esperas arbitrarias ni ocultar errores. La ejecución completa posterior pasó 7/7.

## Regresión final

Resultados ejecutados después de los ajustes del spec:

| Comando desde frontend | Resultado |
|---|---|
| npm.cmd run test:component -- src/features/dashboard/__tests__ | 73/73, 5 archivos |
| npm.cmd run test:unit | 124/124, 0 fallos, 0 cancelados, 0 omitidos |
| npm.cmd run test:component | 369/369, 31 archivos |
| npm.cmd run lint | PASS, exit 0 |
| npm.cmd run build | PASS, 1966 módulos transformados |
| Playwright Dashboard real | 7/7, 0 fallidos, omitidos o flaky |

Vitest emitió una recomendación informativa sobre el coste de crear entornos jsdom; la suite terminó correctamente. Node emitió una advertencia de entorno de color durante Playwright; el proceso terminó con exit 0 y siete casos pasados. No se modificó código productivo ni backend durante T3. No se ejecutó la suite E2E completa del repositorio ni CI remoto; no eran requisito para cerrar el flujo específico.

## Capturas de producto

Se revisaron las once imágenes finales. Son capturas del navegador Playwright real con respuestas de Supabase de desarrollo. Las máscaras neutras cubren nombre/identificador de las cuentas sintéticas y nombres de clientes; no cambian ni simulan los datos comprobados por el test. La sesión conserva visible el rol. La imagen de error parcial incluye una banda de anotación fuera de la UI capturada para advertir que el fallo fue controlado. Las capturas muestran estados completos, sin spinners accidentales, contraseñas, tokens o headers.

| Archivo | Contenido |
|---|---|
| t3/screenshots/dashboard-administrador.png | Inicio y datos reales con Administrador; pedido/cliente y usuario redaccionados. |
| t3/screenshots/dashboard-administrador-navegacion.png | Módulo real Gestión de inventario tras acceso permitido de Administrador. |
| t3/screenshots/dashboard-operario.png | Inicio y datos disponibles para Operario. |
| t3/screenshots/dashboard-operario-navegacion.png | Módulo real Gestión de inventario tras acceso permitido de Operario. |
| t3/screenshots/dashboard-almacenero.png | Inicio con resumen limitado a Inventario para Almacenero. |
| t3/screenshots/dashboard-almacenero-inventario.png | Módulo real Gestión de inventario y tabla cargada. |
| t3/screenshots/dashboard-refresh-session.png | Dashboard recuperado después de refresh con sesión real validada. |
| t3/screenshots/dashboard-logout.png | Login después de logout, sin datos de sesión. |
| t3/screenshots/dashboard-desktop-1366.png | Dashboard real en desktop 1366 px. |
| t3/screenshots/dashboard-mobile-390.png | Dashboard real a 390 px, con acciones apiladas y legibles. |
| t3/screenshots/dashboard-partial-error.png | CONTROLLED FAILURE SCENARIO — NOT REAL BACKEND FAILURE; datos válidos conservados junto a feedback parcial. |

Las capturas de terminal renderizadas desde logs están en t3/terminal/ y se etiquetan como salidas renderizadas, no como fotografías nativas de terminal. El renderer y sus fuentes publicables están en t3/playwright/ y t3/logs/. Las capturas 01–12 preservan el precheck, limitación inicial, regresiones, salud del backend, diff y el descubrimiento inicial con skips; el skip inicial se muestra como historial, nunca como PASS. Las capturas 03–08 se regeneraron desde resúmenes finales para excluir títulos de pruebas no relacionados y conservar únicamente resultados legibles.

| Captura de terminal | Fuente/resultados representados |
|---|---|
| t3/terminal/01-git-precheck.png | Rama/base/working tree inicial, en salida saneada. |
| t3/terminal/02-backend-health.png | Primer intento del agente que no pudo iniciar Python desde su contexto. |
| t3/terminal/03-dashboard-tests.png | 73 pruebas Dashboard. |
| t3/terminal/04-unit-tests.png | 124 unitarias. |
| t3/terminal/05-component-tests.png | 369 componentes. |
| t3/terminal/06-lint.png | Lint PASS. |
| t3/terminal/07-build.png | Build PASS y 1966 módulos. |
| t3/terminal/08-e2e-real.png | Siete E2E finales PASS, sin skips ni fallos. |
| t3/terminal/09-diff-check.png | git diff --check antes de commit. |
| t3/terminal/10-git-status-before-commit.png | Estado de trabajo preparado para la revisión documental, antes del commit. |
| t3/terminal/11-backend-health-recheck.png | Backend existente: OpenAPI/live/ready HTTP 200. |
| t3/terminal/12-dashboard-e2e-skipped.png | Ejecución inicial histórica con credenciales ausentes; no es resultado final. |

El commit de pruebas que contiene el spec Playwright y la configuración dedicada es cd5ac07 (test(TA-DASHBOARD-001): validar flujo e2e del dashboard). El commit documental separado reúne esta evidencia, las capturas y la actualización SDD.

## Matriz de aceptación CA-01…CA-18

| CA | Estado | Evidencia |
|---|---|---|
| CA-01 | VERIFIED | Inicio post-login real para los tres roles; pruebas App/navigation. |
| CA-02 | VERIFIED | Sidebar Inicio activo y navegable; aserciones E2E y pruebas de navegación. |
| CA-03 | VERIFIED | Login real de Administrador, Operario y Almacenero; protección/sesión en pruebas de aplicación. |
| CA-04 | VERIFIED | Fuentes y accesos por rol; E2E confirma datos/accesos y exclusiones para Almacenero; cobertura de permisos component. |
| CA-05 | VERIFIED | Las respuestas de las fuentes y valores mostrados proceden de API/backend real; sin fallback ficticio. |
| CA-06 | VERIFIED | Resumen de planchas desde API real y captura de Dashboard/Inventario. |
| CA-07 | VERIFIED | Resumen de retazos desde API real y captura de Dashboard. |
| CA-08 | VERIFIED | Contadores/listado real de pedidos pendientes y en optimización para los roles autorizados. |
| CA-09 | VERIFIED | Clientes se consultan para Administrador/Operario; la fuente no se solicita para Almacenero. Identidades se redaccionan en capturas. |
| CA-10 | VERIFIED_CONDITIONAL | Se conserva el nombre “Pedidos en orden de gestión”; orden por reglas/fechas/ID reales del contrato, sin afirmar recencia global. |
| CA-11 | VERIFIED | Los resúmenes corresponden a las respuestas de inventario y no mutan su fuente. |
| CA-12 | VERIFIED | Accesos rápidos se dirigen a módulos existentes y autorizados; navegación real probada por rol. |
| CA-13 | VERIFIED | Inspección de alcance y presentación: no se añaden métricas futuras, gráficas, optimización ni alertas inventadas. |
| CA-14 | VERIFIED | Estados loading probados por componentes; E2E espera respuestas antes de capturar datos como resultado cargado. |
| CA-15 | VERIFIED | Estados empty diferenciados de error en pruebas de modelo/componentes existentes. |
| CA-16 | VERIFIED | Pruebas component de errores parciales y escenario E2E de falla controlada, claramente identificado. |
| CA-17 | VERIFIED | Semántica de botones/foco/Enter/Space probada por RTL; CSS respeta prefers-reduced-motion. |
| CA-18 | VERIFIED | E2E real cubre login, navegación, refresh con /api/auth/me, logout y responsive a 1366/390 sin overflow. |

La cobertura de error parcial es un fallo intencional interceptado por Playwright, no una caída real de backend. No se afirma certificación WCAG ni una ejecución en CI.

## Estado SDD

- SPEC: **Verified**. Reviewer: **Fabricio Danniel Aguilar Chávez**. CA-10 permanece condicional por semántica de orden de gestión.
- PLAN: **Approved**. Reviewer: **Andro Joseph Quispe Cesias**. Las tareas T1/T2/T3 figuran completadas.
- PR: **Pending**; no se inventa número.
- No se hizo push, PR, merge ni deploy.

## Despliegue futuro — inspección de configuración

- **Frontend:** GitHub Pages está configurado en .github/workflows/deploy-pages.yml para integration/sprint-01, tras el CI reutilizable. Build: npm ci, npm run build:staging, npm run check:staging. Salida: frontend/dist; base /optimizador-vidrio/. Requiere VITE_API_URL con URL HTTPS aprobada.
- **Backend:** existe Procfile para Uvicorn con host 0.0.0.0 y PORT del proveedor. La documentación registra Heroku newglass-api-staging con despliegue manual; no se consultó un panel remoto. Configuración necesaria: DATABASE_URL, SECRET_KEY, CORS_ORIGINS; TOKEN_MINUTOS tiene default y Heroku aporta PORT.
- **CORS:** CORS_ORIGINS deberá autorizar el origen HTTPS real de GitHub Pages, sin subpath.
- **Supabase:** backend requiere DATABASE_URL y los secretos de runtime ya descritos; no se registran valores.
- No se configuró proveedor ni se desplegó. Después de merge, confirmar workflow/CI y aprobación humana antes de iniciar el despliegue.

Temporary E2E accounts remain active for post-deployment smoke validation and must be disabled/removed after deployment verification.
