# SPEC-HU-016 — Dashboard inicial para usuarios de NewGlass

## Información general

| Campo | Valor |
|---|---|
| Identificador / PBI relacionado | **HU-016** |
| Título | Dashboard inicial para usuarios de NewGlass |
| Estado | **Reviewed** |
| Autor / responsable principal de implementación | Fabricio Melendez |
| Revisor del alcance | Fabricio Aguilar |
| Fecha de elaboración y registro de aprobación | 23/10/2026 |
| Decisión | Alcance funcional revisado y aprobado por Fabricio Aguilar, según la confirmación explícita del solicitante. |
| Tipo | Historia de usuario; independiente de HU-015. |
| Base inspeccionada | `b1112a43579961aff52b57cb469607711e10bdf8`, coincidente con `integration/sprint-01` local. |
| Rama inspeccionada | `fix/S1-02-execution-budget`; no se cambia la rama ni se incorpora implementación de S1-02. |
| Registro de Product Backlog | Pendiente en el backlog externo; esta SPEC documenta la ficha propuesta, no sustituye su fuente oficial. |
| PLAN | No creado. T01/T02/T03 son una división propuesta para revisión y planificación posterior. |

Se utiliza **Reviewed** conforme al ciclo de [SPEC-TEMPLATE](SPEC-TEMPLATE.md): Draft → Reviewed → Implemented → Verified. La aprobación funcional ya comunicada por Fabricio Aguilar habilita la especificación; no acredita implementación, pruebas, verificación ni una nueva revisión humana del archivo generado. El antecedente TA-DASHBOARD-001 conserva sus estados históricos Approved/Verified; no se modifica ni se traslada su verificación a HU-016.

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

HU-016 documenta el alcance aprobado y sus 22 criterios propios sobre esa base reutilizable. T01 deberá contrastar cobertura y diferencias; los comportamientos ya satisfechos se conservan y su evidencia se referencia con fecha/base. No se renombra, elimina ni reabre TA-DASHBOARD-001, no se declara que HU-016 ya esté implementada y no se atribuyen sus horas o pruebas históricas a este nuevo PBI.

Problema que formaliza la historia: disponer de una única entrada autenticada con información operacional real, navegación autorizada y comportamiento consistente, evitando cifras ficticias, acciones sin permiso y resultados parciales interpretados como totales. Entre las brechas visibles están el acceso a Inicio condicionado hoy a `inventory.view`/`orders.view`, los accesos rápidos sin Optimización y la necesidad de verificar los tres anchos solicitados. Véase §21.

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

| Destino existente | Etiqueta coherente | Regla funcional |
|---|---|---|
| `dashboard` | Inicio | Disponible para sesión autenticada; no concede acceso a datos. |
| `orders` | Registro de pedidos | Navegar con `orders.view`; el módulo administra sus acciones. |
| `optimization` | Optimización | Navegar con `optimization.view`. Solo se describe como acceso para calcular si también existe `optimization.execute`; nunca inicia una corrida desde Inicio. |
| `inventory` | Gestión de inventario | Navegar con `inventory.view`. |
| `users` | Administración | Acceso según `users.view` o `roles.view`; cada pestaña mantiene su autorización. |

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
- La regla actual de `canViewDashboard` exige `inventory.view` u `orders.view`; T01 debe alinear la superficie de Inicio con el requisito de cualquier sesión válida, sin relajar un solo permiso de datos o módulos.
- Un rol sin permisos de fuentes ve una pantalla válida de Inicio sin cifras ni solicitudes restringidas, con feedback y logout; no se interpreta la ausencia de permisos como cero registros.
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

Reutilizar AppShell, Sidebar, PageHeader/PageCard, tokens, tarjetas y feedback vigentes. Estructura conceptual: Inicio → saludo e identidad → resumen operativo → accesos rápidos. La composición final puede adaptar el layout propuesto a los estilos existentes; no se crea otro sistema de diseño.

