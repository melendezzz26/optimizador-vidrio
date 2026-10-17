# Auditoría funcional y UX de Optimización — S1

Fecha: 2026-10-17 (America/Bogota). Rama: `feature/S1-optimization-ux-audit`.
Base inspeccionada: `2b21562ad282a8a9760ef976df3c10182c594fea`.

## Alcance y estado de esta entrega

**Auditoría y planificación; no se implementaron correcciones.** La instrucción
posterior del usuario limita esta fase a AUDIT, hallazgos y PLAN/TASKS. No se
modificaron backend, frontend, dependencias, configuración, BD ni despliegue.

Fuentes: implementación de la base anterior, pruebas ejecutadas, inspección de
Chrome con HTTP controlado, páginas públicas de staging y evidencia histórica.
Estas fuentes se distinguen expresamente: una respuesta interceptada no demuestra
funcionamiento del motor ni persistencia real. No se certifica el flujo autenticado
de staging ni equivalencia del SHA desplegado con el local.

Git inicial: rama requerida, árbol limpio, tracking publicado. Se ejecutaron
`git status`, `git branch --show-current`, `git fetch origin --prune` y
`git log HEAD..origin/integration/sprint-01 --oneline`. El fetch inicial requirió
salir del sandbox porque `.git/FETCH_HEAD` no era escribible; después terminó
correctamente. HEAD e integration remota coincidían; no se necesitó merge.

## Fuentes revisadas

| Área | Implementación/contratos revisados |
|---|---|
| Entrada y permisos | `frontend/src/App.jsx`, `shared/components/{AppShell,Sidebar,PageLayout}.jsx`, `features/authentication/{permissions,authApi,useSession}.js` |
| Pedidos/inventario | `features/orders/{GestionPedidos.jsx,ordersApi.js}`, `features/inventory/InventoryPage.jsx`, clientes/stock usados por Dashboard; contratos de piezas y existencias consumidos por Optimization |
| Ejecución | `features/optimization/{OptimizationPage.jsx,useFirstFit.js,optimizationModel.js,pendingOrdersSource.js,runApi.js,runTransport.js,runContract.js}` |
| Agrupación | `materialGroups.js`, `useGlassCatalog.js`, `MaterialGroupsPanel.jsx`, preparación y proveedor de stock backend |
| Geometría y visualización | `PlacementCanvas.jsx`, `placementScene.js`, `PlacementScene3D.jsx` y CSS, `InspectionViewport.jsx` y CSS, `visualizationGeometry.js` |
| Raster | `RasterInspection.jsx`, `rasterInspectionModel.js`, `RasterComparison.jsx`, `RasterPreview.jsx`, `rasterCanvas.js`, `Hu015Rasterization.jsx`, `useOptimization.js`, `optimizationApi.js` |
| Backend | `application/{runs,preparation,calculation,stock,confirmation,use_cases}.py`, `domain/{preparation,first_fit}.py`, contratos `presentation/run_*`, persistencia `infrastructure/{run_uow,orders_adapter}.py` |
| Pruebas | Suites unit/component ejecutadas; revisión de E2E Optimization, HU-015, soporte real, configs, servidor efímero y reportes históricos |
| Documentación | AUDIT/SPEC/PLAN/TASKS S1-OPT-UI; SPEC/PLAN First Fit; deployment staging y cierre de integración/corte comercial |

La documentación histórica describe etapas distintas. Por ejemplo, CONTRIBUTING
aún sitúa First Fit fuera de Sprint 1 y el PLAN de core describe una base sin
motor. El código actual sí tiene motor y confirmación. No se tomó esa descripción
histórica como estado vigente.

## Flujo real encontrado

1. Login obtiene usuario/permisos; App y Sidebar deciden visibilidad por permisos,
   no por nombre del rol. El backend valida sus propios permisos.
2. `createPendingOrdersSource` consulta todos los pendientes paginados y publica
   snapshots completos; repite cada 15 s, reconcilia selección y conserva el
   snapshot de una ejecución cuando cambia la lista. No es un websocket.
3. «Revisar vidrios y piezas» hace GET de cada pedido, valida `PENDIENTE`, agrupa
   por tipo de vidrio + espesor decimal y expande cantidades. No reserva stock,
   rasteriza ni cambia el estado del pedido.
4. «Calcular distribución» envía únicamente `{order_ids}` a
   `POST /api/optimization/runs`. Backend revalida/bloquea la selección y toma
   configuración persistida; acepta la corrida y pasa pedidos a `EN_OPTIMIZACION`.
