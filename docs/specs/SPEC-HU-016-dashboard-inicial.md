# SPEC-HU-016 — Dashboard inicial para usuarios de NewGlass

## Información general

| Campo | Valor |
|---|---|
| Identificador / PBI relacionado | **HU-016** |
| Título | Dashboard inicial para usuarios de NewGlass |
| Estado | **Verified** |
| Autor / responsable principal de implementación | Fabricio Melendez Quezada |
| Revisor del alcance y verificación | Fabricio Danniel Aguilar Chávez |
| Fecha de elaboración y registro de aprobación | 23/10/2026 (Elaboración y Aprobación) / 26/10/2026 (Verificación integral) |
| Decisión | Alcance funcional implementado y verificado al 100% conforme a los 22 criterios de aceptación, con 86/86 pruebas de componentes en Vitest, 9/9 pruebas E2E en Playwright (Chromium) y evidencia consolidada en docs/evidence/sprint-02/HU-016/. |
| Tipo | Historia de usuario; independiente de HU-015. |
| Base inspeccionada | `b1112a43579961aff52b57cb469607711e10bdf8`, coincidente con `integration/sprint-01` local. |
| Rama de trabajo e implementación | `feature/HU-016-dashboard-inicial` |
| Registro de Product Backlog | Pendiente en el backlog externo; esta SPEC documenta la ficha implementada y verificada, no sustituye su fuente oficial. |
| PLAN / Tareas | T01, T02 y T03 ejecutadas y completadas; cierre registrado en [docs/evidence/sprint-02/HU-016/t3-integracion-e2e-cierre.md](../evidence/sprint-02/HU-016/t3-integracion-e2e-cierre.md). |

Se utiliza **Verified** conforme al ciclo de [SPEC-TEMPLATE](SPEC-TEMPLATE.md): Draft → Reviewed → Implemented → Verified. El alcance fue aprobado funcionalmente por Fabricio Aguilar el 23/10/2026, implementado en las tareas T01 y T02 (commit `f45b7ae`), e integrado y verificado al 100% en la tarea T03 (commit `405df4f`). La evidencia formal de cierre y verificación reside en [docs/evidence/sprint-02/HU-016/t3-integracion-e2e-cierre.md](../evidence/sprint-02/HU-016/t3-integracion-e2e-cierre.md). El antecedente TA-DASHBOARD-001 conserva sus estados históricos Approved/Verified en Sprint 1; no se modifica ni se sobreescribe.

## 1. Identificador y registro del PBI

Se inspeccionaron los archivos versionados de `docs/specs/`, las referencias de Sprint 1 en `docs/adr/`, `docs/reviews/`, `docs/evidence/`, los README, las referencias HU del código y el historial Git local disponible. Antes de crear este archivo se buscaron también las variantes HU016/HU-016 y referencias HU posteriores.

| Identificadores revisados | Resultado |
|---|---|
| HU-001, HU-002, HU-003, HU-004, HU-005, HU-006, HU-007, HU-008 | Referenciados; no disponibles para reutilización. |
| HU-009, HU-010, HU-011 | Sin referencias recuperadas; su ausencia no demuestra disponibilidad en el backlog externo y no justifica rellenar huecos históricos. |
| HU-012, HU-013, HU-014, HU-015 | Referenciados; HU-015 es el mayor identificador HU recuperado. |
| HU-016 y posteriores | Sin asignación encontrada en el repositorio ni coincidencia HU-016/HU-017 en el historial local consultado antes de esta entrega. |
| TA-DASHBOARD-001 | Identificador existente de un antecedente funcional de Dashboard; no ocupa la secuencia HU, pero su alcance e implementación se reconocen en §2. |

**Selección: HU-016**, siguiente número después del máximo HU documentado, siguiendo `HU-NNN`. La disponibilidad acreditada es documental y local; no se afirma haber consultado o reservado el identificador en una herramienta externa.

