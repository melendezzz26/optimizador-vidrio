# TA-DASHBOARD-001-T1 — Navegación, sesión y datos

Fecha: 14/10/2026. Rama: `feature/TA-DASHBOARD-001`. Precheck: árbol limpio, HEAD SPEC `835c30d`, ancestro/base integrada `86972fd` con PR #47. No se incorporó el cierre documental independiente de HU-015. PLAN/TASKS: [PLAN-TA-DASHBOARD-001](../../../specs/PLAN-TA-DASHBOARD-001-dashboard-inicial.md), tareas §12; commit documental `d912c6a`. SPEC permanece Approved; PLAN Draft, sin atribuir una nueva aprobación humana técnica.

## Implementación exclusiva T1

- `App` conserva navegación por estado y añade `dashboard` como entrada inicial; Sidebar «Inicio» tiene estado activo/aria-current. No se crea una URL `/dashboard` ni se modifica el subpath Pages. Se conservan Orders, Inventory, Users y Optimization.
- Se reutilizan `useSession`, sessionStorage/`optimizador.auth`, LoginForm, SessionBar, POST login y GET me. Logout/401 desmontan el Dashboard y eliminan sesión; relogin desde otro módulo vuelve a Inicio. No hay autenticación paralela.
- `dashboardModel.js` define fuentes y accesos para roles reales; `dashboardApi.js` compone clientes existentes; `useDashboard.js` carga por fuente y descarta respuestas obsoletas por usuario/rol/token/ronda/unmount. `DashboardPage.jsx` tiene solo shell y presentación textual mínima con componentes compartidos, sin CSS, tarjetas o acabado visual nuevos.
- Inventory permite token/signal opcionales en GET planchas/retazos y propaga cancelación. Clients añade GET sin filtros y conserva HTTP status de errores; los mensajes y operaciones existentes se mantienen. Orders y shared API transport se reutilizan sin cambios.
- Backend, esquema, migraciones, dependencias, SPEC y HU-015 permanecen sin cambios.

## Fuentes y semántica

| Fuente real | Disponibilidad / transformación |
|---|---|
| GET `/api/inventory/planchas` | AVAILABLE; resumen AVAILABLE_WITH_CLIENT_SIDE_DERIVATION: registros totales, activos con cantidad positiva y suma de unidades. No se afirma stock compatible. |
| GET `/api/inventory/retazos` | AVAILABLE; resumen AVAILABLE_WITH_CLIENT_SIDE_DERIVATION: registros totales/activos, unitarios. |
| GET `/api/orders?estado=PENDIENTE&page=1&limit=1` | AVAILABLE; contador procede de `total`, no de la longitud de página. |
| GET `/api/orders?estado=EN_OPTIMIZACION&page=1&limit=1` | AVAILABLE; mismo contrato/estado real. |
| GET `/api/orders?page=1&limit=5` | AVAILABLE; página en orden backend: no cancelados primero, fecha/ID DESC. Se conserva ese orden y alcance; no es cronología global. |
| GET `/api/clients` | AVAILABLE; resumen AVAILABLE_WITH_CLIENT_SIDE_DERIVATION: registros totales/activos. No conserva PII en el estado transformado. |

Inventory se consulta para los tres roles; pedidos/clientes solo para Administrador/Operario. Almacenero no provoca esas consultas. Accesos rápidos preparados para T2: Inventory/Orders/Users conforme a permisos actuales; no se añadió ejecución de optimización. NOT_AVAILABLE: agregado Dashboard y cronología global en una sola página; no son necesarios y no se implementan. No falta ninguna fuente imprescindible de los CA.

Cada bloque tiene loading/success/empty/error y data null en carga/fallo. Globalmente se distingue partial-error, error total y vacío válido. Un error no crea un cero; fuentes exitosas se conservan. Refresh explícito inicia otra ronda; 401 retira todos los datos/aborta pendientes y usa logout global una vez; 403 permanece como error del bloque. Respuestas inválidas o con datos de conteo no válidos son errores recuperables.

## Pruebas ejecutadas

Desde `frontend/`, con HTTP simulado exclusivamente dentro de unit/component; **no se presenta como prueba real contra API/Supabase ni como E2E**:

| Comando | Resultado final real |
|---|---|
| `npm.cmd run test:component -- src/features/dashboard/__tests__ src/shared/__tests__/sidebarNavigation.test.jsx src/shared/__tests__/stagingNavigation.test.jsx` | 59 passed en 6 archivos, 0 fallos; 5.93 s. Incluye 53 pruebas nuevas y 6 de navegación existente. |
| `npm.cmd run test:unit` | 124 passed, 0 failed/cancelled/skipped. |
| `npm.cmd run test:component` | 349 passed en 30 archivos, 0 fallos; 27.58 s. Incluye regresión Inventory, Clients/Orders, Users, Optimization y navegación. |
| `npm.cmd run lint` | PASS, exit 0. |
| `npm.cmd run build` | PASS, exit 0; Vite 8.3.1, 2.70 s. |
| `npm.cmd run test:e2e -- --list --reporter=list` | Colección únicamente: 52 tests en 6 archivos, exit 0. No ejecuta navegador ni cuenta como E2E PASS. |
| `git diff --check` / staged check | PASS. |

Pruebas nuevas: dashboardModel (roles, registros/unidades, total paginado, orden/proyección, DTO inválido y estados), dashboardApi (GET/filtros/token/signal/401/cancelación), useDashboard (cargas independientes, empty, parcial/total, retry, 401/403, contexto y unmount), DashboardNavigation (App/Login/sesión reales con HTTP mock: tres roles, restauración/rol vigente, teclado/subpath, logout/relogin y 401). No se añadió dependencia de pruebas.

Hallazgo de compatibilidad: HU-007/Orders y HU-012 E2E suponían Orders activo al terminar login. Se añadió únicamente la comprobación de Inicio activo y la navegación explícita a Pedidos; se conservaron sus cuerpos/aserciones. Solo se validó colección; la ejecución real queda en T3. No se registraron pruebas T1 fallidas ni impedimentos de entorno en estas corridas. No se ejecutó backend por no estar afectado.

## Estado parcial de los 18 CA

| CA | Estado T1 | Alcance real / pendiente |
|---|---|---|
| CA-01 | DONE_IN_T1 | Login/relogin → Inicio, probado en componentes. |
| CA-02 | DONE_IN_T1 | Sidebar Inicio real, activo y navegación por teclado/subpath. |
| CA-03 | DONE_IN_T1 | Tres roles autenticados; sin sesión no monta ni consulta datos. |
| CA-04 | PARTIAL | Fuentes y navegación restringidas por rol; presentación final de accesos en T2. |
| CA-05 | PARTIAL | GET reales y modelo sin valores ficticios; integración real/visual final T2/T3. |
| CA-06 | PENDING_T2 | Resumen planchas implementado/probado; composición final pendiente. |
| CA-07 | PENDING_T2 | Resumen retazos implementado/probado; composición final pendiente. |
| CA-08 | PARTIAL | Totales por estados reales preparados y presentación textual mínima; UI final pendiente. |
| CA-09 | PARTIAL | Fuente Clients real, conteo/protección por rol; UI final opcional pendiente. |
| CA-10 | PENDING_T2 | Items proyectados y orden/alcance documentados; listado visual final pendiente. |
| CA-11 | PARTIAL | Transformaciones de inventario coherentes/probadas; presentación final pendiente. |
| CA-12 | PENDING_T2 | Modelo de accesos reales listo; botones rápidos finales pendientes. |
| CA-13 | DONE_IN_T1 | No hay métricas futuras, heurísticas, gráficas ni mutaciones. Se preserva en T2/T3. |
| CA-14 | PARTIAL | Estado/carga textual mínima sin cifras falsas; diseño final T2. |
| CA-15 | PARTIAL | Empty de respuestas válidas diferenciado de error; diseño final T2. |
| CA-16 | PARTIAL | Errores independientes, parcial/total y retry probados; composición final T2. |
| CA-17 | PENDING_T2 | Controles básicos heredados; auditoría de UI final/teclado/reduced motion pendiente. |
| CA-18 | PENDING_T3 | Sesión/refresh/logout comprobados en componentes; responsive final T2 y E2E real T3. |

## Pendientes

T2 debe completar exclusivamente la composición visual sobre este modelo: resúmenes, listado en orden de gestión y alcance visible, accesos rápidos, estados por bloque y responsive/accesibilidad/reduced motion con pruebas de presentación. T3 validará flujo real, E2E y evidencia final, revisará los 18 CA y preparará el PR cuando se autorice. No se marca la SPEC Verified, no se generan capturas ni se usan datos reales de BD durante T1. Sin push, PR, merge o deploy.