5. El motor consulta stock compatible, ordena unidades por área/dimensión y prueba
   candidatos, orientaciones y posiciones raster. Rasteriza geometrías/orientaciones
   antes de probar su colocación; reutiliza caché dentro de la corrida. No existe
   una fase pública de raster previo descargable en la preparación frontend.
6. First Fit prioriza retazos frente a planchas. Las posiciones derivan de
   columna/fila × resolución. `rotation_deg` y la geometría ya orientada vienen
   del backend. 2D/3D normalizan y trasladan esa geometría, sin rotarla otra vez.
7. El POST transmite NDJSON. Se validan contrato, secuencia, identidades, unidades
   físicas y compatibilidad. `Location` permite retener el ID incluso si el stream
   falla. Tras evento terminal se hace GET del resultado persistido; el evento
   terminal por sí solo no habilita confirmación.
8. Backend calcula métricas y regiones recuperables; el frontend muestra los
   valores y deriva porcentajes de merma/retazo. Una corrida completa deja pedidos
   `OPTIMIZADO`; una sin solución vuelve a `PENDIENTE`. Calcular no consume stock.
9. Confirmar envía POST vacío a `/runs/{id}/confirm`. Backend bloquea/revalida,
   descuenta existencias, registra movimientos, crea retazos recuperables y pasa
   todos los pedidos a `CONFIRMADO` en una transacción. UI recupera el resultado
   y refresca pendientes. HTTP 409 bloquea repetir la confirmación en esa vista.

### Real, simulado y adaptadores

| Elemento | Estado actual |
|---|---|
| Ruta por defecto de App | `createBackendRunAdapter` y pedidos HTTP reales |
| Stock/dimensiones/posición/rotación/métricas/confirmación | Datos y operaciones backend; no se encontraron dimensiones comerciales impuestas en la ruta productiva |
| `firstFitFixture.js`, `runFixtures.js`, `contractV1Fixture.json` | Ejemplos de pruebas; no son un motor alternativo seleccionado por App |
| `createFixturePendingOrdersSource`, adapters inyectables | Soporte de pruebas; fixtures etiquetados cuando `isFixture` está presente |
| `runTransport` | Parser/lifecycle compartido entre HTTP y tests, no una simulación |
| `visualStock`, `visualPlacement`, `resultSnapshot`, `glassGroups` | Adaptación de DTO para render/nombres; no cálculo de colocación |
| HU-015 `/start` y `/rasterize` | Backend real heredado de un pedido; sigue accesible, pero su ciclo de estado no equivale al de runs |
| Profundidad y grilla 3D | Ilustrativas. Grilla geométrica de referencia, no máscara raster del motor |
| Sombreado 2D | Retazo verde persistido; merma rayada aproximada, advertida por la UI |

Agrupación: `materialGroups.materialKey` y backend usan material + espesor; se
rechaza stock de otro grupo y se distinguen unidades con source/ID/unit_index.
Las pruebas ejecutadas separan material distinto, espesor distinto y cantidades,
y normalizan `6`/`6.0`. **No se comprobó mezcla Bronce 5.5 / Reflejo 6**: no se
declara ese defecto. La validación autenticada remota de esos datos queda pendiente.

## Auditoría práctica y límites

Node portable encontrado en `%TEMP%/newglass-node/node-v24.15.0-win-x64`, agregado
solo al PATH del proceso. No hubo instalación global ni cambios de lockfile.

Chrome local: Vite en loopback, login → Dashboard → Optimización → seleccionar →
revisar → POST/NDJSON controlado → resultado → 2D → detalle raster → 3D →
confirmación controlada. Escritorio 1440×1000 y móvil 390×844. Cero `pageerror`
en los recorridos; sin overflow horizontal en las muestras. Esto no certifica
todos los errores de consola: el primer recorrido registró excepciones de página
y rutas HTTP, no todos los mensajes `console.*`.

Se inspeccionaron las capturas: nombres/material/medidas, vista inicial 2D,
rotación con End, leyenda, tamaño móvil y panel raster vacío. El fixture de 100×50
mm sirve para reproducir render; no representa una plancha comercial ni benchmark.
Tres sondas adicionales reprodujeron AU-02/03/04 sin backend ni datos compartidos.