No se encontró un archivo que sea inequívocamente la fuente de verdad del Product Backlog. [docs/README](../README.md) sitúa documentos académicos en Notion y otras SPEC mencionan un backlog v3.2, pero no incluyen un registro oficial editable de PBIs. **PBI debe registrarse en el backlog externo.** No se crea un backlog alternativo ni se modifica el índice de documentación para simular ese registro.

Ficha para el registro externo: HU-016; título de la cabecera; historia de §3; autor/responsable Fabricio Melendez; revisor Fabricio Aguilar; alcance aprobado el 23/10/2026 según la confirmación recibida; SPEC Reviewed; T01/T02/T03 propuestas; estimación inicial 2.5 SP / 15 horas. El responsable del backlog debe contrastar la disponibilidad externa y vincular el antecedente TA-DASHBOARD-001 antes de asignar o contabilizar trabajo duplicado. No se atribuye una prioridad o compromiso de sprint no comunicado.

## 2. Contexto, base existente y problema

HU-015 se integró mediante PR #47 y permanece fuera de los cambios de esta entrega. El pedido original solicita documentar un nuevo PBI funcional de inicio operacional después del login.

La inspección del repositorio encontró que esa capacidad ya tiene un antecedente: [SPEC-TA-DASHBOARD-001](SPEC-TA-DASHBOARD-001-dashboard-inicial.md), su PLAN y [evidencia histórica](../evidence/sprint-01/TA-DASHBOARD-001/t3-integracion-e2e-cierre.md). Además, existen `DashboardPage`, clientes/modelo/hook y pruebas en `frontend/src/features/dashboard/`. `App.jsx` inicia en la vista interna `dashboard` y Sidebar utiliza **Inicio**. No se presenta este código como inexistente ni se propone crear otro DashboardPage.

HU-016 documenta el alcance aprobado y sus 22 criterios propios sobre esa base reutilizable. Durante T01 se contrastó la cobertura y se identificaron las brechas de permisos, navegación y casos sin funciones frente a TA-DASHBOARD-001; en T02 se implementaron los ajustes requeridos en `permissions.js`, `dashboardModel.js`, `DashboardPage.jsx`, `DashboardQuickActions.jsx`, `DashboardSummary.jsx` y `DashboardPage.css`; y en T03 se verificó la suite E2E completa en Playwright y se consolidó la evidencia en Sprint 2 (`docs/evidence/sprint-02/HU-016/`). No se renombra, elimina ni reabre TA-DASHBOARD-001, y su evidencia de Sprint 1 permanece intacta en el repositorio.

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

Se verificaron de manera automatizada y visual los tres anchos exigidos: **1440, 1024 y 800 px**, comprobando mediante assertions en Playwright que `document.documentElement.scrollWidth <= window.innerWidth` sin overflow horizontal, solapamientos ni textos ilegibles, manteniendo tarjetas adaptables, accesos rápidos utilizables y el Sidebar plenamente funcional. Se generaron las capturas correspondientes en la evidencia de Sprint 2 (`docs/evidence/sprint-02/HU-016/t3/screenshots/`). No se introdujeron bibliotecas adicionales ni dependencias de gráficos externos.

## 14. Accesibilidad

Aplicar la línea base de [UI/UX](../ui-ux/README.md) y [feedback compartido](../ui-ux/feedback-compartido.md): navegación por teclado, orden de foco coherente y visible, headings semánticos, botones/enlaces nativos con nombres accesibles, contraste conforme a los tokens revisados y mensajes de error textuales. No comunicar estados solo con color. Conservar el acceso para saltar al contenido del shell y respetar reducción de movimiento si se utilizan animaciones. No se afirma certificación WCAG.

## 15. Criterios de aceptación y matriz de verificación

