# PLAN-HU-017 — Visualizar proceso de optimización

## Información general

| Campo | Valor |
|---|---|
| Estado | **Verified — local, sin integrar** |
| SPEC | [SPEC-HU-017-proceso-visual-optimizacion.md](SPEC-HU-017-proceso-visual-optimizacion.md), Verified local |
| Responsable / revisor | Implementación y verificación local: Codex por encargo del solicitante. Responsable/revisor humano formal pendientes. |
| Fecha / base | 27/10/2026 / `4bcf54d`, `integration/sprint-01` |
| Estimación | Propuesta, 1 SP = 6 h; sin asignación ni compromiso de sprint. |
| Ejecución actual | T01–T06 implementadas y verificadas en `feature/HU-017-proceso-visual-optimizacion`, con commits y evidencia local. Sin push de HU-017, PR ni merge. |
| DG-01 | **Closed — B (`visual-v2`)**, elegida expresamente e implementada; V1 conservado. |
| Evidencia final | [Matriz de CA, suites, recursos y capturas T03–T06](../evidence/sprint-02/HU-017/t03-t06-visualizacion-y-cierre-local.md). |

## 1. Objetivo y disponibilidad del ID

Convertir la SPEC en trabajo trazable para un único flujo visual A–E, con
preparación real, telemetría acotada y resultado del backend. SPEC Reviewed y
PLAN Approved por autorización documental del solicitante. T01–T06 se completaron
y verificaron localmente; la revisión cruzada humana y la integración siguen
pendientes. El cierre técnico no modifica Notion ni acredita CI remoto/staging.

TA-021 se define como «Comparación/orquestación de FF/BF/WF sobre la misma
instancia, sin selección del ganador». HU-017 consume visualmente sus resultados
y eventos; no implementa esa orquestación ni decide el método ganador.

HU-017 no tiene asignación local encontrada. La búsqueda previa incluyó árbol,
historial de nombres, mensajes de todas las referencias locales y cambios de
texto de `docs/`. La mención de `f5e9e79` describe disponibilidad al crear HU-016,
no otra historia. Confirmar registro externo sin inventar otro identificador.

## 2. Arquitectura antes/después

La base se actualiza a `4bcf54d`: BF y el comparador TA-021 ya están integrados
internamente, TA-037 dispone de SPEC y guardrails. El ciclo HTTP sigue siendo FF;
la implementación visual no habilitará métodos que ese contrato no entregue.

| Área | Antes, base auditada | Después propuesto por SPEC |
|---|---|---|
| Entrada | Sidebar Optimización y dos modos internos de `OptimizationPage`. | Mismo Sidebar, un flujo A–E; inspección raster integrada. |
| Preparación UI | `runApi.prepare`: pedidos/grupos, `rasters: {}`. HU-015 calcula preview por separado. | Descriptor de preparación real ligado a corrida, no a otra lectura mutable de Orders. |
| Preparación backend | `AcceptRun` valida metadatos; `pack` prepara por pieza/material y el contrato de orientaciones entrega una tupla por pieza. | Antes de FF/BF/WF: resolución única, geometrías válidas, bases necesarias listas y configuración geométrica congelada. Orientaciones/posiciones pueden generarse/cachearse bajo demanda; no se precalculan todos los candidatos/layouts. |
| Búsqueda | FF `next()`, WF selector sobre candidatos canónicos; geometría compartida. | Misma política/orden/resultado y observación neutral. FF conserva lazy evaluation y salida temprana; preparar bases no es explorar fuentes/rotaciones/posiciones. |
| Streaming | Ocho eventos V1, método FF, cola de uno con ack. | B seleccionada: perfil `visual-v2` optativo, V1 predeterminado; contrato acotado según DG-01. |
| Máscaras UI | Preview HU-015 y rasters de fixtures; resultado real puede no traerlos. | Recuperación autoritativa por referencia de corrida/resolución/ángulo y presupuesto visual. |
| Resultado | GET/patrón, métricas, 2D/3D/raster y confirmación transaccional FF. | Reutilizados; UI neutral respecto del método entregado. Integrar métodos a persistencia pertenece a sus tareas. |

## 3. Inventario de reutilización exacta

Los caminos frontend de esta tabla pertenecen a `frontend/src/features/optimization/`;
los backend a `backend/app/modules/optimization/`.