Comprobar **1440, 1024 y 800 px** de ancho: sin overflow horizontal, solapamientos o texto ilegible; tarjetas adaptables, accesos utilizables y Sidebar funcional. Alinear el comportamiento a 800 px con el patrón actual del Sidebar. Las capturas anteriores de otros anchos no acreditan automáticamente estos tres. No se exige un número fijo de columnas ni una biblioteca de gráficas.

## 14. Accesibilidad

Aplicar la línea base de [UI/UX](../ui-ux/README.md) y [feedback compartido](../ui-ux/feedback-compartido.md): navegación por teclado, orden de foco coherente y visible, headings semánticos, botones/enlaces nativos con nombres accesibles, contraste conforme a los tokens revisados y mensajes de error textuales. No comunicar estados solo con color. Conservar el acceso para saltar al contenido del shell y respetar reducción de movimiento si se utilizan animaciones. No se afirma certificación WCAG.

## 15. Criterios de aceptación

| ID | Criterio verificable |
|---|---|
| CA-01 | Después de autenticarse correctamente, cualquier usuario con sesión válida llega a Inicio. |
| CA-02 | Inicio puede abrirse nuevamente desde Sidebar y refleja la vista activa de forma visual y accesible. |
| CA-03 | Administrador, Operario y Almacenero autenticados acceden a la misma pantalla común; una sesión sin permisos de fuentes conserva la superficie de Inicio sin consultas restringidas. |
| CA-04 | Las fuentes y accesos visibles corresponden únicamente a los permisos efectivos actuales; el rol no concede excepciones adicionales. |
| CA-05 | Mostrar/ocultar opciones no sustituye la autorización backend; solicitudes directas siguen protegidas por los permisos existentes. |
| CA-06 | Todas las cifras mostradas proceden de respuestas reales exitosas y tienen significado/alcance explícitos; no hay números ficticios. |
| CA-07 | Con `orders.view`, Inicio muestra el total de pedidos PENDIENTE usando `total` del contrato filtrado existente. Sin permiso, no consulta ni muestra ese bloque. |
| CA-08 | Con `orders.view`, Inicio muestra el total de pedidos EN_OPTIMIZACION mediante el mismo contrato; no lo presenta como número de ejecuciones activas. |
| CA-09 | Todo resumen de Inventario utiliza las listas reales autorizadas, distingue registros/unidades y no inventa disponibilidad o compatibilidad. |
| CA-10 | Los accesos rápidos navegan a los módulos existentes de §8, sin URLs ficticias ni operaciones de negocio al pulsarlos. |
| CA-11 | Almacenero sin `optimization.execute` no recibe una acción de ejecución. Una consulta autorizada por `optimization.view` no se presenta como permiso para calcular o confirmar. |
| CA-12 | Operario sin `users.view` no recibe acciones de Usuarios; Administración respeta separadamente los permisos de sus pestañas. |
| CA-13 | La pantalla contempla loading, empty, error y success por fuente, reintento, disabled temporal y datos parciales cuando corresponda. |
| CA-14 | Un fallo recuperable no muestra información inventada u obsoleta como vigente; respuestas tardías no contaminan otro contexto de sesión/permisos. |
| CA-15 | El MVP no muestra merma, aprovechamiento, ahorro, eficiencia ni comparativas FF/BF/WF. La existencia actual de resultados First Fit en otro módulo no incorpora esos indicadores a Inicio. |
| CA-16 | La pantalla puede operarse con teclado, mantiene foco visible, semántica y nombres accesibles; los estados no dependen exclusivamente del color. |
| CA-17 | Inicio funciona sin overflow horizontal ni solapamientos en 1440, 1024 y 800 px, con tarjetas, textos, accesos y Sidebar utilizables. |
| CA-18 | Refresh desde Inicio sobre la URL base/subpath vigente recupera una sesión válida y presenta una pantalla autenticada válida, sin exigir una URL nueva. |
| CA-19 | Logout desde Inicio conserva el flujo actual: elimina la sesión, retira datos protegidos y retorna al acceso no autenticado. |
| CA-20 | Login → Inicio → módulo autorizado tiene cobertura E2E con navegador, API y datos controlados reales; incluye retorno a Inicio, refresh y logout. |
| CA-21 | Las principales variantes de los tres roles, permisos configurados/revocados y sesión sin fuentes autorizadas tienen pruebas automatizadas de componentes/permisos. |
| CA-22 | La navegación existente a Pedidos, Optimización, Inventario y Administración/Usuarios conserva sus flujos y autorizaciones; HU-015 no se modifica. |