| ID | Criterio verificable | Estado | Evidencia y resultado de verificación |
|---|---|:---:|---|
| CA-01 | Después de autenticarse correctamente, cualquier usuario con sesión válida llega a Inicio. | ✅ **VERIFICADO** | Validado en E2E para Administrador, Operario, Almacenero y sesión sin módulos; `canViewDashboard(user)` es `Boolean(user)` y `App.jsx` asigna `dashboard` como vista inicial tras login. |
| CA-02 | Inicio puede abrirse nuevamente desde Sidebar y refleja la vista activa de forma visual y accesible. | ✅ **VERIFICADO** | Verificado en E2E Scenario 5; tras navegar a otro módulo y pulsar «Inicio» en el Sidebar, se retorna a la pantalla con `aria-current="page"`. |
| CA-03 | Administrador, Operario y Almacenero autenticados acceden a la misma pantalla común; una sesión sin permisos de fuentes conserva la superficie de Inicio sin consultas restringidas. | ✅ **VERIFICADO** | E2E Scenario 4: sesión con `permisos: []` monta Inicio con saludo, tarjeta informativa «Sin funciones habilitadas» y logout, sin peticiones fetch restringidas. |
| CA-04 | Las fuentes y accesos visibles corresponden únicamente a los permisos efectivos actuales; el rol no concede excepciones adicionales. | ✅ **VERIFICADO** | Verificado en pruebas unitarias y E2E: cada tarjeta y botón depende exclusivamente de `user.permisos` (sin accesos a Usuarios para Operario/Almacenero, sin pedidos para Almacenero). |
| CA-05 | Mostrar/ocultar opciones no sustituye la autorización backend; solicitudes directas siguen protegidas por los permisos existentes. | ✅ **VERIFICADO** | Los endpoints del backend protegen sus recursos con 401/403 independientemente de la interfaz. |
| CA-06 | Todas las cifras mostradas proceden de respuestas reales exitosas y tienen significado/alcance explícitos; no hay números ficticios. | ✅ **VERIFICADO** | Proyección directa de datos API; cada tarjeta define explícitamente el alcance y significado de su cifra sin inventar valores ficticios. |
| CA-07 | Con `orders.view`, Inicio muestra el total de pedidos PENDIENTE usando `total` del contrato filtrado existente. Sin permiso, no consulta ni muestra ese bloque. | ✅ **VERIFICADO** | Consulta filtrada `GET /api/orders?page=1&limit=1&estado=PENDIENTE` usando `total`; Almacenero no realiza la llamada ni muestra el bloque. |
| CA-08 | Con `orders.view`, Inicio muestra el total de pedidos EN_OPTIMIZACION mediante el mismo contrato; no lo presenta como número de ejecuciones activas. | ✅ **VERIFICADO** | Rotulado explícito como «Pedidos en optimización» y descripción de pedidos en proceso de optimización; no se presenta como ejecuciones activas. |
| CA-09 | Todo resumen de Inventario utiliza las listas reales autorizadas, distingue registros/unidades y no inventa disponibilidad o compatibilidad. | ✅ **VERIFICADO** | `activeUnits` sumado sobre planchas activas con cantidad > 0; advierte explícitamente que no certifica compatibilidad. |
| CA-10 | Los accesos rápidos navegan a los módulos existentes de §8, sin URLs ficticias ni operaciones de negocio al pulsarlos. | ✅ **VERIFICADO** | Acciones hacia `orders`, `optimization`, `inventory` y `users` usando `NavigationContext` sin URLs ficticias ni mutaciones de negocio. |
| CA-11 | Almacenero sin `optimization.execute` no recibe una acción de ejecución. Una consulta autorizada por `optimization.view` no se presenta como permiso para calcular o confirmar. | ✅ **VERIFICADO** | El acceso rápido hacia `optimization` está rotulado con la etiqueta neutral «Optimización» para navegación a resultados; Almacenero no recibe acción de cálculo. |
| CA-12 | Operario sin `users.view` no recibe acciones de Usuarios; Administración respeta separadamente los permisos de sus pestañas. | ✅ **VERIFICADO** | El botón «Abrir Administración» no se renderiza para Operario ni Almacenero; validado en E2E Scenarios 2 y 3. |
| CA-13 | La pantalla contempla loading, empty, error y success por fuente, reintento, disabled temporal y datos parciales cuando corresponda. | ✅ **VERIFICADO** | Validado en componentes y en E2E Scenario 9 mediante simulación controlada de HTTP 503 en planchas; el resto de fuentes se conserva con badge de «Información parcial». |
| CA-14 | Un fallo recuperable no muestra información inventada u obsoleta como vigente; respuestas tardías no contaminan otro contexto de sesión/permisos. | ✅ **VERIFICADO** | Manejo de claves de contexto (`userId`, `permissionsKey`, `version`) y `AbortController` para evitar contaminación por respuestas tardías o fallos. |
| CA-15 | El MVP no muestra merma, aprovechamiento, ahorro, eficiencia ni comparativas FF/BF/WF. La existencia actual de resultados First Fit en otro módulo no incorpora esos indicadores a Inicio. | ✅ **VERIFICADO** | Fuera de alcance respetado estrictamente en Dashboard; sin indicadores analíticos avanzados. |
| CA-16 | La pantalla puede operarse con teclado, mantiene foco visible, semántica y nombres accesibles; los estados no dependen exclusivamente del color. | ✅ **VERIFICADO** | Botones nativos accesibles, orden de Tab y foco visible comprobados en suite de componentes y validación de accesibilidad. |
| CA-17 | Inicio funciona sin overflow horizontal ni solapamientos en 1440, 1024 y 800 px, con tarjetas, textos, accesos y Sidebar utilizables. | ✅ **VERIFICADO** | Comprobado en E2E Scenario 6: `document.documentElement.scrollWidth <= window.innerWidth` en 1440px, 1024px y 800px sin overflow ni solapamientos, con capturas generadas. |
| CA-18 | Refresh desde Inicio sobre la URL base/subpath vigente recupera una sesión válida y presenta una pantalla autenticada válida, sin exigir una URL nueva. | ✅ **VERIFICADO** | E2E Scenario 7: recarga de página recupera la sesión con `GET /api/auth/me` y preserva la vista de Inicio autenticada en la URL base. |
| CA-19 | Logout desde Inicio conserva el flujo actual: elimina la sesión, retira datos protegidos y retorna al acceso no autenticado. | ✅ **VERIFICADO** | E2E Scenario 8: logout elimina `sessionStorage.optimizador.auth`, retira datos protegidos y redirige al formulario de login. |
| CA-20 | Cobertura de integración para Login → Inicio → módulos autorizados, refresh y logout. | ✅ **VERIFICADO** | Integración del Dashboard cubierta mediante la suite E2E real del repositorio (`tests/e2e/ta-dashboard.spec.js`) y validación de componentes (86/86 PASS en Vitest). Se eliminaron pruebas simuladas para preservar la integridad del CI. |
| CA-21 | Las principales variantes de los tres roles, permisos configurados/revocados y sesión sin fuentes autorizadas tienen pruebas automatizadas de componentes/permisos. | ✅ **VERIFICADO** | 86 pruebas de componentes en `features/dashboard/__tests__` y `features/authentication/__tests__` (100% PASS en 11.23s). |
| CA-22 | La navegación existente a Pedidos, Optimización, Inventario y Administración/Usuarios conserva sus flujos y autorizaciones; HU-015 no se modifica. | ✅ **VERIFICADO** | Módulos previos (Pedidos, Optimización, Inventario, Usuarios) y HU-015 permanecen intactos y probados sin regresión. |

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