| Archivo / componente | Reutilización y cambio eventual |
|---|---|
| `OptimizationPage.jsx`, `OptimizationWorkspace`, `OptimizationContent` | Mantener selección/resumen/resultados; sustituir botones de cambio de flujo por etapas y detalle contextual. |
| `Hu015Rasterization.jsx`, `useOptimization.js` | Extraer presentación de pieza y patrón de cancelación/obsolescencia; retirar del camino principal su selector e inicio independientes. No copiar el hook completo al flujo nuevo. |
| `RasterComparison.jsx`, `GeometryPreview.jsx`, `RasterPreview.jsx`, `rasterCanvas.js`, `visualizationGeometry.js` | Comparación geometría/máscara, canvas, escalado y lectura por rangos. Alimentar máscara real orientada y frame coherente. |
| `RasterInspection.jsx`, `rasterInspectionModel.js`, `InspectionViewport.jsx` | Integrar inspección y zoom. Ampliar claves actuales pedido/pieza para corrida/resolución/orientación: hoy no distinguen ese contexto completo. |
| `PlacementCanvas.jsx`, `PlacementScene3D.jsx`, `placementScene.js` | Mantener dibujo de placements/sobrantes y selección de fuente; evitar cálculos heurísticos frontend. |
| `MaterialGroupsPanel.jsx`, `materialGroups.js`, `useGlassCatalog.js`, `pendingOrdersSource.js` | Grupos, catálogo y pedidos; no crear un segundo selector. |
| `useFirstFit.js`, `optimizationModel.js`, `runApi.js`, `runTransport.js`, `runContract.js` | Reducer/transporte, `AbortController`, parseo y GET. Separar estado visual del estado algorítmico; perfil versionado. No basta renombrar STAGES para inventar progreso. |
| `optimizationApi.js` | Conservar clientes de `/start`/`/rasterize` para compatibilidad; no usarlos como prerrequisito de `/runs`. |
| `application/preparation.py`, `domain/preparation.py`, `application/stock.py`, `infrastructure/stock_adapter.py` | Reutilizar validación, cantidades, orden, material y stock. No cambiar prioridades. |
| `domain/raster_mask.py`, `rasterizer.py`, `rotation.py`, `placement.py` | Reutilizar toda geometría; TA-016 gobierna orientaciones. No crear un motor visual alternativo. |
| `domain/packing.py`, `first_fit.py`, `worst_fit.py` | Compartir preparación/observación sin cambiar políticas; preservar evaluación lazy de búsqueda FF y score WF. |
| `presentation/run_stream.py`, `run_schemas.py`, `run_serialization.py`, `run_routes.py` | Extensión visual optativa y autorizada; preservar V1, ack, errores y GET. |
| `application/calculation.py`, `runs.py`, `resource_policy.py` | Coordinar preflight, preparación real, presupuesto y medición. No reutilizar límite de JSON preview como presupuesto global del motor. |
| `domain/metrics.py`, `domain/confirmation.py`, `application/confirmation.py` y adaptadores actuales | Mantener métricas, revalidación raster y transacción; no integrar WF/BF por esta historia. |

`App.jsx` y `shared/components/Sidebar.jsx` se auditarán por regresión. No hace
falta una nueva entrada ni quitar una inexistente de Rasterización. Los
componentes HU-015 ya viven en Optimization; fusionar es composición/flujo,
no mover carpetas sin necesidad.

## 4. Tareas propuestas y estimación

| Tarea | SP | Horas | Dependencias principales | CA |
|---|---:|---:|---|---|
| T01 — Integrar preparación/rasterización en Optimization | 1.5 | 9 | HU-015/S1-01; diseño A–E | 01/02/23 |
| T02 — Preparar máscaras base y preservar búsqueda lazy | 2 | 12 | TA-016, TA-019, contrato TA-018, TA-037 | 03/04/05/11/14/15/16/18/21/26 |
| T03 — Exponer eventos visuales del optimizador | 1.5 | 9 | T02; DG-01 cerrada; contrato TA-021; TA-037 | 06/07/08/09/10/11/12/13/17/19/23/26 |
| T04 — Implementar visualización del proceso | 2 | 12 | T01/T03, contrato de máscaras | 01/06/07/08/09/12/17/19/24/26 |
| T05 — Integrar resultado final | 1 | 6 | T03/T04; resultado canónico existente | 10/17/19/20/22 |
| T06 — Pruebas y evidencia | 2 | 12 | Transversal T01–T05 y decisiones de recursos | 05/11/12/13/14/15/16/18/21/22/23/24/25/26 |
| **Total orientativo HU-017** | **10** | **60** | Sujeto al PLAN final; sin duplicar trabajo de otras tareas | **26 CA** |

