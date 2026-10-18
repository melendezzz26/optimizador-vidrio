# TA-DASHBOARD-001-T2 — Interfaz Dashboard

Fecha: 14/10/2026. Rama: `feature/TA-DASHBOARD-001`. HEAD inicial `cedd9ed`, árbol limpio; T1 `d912c6a`/`cedd9ed` presentes y base conocida `86972fd`. SPEC Approved, 18 CA; PLAN Draft y sin constancia adicional de aprobación técnica humana. **Human PLAN approval still pending**. La autorización de implementación T2 no cambia ese estado documental.

## Alcance y archivos

Se reemplazó la presentación mínima por encabezado, tarjetas de resumen, listado de pedidos y accesos rápidos. La estructura sigue siendo plana dentro de `features/dashboard/`; no se crea una organización paralela ni un segundo sistema visual.

- Modificado `DashboardPage.jsx`: compone UI y mantiene useDashboard/AppShell/sesión existentes.
- Nuevos `DashboardSummary.jsx`, `DashboardOrders.jsx`, `DashboardQuickActions.jsx` y `DashboardSource.jsx`: resúmenes, lista, navegación por NavigationContext y feedback de fuente.
- Nuevo `DashboardPage.css`: estilos locales con tokens y breakpoints existentes (1000/600 px); AppShell conserva su adaptación de Sidebar a 800 px.
- Nuevo `__tests__/DashboardPage.test.jsx`; ampliado `DashboardNavigation.test.jsx` con tres casos que navegan por accesos rápidos a módulos reales desde App. Los mocks adicionales de Users en esa prueba responden a sus GET existentes; no cambian producto ni aserciones previas.
- PLAN actualiza únicamente checklist/historial de T2; este archivo registra sus resultados.

Reutilización: PageCard/PageHeader/AppShell, Sidebar y SessionBar sin rediseño; botones `ng-button`, LoadingState/EmptyState/FeedbackMessage, tokens, foco visible y loader con reduced motion compartidos. Iconos Lucide existentes. Inventory y Orders tienen badges internos, sin componente público común; el estado de la lista usa un indicador local sencillo con tokens y texto, sin importar/rediseñar sus páginas. Clients tiene cliente HTTP y selector contextual en Orders, no una página independiente para ofrecer como destino.

**DEPENDENCIES ADDED: NONE.** Backend, servicios/datos/hook de T1, autenticación, SPEC, package.json y lockfile permanecen sin cambios. No hubo consultas reales a BD, mutaciones, endpoint nuevo, migración, push, PR, merge o deploy.

## Integridad de los datos y decisiones UI

Las fuentes siguen siendo GET `/api/inventory/planchas`, `/api/inventory/retazos`, `/api/orders` (filtros PENDIENTE/EN_OPTIMIZACION y página en orden de gestión) y `/api/clients`, compuestas por T1. Los componentes consumen datos transformados; no recalculan conteos, permisos, estados de dominio ni ordenan pedidos.

| Cifra visible | Significado exacto del modelo T1 |
|---|---|
| Unidades registradas activas — planchas | Suma de cantidad en registros con estado=true y cantidad>0. |
| Registros activos con unidades — planchas | Número de esos registros; no número de unidades ni stock compatible. |
| Registros totales — planchas | Longitud de la lista completa recibida, incluidos inactivos/cantidad cero. |
| Retazos activos registrados / registros totales | Conteos de registros activos / todos; retazo unitario, sin cantidad ficticia. |
| Total de pedidos pendientes / en optimización | `total` real del endpoint filtrado, no longitud de una página. |
| Clientes activos registrados / registros totales | Conteos de activos / todos en lista real; sin documentos/teléfonos en el resumen. |
| Mostrando X de Y pedidos | X = items de la página consultada; Y = total del listado sin filtro de estado. |

