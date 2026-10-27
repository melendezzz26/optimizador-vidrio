# SPEC-HU-016 — Dashboard inicial para usuarios de NewGlass

## Información general

| Campo | Valor |
|---|---|
| Identificador / PBI relacionado | **HU-016** |
| Título | Dashboard inicial para usuarios de NewGlass |
| Estado | **Implemented** — T03 validada; pendiente de revisión del PR |
| Autor del alcance / implementación T01-T02 / regularización T03 | Fabricio Melendez Quezada / Luis Anthony Ibañez Herrera / Fabricio Melendez Quezada con asistencia de Codex |
| Revisor del alcance / revisión del cierre | Fabricio Danniel Aguilar Chávez (alcance histórico) / pendiente de revisión del PR actualizado |
| Fechas | 23/10/2026 (alcance histórico) / 27/10/2026 (regularización de T03) |
| Decisión | T01/T02 integradas en PR #63; T03 ejecutada contra API y PostgreSQL reales, con 22 E2E aprobados sin skips. Evidencia técnica completa; revisión del PR pendiente. |
| Tipo | Historia de usuario; independiente de HU-015. |
| Base inspeccionada | T03: PR #72 `2094b2d`, actualizado con `integration/sprint-01` `9cf6dc8`; pruebas en `32dd715`. |
| Rama de trabajo e implementación | `feature/HU-016-dashboard-inicial` |
| Registro de Product Backlog | HU-016, Sprint 2 del grupo G04 en Notion; no se modifica desde este PR. |
| PLAN / Tareas | T01/T02 integradas; T03 validada con E2E real y evidencia actualizada; revisión de PR pendiente. |

Ciclo de [SPEC-TEMPLATE](SPEC-TEMPLATE.md): Draft → Reviewed → Implemented → Verified.
T01/T02 fueron implementadas por Luis Anthony Ibañez Herrera e integradas en
PR #63. La declaración de Verified del 26/10 no acreditaba T03: la suite nueva
usaba respuestas simuladas y la suite real se omitía por falta de credenciales.

### Plan de regularización T03 — 27/10/2026

Reutilizar `tests.e2e_server` y su PostgreSQL temporal con cuentas sintéticas de
Administrador, Operario, Almacenero y un rol sin permisos. Ejecutar en el mismo
pipeline, sin credenciales externas, login → Inicio → módulos autorizados →
Inicio, refresh/logout, rechazo backend y responsive 1440/1024/800 px (más 390).
Mantener CA-20 original y distinguir el fallo HTTP controlado de la integración
real. Exportar evidencia bajo solicitud, preservando la evidencia de Sprint 1.
Ejecutar regresión, lint y build; registrar resultados y revisión por separado.
No se necesitan endpoints ni migraciones.

## 1. Identificador y registro del PBI

HU-016 corresponde al Dashboard inicial del Sprint 2 del grupo G04 en Notion.
La SPEC original se elaboró el 23/10/2026. Se conserva el vínculo con
TA-DASHBOARD-001 como antecedente de Sprint 1 para evitar contabilizar dos
veces la implementación base. Esta regularización completa las brechas de T03;
no cambia el identificador, la estimación ni el estado del backlog externo.

## 2. Contexto, base existente y problema

HU-015 se integró mediante PR #47 y permanece fuera de los cambios de esta entrega. El pedido original solicita documentar un nuevo PBI funcional de inicio operacional después del login.

La inspección del repositorio encontró que esa capacidad ya tiene un antecedente: [SPEC-TA-DASHBOARD-001](SPEC-TA-DASHBOARD-001-dashboard-inicial.md), su PLAN y [evidencia histórica](../evidence/sprint-01/TA-DASHBOARD-001/t3-integracion-e2e-cierre.md). Además, existen `DashboardPage`, clientes/modelo/hook y pruebas en `frontend/src/features/dashboard/`. `App.jsx` inicia en la vista interna `dashboard` y Sidebar utiliza **Inicio**. No se presenta este código como inexistente ni se propone crear otro DashboardPage.

HU-016 documenta el alcance aprobado y sus 22 criterios propios sobre esa base reutilizable. Durante T01 se contrastó la cobertura y se identificaron las brechas de permisos, navegación y casos sin funciones frente a TA-DASHBOARD-001; en T02 se implementaron los ajustes requeridos en `permissions.js`, `dashboardModel.js`, `DashboardPage.jsx`, `DashboardQuickActions.jsx`, `DashboardSummary.jsx` y `DashboardPage.css`; y en la regularización de T03 se amplía la suite E2E existente contra la API y PostgreSQL reales; véase la evidencia actual de Sprint 2 (`docs/evidence/sprint-02/HU-016/`). No se renombra, elimina ni reabre TA-DASHBOARD-001, y su evidencia de Sprint 1 permanece intacta en el repositorio.