## 16. Fuera de alcance

- Gráficos analíticos avanzados, actividad histórica compleja, tendencias, filtros temporales y productividad histórica.
- Personalización de widgets, drag and drop y preferencias por usuario.
- KPI financieros, ahorro/reducción de costos, merma, aprovechamiento y eficiencia o comparación FF/BF/WF.
- Implementar heurísticas, placement, rasterización, selección de planchas, iniciar o confirmar optimizaciones desde Inicio.
- Notificaciones, alertas/umbrales de inventario y una pantalla global de movimientos inexistente.
- Nuevos permisos, cambios de RBAC, backend nuevo sin necesidad demostrada, BD/migraciones y persistencia de Dashboard.
- Cambiar HU-015 o resolver S1-02 y otros hallazgos de la auditoría.
- Implementación, PLAN completo, componentes nuevos, endpoints, pruebas ejecutadas de producto o evidencia visual nueva en esta entrega.

## 17. Restricciones e invariantes

Dashboard es inicialmente una superficie de lectura/navegación. No consume stock, no modifica inventario, no cambia estados de pedidos, no inicia optimizaciones automáticamente, no modifica usuarios y no introduce persistencia propia. Las acciones rápidas solo conducen a módulos que conservan sus reglas y permisos. Logout y sesión mantienen su almacenamiento ya existente, sin crear preferencias de Dashboard.

No se toca `frontend/src/`, `backend/`, migraciones, dependencias ni workflows durante esta fase. No se crea otro DashboardPage. Tampoco se ejecutan git add/commit/push/merge/rebase, PR ni deploy.

## 18. Impacto técnico previsto

La implementación posterior reutilizará la feature Dashboard y sus pruebas; T01 identificará los ajustes mínimos para los nuevos criterios. Posibles puntos de integración: montaje de Inicio, reglas frontend de navegación, modelo de accesos/datos y componentes actuales. No se prescribe reescribirlos ni cambiar React/navegador/router. Backend, contratos de negocio, BD y HU-015 permanecen sin cambios previstos. Un eventual agregado requiere justificar el gap y revisar su alcance antes de implementarlo; esta SPEC no es una autorización para crearlo.

## 19. Estrategia de pruebas

| Nivel | Cobertura prevista |
|---|---|
| Unitarias/modelo | Transformación de respuestas, `total` frente a tamaño de página, unidades frente a registros, permisos de fuentes/accesos, ausencia de métricas fuera de alcance y contadores cero válidos. |
| Componentes | Vitest/React Testing Library sobre la base existente: tres roles, permisos efectivos, ausencia/revocación de permisos, Inicio sin fuentes, estados independientes, reintento, navegación y respuestas tardías. |
| E2E | Playwright: login → Inicio → módulos autorizados para cada rol; regreso desde Sidebar; refresh; logout; no ejecución por Almacenero sin permiso; no Usuarios para Operario sin permiso. |
| Responsive/accesibilidad | Viewports 1440/1024/800, overflow y solapamientos; recorrido con teclado y foco visible; nombres/estructura semántica; capturas reales revisadas. |
| Regresión | Navegación y permisos de Pedidos/Optimización/Inventario/Administración, sesión y casos existentes de HU-015 pertinentes; no cambiar sus fuentes para adaptar la prueba. |