**Decisión CA-10:** no se renderiza el título «Pedidos recientes» ni se afirma recenticidad global. El contrato prioriza no CANCELADO y después fecha/ID DESC. Se muestra el bloque alternativo permitido por SPEC/PLAN, **«Pedidos en orden de gestión»**, conserva el orden recibido y explica alcance/orden. Cada fila presenta ID funcional, cliente visible, estado con texto/indicador y fecha real en un elemento time. Se omiten material/espesor porque el resumen HTTP de pedidos no los incluye. No se inventa un destino Clientes.

Administrador ve accesos Inventory/Orders/Users; Operario Inventory/Orders; Almacenero Inventory. Los tres ven inventario. Almacenero no recibe bloque ni requests Orders/Clients. Los accesos se toman del modelo y se contrastan con vistas montadas de NavigationContext; son botones reales, sin URLs ficticias ni ejecución de optimización. Header no duplica identidad/rol ya presentes en SessionBar.

Loading no presenta valores provisionales; cada fuente carga independientemente y los accesos siguen utilizables. Empty tiene mensajes específicos por recurso/estado. Un cero puede mostrarse solo si procede de un resultado válido con cero activos; no se usa para reemplazar fallo. Error parcial identifica el bloque y conserva los demás; error total ofrece feedback general y mantiene accesos. «Actualizar datos» / «Reintentar carga» usa exclusivamente refresh de T1, sin fetching/retries paralelos nuevos y con las protecciones de sesión/obsolescencia existentes.

## Validaciones ejecutadas

Desde `frontend/`; pruebas de componentes con HTTP/fixtures simulados únicamente dentro de la automatización, no datos de demostración incorporados al producto:

| Comando real | Resultado |
|---|---|
| `npm.cmd run test:component -- src/features/dashboard/__tests__ src/shared/__tests__/sidebarNavigation.test.jsx src/shared/__tests__/stagingNavigation.test.jsx` | 79 passed en 7 archivos; 0 fallos; 7.67 s. |
| `npm.cmd run test:component -- src/features/dashboard/__tests__` | 73 passed en 5 archivos; 0 fallos; 15.17 s. |
| `npm.cmd run test:unit` | 124 passed; 0 failed/cancelled/skipped. |
| `npm.cmd run test:component` | 369 passed en 31 archivos; 0 fallos; 30.21 s. Incluye regresión de sesión/navegación, Inventory, Orders/Clients, Users y Optimization. |
| `npm.cmd run lint` | PASS, exit 0. |
| `npm.cmd run build` | PASS, exit 0; Vite 8.3.1, 2.67 s. |
| `npm.cmd run test:e2e -- --list --reporter=list` | 52 tests en 6 archivos, exit 0. Discovery únicamente: no es ejecución E2E ni PASS de navegador/backend. |
| `git diff --check` / checks staged | PASS. |

T2 añade 20 casos a los 349 componentes T1: 17 casos de presentación/estados/permisos y 3 de navegación App mediante accesos rápidos. Cubren semántica de cifras, lista/orden/fecha, tres roles, ocultamiento/no requests restringidos, loading sin ceros, datos parciales con fuente lenta, empty, cero válido, error total/parcial/403, retry sin doble envío, Tab/Enter/Space, nombres/semántica de botones y falta de destino/navegador disponible. No hay snapshots masivos ni nuevas librerías.

## Inspección técnica local

Se levantó Vite con `npm.cmd run dev -- --host 127.0.0.1 --port 5173 --strictPort`, URL real http://127.0.0.1:5173/. Playwright/Chromium **153.0.8010.12** inspeccionó la aplicación y su CSS reales con HTTP interceptado exclusivamente en la prueba automatizada aislada. **No se presenta como integración con API/Supabase, E2E real ni evidencia visual final.** No se accedió a BD ni se crearon fixtures persistidos. La aplicación de producción conserva sus fuentes reales y no incluye mocks.