Problema resuelto por la historia: disponer de una única entrada autenticada con información operacional real, navegación autorizada y comportamiento consistente, evitando cifras ficticias, acciones sin permiso y resultados parciales interpretados como totales. Se resolvieron las brechas identificadas: el acceso universal a Inicio mediante `canViewDashboard(user) = Boolean(user)`, el acceso rápido neutral a Optimización para roles con `optimization.view`, el saludo personalizado con nombre real del usuario, el manejo elegante de sesiones sin módulos mediante una tarjeta informativa sin peticiones no autorizadas, y la adaptabilidad responsive verificada en 1440px, 1024px y 800px. Véase §21.

## 3. Historia de usuario

Como usuario autenticado de NewGlass, quiero acceder a una pantalla inicial que resuma la información y acciones relevantes para mi rol, para consultar rápidamente el estado operativo del sistema y acceder a sus funciones principales.

Actores: **Administrador, Operario y Almacenero**. El rol orienta las prioridades; los permisos efectivos determinan las consultas y acciones disponibles.

## 4. Objetivo

Después de un login correcto, cualquier usuario autenticado llega a **Inicio**, una sola pantalla de Dashboard operacional simple. Presenta identidad real, resumen permitido y accesos rápidos, con estructura común y adaptación por permisos. No es un sistema BI.

La pantalla debe seguir siendo válida al recuperar la sesión mediante refresh y al regresar desde Sidebar. Una sesión válida con permisos de módulos vacíos conserva Inicio, identidad y cierre de sesión, con un mensaje de ausencia de funciones habilitadas y sin consultar fuentes restringidas. Mostrar esa superficie no concede ningún permiso backend.

## 5. Alcance MVP

- Reutilizar el Dashboard y shell existentes; una pantalla común para los tres roles, sin tres implementaciones independientes.
- Saludo con nombre/usuario real de la sesión y texto de resumen operativo, sin exponer tokens o credenciales.
- Conteos reales de pedidos PENDIENTE y EN_OPTIMIZACION cuando exista `orders.view`.
- Accesos a Pedidos, Optimización, Inventario y Administración únicamente cuando el módulo real y sus permisos lo permitan.
- Resúmenes simples de inventario con definición explícita de lo contado; su carga no exige crear una API nueva.
- Loading, empty, error, success, disabled temporal y funcionamiento parcial por fuente.
- Responsive, navegación por teclado, foco visible y regresión de sesión/navegación.

Los bloques preexistentes de clientes y pedidos en orden de gestión no son requisitos adicionales de HU-016. Si se conservan, deben mantener sus fuentes/permisos reales y no presentarse como métricas nuevas; una primera página ordenada por gestión no equivale a una cronología global de actividad.

## 6. Roles y contenido condicionado

La siguiente matriz expresa prioridades funcionales, no una matriz alternativa de autorización. Las asignaciones de rol son configurables en la base; no se codifican permisos nuevos ni excepciones por nombre de rol.

| Rol de referencia | Prioridad de información y accesos | Condiciones |
|---|---|---|
| Administrador | Pedidos, resumen de estados, Optimización, Inventario y Administración | Cada bloque y acción exige su permiso efectivo; administrar roles no implica automáticamente permiso para ver usuarios. |
| Operario | Pedidos pendientes/en optimización, Pedidos, Optimización y consulta de Inventario | No mostrar Usuarios sin `users.view`. Crear un pedido requiere `orders.create`, además de acceso al módulo. |
| Almacenero | Inventario, planchas, retazos e historial por material dentro del módulo | No ofrecer ejecución sin `optimization.execute`. La asignación inicial actual sí incluye `optimization.view`; una consulta de resultados autorizada no equivale a ejecutar. |

## 7. Flujo funcional

1. Authentication procesa el login mediante su mecanismo vigente.
2. Tras éxito, la aplicación entra en Inicio y muestra la identidad de la sesión.
3. Determina fuentes y accesos según los permisos recibidos del backend, sin consultar bloques no autorizados.
4. Carga independientemente las fuentes permitidas y comunica su estado; un resultado parcial no impide la navegación.
5. Muestra cifras válidas con significado explícito; una respuesta exitosa con cero corresponde a empty.
6. Un acceso rápido navega al módulo autorizado existente. No ejecuta una operación de negocio.
7. Sidebar permite volver a Inicio. Refresh valida la sesión actual antes de presentar información protegida.
8. Logout conserva el cierre actual, limpia sesión/datos protegidos y vuelve al flujo no autenticado. Las respuestas tardías de otro usuario o contexto no se publican.