La distribución adopta la referencia preliminar solicitada: T01 1.5, T02 2,
T03 1.5, T04 2, T05 1 y T06 2 SP: **10 SP / 60 h**. Es una estimación sujeta al
PLAN final y a los contratos compartidos, no una garantía de plazo.

La reutilización justifica ese total: T01 recompone selección y vistas HU-015
existentes; T02 utiliza validadores/raster/cache comunes y añade la preparación
base sin agotar rotaciones; T03 reutiliza NDJSON, ack, envolvente y transporte;
T04 compone renderizadores y viewport existentes; T05 conserva resultado/GET y
confirmación actuales; T06 amplía suites ya disponibles. No se estiman de nuevo
esas capacidades implementadas. No se propone desviación respecto de la referencia.

Incluye integración y revisión habitual, pero no implementación propia de
TA-016/018/019/021/037, un algoritmo nuevo, generalización completa multimétodo
ni validador vectorial. Si faltan contratos necesarios o crece el alcance de
recuperación de máscaras, reestimar T02/T03/T06; no reducir pruebas para forzar
el total ni contabilizar dos veces trabajo ajeno.

### T01 — Integrar preparación/rasterización en Optimization

- Unificar entrada y selección de pedidos; llevar la máscara a la misma pantalla.
- Mantener nombres de catálogo/material y configuración aplicable, sin inventar
  una API vigente ni crear CRUD de configuración.
- Descomponer HU-015 para reutilizar sus vistas; preservar contratos históricos
  y tests de S1-01. No volver a transicionar el pedido mediante `/start`.
- Conservar una ruta de compatibilidad técnica, no un paso visible obligatorio.
- No borrar HU-015, su SPEC, PLAN ni evidencia histórica al integrar la experiencia.

**Salida:** diseño/componentes del flujo A–E y pruebas de navegación/compatibilidad.

**Primer incremento autorizado (27/10):** retirar el selector de dos flujos de
la pantalla principal, integrar la inspección en la selección multipedido y
mostrar solo estados respaldados por el contrato actual. Si faltan máscaras o
telemetría de preparación/orientaciones, informar su ausencia; no fabricarlas ni
llamar `/start` o `/rasterize` para habilitar `/runs`. Conservar el componente
HU-015 mediante entrada técnica de pruebas fuera de la navegación principal,
con sus contratos autenticados y regresiones existentes. En ese primer incremento
T02–T05 quedaron pendientes; no se declaró CA-03/06/08/26 ni cierre de HU-017.

**Avance local:** primer incremento implementado en `1eeff98`;
[evidencia histórica y límites](../evidence/sprint-02/HU-017/t01-flujo-unificado.md).
T01 completada junto con T03–T05 en `3574609`: máscaras reales y preparación
integradas, verificadas en la evidencia final del 28/10.

### T02 — Preparar máscaras base y preservar búsqueda lazy

- Formalizar `PreparedRunGeometry` o equivalente: handle acotado de geometrías
  únicas y máscaras base de piezas/materiales, resolución y configuración; no
  contener por obligación todas las orientaciones. Nombre orientativo.
- Fijar y validar una única resolución efectiva según configuración. No buscar
  automáticamente el mínimo ni una resolución «más fina»; comprobar presupuesto
  de bases y trabajo incremental sin generar todas las máscaras orientadas.
- Validar geometrías antes de preparar las bases. Congelar la configuración
  geométrica aplicada antes de llamar FF/BF/WF: resolución, margen, separación,
  paso angular y reglas de normalización. Cambios posteriores de UI/configuración
  no alteran el snapshot ni los cálculos de la corrida aceptada.
- Preparar las bases antes del primer `SheetLayout.first_position/check` de
  búsqueda y compartirlas entre unidades. No enumerar posiciones o combinaciones.
- Coordinar con TA-016 el consumo bajo demanda y cualquier evolución incremental
  del contrato compartido actual que devuelve tuplas por pieza. Conservar orden,
  deduplicación y precisión; no crear rotaciones propias ni forzar su refactor
  desde HU-017. No agotar iteradores para animar; reutilizar orientaciones cacheadas.
- Conservar evaluación perezosa de posiciones y salida temprana de FF: sin score
  ni examen de fuentes/orientaciones/posiciones posteriores al primer factible.
  WF conserva score posterior, colocación canónica y prioridad de retazos.
- Error técnico si no cabe una base o un cálculo bajo demanda; no omitir fuentes,
  rotaciones o piezas, modificar precisión o informar NO_FIT artificialmente.
