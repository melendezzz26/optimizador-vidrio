# Grupos, preparación raster e inspección — entrega frontend

2026-10-15, America/Bogota. Rama feature/S1-optimization-ui.

| Frente | Estado |
|---|---|
| SPEC | APPROVED |
| Frontend de optimización | COMPLETED WITH FIXTURES |
| Agrupación visual por material/espesor | IMPLEMENTED |
| Preparación raster previa | IMPLEMENTED |
| Vista 2D | IMPLEMENTED |
| Vista 3D | IMPLEMENTED |
| Integración real con motor First Fit | PENDING |
| Agrupación final y rotaciones automáticas reales | PENDING |
| Confirmación persistente real | PENDING |

Fabricio Meléndez desarrolla el motor real, agrupación final, rotaciones y persistencia. Andro Q. deja preparada la interfaz y coordina su conexión. No se declara solución de producción Verified.

## Auditoría y decisiones

Inicio sobre f538eeb: rama correcta, working tree limpio, fetch origin --prune exitoso; HEAD..origin/integration/sprint-01 vacío. Integration no avanzó respecto de la feature, sin merge ni conflictos. Se inspeccionaron modelo, fixture, página, renderers, HU-015 y pruebas antes de implementar. SPEC/PLAN/TASKS recibieron el alcance de este ajuste antes del código.

La selección genera una vista previa por ID de material y espesor numérico (6 y "6.0" son compatibles). Un mismo pedido puede aportar piezas a varios grupos. Las tarjetas muestran unidades, pedidos, plancha base y estado Pendiente/Listo/Optimizado. Datos faltantes se señalan, no se completan con el inventario ficticio. El listado mantiene selección múltiple, cliente, cantidades, material/espesor, estado y actualización automática; para pedidos reales sin detalle se indica que faltan esos datos.

`fixtureMaterialSource` es la fuente desacoplada de planchas sintéticas: Templado 6 mm, plancha #15 3300×2140; Bronce 5.5 mm, plancha #16 1600×1000. Cada grupo tiene su propia plancha base. Bronce conserva retazo #8 como alternativa de inventario sintético, sin colocaciones en esta corrida. No representa sobrante calculado. Se conserva el ejemplo Templado existente, sin renombrarlo arbitrariamente a Reflejo.

Se valida pieza/unidad/pedido/grupo, material y espesor del contenedor, y se rechaza compartir un contenedor entre grupos incompatibles. El reducer falla ante una colocación incompatible; el renderer también filtra snapshots importados. No se comprueban colisiones ni factibilidad geométrica: esa responsabilidad permanece en el motor.

## Preparación e inspección

La sección de preparación aparece antes de Ejecutar First Fit: selector de grupo y pieza, estado, resolución, celdas ocupadas y texto «A mayor resolución raster, mayor costo computacional». Máscaras fixture explícitas a 100 mm/celda para rectángulos, círculo y polígono; no se calcula raster en frontend. Si falta una máscara válida, no se habilita ejecución. Las etapas de generación/evaluación del playback son simuladas, no computación real.

Resultado con un grupo y un contenedor seleccionados a la vez. Los modos Ver en 2D / Ver en 3D / Ver máscara raster aparecen solo cuando el grupo tiene colocaciones compatibles. Cambiar modo conserva grupo, contenedor, snapshot, métricas y progreso. Las altas/cambios de pedidos durante una corrida no alteran sus grupos/máscaras. Repetir inicia nueva corrida en 2D; descartar limpia el resultado; confirmar conserva el modal y no persiste ni descuenta inventario.

2D mantiene posiciones/giro/escala física y ahora comparte la paleta por unidad con 3D, con leyenda de pedido/pieza/unidad. Zoom 100–400%, ajuste y desplazamiento nativo por barras/touch/teclado. El panel raster prioriza la lectura 2D de spans recibidos: zoom, celdas activables y comparación HU-015. El raster mostrado es local por pieza antes del giro, con referencia textual a colocaciones recibidas; NO es una máscara global de plancha ni cálculo de retazos.

3D conserva extrusión ilustrativa, leyenda, yaw −90°/+90°, mouse/touch/teclado y reduced-motion. Amplía la cámara 100–400%; Restablecer vista restaura yaw y zoom. No añade órbita vertical ni pane 3D. Zoom 2D/raster se ajusta de nuevo al desmontar el panel; cámara 3D se conserva al alternar. No hay dependencias nuevas.

## Archivos y contrato listo para integrar