| Ancho | Columnas de resumen | Ancho del documento | Accesos dentro del viewport |
|---|---|---|---|
| 1366 (alto 768) | 3 | 1366 | Sí |
| 1024 | 3 | 1024 | Sí |
| 800 | 2 | 800 | Sí |
| 390 | 1 | 390 | Sí |

Se inspeccionaron individualmente tres PNG temporales (1366/800/390): tarjetas/lista/textos legibles, adaptación sin recortes esenciales y sin overflow horizontal. Se comprobó Tab desde actualizar al acceso rápido, foco `:focus-visible` con outline de 3 px, Enter hacia Inventory y retorno a Inicio; cero pageerrors. Con prefers-reduced-motion=reduce, animationName del loader fue none. No se añadieron animaciones al Dashboard ni se afirma certificación WCAG.

El primer intento de esa inspección falló por un selector con tilde convertido a `?` al pasar JavaScript por stdin en Windows; se corrigió con escape Unicode en el script temporal, sin cambiar producto ni debilitar la aserción. Las mediciones/teclado posteriores completaron con exit 0. No hubo bug productivo ni prueba component fallida. Navegador cerrado, Vite propio detenido y los PNG temporales eliminados; no se guardaron scripts/reportes/capturas en Git ni se tocó NewGlass-Notion.

## Matriz CA al cierre de T2

DONE significa implementación y verificación de UI/componentes en este bloque; no sustituye la validación real de integración ni revisión final T3.

| CA | Estado | Evidencia / observación |
|---|---|---|
| CA-01 | DONE | Entrada post-login/relogin preservada, componentes App/T1. |
| CA-02 | DONE | Inicio en Sidebar y activo preservados; regresión navegación. |
| CA-03 | DONE | Tres roles autenticados/sin sesión, regresión T1. |
| CA-04 | DONE | Fuentes/accesos por capabilities, UI para los tres roles y destinos reales. |
| CA-05 | DONE | Valores consumen modelo de contratos reales; sin fallback o métricas ficticias en producto. |
| CA-06 | DONE | Unidades y registros de planchas con etiquetas diferenciadas. |
| CA-07 | DONE | Retazos unitarios/activos/totales, sin compatibilidad inferida. |
| CA-08 | DONE | Totales reales PENDIENTE/EN_OPTIMIZACION y estados textuales en lista. |
| CA-09 | DONE | Clientes disponibles por contrato, resumen restringido al rol autorizado. |
| CA-10 | CONDITIONAL_NOT_RENDERED | «Pedidos recientes» globales omitido por prioridad de estado; alternativa «Pedidos en orden de gestión» implementada conforme a la condición/orden documentados en SPEC. |
| CA-11 | DONE | Datos transformados de inventario, sin duplicar reglas/cálculos en UI. |
| CA-12 | DONE | Accesos rápidos operables a Inventory/Orders/Users existentes, según permisos/vistas montadas. |
| CA-13 | DONE | Sin gráficas/métricas futuras/heurísticas/mutaciones. |
| CA-14 | DONE | Loading independiente, sin cero provisional ni bloqueo de accesos. |
| CA-15 | DONE | Mensajes empty específicos y cero válido distinguido de fallo. |
| CA-16 | DONE | Error total/parcial, bloques identificados, datos válidos conservados y retry. |
| CA-17 | DONE | HTML semántico/headings/botones, Tab/Enter/Space, foco y reduced motion comprobados; inspección responsive técnica aislada. |
| CA-18 | PENDING_T3 | Responsive/sesión tienen comprobación técnica/component; falta flujo E2E real final, refresh/logout/permisos sobre backend. |

## Pendientes T3

Integración final, E2E real contra entorno controlado, regresión final, contraste definitivo de 18 CA, evidencia final auténtica, actualización autorizada de SPEC y preparación de PR/revisión humana. La SPEC sigue Approved, el PLAN Draft; no se declara el PBI Verified ni se publica esta rama.