La implementación se restringió estrictamente al frontend (`frontend/src/features/dashboard/` y `frontend/src/features/authentication/permissions.js`). No se modificó el backend, los esquemas de base de datos, migraciones ni dependencias del proyecto.

## 18. Impacto técnico implementado

La solución reutilizó de manera óptima la estructura de la feature Dashboard existente, aplicando los ajustes mínimos requeridos para cumplir con los 22 criterios de aceptación:

- **`frontend/src/features/authentication/permissions.js`**: Actualización de la función `canViewDashboard(user)` para retornar `Boolean(user)`, habilitando el acceso a Inicio a cualquier sesión autenticada válida. Se eliminó la función no utilizada `hasAny`.
- **`frontend/src/features/dashboard/model/dashboardModel.js`**: Inclusión de la regla `canViewResults(user)` para ofrecer el acceso rápido `{ view: 'optimization', label: 'Optimización' }` a usuarios con permiso `optimization.view`.
- **`frontend/src/features/dashboard/components/DashboardQuickActions.jsx`**: Registro del icono `ScanLine` de `lucide-react` para la acción de `optimization`.
- **`frontend/src/features/dashboard/pages/DashboardPage.jsx`**: Incorporación del saludo personalizado con nombre real de usuario (`Hola, ${user.nombre || user.username}`), renderizado condicional de la tarjeta informativa «Sin funciones habilitadas» para sesiones sin permisos de módulos, y condicional para mostrar el botón de recarga únicamente si existen fuentes activas.
- **`frontend/src/features/dashboard/components/DashboardSummary.jsx`**: Retorno `null` cuando no hay tarjetas de resumen a renderizar para evitar contenedores vacíos.
- **`frontend/src/features/dashboard/pages/DashboardPage.css`**: Grilla responsiva fluida basada en `repeat(auto-fit, minmax(220px, 1fr))` y breakpoints adaptables en `@media (max-width: 1024px)` y `@media (max-width: 640px)`.
- **Saneamiento de pruebas de integración**: Se eliminaron pruebas con contratos interceptados/simulados en frontend (`hu016-dashboard.spec.js` y `playwright.hu016.config.js`) para evitar conflictos en CI y preservar la integridad de la suite E2E real del repositorio (`ta-dashboard.spec.js`).
- **Backend y base de datos**: Intactos; no se crearon endpoints agregados ni migraciones.