- Referencias visuales a la máscara backend real, ligadas a corrida, geometría,
  orientación y resolución efectiva, y al contorno realmente usado. La UI no
  presenta una rasterización independiente con reglas distintas como si fuera
  la del motor.

**Compatibilidad:** la preparación de bases puede cambiar el momento de ciertas
asignaciones; medir memoria con TA-037. No materializar el producto de todas las
rotaciones/posiciones ni convertir FF en una búsqueda exhaustiva. El contrato de
generación/cache lazy es coordinación TA-016, no una reimplementación dentro de
HU-017. La invariancia previa no exige todos los candidatos ni todos los layouts.

**Salida:** bases listas, resolución única y generación/evaluación bajo demanda,
con fidelidad visual comprobable. Fuera de transacciones DB largas y con
checkpoints de desconexión.

**Diseño del incremento T02 (27/10, local):** `PreparedRunGeometry` vinculará
el problema inmutable, su configuración y máscaras base compartidas. La barrera
de preparación se completará antes del primer layout/búsqueda; preparar una
fuente no significa evaluarla como candidato. `RasterCache.iter_orientations`
será reiterable y lazy, reutilizando exactamente la rotación/deduplicación de
TA-016. Se conserva `orientations()` como adaptador a tupla para consumidores
actuales (métricas, confirmación y pruebas del contrato histórico). Cada fuente
recorre desde el primer ángulo: no reutilizar un generador ya agotado.

Los checkpoints internos cubrirán preparación y trabajo bajo demanda, sin
añadir eventos V1 ni esperar animaciones. El cache conservará el límite de
64 MiB y los layouts usados el de 128 MiB. La admisión TA-037 y su estimador
angular previo se conservan como política existente; no se amplía la aceptación
de cargas por introducir laziness. Referencias HTTP/máscaras y retención siguen
en T03, tras DG-01. La comparación de regresión usa una captura funcional previa
de los ocho casos representativos de TA-021 para FF/BF/WF, además de sus suites.

**Avance local T02:** núcleo implementado en `1291d65`; 2270 pruebas backend y
34 E2E correctos, con medición de memoria y 24/24 resultados de referencia
FF/BF/WF iguales. [Evidencia T02 y límites](../evidence/sprint-02/HU-017/t02-bases-y-rotaciones-lazy.md).
La fidelidad interna quedó probada en ese incremento. Descriptores públicos,
UI autoritativa y comprobaciones CA-11/26 completados por T03/T04/T06; evidencia
final del 28/10. La revisión cruzada humana no se atribuye a las pruebas locales.

### DG-01 — Seleccionar estrategia de streaming visual

**Estado: Closed — alternativa B.** El 27/10/2026 el solicitante eligió
expresamente «Vamos por B», después de comparar las alternativas. La decisión,
compatibilidad, negociación, límites, entrega/recuperación y validación previstas
quedan registradas en [DECISION-HU-017-DG-01](DECISION-HU-017-DG-01-streaming-visual.md).
La puerta previa a T03 quedó cumplida antes de desarrollar. La implementación
posterior se acredita por `1ec14f7`, `3574609` y sus pruebas, no por la elección B.

**Alternativa A, no elegida:** extensión compatible del stream actual.

**Alternativa B, elegida:** perfil/versionado `visual-v2`, V1 predeterminado.

La elección corresponde al solicitante; Codex concreta el contrato a partir de
la SPEC/PLAN y los consumidores auditados. Se registra la aprobación de B, sin
atribuir revisión humana de una implementación aún inexistente. Los parámetros
técnicos iniciales deberán comprobarse en T03; no se presentan como benchmarks
ni como valores revisados individualmente por el solicitante.

La comparación siguiente sustenta DG-01. No se añaden SP: su resolución forma
parte de la planificación ya estimada de T03; el total permanece 10 SP / 60 h.

### T03 — Exponer eventos visuales del optimizador

**Precondición de implementación cumplida:** DG-01 cerrada y decisión B registrada.

**Comparación registrada antes de implementar:**

