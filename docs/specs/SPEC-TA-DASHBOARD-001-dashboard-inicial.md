# SPEC-TA-DASHBOARD-001 — Dashboard inicial para usuarios de NewGlass

## Información general

| Campo | Valor |
|---|---|
| Estado | **Approved** |
| PBI relacionado | TA-DASHBOARD-001 — Dashboard inicial para usuarios de NewGlass |
| Tipo | PBI funcional nuevo; independiente de HU-015 |
| Responsable / Autor | Fabricio Melendez Quezada |
| Reviewer | Fabricio Danniel Aguilar Chávez |
| Revisión | Aprobada; revisión funcional previa confirmada por el equipo para esta SPEC. |
| Fecha de elaboración | 14/10/2026 |
| Sprint | Sprint 1 |
| Rama | `feature/TA-DASHBOARD-001` |
| Base auditada | `origin/integration/sprint-01` — `86972fd779bae826909a401874f06d5b7dd2a3ed`, merge del PR #47 |
| Convención | Archivo único `SPEC-<ID>-<tema>.md`, conforme a `SPEC-TEMPLATE.md` y `CONTRIBUTING.md`. |

Esta SPEC registra el alcance funcional aprobado. No constituye implementación, PLAN, TASKS ni evidencia de pruebas ejecutadas del Dashboard. Se reutiliza la estructura de la plantilla y de las SPEC existentes; la revisión humana aprobada procede de la confirmación expresa del equipo, sin atribuirle una ejecución técnica anticipada.

## 1. Objetivo

Proporcionar una pantalla inicial común después del inicio de sesión que permita a Administrador, Almacenero y Operario visualizar información operativa real disponible durante Sprint 1 y acceder rápidamente a las funciones que tienen autorizadas.

El Dashboard actúa como punto de entrada al sistema después del login y como vista de consulta y navegación. Compone capacidades HTTP existentes; no es una fuente de verdad de inventario o pedidos ni ejecuta optimización.