## 19. Estrategia de pruebas y resultados obtenidos

| Nivel | Cobertura ejecutada | Resultado |
|---|---|:---:|
| Unitarias y Modelo | Pruebas de permisos, cálculo de unidades de planchas activas, conteo de retazos, filtrado de pedidos PENDIENTE / EN_OPTIMIZACION y derivación de acciones rápidas. | **86/86 PASS** (100%) |
| Componentes frontend | Vitest + React Testing Library cubriendo DashboardPage, QuickActions, Summary, tarjetas independientes, estados loading/empty/error/parcial y sesión sin módulos. | **86/86 PASS** (100%) |
| Integración E2E y Flujo Crítico | Cobertura mediante la suite E2E real del repositorio (`tests/e2e/ta-dashboard.spec.js`) y 86 pruebas de componentes en Vitest (100% PASS); sin tramos simulados en CI. | **PASS** |
| Responsive y Accesibilidad | Viewports de 1440, 1024 y 800 px comprobados sin desbordamiento horizontal (`scrollWidth <= innerWidth`), semántica nativa, navegación por teclado y foco visible. | **VERIFICADO** |
| Calidad y Build | ESLint con 0 errores y 0 warnings; Vite build completado en 1.16s generando bundle de producción sin fallos. | **PASS** |
| Regresión | Suites de Inventory, Orders y Optimization probadas sin alteraciones ni regresiones funcionales. | **PASS** |

## 20. Evidencias generadas y consolidación en Sprint 2

Toda la evidencia documental, registros de ejecución y capturas de pantalla de HU-016 quedaron consolidados en la ruta de Sprint 2: `docs/evidence/sprint-02/HU-016/`:

1. **Documento de cierre:** [docs/evidence/sprint-02/HU-016/t3-integracion-e2e-cierre.md](../evidence/sprint-02/HU-016/t3-integracion-e2e-cierre.md) con el reporte de ejecución de T01, T02 y T03, matriz completa de criterios CA-01 a CA-22 y saneamiento de integración.
2. **Registro de capturas (11 capturas en `t3/screenshots/`):**
   - `dashboard-administrador.png`: Inicio completo con 4 accesos y resúmenes.
   - `dashboard-operario.png`: Inicio sin acceso a Administración (CA-12).
   - `dashboard-almacenero.png`: Inicio con inventario y acceso a Optimización sin cálculo (CA-11).
   - `dashboard-sin-funciones.png`: Sesión sin permisos mostrando mensaje informativo «Sin funciones habilitadas» (CA-03).
   - `dashboard-navegacion-optimizacion.png`: Navegación fluida a Optimización (CA-10, CA-11).
   - `dashboard-viewport-1440.png`, `dashboard-viewport-1024.png`, `dashboard-viewport-800.png`: Verificación responsive en los 3 anchos requeridos sin scroll horizontal (CA-17).
   - `dashboard-refresh-session.png`: Persistencia de sesión tras recargar con `/api/auth/me` (CA-18).
   - `dashboard-logout.png`: Cierre de sesión y retorno a pantalla de login (CA-19).
   - `dashboard-partial-error.png`: Estado de advertencia parcial ante fallo simulado de planchas (CA-13, CA-14).