Staging se localizó en `docs/evidence/sprint-01/TA-DEPLOY-001/actualizacion-predeploy-post-ta036.md`:

- Frontend: <https://melendezzz26.github.io/optimizador-vidrio/> — 200; login visible,
  assets 200, sin excepción de página observada.
- Bundle público `index-CHQPF7Oa.js` referencia la API documentada.
- API: <https://newglass-api-staging-5f52e8e9b00c.herokuapp.com> — `/health/live`
  y `/health/ready` 200; OpenAPI 200 expone `/start`, `/rasterize`, `/runs`, GET
  del resultado y confirmación.
- El primer intento fue bloqueado por red del sandbox, no por el servidor. La
  consulta autorizada posterior produjo los 200 registrados.

No se encontró `storageState`/`authState` utilizable en las ubicaciones revisadas.
`optimizationRealSupport.js` genera actores del servidor efímero local;
`integration/final/README.md` especifica que esas cuentas no son de staging.
HU-015/Dashboard esperan credenciales externas por variables, sin valores de
staging documentados. No se probaron contraseñas locales contra staging ni se
consultaron secretos fuera del repositorio. **Dashboard, pedidos, inventario,
usuarios, raster, cálculo y confirmación autenticados de staging no se recorrieron.**

## Hallazgos priorizados

No hay P0 demostrado. P1 significa impacto funcional grave en el escenario
descrito, no corrupción de BD probada. A = frontend seguro; B = backend;
C = decisión de negocio; D = fuera del alcance de correcciones frontend.