| Alternativa | Alcance y reutilización | Riesgo / condición de seguridad |
|---|---|---|
| A — Extensión compatible del contrato actual | Conservar transporte y envolvente actuales; reutilizar hitos y ampliar capacidades visuales solo donde sean negociables/compatibles. Menos ramificación si los clientes y schemas permiten la evolución. | Los parsers actuales enumeran eventos y los schemas son estrictos: añadir tipos/campos sin más no es compatible. Auditar clientes, negociar capacidades cuando haga falta y mantener intacta la respuesta para consumidores existentes. No inventar progreso a partir de hitos que no lo acreditan. |
| B — Perfil/versionado `visual-v2` | **Elegida:** `stream_profile=visual-v2`, eventos `schema_version: 2`, V1 por defecto. Reutilizar NDJSON/ack/GET con schemas/parsers explícitos para el perfil visual. | Aísla semántica nueva, pero añade negociación, mantenimiento y pruebas de dos contratos. Evitar duplicar motor o estado de corrida; comprobar clientes antiguos y recuperación. |

**Decisión:** B, autorizada expresamente. La auditoría de lectores V1 muestra
versiones/nombres de evento restringidos y schemas que prohíben campos extra;
no se demostró una ampliación directa compatible. V2 optativo conserva V1 y
permite probar ambos contratos. El mantenimiento adicional se acepta como coste
de la alternativa elegida. T03 implementará las reglas del documento DG-01;
los 26 CA de la SPEC y el total estimado permanecen intactos.

- Conservar los ocho hitos V1. Los siete hechos visuales propuestos en SPEC §9
  deben tener secuencias, unidades y correlación inequívocas; su representación
  concreta seguirá DG-01/B, sin enviar tipos desconocidos a clientes antiguos.
- Emitir `preparation_completed` cuando las máscaras base estén listas, antes de
  evaluar colocaciones; no afirmar que se generaron todas las rotaciones.
  `piece_started` mantiene significado de pieza en búsqueda. Distinguir una
  orientación generada bajo demanda de una realmente evaluada.
- `orientation_testing` admite muestras acotadas por ordinal, fuente actual y
  máscara/ref; `source_selected` representa ganador, no la mera fuente probada.
- Emitir `piece_unplaced` por unidad NO_FIT. Actualizar contadores procesados sin
  reinterpretar el porcentaje V1 de colocadas. No emitir NO_FIT por timeout/error.
- Descriptor `mask_ref` y recuperación autenticada por corrida/resolución/ángulo;
  rangos/ventanas acotados. URI, retención y límites iniciales según DG-01,
  conservando guardrails TA-037. Un preview
  histórico a 5 mm no reemplaza una máscara de corrida a otra resolución.
- No repetir máscaras completas por evento. Deduplicar referencias/recuperación
  por contexto de máscara y reutilizar la representación backend obtenida.
- Throttling, batching/agrupamiento o eventos significativos de orientación con
  límites iniciales de frecuencia, número y bytes registrados en DG-01,
  a validar durante T03 y sin ampliar límites del motor TA-037.
  No detener el motor para animar. Mantener orden/correlación y conservar todos
  los hechos críticos, aunque se agrupen para entrega/renderizado.
- No emitir registros de celdas ni posiciones candidatas individuales. Solo
  las colocaciones aceptadas llevan coordenadas; las máscaras se representan
  mediante rangos compactos u otra representación backend acotada.
- Mantener backpressure y tiempos que excluyen entrega; no guardar todos los
  intentos ni enviar puntos de grilla. No esperar animaciones del navegador.
- Conservar recuperación GET/Location, manejo del resultado ya persistido y
  estados reales de desconexión; no implementar replay o cancelación distribuida.

**Salida:** decisión A/B documentada, contrato limitado revisable y pruebas de
compatibilidad de la alternativa elegida; V1 sigue soportado.

**Completada localmente:** contrato/máscaras en `1ec14f7`, recuperación y diagnóstico
en `3574609`; pruebas de negociación, permisos, bytes, retención, presupuesto visual,
relojes y consumidor lento. V1 conserva sus contratos. Véase evidencia final.

### T04 — Implementar visualización del proceso

- Panel operativo con etapa, pieza/unidad, máscara, ángulo, fuente y progreso.
- Reutilizar canvas/viewport y comparación; detalle técnico plegable con
  resolución, dimensiones, método, score solo si existe y fuente física.
- Asociar respuestas a corrida, unidad, resolución y orientación; abortar/ignorar
  respuestas viejas, sin que un fetch de máscara reinicie o cambie el algoritmo.
- Mostrar la máscara backend real correspondiente a esas claves; si hay tiles o
  reducción visual, derivarlos de ella y rotularlos, sin rasterización alternativa.
- Priorizar pieza actual, máscara, orientación relevante, fuente evaluada/ganadora,
  colocación aceptada, pieza no colocable y progreso; no usar una animación de
  celdas/posiciones probadas como sustituto de esa información.