- `materialGroups.js`: vista previa pura y validación de pertenencia/material.
- `MaterialGroupsPanel.jsx`: tarjetas y preparación previa por grupo.
- `rasterInspectionModel.js`, `RasterInspection.jsx`: lectura/validación de máscaras y detalle con HU-015.
- `InspectionViewport.jsx/CSS`: zoom acotado, ajuste, área desplazable y controles accesibles.
- `OptimizationPage.jsx/CSS`, `firstFitFixture.js`, `optimizationModel.js`: flujo, datos sintéticos, estados, bloqueo por máscaras y timeline.
- `PlacementCanvas.jsx`, `PlacementScene3D.jsx`, `placementScene.js`: aislamiento, tres modos, cámara y colores compartidos.
- `RasterComparison.jsx`: IDs accesibles únicos para instancias simultáneas.
- Pruebas unitarias de material/raster, actualización del reducer, componentes de grupos/raster y ajustes de E2E/3D.
- AUDIT, SPEC, PLAN, TASKS, README, compatibilidad y esta evidencia.

Se mantienen prepare(ids), createEventSource(snapshot), confirm(result), fuente viva y contrato público de ocho eventos. stage_changed sigue interno/opcional. resolveMaterial(id) puede sustituirse por configuración real; snapshot requiere grupos, unidades, contenedores compatibles y máscaras. Clave raster preferida pedido:pieza, con fallback id_pieza para compatibilidad. El contrato definitivo debe acordar IDs de grupos, pivote/giro, stock y raster global si se necesita; todavía no se conectan endpoints de First Fit.

## Validación real y reproducción

Node portátil 24.15.0/npm 11.9.0, sin cambios de dependencias. Desde frontend, Node en PATH:

| Comando | Resultado | Log |
|---|---|---|
| npm run test:unit | 147 PASS, 0 fallos/skips | [unit](groups-unit.txt) |
| npm run test:component | Suite completa: 357 PASS, 33 archivos | [component](groups-component.txt) |
| npm run lint | exit 0 | [lint](groups-lint.txt) |
| npm run build | exit 0; JS 426.13 kB, gzip 128.55 kB | [build](groups-build.txt) |
| npx playwright test --config playwright.optimization.config.js | 8 PASS, desktop/mobile | [E2E](groups-e2e.txt) |

E2E con `$env:OPTIMIZATION_E2E_PORT='5187'`, solo Vite/Chrome y HTTP simulado, preservando puerto 5186 de revisión manual. Sin backend, PostgreSQL ni migraciones. NO_COLOR/FORCE_COLOR produce advertencia conocida, no fallo. PowerShell rotula stderr como NativeCommandError; el exit real del proceso fue 0.

Regresiones nuevas: mismo material/distinto espesor y distinto material/mismo espesor separados; pedidos mixtos; cantidad y pertenencia; inventario incompatible; spans fuera de límites; máscaras faltantes; grupos inmediatamente tras selección; raster antes de ejecutar; tres modos; zoom y desplazamiento real; filtros de grupo/contenedor; cambios live y snapshot; leyendas. Se conservan escenarios de progreso, teclado/touch 3D, modal, retry y discard. Primer pase focal encontró tres expectativas antiguas y una consulta de prueba ambigua; corregidas antes de las suites completas. No se omiten pruebas para obtener PASS.

No ejecutado: suites backend/BD, E2E general con PostgreSQL, integración real ni confirmación persistente. Fuera del alcance autorizado; [cobertura HU-015 reproducible existente](compatibility.md) conservada. Las pruebas fixture no reemplazan integración real.

## Capturas

| Escenario | Desktop | Mobile |
|---|---|---|
| Grupos y preparación | [grupos](desktop-groups.png) | [grupos](mobile-groups.png) |
| Raster previo ampliado | [preparación](desktop-raster-preparation.png) | [preparación](mobile-raster-preparation.png) |
| Resultado raster por grupo | [raster](desktop-raster-result.png) | [raster](mobile-raster-result.png) |
| Plancha Bronce en 3D | [Bronce](desktop-3d-bronce.png) | [Bronce](mobile-3d-bronce.png) |

Inspección visual de grupos desktop y resultado raster móvil: controles legibles, scroll contenido y modos distribuidos sin overflow de página. El raster ampliado recorta dentro del panel de forma intencional y permite desplazarse. Las capturas compartidas se actualizaron; los logs históricos y capturas 3d-retazo siguen documentando las entregas anteriores.

Diff check y Git se verifican antes del commit. Publicación únicamente de feature/S1-optimization-ui; hash/resultado en la entrega final. Sin PR, rebase, cambios de integration, backend, BD o migraciones.