Usar la estrategia de [pruebas del repo](../testing/README.md). Los mocks son adecuados para componentes y fallos controlados, pero no demuestran integración real. Los E2E usarán datos/usuarios sintéticos controlados, preferentemente el harness local de PostgreSQL existente, sin alterar datos compartidos ni copiar credenciales. Una omisión por falta de entorno se informa como bloqueo, no como CA verificado. No se modifica CI como parte de esta SPEC.

## 20. Evidencias esperadas

En el cierre posterior se prevé `docs/evidence/sprint-01/HU-016/` como ubicación documental conforme al repositorio, sin atribuir por ello un compromiso nuevo de sprint. Debe contener base/fecha/comandos/resultados, matriz CA-01…CA-22, relación con la base TA-DASHBOARD-001, capturas revisadas por rol y ancho, E2E real, pruebas de componentes, lint/build aplicables y regresión de navegación. Redactar identidades cuando corresponda y no incluir tokens/secretos.

Las evidencias anteriores de TA-DASHBOARD-001 y HU-015 permanecen intactas. No se copian sus resultados como si se hubieran ejecutado para HU-016. En esta entrega solo se verifica la documentación; no se crea todavía la carpeta de evidencia funcional ni se atribuye ningún PASS de producto.

## 21. Riesgos y gaps que T01 debe verificar

| Gap / riesgo observado | Tratamiento requerido |
|---|---|
| TA-DASHBOARD-001 ya cubre buena parte del alcance | Mapear código/pruebas/evidencia contra los 22 CA; evitar trabajo duplicado y aclarar la relación en el backlog externo. |
| Backlog oficial no recuperado | Registrar HU-016 externamente tras contrastar el identificador; no afirmar reserva global por una búsqueda local. |
| `canViewDashboard` condiciona Inicio a permisos de inventario/pedidos | Verificar y ajustar en implementación futura la superficie para cualquier sesión válida, sin ampliar permisos de fuentes/módulos. |
| `getDashboardActions` no ofrece Optimización | Definir navegación mediante la vista existente y separar consulta de ejecución; no crear rutas o ejecutar POST desde Inicio. |
| Roles con permisos configurables | Probar permisos efectivos, revocaciones y ausencia de permisos; no extrapolar la asignación inicial como regla permanente. |
| El módulo Pedidos expone «Nuevo pedido»; no existe navegación directa desde Inicio a su formulario | Mantener acceso al módulo y comprobar `orders.create` dentro de él; no inventar un atajo profundo ni ampliar este PBI a corregir todo el módulo. |
| Listas completas de Inventario | Medir volumen/bytes; omitir indicadores no razonables o justificar un agregado mediante revisión separada. No inferir necesidad sin datos. |
| EN_OPTIMIZACION no acredita ejecución activa | Contar y rotular pedidos; no normalizar históricos ni prometer recuperación automática. |
| Anchos/evidencia histórica diferentes | Verificar específicamente 1440/1024/800 para HU-016; no dar por probado el criterio por capturas anteriores. |
| Fuentes independientes y errores/cambios de sesión | Datos parciales explícitos, invalidación/cancelación de respuestas obsoletas y ninguna sustitución por cero. |

## 22. División propuesta T01/T02/T03

| Tarea | Título | Alcance y cierre previsto |
|---|---|---|
| HU-016-T01 | Contrato, navegación y datos del Dashboard | Contrastar rutas/permisos y antecedente; definir fuentes/modelo frontend; alinear entrada tras login, refresh y sesión sin fuentes; decidir accesos reales y datos razonables; pruebas de contrato/navegación. Cierre con decisiones trazables y sin backend nuevo injustificado. |
| HU-016-T02 | Interfaz Dashboard por rol | Reutilizar DashboardPage, tarjetas y accesos; saludo/estructura común; contenido Administrador/Operario/Almacenero según permisos; loading/empty/error/success/disabled; responsive y accesibilidad; pruebas de componentes. No crear tres pantallas ni duplicar la implementación existente. |
| HU-016-T03 | Integración, E2E y cierre | Login → Inicio → módulo autorizado; navegación por permisos, regreso, refresh, logout y regresión; Playwright con datos controlados; 1440/1024/800, teclado y foco; evidencia y matriz CA; documentación final con resultados reales. |