- Render acotado por frame, sin historial infinito ni una figura DOM por celda.
  Respetar movimiento reducido y pausa de animación solo local.
- Teclado/foco/lectores y estados SPEC §5; no ocultar una pieza fallida bajo
  «completado» ni presentar el proceso muestreado como reproducción exhaustiva.

**Salida:** componentes responsivos con tests de loading/error/obsolescencia.

**Completada localmente en `3574609`:** panel, inspección de máscara backend por
ventana, muestras identificadas, pausa/ocultar locales, abortos y errores visuales
separados. Componentes y E2E verifican foco/teclado, movimiento reducido y anchos
360/768/1440; capturas en la evidencia final.

### T05 — Integrar resultado final

- Alimentar 2D/3D/raster desde placements canónicos y máscaras de la misma corrida.
- Mostrar método entregado, faltantes con motivo, métricas disponibles y
  residuales; no confundir retazo propuesto con inventario creado.
- Cargar GET tras terminal, manteniendo no confirmable hasta estado autoritativo.
- Reutilizar diálogo/permiso/transacción actuales. Mostrar confirmar solo si
  resultado completo confirmable; no recalcular al confirmar o recuperar.
- UI neutral FF/BF/WF; no activar métodos que backend/persistencia no soportan.

**Salida:** continuidad visual a resultado y confirmación separada existente.

**Completada localmente en `3574609`:** resultado canónico GET, faltantes/motivos,
método/configuración efectivos, 2D/3D/raster de la corrida y confirmación actual.
Recuperación por ID y máscara ganadora a 90° sin un nuevo POST. Se mantiene HTTP FF;
integrar persistencia BF/WF no forma parte de esta historia.

### T06 — Pruebas y evidencia

| Nivel | Casos previstos | Evidencia esperada |
|---|---|---|
| Dominio/unitarias | Resolución única, geometrías válidas, bases listas y configuración congelada antes de FF/BF/WF; cambios posteriores no afectan la corrida; orientaciones/posiciones lazy y salida temprana FF. | Suites Optimization y casos pequeños reproducibles. |
| Contrato | Compatibilidad de A/B elegida, V1 intacto, frecuencia/bytes acotados, batching/hitos, hechos críticos completos, sin eventos por celda/posición ni máscaras completas repetidas. | Validación schemas/parsers y fixtures versionados. |
| Componentes | Máscara y contorno corresponden al backend real por corrida/geometría/ángulo/resolución; rechazo de obsoletas o rasterizaciones ajenas, representación reducida rotulada y accesibilidad. | Vitest y capturas 360/768/1440 px. |
| Integración | Preparación real antes de búsqueda, contrapresión, desconexión/estado persistido, GET y stock intacto; permisos. | Tests backend con recursos controlados. |
| E2E | Sin modo hu015 como requisito; multipedido/multimaterial; retazo/fallback; rotación; SIN_SOLUCION; recuperación; confirmación separada. | Playwright real y capturas/logs de la versión ensayada. |
| Rendimiento | Lote pequeño y caso representativo medido: bytes/evento, total de muestras, RAM, tiempo de cálculo/transporte/render y consumidor lento. | Presupuesto aprobado con TA-037; sin umbrales ficticios ni prueba OOM. |

Reutilizar `backend/tests/unit/optimization/`, `tests/optimization/`,
`tests/api/optimization/`, `tests/integration/optimization/`, tests frontend de
HU-015/Optimization/visualización y `frontend/tests/e2e/s1-optimization-ui.spec.js`.
No afirmar que esos tests ya prueban la barrera o los nuevos eventos.

**Completada localmente:** pruebas en `da40a11`, medición en `f13d4c7` y
evidencia final en `docs/evidence/sprint-02/HU-017/`: 2312 backend; ampliación API
visual 12/12; 161 unitarias frontend, 506 componentes y 38 E2E; lint/build correctos.
Pruebas temporales autorizadas expresamente para HU-017; no se usó Supabase/staging.
La evidencia distingue memoria Python, bytes contabilizados y tiempos locales;
no afirma FPS/CPU de render aislados ni SLO de producción.

## 5. Resolución: decisión previa a T02