## 8. Navegación y accesos rápidos reales

Se adopta **Inicio**, término ya usado por Sidebar y DashboardPage. `dashboard`, `orders`, `optimization`, `inventory` y `users` son identificadores de vista interna mediante `NavigationContext`, **no rutas URL nuevas**. No se inventan `/dashboard`, `/pedidos`, `/inventario` ni enlaces profundos no soportados. Se conserva la URL base/subpath de la aplicación y su flujo de sesión.

| Destino existente | Etiqueta coherente | Icono Lucide | Regla funcional implementada |
|---|---|---|---|
| `dashboard` | Inicio | `LayoutDashboard` | Disponible para toda sesión autenticada (`Boolean(user)`); no concede acceso directo a datos. |
| `orders` | Registro de pedidos | `FileSpreadsheet` | Navegar con `orders.view`; el módulo administra sus acciones internas. |
| `optimization` | Optimización | `ScanLine` | Navegar con `optimization.view` (`canViewResults`). Se rotula de forma neutral como «Optimización» para permitir consulta de corridas sin sugerir ejecución (`optimization.execute`). No inicia ejecuciones desde Inicio. |
| `inventory` | Gestión de inventario | `Package` | Navegar con `inventory.view`. |
| `users` | Administración | `Users` | Acceso según `users.view` o `roles.view`; cada pestaña mantiene su autorización interna. |

«Nuevo pedido» ya es una acción dentro de Pedidos, pero no hay un destino independiente desde Inicio que abra ese formulario. El MVP ofrece Registro de pedidos; no inventa un enlace de creación directa. Planchas/Retazos son pestañas internas de Inventario. Historial se abre para una plancha o retazo concreto; no hay una pantalla global de historial. El acceso de Almacenero puede conducir a Gestión de inventario y explicar esas funciones existentes, sin botones hacia rutas ficticias.

No utilizar «Continuar proceso» para un contador EN_OPTIMIZACION si no existe una ejecución identificada y una navegación real de recuperación. El acceso general a Optimización no promete recuperar un trabajo concreto.

## 9. Datos requeridos y significado de las cifras

| Dato | Fuente real | Regla de presentación |
|---|---|---|
| Nombre, usuario y permisos efectivos | Sesión de login y `GET /api/auth/me` | Saludo/identidad de sesión; no duplicar consultas si ya está validada. |
| Pedidos PENDIENTE | `GET /api/orders?page=1&limit=1&estado=PENDIENTE` | Usar `total`, no `items.length`; incluye todos los pedidos del filtro. |
| Pedidos EN_OPTIMIZACION | `GET /api/orders?page=1&limit=1&estado=EN_OPTIMIZACION` | Rotular «Pedidos en optimización». No contar ejecuciones: una corrida puede agrupar varios pedidos y ese estado no acredita un cálculo activo. |
| Unidades de plancha registradas activas | `GET /api/inventory/planchas` | Sumar `cantidad` solo con `estado=true` y `cantidad>0`; distinguir registros de unidades físicas. |
| Retazos activos registrados | `GET /api/inventory/retazos` | Contar registros con `estado=true`; no inferir compatibilidad, factibilidad ni reserva de stock. |
| Historial por material | GET de movimientos de una plancha/retazo identificado | Se consulta dentro del módulo existente, no se descarga todo el historial para el Dashboard. |

Los indicadores de inventario describen lo registrado por sus APIs; no certifican disponibilidad geométrica para un pedido ni corrigen inconsistencias de inventario. No se crean umbrales de stock bajo o alertas sin definición de negocio.

## 10. Estrategia de APIs y decisión arquitectónica

Decisión: **«reutilización prioritaria de contratos existentes; endpoint agregado solo si el análisis de implementación demuestra necesidad»**. La solución objetivo es frontend-only sobre los servicios actuales.