| ID / prioridad / clase | Escenario y comportamiento actual | Esperado / riesgo | Evidencia y módulo probable | Propuesta |
|---|---|---|---|---|
| AU-01 · P1 · B/C, mitigación A | HU-015 «Preparar vista previa» envía `/start`, deja `EN_OPTIMIZACION`; First Fit exige `PENDIENTE`. Se presenta como paso previo del mismo trabajo. | Una inspección no debe dejar al usuario sin ruta para calcular ese pedido. Riesgo de pedido apartado del flujo. | `useOptimization.start`, `use_cases.StartOptimizationUseCase`, `run_uow` valida pendientes. Confirmado por código, no reproducido en staging. | Advertir claramente el cambio de estado; decidir retiro del inicio heredado o contrato de preview de solo lectura. No cambiar estados desde frontend para simular una solución. |
| AU-02 · P1 · A | Resultado parcial con primer grupo sin contenedor: desaparece todo el visualizador, incluidos grupos posteriores con colocaciones. Elegir un grupo vacío también pierde el selector. | Mantener selector y explicar grupo sin colocaciones; permitir inspeccionar los demás. | `PlacementCanvas`: `if (!container) return null` antes del selector. Sonda Chrome: DTO con 3 placements, 0 visibles, 0 selectores. | Renderizar selección/empty por grupo antes de exigir contenedor; test con orden de grupos invertido y cambio hacia/desde vacío. |
| AU-03 · P1 · A | GET «Recuperar resultado» pendiente; usuario selecciona #12; llega resultado #101 de pedido #10 y vuelve la confirmación junto a selección #12. | Resultado tardío no debe reemplazar el contexto nuevo. Riesgo de confirmar un trabajo distinto al que el usuario cree preparar. | `useFirstFit.recover` verifica lifecycle/run, pero `select` no los invalida; dispatch result sin runId. Sonda Chrome `late-result`. La carga terminal automática sí se filtra por runId; no se generaliza ese defecto a ella. | Versionar contexto al seleccionar/preparar y rechazar recuperaciones obsoletas; bloquear/reconciliar solicitudes concurrentes. |
| AU-04 · P1 · A | Mientras POST confirm está pendiente, «Preparar otro corte» sigue activo. Al pulsarlo, la continuación de confirmación restaura el trabajo anterior. | Mantener contexto estable hasta reconciliar el POST y mostrar qué trabajo se confirmó. | `OptimizationPage` aplica `confirming` a algunos controles, no a ese botón; sonda `confirmation-switch`: enabled=true, vuelve #101. | Aplicar bloqueo coherente y capturar ID/contexto en continuación; prueba con POST demorado, cambio de vista y error de red. |
| AU-05 · P2 · A/B | «Ver detalle de piezas» del resultado muestra «Pendiente» y remite a HU-015, que exige EN_OPTIMIZACION; el resultado normal corresponde a OPTIMIZADO/CONFIRMADO. | Explicar que el resultado no incluye máscaras; no prometer una carga que nunca ocurre ni una ruta inválida. | `resultSnapshot` produce `rasters:{}`; captura `desktop-raster-before.png`; `RasterizeOrderPieceUseCase` exige estado. | A: texto/estado honesto y resolución recibida. B: endpoint/snapshot de máscaras de corrida para inspección real de contactos, con presupuesto y permisos. No rasterizar de nuevo en JS. |
| AU-06 · P2 · A | SIN_SOLUCION indica «revisa las piezas que quedaron sin ubicar», pero no enumera `unplaced_units` ni sus motivos. | Mostrar pedido/pieza/unidad/material/motivo para corregir la entrada. | Contrato parsea `unplaced_units`; reducer/resultSnapshot no los conserva para la UI. | Conservar diagnóstico canónico y listar unidades no colocadas; no inferirlas de colores o métricas. |
| AU-07 · P2 · A | «Descartar» limpia estado local e ID; no cancela ni revierte corrida/pedidos persistidos. | Acción y efecto explícitos; conservar acceso al ID del trabajo. Riesgo de perder referencia a un corte que dejó pedidos OPTIMIZADO. | `useFirstFit.discard`, reducer; router carece de cancelación de corrida. | Nombrar como cerrar vista, avisar persistencia y ofrecer ID; cancelación real requiere decisión B/C independiente. |
| AU-08 · P2 · A | Cámara acepta ±180° por teclado/pointer, fuera de ±90° solicitado. | Limitar cámara sin modificar rotation_deg. | `clampYaw`, aria/Home/End; Chrome End=180, captura móvil. Tests actuales exigen 180. | Unificar límites ±90 en proyección, teclado, pointer y ARIA; actualizar regresión, conservar reset/zoom/pan. |
| AU-09 · P2 · A | Preparación muestra «Listo para calcular» aun al visualizar resultado terminado; etapas raster/orden/rotaciones se presentan como progreso pese a no tener eventos públicos individuales. | Diferenciar resumen revisado, cálculo en curso y resultado, sin inventar progreso medido. | `MaterialGroupsPanel` texto depende de snapshot; STAGES vs eventos reales de `run_stream` y `optimizationModel`. | Pasar estado explícito; distinguir etapas conceptuales de hitos recibidos. |
| AU-10 · P3 · A | 2D repite identificaciones en dos listas; controles 3D ocupan gran altura en móvil. | Reducir scroll y mantener acciones/leyenda próximas a dibujo. | Capturas locales; `PlacementCanvas` renderiza leyenda y detalle separados, `PlacementScene3D` agrupa numerosos controles. | Integrar rotación/coordenadas en una leyenda, agrupar ajustes secundarios con controles accesibles. Validar a 390 px y teclado. |
| AU-11 · P3 · D documental | Guías generales y README de pruebas conservan alcance/conteos anteriores al motor real. | Facilitar reproducción actual sin confundir historia y estado vigente. | CONTRIBUTING; frontend README frente a configs y cierre de integración. | Actualización documental acotada posterior, preservando evidencia histórica y sus SHAs. |

## Matriz de escenarios A–O

| Escenario | Evidencia disponible en esta fase | Límite pendiente |
|---|---|---|
| A un pedido | Recorrido Chrome controlado completo; E2E1 histórico real | Repetir autenticado con datos autorizados |
| B varios compatibles | Unit/component PASS; E2E2 histórico | No se reejecutó motor real |
| C distinto material | Unit/component PASS; E2E3/10 histórico, AU-02 parcial controlado | No se certifica stock staging |
| D igual material/distinto espesor | Unit `materialGroups` PASS | Falta recorrido real específico |
| E material/espesor iguales | Unit/component PASS, expansión y consolidación | Validación remota pendiente |
| F geometrías diferentes | Suites de geometría/visualización PASS; E2E9 rotación histórico | Sin inspección visual nueva de todos los polígonos/círculos |
| G múltiples piezas | Componentes y fixtures contractuales PASS; comercial histórico 8 piezas | No nuevo benchmark |
| H cantidades >1 | Unit/component PASS; E2E4/10 histórico | Motor no reejecutado |
| I lista vacía | Componentes PASS, estado vacío explícito | Sin vacío remoto provocado |
| J nuevo pedido abierto | Componentes live-add/polling PASS | No alta en staging |
| K deja de pendiente | Componentes reconciliación PASS | No modificación remota |
| L errores HTTP | Componentes 401/403/409/config y stream PASS | No inyección en staging |
| M repetición | Componentes rerun y parsers PASS; carreras AU-03/04 reproducidas | Repetición del motor pendiente |
| N descarte | Componentes PASS para limpieza local; AU-07 por contrato | No existe cancelación backend equivalente |
| O confirmación | Chrome controlado; componentes PASS; histórico real stock/movimientos | Ninguna confirmación remota ejecutada |