| Fuente | Hecho actual | Decisión propuesta |
|---|---|---|
| SP-001 incorporada en rasterizador/SPEC TA-005/006 | Default 5 mm; `useOptimization` inicia en 5. Sin informe SP-001 separado recuperado. | Conservar trazabilidad histórica, no convertirlo en mínimo obligatorio. |
| Configuración vigente y `SqlRunUnitOfWork.configuration` | Resolución positiva de BD usada por corrida; no hay mínimo global ni modo automático. | Modo configurado compatible como base. |
| Seed demo/E2E | 1 mm explícito. | No extrapolarlo como política de producción. |
| `HU015_RASTER_BUDGET` | Presupuesto de preview/JSON independiente. | Preservar sus límites; no ampliar por necesidad de una máscara interna. |
| `RasterCache`, `pack` | Presupuestos por máscara/cache/layouts usados. | Añadir preflight global coordinado con TA-037, incluyendo preparación y entrega visual. |

HU-017 mantiene una sola resolución efectiva configurada que pase el presupuesto,
común a bases, orientaciones, fuentes y placements. No incluye búsqueda automática
del mínimo ni cambio de resolución durante la corrida. Si no pasa la validación,
error técnico explícito; no se selecciona otro valor silenciosamente. Los límites
técnicos de TA-037 son restricciones, no un objetivo de optimización de precisión.
No se presupone migración ni nueva API pública de Configuration. Investigar una
selección automática de resolución más fina, si se solicita después, será una
decisión separada coordinada con TA-037; no condiciona esta historia.

## 6. GAP vectorial y trabajo separable

No existe el validador final independiente solicitado conceptualmente: se
inspeccionaron rasterizador, placement, rotación, métricas, confirmación y
validación individual de Orders. La comprobación de autointersección de una
pieza no es comprobación vectorial de toda la distribución.

**Trabajo recomendado, pendiente de decisión e identificador externo:**

1. Investigación de precisión/tolerancias y necesidad de defensa vectorial:
   **2 SP / 12 h**, separada de las aproximadamente 10 SP de HU-017.
2. Si se aprueba, tarea técnica de validación final de contención, no solapamiento
   y distancias sobre originales transformados: estimación preliminar
   **4 SP / 24 h**, a reestimar tras investigación; fuera del total HU-017.

No se inventa un TA/SP nuevo ni se integra un motor vectorial en esta entrega.
La investigación debe decidir criterios numéricos, círculos/convexos, error de
rotación, margen/separación y tratamiento de discrepancias antes de prometer
una garantía. Evaluar si debe bloquear la futura confirmación; no cambiar la
transacción actual como efecto lateral de HU-017.

## 7. Dependencias, ownership y secuencia

| Dependencia | Coordinación requerida |
|---|---|
| TA-016 | Generación incremental compartida de orientaciones, orden/deduplicación, máscaras coherentes y puntos observables, sin rotación propia de HU-017/frontend. |
| TA-018 | BF integrado en dominio; acordar instrumentación neutral. Sus reglas e integración HTTP no se implementan aquí. |
| TA-019 | Conservar WF de dominio y retención acotada; no enviar sus resultados a adaptadores FF actuales sin integración posterior propia. |
| TA-021 | Comparación/orquestación de FF/BF/WF sobre la misma instancia, sin selección del ganador. Coordinar contrato e identidad de instancia/método en resultados/eventos; HU-017 es consumidor visual y no decide el método ganador. |
| TA-037 | SPEC y guardrails integrados: conservar sus límites de admisión y coordinar bases/generación bajo demanda, throttling/agrupamiento, máscaras acotadas y checkpoints. Sin selección automática de resolución en HU-017. |
| HU-015/S1-01 | Compatibilidad y reutilización de UI/preview; preservar rutas y evidencia histórica. |

Secuencia propuesta: decisiones de recursos y diseño → T01/T02 con TA-016/TA-037
→ cierre explícito de DG-01 → implementación de T03 → T04/T05 → cierre T06.
Los tests de regresión se definen desde T02, no solo al final. Un único owner
de `packing.py`/contrato preparado y otro del contrato visual reduce conflictos.
Coordinar ownership de TA-021 sin trasladar a HU-017 la comparación/orquestación
ni la selección de un método ganador; esta última queda fuera de ambos alcances.

## 8. Riesgos y decisiones abiertas