| Contrato actual | Autorización existente | Uso en este PBI |
|---|---|---|
| `POST /api/auth/login`, `GET /api/auth/me` | Autenticación vigente | Reutilizar sesión e identidad/permisos; no modificar Authentication backend. |
| `GET /api/orders` | `orders.view` | Dos consultas filtradas de conteo, con `total` paginado. |
| `GET /api/inventory/planchas` | `inventory.view` | Lista real de planchas para resumen simple. |
| `GET /api/inventory/retazos` | `inventory.view` | Lista real de retazos para resumen simple. |
| `GET /api/inventory/planchas/{id_plancha}/movimientos` | `inventory.view` | Contrato ya usado por el historial del módulo destino. |
| `GET /api/inventory/retazos/{id_retazo}/movimientos` | `inventory.view` | Contrato ya usado por el historial del módulo destino. |
| `GET /api/users` | `users.view` | Pertenece a Administración; no es necesario descargar usuarios para ofrecer su acceso. |
| `GET /api/roles`, `GET /api/permissions` | `roles.view` | Administración existente; no se necesitan nuevas consultas para decidir el acceso desde Inicio. |
| `GET /api/optimization/runs/{id_optimizacion}` | `optimization.view` | Resultado de una ejecución conocida; no proporciona un listado agregado de procesos. No se requiere para contar pedidos. |

No se invocan desde Dashboard `POST /api/optimization/start`, `/rasterize`, `/runs` ni `/runs/{id}/confirm`. Tampoco se necesita consultar stock compatible o ejecutar heurísticas para mostrar los conteos.

Los conteos de pedidos requieren dos solicitudes pequeñas. El inventario actual entrega listas completas, con geometría de retazos: su costo depende del volumen. T01 debe medir cantidad de requests, bytes y tamaño realista antes de recomendar un agregado. No hay evidencia actual que obligue a crear `GET /api/dashboard/summary`; es únicamente una alternativa condicionada a necesidad demostrada y revisión posterior, fuera de esta entrega. Se mantienen base API, transporte, manejo de sesión y cancelación existentes; React no accede directamente a la BD.

## 11. Principio de autorización

- El backend es la fuente definitiva de autorización y conserva la comprobación en cada endpoint.
- La UI consulta `permisos` de la sesión para ocultar fuentes/acciones no autorizadas, no para conceder capacidades.
- No se introduce `dashboard.view` ni otro permiso específico de Inicio.
- `orders.view` no concede `orders.create`; `optimization.view` no concede ejecutar ni confirmar; `roles.view` no concede `users.view`.
- La regla `canViewDashboard(user)` fue actualizada a `Boolean(user)`, alineando la superficie de Inicio con el requisito de permitir el acceso a toda sesión autenticada válida, sin relajar un solo permiso de datos o módulos backend.
- Un rol o sesión sin permisos de módulos (ej. `permisos: []`) visualiza una pantalla válida de Inicio con saludo de identidad real, una tarjeta informativa con el mensaje «Sin funciones habilitadas» y la opción de cerrar sesión, sin disparar consultas HTTP a endpoints restringidos (0 llamadas a inventario o pedidos) y sin interpretar la ausencia de permisos como cero registros.
- Un 401 utiliza el cierre/recuperación de sesión vigente. Un 403 no concede acceso por fallback: retira/invalida la sección afectada y permite actualizar el contexto de permisos conforme al mecanismo existente.

## 12. Estados de interfaz

| Estado | Comportamiento esperado |
|---|---|
| Loading | Indicador textual por bloque; no mostrar ceros provisionales como datos reales. |
| Empty | Respuesta válida sin registros o con total cero; mensaje como «0 pedidos pendientes». No es un error. |
| Success | Cifras y contenido de la última respuesta válida del contexto actual. |
| Error | Mensaje comprensible y reintento explícito; una fuente fallida no se sustituye por cero. |
| Error parcial | Conservar otros bloques válidos e identificar la sección fallida; los accesos autorizados siguen utilizables. |
| Disabled temporal | Deshabilitar actualización mientras corresponda, comunicar carga y evitar dobles solicitudes; no usar disabled como sustituto habitual de ocultar opciones sin permiso. |
| Sin funciones autorizadas | Inicio, identidad, explicación y logout; sin fuentes restringidas ni cifras inventadas. |

Durante recarga o fallo posterior no se presentan datos anteriores como vigentes sin identificación. Al cambiar usuario, token, permisos o módulo se cancelan/ignoran respuestas tardías y se retiran los datos que ya no correspondan. No se exige tiempo real, polling nuevo ni coherencia transaccional entre indicadores obtenidos en solicitudes separadas.

## 13. Responsive y diseño visual

Reutilización de AppShell, Sidebar, PageHeader/PageCard, tokens, tarjetas y feedback vigentes. Estructura conceptual: Inicio → saludo e identidad con nombre de usuario real → resumen operativo → accesos rápidos. La composición se adaptó en `DashboardPage.css` con grillas fluidas basadas en `repeat(auto-fit, minmax(220px, 1fr))` y breakpoints en `@media (max-width: 1024px)` y `@media (max-width: 640px)`.