Son tareas propuestas de este PBI; no se presentan como tareas históricas recuperadas de un backlog. Orden de dependencia T01 → T02 → T03; no constituyen un PLAN técnico completo ni autorización de implementación en esta fase.

## 23. Estimación

Regla solicitada: **1 SP = 6 horas; 0.5 SP = 3 horas**. Estimación inicial de esfuerzo para contrastar/adaptar y verificar sobre la implementación existente, no para construir el Dashboard desde cero ni para cubrir un plazo personal.

| Tarea | SP | Horas | Justificación |
|---|---:|---:|---|
| HU-016-T01 | 0.5 | 3 | Los contratos y la navegación existen; el esfuerzo se concentra en mapear diferencias, permisos/accesos y pruebas de contrato de la adaptación. |
| HU-016-T02 | 1 | 6 | Ajustes de interfaz sobre componentes actuales, variantes de permisos, estados y pruebas responsive/accesibles; sin duplicar la pantalla. |
| HU-016-T03 | 1 | 6 | Ampliar/reutilizar los E2E, verificar tres roles y tres anchos, sesión/navegación, regresiones y evidencia revisada. |
| **Total** | **2.5** | **15** | Alcance frontend sobre base reutilizable, sin backend ni migraciones. |

El PLAN posterior refinará la estimación tras T01 si aparece una necesidad demostrada. No se suman horas históricas de TA-DASHBOARD-001 ni se incluye un endpoint agregado no aprobado. Las pruebas/evidencias existentes reducen implementación, pero no acreditan automáticamente los nuevos criterios.

## 24. Decisiones

- D-01: HU-016 es el siguiente identificador disponible en la secuencia local; registro externo pendiente y sin creación de backlog alternativo.
- D-02: estado Reviewed y alcance aprobado por Fabricio Aguilar; autor/responsable Fabricio Melendez. No declarar Implemented/Verified por esta entrega documental.
- D-03: reconocer y reutilizar TA-DASHBOARD-001; preservar su SPEC, PLAN, implementación y evidencia, sin duplicar DashboardPage ni retocar HU-015.
- D-04: navegación «Inicio» mediante vistas internas actuales; ninguna URL nueva ni atajo sin soporte real.
- D-05: una pantalla para toda sesión válida, consultas/acciones según permisos efectivos; backend autoritativo y ningún permiso específico nuevo.
- D-06: preferir APIs existentes; dos totales filtrados de pedidos y resúmenes de inventario con definición precisa; agregado solo con necesidad demostrada y revisión posterior.
- D-07: lectura/navegación, sin operaciones de negocio ni métricas analíticas; EN_OPTIMIZACION cuenta pedidos y no ejecuciones activas.
- D-08: 22 CA, tareas propuestas y estimación incluidas en este único archivo; no crear PLAN completo ni implementación en esta fase.

## Historial de estado

- **23/10/2026 — Reviewed:** SPEC HU-016 creada por encargo del responsable, con Fabricio Melendez como autor y Fabricio Aguilar como revisor del alcance funcional ya aprobado según la confirmación explícita recibida. Se documentan la auditoría de identificador/base, el registro externo pendiente, los 22 CA, T01/T02/T03 y 2.5 SP / 15 horas. No se implementó código, no se ejecutaron pruebas de producto, no se modificó HU-015 ni se creó PLAN, commit, push, PR, merge o deploy.