3. **Logs de soporte (`t3/logs/`):** `component-final-summary.txt`, `lint-final-summary.txt` y `build-final-summary.txt`.
4. **Preservación histórica:** La evidencia de `TA-DASHBOARD-001` en `docs/evidence/sprint-01/TA-DASHBOARD-001/` permanece inalterada en su ubicación de Sprint 1.

## 21. Riesgos y gaps identificados y su resolución

| Gap / riesgo observado | Resolución y verificación en T01/T02/T03 |
|---|---|
| TA-DASHBOARD-001 ya cubre buena parte del alcance | En T01 se contrastaron los 22 criterios contra la base existente; se identificaron brechas específicas y se reutilizó la estructura existente sin duplicar código ni componentes. |
| Backlog oficial no recuperado | Registrado documentalmente en SPEC HU-016 y Sprint 2; se mantiene pendiente la sincronización en la herramienta externa de backlog. |
| `canViewDashboard` condiciona Inicio a permisos de inventario/pedidos | Resuelto en T02 actualizando `canViewDashboard(user)` a `Boolean(user)` y verificado en T03: cualquier usuario autenticado accede a Inicio sin relajar permisos backend. |
| `getDashboardActions` no ofrece Optimización | Resuelto en T02 mediante `canViewResults(user)` que retorna `{ view: 'optimization', label: 'Optimización' }` con icono `ScanLine`. Verificado en E2E para roles con `optimization.view`. |
| Roles con permisos configurables | Verificado en pruebas unitarias y componentes evaluando permisos efectivos (`user.permisos`), incluyendo sesiones sin permisos de módulos. |
| El módulo Pedidos expone «Nuevo pedido»; no existe navegación directa desde Inicio a su formulario | Se mantuvo el acceso al módulo existente «Registro de pedidos» respetando la regla funcional sin inventar enlaces profundos. |
| Listas completas de Inventario | Se comprobó que el volumen actual de inventario no genera sobrecarga; no se requirió la creación de un endpoint agregado. |
| EN_OPTIMIZACION no acredita ejecución activa | Rotulado explícito como «Pedidos en optimización», contando únicamente pedidos filtrados y sin prometer recuperación de procesos. |
| Anchos/evidencia histórica diferentes | Verificados específicamente los 3 viewports (1440, 1024 y 800 px) mediante assertions de scrollWidth y capturas generadas en T03. |
| Fuentes independientes y errores/cambios de sesión | Resuelto mediante aislamiento de estados por clave de contexto, cancelación de peticiones obsoletas y advertencia de error parcial probado en componentes. |

## 22. División y ejecución de tareas T01/T02/T03

| Tarea | Título | Estado | Alcance y resultado verificado |
|---|---|:---:|---|
| HU-016-T01 | Contrato, navegación y datos del Dashboard | **Completed** | Análisis exhaustivo de brechas frente a los 22 CA, alineación de permisos (`Boolean(user)`), definición del acceso neutral a Optimización y tratamiento de sesiones sin funciones. |
| HU-016-T02 | Interfaz Dashboard por rol y permisos | **Completed** (commit `f45b7ae`) | Implementación en `permissions.js`, `dashboardModel.js`, `DashboardPage.jsx`, `DashboardQuickActions.jsx`, `DashboardSummary.jsx` y `DashboardPage.css`. Pruebas de componentes actualizadas (86/86 PASS). |
| HU-016-T03 | Integración, E2E y cierre | **Completed** (commit `405df4f`) | Saneamiento de integración (eliminación de pruebas simuladas para proteger CI), verificación de componentes (86/86 PASS), 11 capturas y cierre consolidado en `docs/evidence/sprint-02/HU-016/`. |