La suite de T03 comprueba 1440, 1024 y 800 px (además de 390), sin overflow
horizontal, con Sidebar navegable y sin intersección con el contenido. Los
accesos rápidos pueden requerir scroll vertical; se comprueba que sean
utilizables. Las capturas actuales se distinguen de las históricas en §20.

## 14. Accesibilidad

Aplicar la línea base de [UI/UX](../ui-ux/README.md) y [feedback compartido](../ui-ux/feedback-compartido.md): navegación por teclado, orden de foco coherente y visible, headings semánticos, botones/enlaces nativos con nombres accesibles, contraste conforme a los tokens revisados y mensajes de error textuales. No comunicar estados solo con color. Conservar el acceso para saltar al contenido del shell y respetar reducción de movimiento si se utilizan animaciones. No se afirma certificación WCAG.

## 15. Criterios de aceptación y matriz de verificación

| ID | Criterio verificable | Estado | Evidencia y resultado de verificación |
|---|---|:---:|---|
| CA-01 | Después de autenticarse correctamente, cualquier usuario con sesión válida llega a Inicio. | Verificado técnicamente | E2E real para los tres roles y rol sin permisos; login HTTP 200 y saludo con identidad de la respuesta. |
| CA-02 | Inicio puede abrirse nuevamente desde Sidebar y refleja la vista activa de forma visual y accesible. | Verificado técnicamente | E2E real: navegación desde accesos rápidos y retorno mediante Sidebar con aria-current=page. |
| CA-03 | Administrador, Operario y Almacenero autenticados acceden a la misma pantalla común; una sesión sin permisos de fuentes conserva la superficie de Inicio sin consultas restringidas. | Verificado técnicamente | E2E real: rol sin filas en rol_permisos; Inicio, mensaje, refresh y logout; cero solicitudes del navegador a módulos restringidos. |
| CA-04 | Las fuentes y accesos visibles corresponden únicamente a los permisos efectivos actuales; el rol no concede excepciones adicionales. | Verificado técnicamente | E2E real: fuentes y accesos por rol; ausencia de Pedidos/Usuarios donde corresponde. Componentes para permisos efectivos y revocados. |
| CA-05 | Mostrar/ocultar opciones no sustituye la autorización backend; solicitudes directas siguen protegidas por los permisos existentes. | Verificado técnicamente | E2E real: llamadas directas con token sin permisos reciben 403 en Inventario, Pedidos, Clientes y Usuarios; controles backend existentes. |
| CA-06 | Todas las cifras mostradas proceden de respuestas reales exitosas y tienen significado/alcance explícitos; no hay números ficticios. | Verificado técnicamente | E2E compara unidades/registros de planchas y totales de pedidos con las respuestas HTTP reales. Componentes verifican las otras transformaciones. |
| CA-07 | Con `orders.view`, Inicio muestra el total de pedidos PENDIENTE usando `total` del contrato filtrado existente. Sin permiso, no consulta ni muestra ese bloque. | Verificado técnicamente | E2E distingue estado=PENDIENTE y compara total; sin consulta ni tarjeta para Almacenero. |
| CA-08 | Con `orders.view`, Inicio muestra el total de pedidos EN_OPTIMIZACION mediante el mismo contrato; no lo presenta como número de ejecuciones activas. | Verificado técnicamente | E2E distingue estado=EN_OPTIMIZACION y compara total; componentes comprueban el rotulado sin métricas de ejecución. |
| CA-09 | Todo resumen de Inventario utiliza las listas reales autorizadas, distingue registros/unidades y no inventa disponibilidad o compatibilidad. | Verificado técnicamente | E2E compara unidades/registros de planchas; dashboardModel/DashboardPage prueban retazos y advertencias de compatibilidad. |
| CA-10 | Los accesos rápidos navegan a los módulos existentes de §8, sin URLs ficticias ni operaciones de negocio al pulsarlos. | Verificado técnicamente | E2E real: Inventario y Optimización para tres roles; Pedidos para Administrador/Operario; Usuarios para Administrador; retorno a Inicio. |
| CA-11 | Almacenero sin `optimization.execute` no recibe una acción de ejecución. Una consulta autorizada por `optimization.view` no se presenta como permiso para calcular o confirmar. | Verificado técnicamente | E2E Almacenero: acceso neutral a Optimización, consulta visible, sin controles de cálculo ni confirmación. |
| CA-12 | Operario sin `users.view` no recibe acciones de Usuarios; Administración respeta separadamente los permisos de sus pestañas. | Verificado técnicamente | E2E sin Administración para Operario/Almacenero; pruebas de permisos y componentes para pestañas independientes. |
| CA-13 | La pantalla contempla loading, empty, error y success por fuente, reintento, disabled temporal y datos parciales cuando corresponda. | Verificado técnicamente | Componentes: loading/empty/error/success, disabled y parciales. E2E: datos vacíos reales y fallo 503 controlado seguido de reintento contra API real. |
| CA-14 | Un fallo recuperable no muestra información inventada u obsoleta como vigente; respuestas tardías no contaminan otro contexto de sesión/permisos. | Verificado técnicamente | useDashboard y DashboardNavigation: cancelación/aislamiento por sesión y permisos; E2E controlado conserva fuentes exitosas. |
| CA-15 | El MVP no muestra merma, aprovechamiento, ahorro, eficiencia ni comparativas FF/BF/WF. La existencia actual de resultados First Fit en otro módulo no incorpora esos indicadores a Inicio. | Verificado técnicamente | Contrato y pruebas de componentes: Inicio no incorpora indicadores ni comparativas del optimizador. |
| CA-16 | La pantalla puede operarse con teclado, mantiene foco visible, semántica y nombres accesibles; los estados no dependen exclusivamente del color. | Verificado técnicamente | DashboardNavigation: teclado, foco y semántica. E2E: accesos y Sidebar utilizables; no se afirma certificación WCAG. |
| CA-17 | Inicio funciona sin overflow horizontal ni solapamientos en 1440, 1024 y 800 px, con tarjetas, textos, accesos y Sidebar utilizables. | Verificado técnicamente | E2E parametrizado en 1440/1024/800/390: scrollWidth <= innerWidth, controles accesibles al hacer scroll y Sidebar sin solapamiento. |
| CA-18 | Refresh desde Inicio sobre la URL base/subpath vigente recupera una sesión válida y presenta una pantalla autenticada válida, sin exigir una URL nueva. | Verificado técnicamente | E2E real: reload en URL base, GET /api/auth/me 200 y sesión recuperada; componentes conservan navegación en subpath. |
| CA-19 | Logout desde Inicio conserva el flujo actual: elimina la sesión, retira datos protegidos y retorna al acceso no autenticado. | Verificado técnicamente | E2E real: desaparecen Inicio y sus datos, sessionStorage.optimizador.auth queda vacío y se presenta Login. |
| CA-20 | Login → Inicio → módulo autorizado tiene cobertura E2E con navegador, API y datos controlados reales; incluye retorno a Inicio, refresh y logout. | Verificado técnicamente | ta-dashboard.spec.js: navegador, API y PostgreSQL temporal reales; login, módulos, retorno a Inicio, refresh/logout. El fallo 503 controlado no acredita este CA. |
| CA-21 | Las principales variantes de los tres roles, permisos configurados/revocados y sesión sin fuentes autorizadas tienen pruebas automatizadas de componentes/permisos. | Verificado técnicamente | 86 pruebas de permisos/componentes de Dashboard y Authentication, incluyendo permisos revocados y sesión sin fuentes. |
| CA-22 | La navegación existente a Pedidos, Optimización, Inventario y Administración/Usuarios conserva sus flujos y autorizaciones; HU-015 no se modifica. | Verificado técnicamente | E2E real navega a los cuatro módulos autorizados; regresión completa registrada en la evidencia. Sin cambios en HU-015 ni código de producción. |

