# PLAN-TA-DASHBOARD-001 — Dashboard inicial

## Información general

| Campo | Valor |
|---|---|
| Estado del plan | **Approved** |
| SPEC de referencia | [SPEC-TA-DASHBOARD-001-dashboard-inicial.md](SPEC-TA-DASHBOARD-001-dashboard-inicial.md), **Approved**, 18 CA |
| Autor | Fabricio Melendez Quezada |
| Reviewer de la SPEC | Fabricio Danniel Aguilar Chávez |
| Reviewer del plan | Andro Joseph Quispe Cesias |
| Base de planificación | `835c30d`, sobre `origin/integration/sprint-01` en `86972fd` (PR #47 integrado) |
| Rama | `feature/TA-DASHBOARD-001` |
| Fecha | 14/10/2026 |
| Autorización de T1 | Implementación de navegación/datos solicitada expresamente por el equipo junto con este PLAN; no implica aprobación humana técnica del documento. |

## 1. Objetivo técnico y convención

Añadir la vista autenticada inicial y un modelo de consulta que componga contratos reales, conservando navegación, sesión, permisos, transporte y estilo existentes. T1 entrega una pantalla funcional mínima; T2 compone la interfaz completa y T3 valida integración/E2E/evidencia final.

`docs/specs/` usa archivos planos. El único PLAN previo, HU-015, reúne sus tareas dentro del mismo documento (§10); no existe convención separada de `tasks.md`. Se reutiliza ese patrón: **TASKS de Dashboard están en §12 de este PLAN**, sin crear directorios o documentos de tareas paralelos. La SPEC Approved permanece intacta. El commit documental independiente de cierre HU-015 no forma parte de esta rama.

## 2. Auditoría del frontend

- Entrypoint `frontend/src/main.jsx`: React StrictMode → App. Features planas en `src/features/`; utilidades/layout/feedback en `src/shared/`.
- No hay React Router ni tabla URL de rutas. App selecciona módulos mediante `view`/`allowedViews`; `NavigationContext` aporta `onNavigate`/`availableViews`. Vite conserva el subpath Pages en staging. No se introduce `/dashboard` ni se cambia el pathname.
- App inicialmente selecciona `orders`; Almacenero obtiene Inventory como fallback. T1 cambia la entrada común a la vista `dashboard`, rotulada **Inicio**.
- `AppShell`, Sidebar, `PageHeader`, `PageCard`, `ActionBar`, LoadingState/EmptyState/FeedbackMessage, `ui.css`/`tokens.css` son reutilizables. Sidebar usa botones, `aria-current`, estado activo y teclado nativo; SessionBar conserva identidad/rol/logout en el header.
- `useSession` usa `authApi`: `sessionStorage` bajo `optimizador.auth`, POST login, GET me al restaurar y eliminación al cerrar sesión. App no monta páginas protegidas mientras comprueba sesión o sin sesión. El rol vigente es `session.usuario.rol`.
- Roles exactos: `Administrador`, `Almacenero`, `Operario`. Helpers frontend reflejan permisos; backend valida rol vigente por solicitud.
- `shared/apiUrl.js` conserva `VITE_API_URL`; `shared/apiRequest.js` es transporte común para Orders/Optimization. Inventory y Clients tienen clientes existentes propios. No se migra globalmente su transporte por conveniencia.
- Pruebas: `test:unit` (node:test), `test:component` (Vitest + RTL/jsdom), lint ESLint, build Vite y Playwright E2E. Solo unit/component/lint/build se ejecutan en T1; E2E final queda en T3.

## 3. Contratos backend auditados y decisión

Todos los GET requieren sesión Bearer válida. Son listados, no agregados de Dashboard.

| Capacidad / método y ruta | Permiso/roles | Respuesta, filtros y orden | Clasificación y uso |
|---|---|---|---|
| POST `/api/auth/login`; GET `/api/auth/me` | Login público; me autenticado | Login: token/usuario; me: ID, username, nombre, rol vigente. Sin paginación. | AVAILABLE; se reutiliza sesión, sin nuevas llamadas paralelas de identidad. |
| GET `/api/users`, `/api/users/roles` | GESTIONAR_USUARIOS; Administrador | Listas UserResponse/RoleResponse; usuario incluye estado y rol. Sin filtros/paginación/fecha en UserResponse. | AVAILABLE; solo navegación al módulo, no se carga ni agrega un KPI de usuarios. |
| GET `/api/inventory/planchas` | CONSULTAR_STOCK; tres roles | Lista completa PlanchaResponse: ID, cantidad, estado bool, medidas/espesor, tipo, fecha_registro. Sin filtros/paginación/orden temporal contractual. | Registros AVAILABLE; resumen AVAILABLE_WITH_CLIENT_SIDE_DERIVATION. |
| GET `/api/inventory/retazos` | CONSULTAR_STOCK; tres roles | Lista completa RetazoResponse: ID, código, estado bool, geometría, área, espesor, tipo, fecha_registro, origen nullable. Sin cantidad/filtros/paginación. | Registros AVAILABLE; resumen AVAILABLE_WITH_CLIENT_SIDE_DERIVATION. |
| GET `/api/orders` | GESTIONAR_PEDIDOS; Administrador/Operario | items/total/page/limit/total_pages. Filtros estado/cliente/fecha, page≥1, limit 1–100. Item: id_pedido, fecha_registro, estado, cliente. Orden: no CANCELADO primero, fecha DESC, ID DESC. | AVAILABLE; totales reales PENDIENTE y EN_OPTIMIZACION mediante filtros backend. |
| GET `/api/clients` | GESTIONAR_PEDIDOS; Administrador/Operario | Lista ClientResponse: ID, nombre, estado, fecha, documento/teléfono. Filtros document/query; sin filtro estado/paginación; orden actual ID ASC. | Registros AVAILABLE; conteo AVAILABLE_WITH_CLIENT_SIDE_DERIVATION; no conservar PII innecesaria en el modelo. |

Fuentes: routers/schemas de Authentication, Users, Inventory, Orders y Clients; permisos en `backend/app/core/permissions.py`; orden/paginación en Orders application/use_cases e infrastructure/repositories. Los cinco estados Orders ya incluyen PENDIENTE/EN_OPTIMIZACION; no se inventan estados.

**Backend: NO MODIFICADO.** Todos los datos imprescindibles existen; no se necesita agregado, migración ni cambio de esquema. NOT_AVAILABLE: endpoint agregado Dashboard, cronología global de recientes en una sola página sin prioridad de estado, métricas futuras/alertas/compatibilidad. No son capacidades que se agreguen en este PBI. Un agregado futuro solo sería admisible con justificación y revisión previa conforme a SPEC RN-10.

## 4. Arquitectura y archivos previstos

Nuevo código dentro de `frontend/src/features/dashboard/`, siguiendo features planas:

| Archivo previsto | Responsabilidad |
|---|---|
| `dashboardApi.js` | Componer GET existentes; ninguna llamada HTTP dentro de componentes. |
| `dashboardModel.js` | Transformaciones de transporte a resúmenes; fuentes/accesos por rol; validación proporcionada del DTO utilizado. |
| `useDashboard.js` | Carga independiente, refresh explícito, estados por fuente, sesión/abort y descarte de resultados obsoletos. |
| `DashboardPage.jsx`, `index.js` | Montaje mínimo T1 con AppShell/feedback; composición final T2. Sin CSS nuevo en T1. |
| `__tests__/` | Comportamiento de datos, clientes, página mínima y App/sesión/navegación. |

Extensiones localizadas: App, Sidebar y helper público `canViewDashboard` de Authentication. Inventory: permitir signal/token opcionales en GET planchas/retazos sin cambiar firmas previas ni mutaciones. Clients: exponer listado sin filtro y conservar HTTP status en sus errores para manejar 401; mensajes previos intactos. Orders se reutiliza sin modificar. No se instala ninguna dependencia.

## 5. Navegación, sesión y roles

`dashboard` es un identificador de vista interna, no una ruta URL nueva. Se añade a allowedViews para los tres roles reconocidos y al Sidebar como Inicio. App mantiene Login/comprobación fuera del contenido protegido. Login exitoso reinicia la vista a dashboard incluso tras logout/relogin desde otro módulo; refresh con sesión válida entra a Inicio una vez confirmado GET me. Logout y 401 usan signOut existente y desmontan datos protegidos.

Permisos de datos: Inventory para los tres roles; Orders/Clients solo Administrador/Operario. Modelo de accesos rápidos T2: Inventory, Orders y Users únicamente cuando sus helpers reales lo permitan; ninguna acción de optimización y ningún destino Clientes inexistente. No se concede acceso por ocultamiento ni se hace fetch restringido para Almacenero.

## 6. Fuentes y transformación

Se consultan en paralelo seis fuentes independientes cuando el rol lo permite:

1. Planchas: getPlanchas existente.
2. Retazos: getRetazos existente.
3. Pedidos PENDIENTE: listOrders con filtro backend y página limitada; `total` es el contador, nunca items.length.
4. Pedidos EN_OPTIMIZACION: mismo contrato filtrado.
5. Primera página de pedidos en **orden de gestión**: no cancelados primero, fecha/ID descendentes; cinco registros como tamaño de presentación, no como cantidad operativa hardcodeada. T2 explicará el alcance, sin llamarla cronología global.
6. Clientes: listado real sin filtros; solo resumen total/activos, sin nombres/documentos/teléfonos en estado de Dashboard.

Modelo de presentación propuesto:

- Planchas: total de registros, registros activos con unidades (`estado===true && cantidad>0`) y suma de sus unidades; etiqueta exacta, sin afirmar compatibilidad/disponibilidad para un pedido.
- Retazos: registros totales y activos; retazo unitario, sin cantidad inventada.
- Pedidos por estado: total HTTP real; la lista de una página no cambia ese significado.
- Pedidos en orden de gestión: items proyectados a ID, fecha, estado y cliente visible, junto con página/tamaño/total y descripción del orden; se mantiene el orden backend.
- Clientes: registros totales/activos a partir de lista completa real; cero solo después de respuesta válida vacía.
- Accesos: IDs/labels de módulos existentes permitidos; no mezclados con cifras ni permisos backend nuevos.

Verificar estructura/tipos de los campos realmente usados y números enteros seguros no negativos para conteos; una respuesta inesperada es error, nunca cero. No se normalizan geometrías ni se calculan métricas del optimizador.

## 7. Carga, errores parciales y obsolescencia

Cada fuente tiene `{status, data, error}`: loading con data null; success con DTO transformado; empty con respuesta válida vacía; error con data null. Fuentes sin permiso se omiten, no se muestran como error ni cero. El resumen global distingue loading, success, empty, partial-error y error; puede conservar datos válidos mientras otra consulta está pendiente o falla.

Sin polling, requests masivos de todas las páginas ni reintentos automáticos. Refresh explícito invalida resultados previos de la ronda y vuelve a consultar. AbortController y guardas de contexto/actividad evitan publicaciones posteriores a cambio de usuario/rol/token, refresh o unmount. Nunca mostrar datos del contexto anterior durante una nueva sesión.

401: llamar signOut existente una sola vez, abortar solicitudes restantes y retirar todos los datos protegidos. 403: error seguro del bloque, sin datos previos ni ampliar permisos; otras fuentes autorizadas siguen funcionando. Error de red/500/respuesta inválida: mensaje seguro recuperable, sin SQL/stack trace. No sustituir fallo por empty ni cero.

## 8. UI prevista para T2

T1: PageHeader Inicio, toolbar SessionBar, feedback compartido y lista textual mínima de fuentes/resúmenes; refresh sencillo para validar la capa. No tarjetas KPI finales, gráficos, animaciones ni nuevos estilos.

T2: jerarquía título → resumen → contenido → accesos, resúmenes con semántica de §6, pedidos en orden de gestión, información de inventario y accesos rápidos por rol. Loading/empty/error/partial-error por bloque; no PII innecesaria ni cifras de ejemplo.

Reutilizar tokens/layout y controles nativos; desktop-first, adaptación sin perder acciones esenciales, labels/nombres accesibles, foco visible, teclado y feedback textual. Microinteracciones discretas y prefers-reduced-motion. No rediseñar Sidebar ni introducir Router, gráficas o librerías nuevas.

## 9. Estrategia de pruebas

T1: modelo (registros vs unidades, inactivos/cero, totales paginados, orden y proyección, DTO inválido); composición API (GET/filtros/auth/signal/status); hook (cargas independientes, vacío, parcial/total, retry, 401/403, contexto y unmount); App real con HTTP mock (Login → Inicio, recuperación sesión, logout/relogin, subpath, roles y Sidebar). Fixtures únicamente dentro de tests.

Comandos reales desde frontend: focalizadas con `npm.cmd run test:component -- <rutas>`, `npm.cmd run test:unit`, `npm.cmd run test:component`, `npm.cmd run lint`, `npm.cmd run build`. No usar npm test en T1 porque encadena E2E. No backend tests si backend permanece intacto. Regresión de Inventory/Clients/Orders/sesión/navegación incluida en componentes completa.

T3: Playwright existente con navegador/backend/datos reales controlados; login de cada rol → Inicio → información real → función permitida; refresh, logout, permisos, teclado/responsive. No se declara aprobado por listar tests ni por mocks. Mantener seguridad/cleanup y distinguir skips de PASS.

## 10. Riesgos y fuera de alcance

- Inventory/Clients devuelven listas completas: costo crece con volumen; no inventar paginación o agregados. Evaluar necesidad solo si existe evidencia técnica.
- No hay snapshot transaccional entre fuentes; rotular alcance y evitar prometer tiempo real.
- Orders prioriza no cancelados: no presentar los primeros cinco como los cinco últimos absolutos.
- Clientes no conserva status en errores actualmente; extensión mínima para 401 debe mantener mensajes/contratos de consumidores existentes.
- Cambio del destino inicial modifica expectativas de pruebas de navegación: actualizar sus entradas al módulo explícitamente, sin eliminar aserciones anteriores.
- HU-007/Orders y HU-012 E2E asumían Orders activo justo después de login. T1 adapta únicamente su entrada a Inicio → Pedidos, conservando cuerpos/aserciones; ejecución real y cierre E2E permanecen pendientes de T3.
- La aprobación humana del PLAN quedó confirmada por Andro Joseph Quispe Cesias; el estado vigente es Approved. La evidencia T3 registra la finalización técnica sin cambiar al reviewer de la SPEC.

Fuera de alcance: gráficos, alertas/umbrales, métricas futuras/M1/M2, FF/BF/WF, ejecución de optimización, stock compatible, placement, merma/aprovechamiento, mutaciones, migraciones, dashboard final T2, E2E/evidencia final T3, push/PR/merge/deploy.

## 11. Definition of Done técnica

T1: entrada autenticada real por estado, Inicio para tres roles, sesión existente preservada, fuentes/transformaciones comprobadas, errores aislados y sin fallback falso, pruebas correspondientes y regresión frontend/lint/build ejecutadas, backend/SPEC intactos y commit local limpio. T2/T3 siguen pendientes; SPEC continúa Approved.

PBI completo posteriormente: UI final T2, 18 CA contrastados, integración/regresión y E2E real T3, evidencia reproducible y revisión humana/PR. No anticipar Verified ni resultados de tareas futuras.

## 12. TASKS — T1/T2/T3

### T1 — Navegación + datos

- [x] Auditar rama/base, SPEC completa, navegación/sesión/roles y contratos HTTP.
- [x] Crear este PLAN y la división de tareas sin atribuir aprobación humana nueva.
- [x] Añadir vista dashboard protegida, Inicio en Sidebar, entrada post-login/restauración y logout/relogin.
- [x] Reutilizar GET existentes, extender opciones/errores mínimos y componer fuentes por permisos.
- [x] Transformar resúmenes con alcance real; implementar loading/empty/success/error/partial-error sin valores ficticios.
- [x] Descartar respuestas obsoletas y resolver 401 mediante sesión global.
- [x] Añadir pantalla mínima y pruebas de modelo/API/hook/App; ejecutar focalizadas, unit/component, lint/build/diff check.
- [x] Registrar resultados reales y estado de 18 CA; entrega mediante commit local técnico.

**Cierre verificable:** infraestructura de navegación/datos funcional y probada; no UI final ni E2E/capturas finales. Evidencia técnica T1 en `docs/evidence/sprint-01/TA-DASHBOARD-001/t1-navegacion-datos.md` cuando exista.

### T2 — Interfaz Dashboard

- [x] Componer la UI final con resúmenes permitidos, pedidos en orden documentado, inventario y accesos rápidos por rol.
- [x] Presentar loading/empty/error/partial-error sin números ficticios y con recuperación comprensible.
- [x] Verificar responsive, teclado, foco, reduced motion y semántica accesible; reutilizar componentes/tokens.
- [x] Pruebas de componente de presentación y permisos; regresión del bloque y lint/build aplicables.

**Dependencia:** T1 estable. **Cierre:** interfaz completa sobre el modelo real; no atribuir todavía E2E/evidencia final.

### T3 — Integración + E2E + evidencia

- [x] Auditar integración final y regresión frontend (Dashboard targeted, unit, component, lint y build); backend no fue afectado.
- [x] E2E real login → Dashboard → función permitida, información real, refresh, logout y permisos; sin mocks en los happy paths.
- [x] Contrastar individualmente los 18 CA, responsive/teclado y seguridad; corregir problemas reales de aserciones con regresión.
- [x] Generar evidencia auténtica y resultados reproducibles; mantener únicamente las cuentas sintéticas autorizadas para el smoke posterior al despliegue.
- [x] Actualizar la SPEC a Verified después de validar los CA y la regresión, conservando a Fabricio Danniel Aguilar Chávez como reviewer y PR Pending.

**Estado T3:** siete E2E pasaron en Chromium 153.0.8010.12 contra Vite, el backend existente y la base Supabase de desarrollo configurada. Se verificaron los tres roles, navegación a Inventario, refresh con `/api/auth/me`, logout, responsive 1366/390 y un fallo parcial controlado (no una falla real del backend). Regresión final: 73 Dashboard, 124 unit, 369 componentes, lint y build PASS. Las capturas de producto redaccionan identidades; las cuentas E2E sintéticas quedan temporalmente activas para smoke posterior al despliegue. La matriz CA y la decisión documental constan en [evidencia T3](../evidence/sprint-01/TA-DASHBOARD-001/t3-integracion-e2e-cierre.md).

**Dependencias:** T1/T2 completos. **Cierre:** flujo integrado probado, evidencia y revisión final; publicación solo cuando se autorice.

## Historial del plan

- 14/10/2026 — Draft: planificación y TASKS derivadas de SPEC Approved `835c30d` y contratos de la base integrada `86972fd`. Backend innecesario; tareas en §12 conforme al PLAN previo. La implementación T1 fue solicitada expresamente; no se inventa aprobación técnica del PLAN ni se marca el PBI completo.
- 14/10/2026 — T1 implementada y comprobada; estado documental del PLAN sigue Draft, revisión técnica humana pendiente. Resultados y matriz CA parcial en [evidencia técnica T1](../evidence/sprint-01/TA-DASHBOARD-001/t1-navegacion-datos.md). T2/T3 siguen sin ejecutar; SPEC conserva Approved.
- 14/10/2026 — T2 implementada y comprobada mediante componentes y una inspección técnica aislada de layout con HTTP simulado, sin E2E real ni evidencia final del PBI. Resultados y matriz CA en [registro T2](../evidence/sprint-01/TA-DASHBOARD-001/t2-interfaz-dashboard.md). PLAN sigue Draft: **Human PLAN approval still pending**. SPEC Approved intacta; T3 pendiente.
- 2026-10-14 — T3 parcial: 73 Dashboard component tests, 124 unit, 369 component, lint y build PASS. Playwright descubrió 52 pruebas existentes en 6 archivos, pero ninguna spec Dashboard. El backend Supabase no inició porque el intérprete base de `backend/venv` no está disponible en este entorno; por ello no se ejecutó E2E real ni se actualizó la SPEC. Evidencia de bloqueo y salidas en [registro T3](../evidence/sprint-01/TA-DASHBOARD-001/t3-integracion-e2e-cierre.md). PLAN continúa Draft; **Human PLAN approval pending**.
- 2026-10-14 — Actualización: el usuario confirmó aprobación del PLAN por Andro Joseph Quispe Cesias; estado vigente **Approved**. Reanudación T3 con backend iniciado por el usuario: `/openapi.json`, `/health/live`, `/health/ready` y Vite devolvieron HTTP 200. Se creó la spec E2E Dashboard (7 escenarios), colección exitosa y ejecución explícita resultó en 7 skipped por ausencia de credenciales, no PASS. Regresión: 73 Dashboard component, 124 unit, 369 component, lint y build PASS. E2E autenticado, capturas del producto y cierre de CA-18 siguen pendientes; SPEC conserva Approved.
- 2026-10-14 — Cierre T3: el backend existente iniciado por el usuario se mantuvo en ejecución. Tras la autorización expresa se crearon tres cuentas sintéticas temporales por el caso de uso/repositorio de aplicación y el helper real de hashing; se verificaron logins y sesiones sin revelar credenciales. Los siete E2E reales pasaron, con capturas revisadas y redaccionadas. La regresión final pasó (73 Dashboard, 124 unit, 369 componentes, lint, build). Los 18 CA se contrastaron; CA-10 continúa VERIFIED_CONDITIONAL por el orden de gestión del contrato. Las cuentas permanecen activas para validación posterior al despliegue y deben retirarse después de esa comprobación.