## 2D, 3D, raster e inventario

2D conserva escala/proporción mediante viewBox y `preserveAspectRatio`; normaliza
bounds de geometrías y traslada x/y en mm. Ya hay zoom 100–400 %, ajuste y scroll
para pan táctil/teclado. No hay overlay de máscaras de toda la plancha ni grilla
raster del resultado. La vista técnica no debe llamar «raster» a una grilla
decorativa. Clipping/overlap adversarial, máximos de piezas y rendimiento no se
certificaron mediante navegador en esta fase; no se inventa un fallo geométrico.

3D es proyección SVG con extrusión ilustrativa, no WebGL/CAD. Cámara separada de
placements, colores por unidad, leyenda, pointer/touch, teclado, reset, elevación,
pan y zoom existentes. CSS contempla reduced motion y no hay inercia automática.
No se observó z-fighting en las muestras; no se hizo benchmark de escenas grandes.
La grilla 3D toma un paso visual de la dimensión, no la resolución del motor.

Raster previo: backend usa `RasterCache.orientations/material` antes de buscar
posición y valida máscaras dentro del contenedor. Raster inspección: HU-015
obtiene spans del backend y los dibuja en canvas; el inspector de fixtures usa
spans SVG con zoom/grilla. La representación no devuelve máscaras de corrida ni
contactos en el resultado real. Resolución/configuración sí están en el DTO y
pueden mostrarse sin inventar datos, pero exponer máscaras necesita contrato B.

Inventario: dimensiones salen de geometría de stock en `materials_used` y eventos.
Se muestra source, ID, unidad física, material y espesor; el motor elige stock,
no un selector comercial frontend. Confirmación es quien consume stock. No se
añadió una selección manual de plancha ni reserva que el contrato no soporte.

Consistencia UX: AppShell, Sidebar, tokens, PageHeader/PageCard, botones y feedback
son compartidos con Dashboard/Orders/Inventory/Users. No se justifica reescribir
el shell. Problemas prioritarios son contexto asíncrono, estados y diagnóstico;
el polish queda después. La revisión visual comparativa autenticada completa de
los otros módulos remotos sigue pendiente.

## Validación y evidencia

| Comando / recorrido | Resultado nuevo |
|---|---|
| `npm.cmd run test:unit` | 159 PASS, 0 fail, 0 skipped |
| `npm.cmd run test:component` | 41 archivos, 468 PASS |
| `npm.cmd run lint` | exit 0 |
| `npm.cmd run build` | exit 0, Vite 8.3.1, 1988 módulos |
| `npm.cmd run test:e2e -- --config playwright.optimization.config.js` | No inició: Python no tiene `sqlalchemy`; no es PASS ni fallo de producto |
| Chrome controlado desktop/mobile | Recorrido ejecutado, sin pageerror; hallazgos reproducidos |
| Staging público | Login/assets/health/OpenAPI 200; no login enviado |

El intento E2E ocurrió antes de la restricción posterior de no crear BD y terminó
en importación, sin iniciar PostgreSQL, crear BD ni ejecutar migraciones. No se
reintentará ese runner bajo dicha restricción. No se instalaron dependencias.

Evidencia nueva: [índice](../evidence/sprint-01/S1-OPTIMIZATION-UX/README.md).
Histórica, no reejecutada: [integración final](../evidence/sprint-01/S1-OPTIMIZATION-FIRST-FIT/integration/final/README.md)
(86 E2E previos) y [corte comercial](../evidence/sprint-01/S1-COMMERCIAL-CUT/README.md).
No se suman esos conteos a las pruebas actuales.

Siguiente fase propuesta: [PLAN](PLAN-S1-OPTIMIZATION-UX.md) y
[TASKS](TASKS-S1-OPTIMIZATION-UX.md). Ninguna tarea de implementación está marcada
como realizada. La auditoría autenticada real permanece limitada por falta de
cuenta/sesión de prueba de staging documentada y datos inequívocamente sintéticos.