## 16. Fuera de alcance

- Gráficos analíticos avanzados, actividad histórica compleja, tendencias, filtros temporales y productividad histórica.
- Personalización de widgets, drag and drop y preferencias por usuario.
- KPI financieros, ahorro/reducción de costos, merma, aprovechamiento y eficiencia o comparación FF/BF/WF.
- Implementar heurísticas, placement, rasterización, selección de planchas, iniciar o confirmar optimizaciones desde Inicio.
- Notificaciones, alertas/umbrales de inventario y una pantalla global de movimientos inexistente.
- Nuevos permisos de base de datos, cambios de modelo RBAC, backend nuevo sin necesidad demostrada, tablas/migraciones y persistencia de Dashboard.
- Modificar HU-015 o alterar contratos de otros módulos sin requerimiento justificado.

## 17. Restricciones e invariantes

Dashboard es una superficie de lectura y navegación autorizada. No consume stock, no modifica inventario, no cambia estados de pedidos, no inicia optimizaciones automáticamente, no modifica usuarios y no introduce persistencia propia. Las acciones rápidas solo conducen a módulos existentes que conservan sus reglas y permisos. Logout y sesión mantienen su almacenamiento ya existente en `sessionStorage`, sin crear preferencias locales.

T02 modificó el frontend existente. La regularización T03 solo modifica la suite de navegador y el servidor de pruebas `backend/tests/e2e_server.py` para añadir un rol y usuario sintéticos sin permisos. No modifica código de producción, endpoints, esquemas, migraciones ni dependencias.