| Riesgo | Mitigación / puerta de revisión |
|---|---|
| Preparación agota RAM | Preparar solo bases compartidas y generar orientaciones bajo demanda con presupuesto; no materializar rotaciones ni todos los candidatos. |
| FF deja de ser lazy o WF cambia score por visualización | Tests de generación/evaluación incremental y salida temprana; no consumir iteradores ni tocar ranks para animar. |
| Límites de resolución/recursos insuficientes | Validar resolución configurada única y coordinar guardrails TA-037; sin mínimo automático ni 1 mm arbitrario. |
| Máscaras grandes en JSON/DOM | Descriptor, recuperación acotada/ventanas y canvas; mantener resolución algorítmica independiente del nivel visual. |
| Clientes actuales rechazan eventos nuevos | Resolver comparación A/B mediante pruebas; no asumir que una extensión es compatible ni imponer visual-v2 sin revisión. |
| Progreso ficticio | Solo hitos reales, muestras rotuladas y contadores procesadas/colocadas separados. |
| Cerrar vista se interpreta como rollback de pedidos | Explicar estado real, aborto cooperativo y GET; no consumir inventario ni normalizar pedidos automáticamente. |
| Datos originales editados difieren del preview | Fuente visual ligada al snapshot aceptado, no a otro `/rasterize` sobre Orders mutable. |
| Confundir conservador con exacto | Mensaje de aproximación y GAP vectorial separado; no nuevas garantías sin validar. |
| Duplicación/conflicto de trabajo | Acordar TA-016/018/019/021/037 y delimitar preparación, telemetría e integración multimétodo. |

## 9. Definition of Done y cierre técnico local

- [ ] SPEC y PLAN revisados; responsables, dependencias y contrato visual acordados.
- [x] DG-01 cerrada y registrada antes de implementar T03: B elegida expresamente.
- [x] Los 26 CA cuentan con implementación y pruebas propias trazables, conservando la condición multimétodo de CA-17.
- [x] Bases previas y trabajo lazy medidos; resolución única configurada validada.
- [x] Máscara visual backend verificable y throttling/agrupamiento probados.
- [x] FF/WF sin regresiones; UI lista para métodos realmente integrados.
- [x] V1 y HU-015 compatibles; no consumo hasta confirmación explícita.
- [x] Pruebas unitarias/componentes/integración/E2E y rendimiento aplicables correctas.
- [x] Evidencia reproducible, diff de alcance y revisión local de accesibilidad disponibles.
- [x] Decisión del GAP vectorial registrada sin atribuir garantías inexistentes.

El cierre técnico local cubre T01–T06. El primer punto permanece abierto por la
asignación formal/revisión cruzada humana pendiente; no se inventa un responsable
humano ni una aprobación independiente. SPEC/PLAN y DG-01 sí fueron aprobados
por el solicitante. Las pruebas no sustituyen esa revisión ni la integración.
No se cambió el backlog remoto, publicó HU-017, abrió PR o hizo merge. Las
correcciones HU-016 publicadas por instrucción independiente y el cambio local
de CI no forman parte de esta rama.

## Historial de estado

| Fecha | Estado | Nota |
|---|---|---|
| 25/10/2026 | Draft | Plan derivado de SPEC HU-017; 18 SP / 108 h propuestas más trabajo vectorial opcional separado. Pendiente de revisión. |
| 25/10/2026 | Draft | Estimación revisada a aproximadamente 10 SP / 60 h, sujeta al PLAN final; bases previas, orientaciones/posiciones lazy, CA-26 y throttling. Perfil visual-v2 solo como decisión técnica propuesta. |
| 25/10/2026 | Draft | Precisada congelación previa de configuración y fidelidad de máscara/geometría; alternativas A/B de streaming pendientes. Estimación preliminar T01..T06: 1.5/2/1.5/2/1/2 SP, total 10 SP / 60 h. |
| 25/10/2026 | Approved | Cierre documental autorizado: DG-01 obligatoria y abierta antes de implementar T03; TA-021 definida, HU-017 consumidor visual sin ganador. Se mantienen 10 SP / 60 h; sin implementación ni revisión cruzada atribuida. |
| 27/10/2026 | Approved | Inicio local autorizado de T01 desde `4bcf54d`, con commits y validación por incremento. DG-01 abierta; sin alterar estimación ni declarar cierre global. |
| 27/10/2026 | Approved | Núcleo T02 implementado/validado en `1291d65`; DG-01 sigue abierta antes de T03. Sin cierre global, publicación ni cambios en los 26 CA o la estimación. |
| 27/10/2026 | Approved | Solicitante elige B («Vamos por B»); DG-01 Closed con perfil visual-v2 optativo y reglas documentadas. T03 habilitada, aún no implementada; sin cambio de estimación ni cierre global. |
| 28/10/2026 UTC | Verified — local | T01–T06 implementadas, pruebas completas y evidencia final/matriz CA; misma estimación 10 SP / 60 h. PostgreSQL temporal por autorización expresa. Cierre técnico local, sin publicación ni revisión humana atribuida. |