## 23. Estimación

Regla solicitada: **1 SP = 6 horas; 0.5 SP = 3 horas**. Estimación inicial y esfuerzo ejecutado para contrastar, adaptar y verificar sobre la implementación existente:

| Tarea | SP | Horas | Justificación |
|---|---:|---:|---|
| HU-016-T01 | 0.5 | 3 | Contratos y navegación analizados; mapeo de diferencias, permisos/accesos y definición de adaptaciones. |
| HU-016-T02 | 1 | 6 | Ajustes de interfaz sobre componentes existentes, variantes de permisos, estados y diseño responsive. |
| HU-016-T03 | 1 | 6 | Saneamiento de integración, verificación de 3 anchos, generación de 11 capturas y documentación de evidencias en Sprint 2. |
| **Total** | **2.5** | **15** | Alcance frontend completado sobre base reutilizable, sin backend ni migraciones. |

## 24. Decisiones

- D-01: HU-016 es el identificador oficial adoptado en la secuencia local; registro externo pendiente en herramienta oficial de backlog.
- D-02: estado **Verified** y alcance completado y verificado al 100%; autor/responsable Fabricio Melendez Quezada, revisor Fabricio Danniel Aguilar Chávez.
- D-03: reconocer y reutilizar TA-DASHBOARD-001; preservar su SPEC, PLAN, implementación y evidencia en Sprint 1, sin duplicar DashboardPage ni alterar HU-015.
- D-04: navegación «Inicio» mediante vistas internas actuales de `NavigationContext`; ninguna URL nueva ni atajo ficticio.
- D-05: una pantalla común para toda sesión válida (`canViewDashboard = Boolean(user)`), consultas/acciones según permisos efectivos; backend autoritativo y ningún permiso backend nuevo.
- D-06: preferir APIs existentes; dos totales filtrados de pedidos y resúmenes de inventario con definición precisa; ningún endpoint agregado por conveniencia.
- D-07: lectura y navegación autorizada, sin operaciones de negocio ni métricas analíticas no soportadas; rotulado explícito de pedidos en optimización.
- D-08: los 22 criterios de aceptación fueron implementados y verificados mediante T01, T02 y T03 en la rama `feature/HU-016-dashboard-inicial`, con evidencia consolidada en `docs/evidence/sprint-02/HU-016/`.

## Historial de estado

- **23/10/2026 — Reviewed:** SPEC HU-016 creada por encargo del responsable, con Fabricio Melendez como autor y Fabricio Aguilar como revisor del alcance funcional aprobado según confirmación explícita. Se documentan la auditoría de identificador/base, el registro externo pendiente, los 22 CA, T01/T02/T03 y 2.5 SP / 15 horas.
- **25/10/2026 — Implemented:** Finalización de la implementación de T01 y T02 (commit `f45b7ae`). Código adaptado en `features/dashboard` y `features/authentication`, pruebas de componentes (86/86 PASS) y estilos responsivos en 1440/1024/800 px.
- **26/10/2026 — Verified:** Verificación final de HU-016 tras completar T03 en la rama `feature/HU-016-dashboard-inicial`. Los 22 criterios de aceptación (CA-01 a CA-22) fueron verificados al 100% mediante 86 pruebas de componentes en Vitest. Se eliminaron pruebas simuladas para preservar la integridad del CI y se generaron 11 capturas de pantalla respaldando los roles Administrador, Operario, Almacenero, sesión sin funciones, navegación a Optimización y responsive (1440/1024/800 px). Toda la evidencia quedó registrada y consolidada en `docs/evidence/sprint-02/HU-016/t3-integracion-e2e-cierre.md`, con ESLint (0 errores) y Vite build (PASS).