## 18. Impacto técnico implementado

T01/T02 reutilizan la feature Dashboard existente (PR #63):

- **`frontend/src/features/authentication/permissions.js`**: Actualización de la función `canViewDashboard(user)` para retornar `Boolean(user)`, habilitando el acceso a Inicio a cualquier sesión autenticada válida. Se eliminó la función no utilizada `hasAny`.
- **`frontend/src/features/dashboard/dashboardModel.js`**: Inclusión de la regla `canViewResults(user)` para ofrecer el acceso rápido `{ view: 'optimization', label: 'Optimización' }` a usuarios con permiso `optimization.view`.
- **`frontend/src/features/dashboard/DashboardQuickActions.jsx`**: Registro del icono `ScanLine` de `lucide-react` para la acción de `optimization`.
- **`frontend/src/features/dashboard/DashboardPage.jsx`**: Incorporación del saludo personalizado con nombre real de usuario (`Hola, ${user.nombre || user.username}`), renderizado condicional de la tarjeta informativa «Sin funciones habilitadas» para sesiones sin permisos de módulos, y condicional para mostrar el botón de recarga únicamente si existen fuentes activas.
- **`frontend/src/features/dashboard/DashboardSummary.jsx`**: Retorno `null` cuando no hay tarjetas de resumen a renderizar para evitar contenedores vacíos.
- **`frontend/src/features/dashboard/DashboardPage.css`**: Grilla responsiva fluida basada en `repeat(auto-fit, minmax(220px, 1fr))` y breakpoints adaptables en `@media (max-width: 1024px)` y `@media (max-width: 640px)`.
- **T03**: se conserva la eliminación de la suite simulada y se amplía `ta-dashboard.spec.js` con integración real sin skips por credenciales. El escenario 503 se identifica como fallo controlado y se prueba su recuperación real; no hay respuestas simuladas en los flujos que acreditan CA-20.
- **Backend de producción y base de datos**: sin cambios. Solo se amplía el seed sintético del servidor de pruebas; no se crean endpoints ni migraciones.

## 19. Estrategia de pruebas y resultados

Los resultados actuales y comandos reproducibles se registran en la
[evidencia T03](../evidence/sprint-02/HU-016/t3-integracion-e2e-cierre.md).
La ejecución focalizada de Dashboard del 27/10 obtiene **22 passed, 0 skipped**:
20 escenarios de integración real y 2 de fallo controlado (11 por proyecto).
Las 86 pruebas de componentes de Dashboard/Authentication también pasan.
Regresión: 2146 backend y 483 componentes aprobados; CI frontend con 161
unitarias y lint/build aprobados; CI E2E con 100 passed y 6 skips históricos de
HU-015. Se registra además el fallo de Inventario móvil con Chromium local,
aprobado en CI. No se presentan componentes o capturas simuladas como
integración real. La revisión humana del PR sigue pendiente.

## 20. Evidencia

- [Reporte actual y matriz](../evidence/sprint-02/HU-016/t3-integracion-e2e-cierre.md).
- Capturas nuevas de PostgreSQL real: `docs/evidence/sprint-02/HU-016/t3/real/`.
- Las capturas anteriores en `t3/screenshots/` son históricas de la ejecución
  simulada; no acreditan la regularización T03 ni se sobrescriben.
- `TA-DASHBOARD-001` conserva sus documentos y evidencia histórica en Sprint 1.
- Las ejecuciones normales escriben solo en `frontend/test-results/` (ignorado).
  La exportación a otra carpeta exige `NEWGLASS_HU016_EVIDENCE_DIR` y separa
  proyectos de escritorio/móvil para evitar sobrescrituras.

## 21. Riesgos y límites de verificación

- Sin credenciales externas: las cuentas sintéticas solo pertenecen al servidor
  `tests.e2e_server`, en PostgreSQL temporal de loopback con migraciones reales.
- La ausencia de PostgreSQL falla en CI (`NEWGLASS_REQUIRE_POSTGRES=1`); la suite
  Dashboard no tiene omisiones condicionales por credenciales.
- El escenario 503 es una inyección controlada de fallo; el reintento vuelve a
  la API real. No es evidencia de una avería natural del backend.
- Las pruebas de componentes acreditan loading, cancelación de peticiones,
  permisos revocados y teclado. E2E y componentes tienen alcances distintos.
- Validación técnica, revisión humana del PR y actualización del backlog son
  pasos diferentes; este documento no atribuye una aprobación a Aguilar.

## 22. Tareas

| Tarea | Estado técnico | Responsable y evidencia |
|---|---|---|
| HU-016-T01 | Integrada en PR #63 | Luis Anthony Ibañez Herrera; contraste de 22 CA y definición de brechas. |
| HU-016-T02 | Integrada en PR #63 | Luis Anthony Ibañez Herrera, `f45b7ae`; interfaz y 86 pruebas de componentes. |
| HU-016-T03 | Validada técnicamente; revisión del PR pendiente | Regularización por Fabricio Melendez Quezada con Codex; commit `32dd715`. La entrega simulada `405df4f` no acredita por sí sola el cierre. |

## 23. Estimación

Regla solicitada: **1 SP = 6 horas; 0.5 SP = 3 horas**. Estimación inicial para contrastar, adaptar y verificar sobre la implementación existente; no representa horas efectivamente medidas:

| Tarea | SP | Horas | Justificación |
|---|---:|---:|---|
| HU-016-T01 | 0.5 | 3 | Contratos y navegación analizados; mapeo de diferencias, permisos/accesos y definición de adaptaciones. |
| HU-016-T02 | 1 | 6 | Ajustes de interfaz sobre componentes existentes, variantes de permisos, estados y diseño responsive. |
| HU-016-T03 | 1 | 6 | Integración real, variantes de permisos, verificación de anchos y evidencia reproducible en Sprint 2. |
| **Total** | **2.5** | **15** | Alcance sobre base reutilizable, sin backend de producción ni migraciones. |

## 24. Decisiones

- D-01: HU-016 es el identificador oficial adoptado en la secuencia local; registro externo pendiente en herramienta oficial de backlog.
- D-02: la validación técnica se registra con resultados reales; la revisión del cierre del PR se registra por separado, sin inventar una aprobación humana.
- D-03: reconocer y reutilizar TA-DASHBOARD-001; preservar su SPEC, PLAN, implementación y evidencia en Sprint 1, sin duplicar DashboardPage ni alterar HU-015.
- D-04: navegación «Inicio» mediante vistas internas actuales de `NavigationContext`; ninguna URL nueva ni atajo ficticio.
- D-05: una pantalla común para toda sesión válida (`canViewDashboard = Boolean(user)`), consultas/acciones según permisos efectivos; backend autoritativo y ningún permiso backend nuevo.
- D-06: preferir APIs existentes; dos totales filtrados de pedidos y resúmenes de inventario con definición precisa; ningún endpoint agregado por conveniencia.
- D-07: lectura y navegación autorizada, sin operaciones de negocio ni métricas analíticas no soportadas; rotulado explícito de pedidos en optimización.
- D-08: conservar los 22 CA, incluido el contrato original de integración real de CA-20. La evidencia de la regularización T03 sustituye las afirmaciones anteriores de cierre.

## Historial de estado

- **23/10/2026 — Reviewed:** SPEC HU-016 creada por encargo del responsable, con Fabricio Melendez como autor y Fabricio Aguilar como revisor del alcance funcional aprobado según confirmación explícita. Se documentan la auditoría de identificador/base, el registro externo pendiente, los 22 CA, T01/T02/T03 y 2.5 SP / 15 horas.
- **25/10/2026 — Implemented:** Finalización de la implementación de T01 y T02 (commit `f45b7ae`). Código adaptado en `features/dashboard` y `features/authentication`, pruebas de componentes (86/86 PASS) y estilos responsivos en 1440/1024/800 px.
- **26/10/2026 — Verified declarado en la entrega anterior:** no acreditaba T03 contra API/datos reales; declaración corregida por esta regularización. No se modifica la evidencia histórica de TA-DASHBOARD-001.
- **27/10/2026 — Implemented, regularización T03:** CA-20 restaurado, suite existente ampliada y ejecutable sin credenciales externas, 22 E2E focalizados aprobados sin skips y 86 componentes aprobados. Regresión técnica y límites registrados en la evidencia; revisión del PR pendiente, sin atribuir aprobación humana.