La base integrada ya contiene HU-015 mediante [PR #47](https://github.com/melendezzz26/optimizador-vidrio/pull/47). El Dashboard es un PBI separado: no amplía el alcance ni modifica la implementación, PLAN o TASKS de HU-015.

## 2. Alcance

### Incluye

- Pantalla inicial protegida para los tres roles autenticados, tanto después de login válido como tras recuperar una sesión válida al recargar.
- Opción «Inicio» o «Dashboard» en el Sidebar existente, con estado activo y navegación consistente con los módulos actuales.
- Información real de inventario de planchas y retazos obtenida de los contratos disponibles, identificando claramente qué se cuenta y su estado.
- Información real de pedidos para los roles autorizados, incluyendo `PENDIENTE` y `EN_OPTIMIZACION`, soportados por el contrato integrado.
- Información de clientes únicamente si la fuente real y los permisos del actor permiten consultarla. Existe `GET /api/clients`; incluir su resumen es opcional y nunca implica inventar una pantalla de Clientes.
- Pedidos recientes opcionales conforme al orden y alcance reales de la consulta, descritos en §4 y CA-10.
- Accesos rápidos únicamente a funciones existentes y autorizadas; consulta y navegación sin realizar mutaciones desde el Dashboard.
- Estados loading, empty, error y datos parciales cuando fuentes independientes tengan resultados distintos.
- UI/UX consistente, accesibilidad básica, teclado, foco visible, reducción de movimiento y adaptación a anchuras menores.

La selección final de tarjetas y componentes corresponde al PLAN; cada cifra elegida debe tener fuente, significado y alcance verificables en los contratos actuales.

### Fuera de alcance

- Gráficas, charts, predicciones, métricas futuras, M1/M2, aprovechamiento y merma.
- Comparaciones o ejecución de First Fit, Best Fit y Worst Fit; resultados del optimizador, rasterización, placement, selección de plancha o confirmación de solución.
- Ejecución de optimización desde el Dashboard. Consultar el estado existente `EN_OPTIMIZACION` no ejecuta ese proceso.
- Alertas de stock, umbrales o reglas de disponibilidad no formalizados; inferir que una pieza cabe o que existe stock compatible para un pedido.
- Mocks visibles, cifras de ejemplo o valores hardcodeados presentados como información operativa.
- Modificar inventario, clientes, pedidos o reglas críticas; formularios de alta/edición dentro del Dashboard.
- Nuevos roles/permisos, un nuevo sistema de autenticación o un rediseño de navegación y arquitectura.
- Cambios de esquema/migraciones y un endpoint agregado por conveniencia sin justificación técnica previa.
- Implementación, PLAN, TASKS, pruebas ejecutadas o capturas anticipadas en esta entrega documental.

Si un dato no dispone de una fuente real, se omite; no se simula.

## 3. Actor y precondiciones

**Actores:** Administrador, Almacenero y Operario autenticados.

La matriz vigente de [permisos backend](../../backend/app/core/permissions.py) y sus equivalentes de [presentación frontend](../../frontend/src/features/authentication/permissions.js) permiten:

| Información o acceso existente | Administrador | Almacenero | Operario |
|---|---|---|---|
| Dashboard protegido | Sí | Sí | Sí |
| Consulta de planchas y retazos (`CONSULTAR_STOCK`) | Sí | Sí | Sí |
| Consulta de pedidos (`GESTIONAR_PEDIDOS`) | Sí | No | Sí |
| Consulta de clientes (`GESTIONAR_PEDIDOS`) | Sí | No | Sí |
| Navegar al módulo Inventory | Sí | Sí | Sí |
| Navegar al módulo Orders | Sí | No | Sí |
| Navegar al módulo Users | Sí | No | No |

Esta matriz describe capacidades actuales, no añade permisos. Almacenero accede al Dashboard con contenido permitido de inventario; no recibe cifras de pedidos/clientes ni provoca consultas a esas fuentes restringidas. Las acciones de gestión dentro de cada módulo mantienen sus permisos originales. No se requiere un permiso backend nuevo solo para montar la pantalla.

**Precondiciones:**

- Cuenta activa, rol vigente y sesión validada por el mecanismo de Authentication existente.
- API configurada con el mecanismo actual de `VITE_API_URL` y servicios HTTP disponibles para obtener información; si una fuente falla se aplican los estados de §7.
- Datos reales o una respuesta real vacía de las fuentes consultables por el actor.
- Navegación por estado, Sidebar, layout y módulos existentes en la base integrada. No se presupone React Router ni una URL independiente por módulo.

Un usuario sin sesión válida continúa en el flujo no autenticado y no utiliza el Dashboard protegido. Ocultar un bloque o acceso no sustituye la autorización backend.

## 4. Entradas y datos

Contratos inspeccionados en la base `86972fd`; no se proponen endpoints nuevos:

| Fuente HTTP existente | Datos / alcance real | Uso permitido |
|---|---|---|
| `GET /api/auth/me` | Identidad y rol vigentes de una sesión válida. | Reutilizar recuperación/comprobación de sesión; no exponer token o credenciales. |
| `GET /api/inventory/planchas` | Lista de registros con `id_plancha`, `cantidad`, `estado`, medidas, espesor, fecha y tipo de vidrio; incluye activos e inactivos y admite cantidad cero. | Resumen real de planchas registradas/activas; distinguir número de registros de suma de unidades. No equivale a stock compatible. |
| `GET /api/inventory/retazos` | Lista de registros con `id_retazo`, `estado`, geometría, área, espesor, fecha y tipo de vidrio; un retazo es un registro unitario. | Resumen de retazos activos registrados; no inventar una cantidad por retazo ni afirmar compatibilidad geométrica. |
| `GET /api/orders` | `items`, `total`, `page`, `limit`, `total_pages`; filtros `estado`, `cliente`, `fecha`. Resúmenes con ID, estado, `fecha_registro` y cliente visible. | Pedidos y contadores por `PENDIENTE` / `EN_OPTIMIZACION`, exclusivamente para los roles autorizados. Usar `total` del filtro para un total, no `items.length` de una página. |
| `GET /api/clients` | Lista real con ID, nombre, estado y fecha; filtros opcionales `document` y `query`; no expone un total paginado ni un filtro `estado` en la ruta actual. | Resumen opcional para Administrador/Operario; derivar un conteo solo de la lista efectivamente recibida y del alcance rotulado. Omitir para un actor sin permiso. |

Reglas de interpretación de los datos:

- Un resumen de planchas activas con unidades debe derivar de registros con `estado=true` y `cantidad>0`; su etiqueta distinguirá registros y unidades. No se contará un registro inactivo como disponible ni una cantidad cero como unidad disponible. Esto reutiliza datos/reglas existentes, sin crear una política de stock nuevo.
- Un resumen de retazos activos se deriva de `estado=true` y cuenta registros unitarios. «Activo registrado» no acredita por sí solo que sirva para un pedido ni define una alerta de reutilización.
- Si solo se muestra una página/subconjunto, el Dashboard debe identificar ese alcance. No extrapola totales desde datos incompletos ni duplica reglas críticas de disponibilidad.
- El listado Orders integrado ordena primero no cancelados, luego `fecha_registro` descendente e `id_pedido` descendente. Si se presenta una sección de pedidos recientes con ese contrato, se documenta y comunica ese orden de gestión; no se presenta una página como los últimos pedidos absolutos de todos los estados. Un orden diferente debe justificarse en el PLAN con datos completos y una fuente real, sin inventar un parámetro de orden no soportado.
- Los números/fechas se presentan conforme a su serialización real, con unidades cuando corresponda; no asumir que todo Decimal HTTP llega como `number`.
- No se mostrarán documentos/teléfonos de clientes ni otros datos personales ajenos al resumen necesario. No se crean datos sintéticos en esta etapa.

Fuentes de contrato: [Inventory router](../../backend/app/modules/inventory/presentation/router.py) y [schemas](../../backend/app/modules/inventory/presentation/schemas.py); [Orders router](../../backend/app/modules/orders/presentation/router.py) y [repositorio](../../backend/app/modules/orders/infrastructure/repositories.py); [Clients router](../../backend/app/modules/clients/presentation/router.py) y [schemas](../../backend/app/modules/clients/presentation/schemas.py).

## 5. Reglas de negocio

- **RN-01:** El Dashboard es de consulta y navegación; no cambia inventario, pedidos, estados ni datos de clientes, y no ejecuta optimización.
- **RN-02:** Toda cifra, listado o resumen operativo proviene de respuestas HTTP reales. Se omite una capacidad sin fuente; un error no se sustituye por cero, mocks o información de ejemplo.
- **RN-03:** Las fuentes y accesos se seleccionan según permisos actuales del actor. La autorización definitiva sigue en backend en cada solicitud. No se consultan pedidos/clientes para Almacenero ni se amplían permisos para alimentar esta pantalla.
- **RN-04:** Frontend puede transformar DTOs, contar/sumar campos permitidos y preparar su presentación; no duplica validaciones críticas del negocio ni decide viabilidad/compatibilidad de stock.
- **RN-05:** Todo contador declara qué representa, estado/filtro y alcance. Se conserva la distinción entre registros, unidades y totales paginados de §4.
- **RN-06:** El contenido refleja las consultas realizadas; no promete una instantánea transaccional entre fuentes independientes ni datos en tiempo real. No se requiere polling para el alcance inicial.
- **RN-07:** Carga, vacío y error se distinguen. Si se muestran datos parciales, cada fuente fallida tiene feedback propio y los resultados válidos no se fabrican ni se presentan como pertenecientes a otra sesión.
- **RN-08:** Inicio de sesión válido conduce al Dashboard. Refresh con sesión válida conserva el flujo autenticado; logout elimina sesión y datos protegidos conforme a Authentication existente. Una respuesta tardía no reintroduce datos de la sesión cerrada.
- **RN-09:** Los accesos rápidos resuelven hacia módulos/funciones implementados. No se añade un botón Clientes hacia una pantalla independiente inexistente, ni botones de resultados/ejecución futuros.
- **RN-10:** No se añade un endpoint únicamente para el Dashboard cuando puede componerse con contratos existentes. Si el PLAN demuestra una necesidad técnica real de agregación, debe justificarla y obtener su revisión antes de implementar cambios backend.

## 6. Flujo principal

1. El usuario se autentica mediante Login y Authentication existentes.
2. La aplicación entra al Dashboard protegido; «Inicio» o «Dashboard» queda activo en el Sidebar.
3. El sistema determina las fuentes y accesos permitidos por el rol vigente y muestra loading identificable en los bloques que lo necesiten.
4. Consulta las fuentes HTTP existentes y presenta resúmenes/listados reales con etiquetas y alcance comprensibles. Almacenero recibe únicamente contenido autorizado.
5. Cada bloque informa resultado válido, vacío o error; las consultas independientes pueden conservar sus resultados válidos si otra falla.
6. El usuario activa un acceso rápido permitido y navega al módulo existente, que conserva sus propias reglas y autorización.
7. Puede volver al Dashboard mediante el Sidebar y consultar nuevamente información real conforme al mecanismo que defina el PLAN.
8. Al refrescar se valida la sesión existente; al cerrar sesión se elimina y se vuelve al flujo no autenticado, retirando datos protegidos.

El flujo no crea ni modifica registros operativos.

## 7. Flujos alternativos y errores

- **Sesión en comprobación:** mostrar el estado existente de comprobación; no presentar datos protegidos antes de confirmar la sesión.
- **Sin sesión / sesión vencida / 401:** seguir el manejo global de Authentication, retirar información protegida y devolver al flujo no autenticado.
- **Permiso perdido / 403:** informar de forma comprensible y retirar/bloquear el contenido afectado conforme a la política de sesión/rol vigente; no reemplazarlo con datos inventados ni conceder acceso localmente.
- **Carga:** informar espera; un placeholder no se presenta como cifra real y no parpadean contadores ficticios.
- **Respuesta válida sin registros:** mostrar un empty comprensible. Un contador cero solo es válido si se deriva de una respuesta exitosa correspondiente a ese alcance.
- **Red, servidor o respuesta inválida:** feedback textual seguro y posibilidad de recuperar la consulta según el patrón existente; sin stack trace, SQL, secretos ni valores falsos.
- **Fallo parcial:** si se implementan bloques independientes, conservar los resultados válidos y señalar cuál fuente falló; no hacer pasar el panel entero por actualizado correctamente.
- **Fuente opcional no disponible:** omitirla cuando no exista soporte real; si una fuente real seleccionada falla, tratarlo como error, no como ausencia de capacidad o cero.
- **Cambio de módulo o cierre de sesión durante una consulta:** no publicar resultados tardíos como información de otro contexto/sesión.

## 8. Criterios de aceptación

- **CA-01 — Redirección después del login:** después de autenticarse correctamente, el usuario es dirigido al Dashboard. La navegación no deja al usuario autenticado en Login; se conserva el mecanismo real de navegación del proyecto.
- **CA-02 — Navegación principal:** Dashboard aparece como «Inicio» o «Dashboard» en el Sidebar existente. Al estar en esta pantalla, la opción refleja el estado activo según el patrón visual actual y su semántica accesible.
- **CA-03 — Acceso por roles:** Administrador, Almacenero y Operario autenticados acceden al Dashboard. Un usuario no autenticado no utiliza la pantalla protegida.
- **CA-04 — Permisos reales:** las acciones visibles respetan las capacidades reales de cada rol; no se presenta una acción funcional sin autorización para ejecutarla. Backend conserva la autorización definitiva. No se consulta una fuente restringida para un rol sin permiso.
- **CA-05 — Datos reales:** toda cifra, contador, listado y resumen mostrado se obtiene de datos reales del sistema. No hay métricas simuladas, ejemplos ni valores hardcodeados presentados como datos operativos.
- **CA-06 — Inventario de planchas:** cuando haya información disponible mediante el contrato de inventario, puede mostrarse un resumen real de planchas disponibles/activas, derivado de su estado/cantidad conforme a §4. Se distingue número de registros de unidades; no se usa una constante local.
- **CA-07 — Inventario de retazos:** puede mostrarse un resumen real de retazos activos registrados mediante el contrato actual; no se infiere reutilización para un pedido ni se calculan métricas adicionales no definidas.
- **CA-08 — Pedidos:** para los roles con permiso, Dashboard muestra información real de pedidos e incluye al menos los estados relevantes soportados `PENDIENTE` y `EN_OPTIMIZACION`. No inventa estados ni concede a Almacenero una consulta que el contrato le niega.
- **CA-09 — Clientes condicionados a soporte real:** información de clientes solo se muestra si hay una fuente real y accesible para el actor. En la base existe `GET /api/clients`, protegido por `GESTIONAR_PEDIDOS`; sin esa capacidad/permisos se omite por completo la sección/KPI. No se sustituye con un mock.
- **CA-10 — Pedidos recientes:** si se incluye esa sección, se basa en pedidos reales y su orden deriva de campos existentes y queda documentado. Se respeta el orden actual de gestión (no cancelados primero, fecha e ID descendentes), o se justifica en PLAN otro orden sustentado por una fuente real; no se atribuye cronología global a una página incompleta.
- **CA-11 — Resumen de inventario:** los resúmenes mantienen coherencia con las respuestas de los servicios existentes, sus estados y alcance. El Dashboard no se convierte en fuente de verdad del inventario.
- **CA-12 — Accesos rápidos:** solo dirigen a rutas o funciones existentes y se muestran conforme a permisos. No hay botones decorativos hacia páginas inexistentes ni ejecuciones de optimización desde Dashboard.
- **CA-13 — Sin métricas futuras:** el Dashboard Sprint 1 no muestra merma, aprovechamiento, M1/M2, FF/BF/WF, resultados del optimizador, gráficas, predicciones, umbrales de stock ni alertas no formalizadas. Su incorporación corresponde a PBIs posteriores con fuente y reglas definidas.
- **CA-14 — Loading:** durante la carga se comunica claramente la espera; no se muestran valores temporales como datos reales ni parpadean métricas ficticias.
- **CA-15 — Empty:** una fuente válida sin registros presenta un vacío comprensible, diferenciado de un error técnico. Un cero debe proceder de una respuesta real exitosa, no de un fallback ante fallo.
- **CA-16 — Error y datos parciales:** ante una consulta fallida hay feedback visible y comprensible. Si otras fuentes independientes respondieron, puede conservarse su información válida indicando qué bloque falló. Ningún error de red/API se reemplaza con valores falsos.
- **CA-17 — Accesibilidad e interacción:** controles utilizables por teclado, foco visible, semántica adecuada de botones/enlaces y estados comunicados también mediante texto. Labels/nombres accesibles cuando correspondan; animaciones discretas que respeten `prefers-reduced-motion`.
- **CA-18 — Responsive, sesión y flujo crítico:** Dashboard es utilizable en el desktop objetivo de NewGlass y en anchuras menores sin perder acciones esenciales. Refresh con sesión válida conserva el flujo autenticado; logout elimina la sesión y devuelve al flujo no autenticado. El flujo login → Dashboard → función permitida queda preparado para una prueba E2E real, junto con refresh/logout y navegación según permisos.

## 9. Impacto técnico

### Módulos

| Área | Impacto esperado |
|---|---|
| Frontend | Sí: nueva funcionalidad de consulta/presentación en el patrón feature-first existente. |
| Backend | Consumo de capacidades actuales. Toda modificación adicional requiere justificación y revisión durante PLAN. |
| Inventario | Solo lectura; no altas, bajas, reservas ni consumo. |
| Pedidos | Solo lectura y navegación al módulo existente; no creación, edición o transición desde Dashboard. |
| Autenticación | Integración con sesión, rol, comprobación al refresh y logout existentes. |
| UI/UX | Sí: pantalla inicial y acceso principal con blueprint actual. |
| E2E | Sí, después de estabilizar el flujo implementado. |

### API

Componer los GET auditados en §4 y reutilizar servicios/capa HTTP existentes, configuración base y tratamiento de sesión. React se limita a presentación, interacción y transformación de datos de transporte. No accede directamente a PostgreSQL/Supabase, no duplica reglas críticas y no introduce una API de Dashboard por conveniencia. La eventual necesidad técnica de un agregado deberá quedar sustentada y revisada en PLAN antes de implementarse.

### Base de datos / migración

No se prevén cambios de esquema ni migraciones. Esta SPEC no autoriza DDL ni cambios de datos. Las pruebas futuras usarán datos sintéticos controlados y cleanup específico, sin alterar registros ajenos.

### UI

- Conservar el blueprint NewGlass: desktop-first, superficies/tokens existentes y jerarquía título → resumen → contenido → accesos.
- Reutilizar AppShell, Sidebar, PageHeader/PageCard, feedback y componentes pertinentes; no crear un segundo sistema de diseño.
- Mantener navegación por estado y un único punto principal en Sidebar; el header conserva identidad/sesión/logout.
- Loading/error/empty textuales, foco visible, teclado, labels/nombres accesibles y semántica nativa; no depender únicamente del color.
- Responsive sin ocultar funciones esenciales; evitar overflow que impida usar los controles.
- Animaciones o microinteracciones sutiles y respetuosas de `prefers-reduced-motion`; sin movimiento necesario para interpretar datos.

El layout concreto, componentes, estrategia de consultas y cambios de montaje corresponden al PLAN; no se prescriben aquí una biblioteca de gráficas, React Router ni una implementación nueva de sesión.

## 10. Pruebas previstas

No se ejecutan pruebas del Dashboard antes de implementarlo. Los resultados de HU-015 no validan este nuevo PBI.

| Nivel | Cobertura mínima prevista |
|---|---|
| Component / Unit | Transformación de respuestas reales/fixtures de contrato a KPIs o resúmenes; distinción registros/unidades/total paginado; visibilidad de fuentes y acciones según rol. |
| Componentes frontend | Vitest + React Testing Library según configuración/estándares existentes: loading, empty, error, contenido válido, estados parciales si se implementan, acceso protegido, navegación y semántica accesible. |
| Regresión frontend | Sesión, roles, Sidebar, Orders e Inventory continúan funcionando; logout/401 retiran datos protegidos y se descartan resultados obsoletos. Unit/component, lint y build según el alcance real del cambio. |
| E2E posterior | Playwright con navegador real, backend y datos controlados una vez estabilizada la integración: login válido → Dashboard → información real → función permitida. También refresh con sesión válida, logout y navegación por permisos para los tres roles. |

Las unitarias aislables siguen la suite vigente; las pruebas de componente usan Vitest/RTL. El PLAN precisará ubicación y comandos sin sustituir herramientas por preferencia. Mocks de contrato son válidos para componentes, pero no se presentarán como integración real ni como datos visibles de producción. Credenciales/secretos se suministrarán por mecanismos de entorno/fixtures seguros, nunca hardcodeados.

## 11. Evidencias requeridas

Evidencia futura, todavía no generada:

- Resultados reales de pruebas unit/component con comandos, contexto y conteos.
- Build frontend y lint correspondientes a la implementación final.
- E2E del flujo crítico y resultados reales de refresh/logout/permisos; distinguir ejecuciones de colecciones y skips.
- Captura auténtica o evidencia reproducible del Dashboard implementado, datos reales y estados relevantes, sin secretos ni datos personales innecesarios.
- Trazabilidad **PBI TA-DASHBOARD-001 → SPEC aprobada → PLAN posterior → implementación → pruebas → evidencia → PR/revisión humana**.

No se crea evidencia falsa ni se marca la funcionalidad Implemented/Verified anticipadamente. El cierre futuro requiere comprobar los CA sobre la implementación y su evidencia, además de revisión humana.

Referencias de ingeniería: [CONTRIBUTING](../../CONTRIBUTING.md), [ADR-001](../adr/ADR-001-seleccion-arquitectura.md), [pruebas](../testing/README.md), [UI/UX](../ui-ux/README.md), [base visual](../ui-ux/inventario-base-visual.md), [feedback compartido](../ui-ux/feedback-compartido.md), [SPEC HU-001](SPEC-HU-001-inicio-login.md) y [SPEC HU-015](SPEC-HU-015-interfaz-rasterizacion.md). Las notas históricas de esos documentos se contrastan con el código integrado de la base indicada, no se convierten en nuevos contratos.

## Historial de estado

- 14/10/2026 — **Approved**: creación documental de la SPEC TA-DASHBOARD-001 conforme a la revisión funcional previa **aprobada por Fabricio Danniel Aguilar Chávez**, confirmada por el equipo. Autor: Fabricio Melendez Quezada. Se registran 18 CA verificables y el alcance de consulta/navegación Sprint 1, con fuentes/permisos reales. Sin implementación, PLAN, TASKS, pruebas ejecutadas, evidencia nueva, push o PR en esta entrega.
