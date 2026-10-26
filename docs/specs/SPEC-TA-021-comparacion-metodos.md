# SPEC-TA-021 — Comparar FF/BF/WF sobre una instancia idéntica

## Información general

| Campo | Valor |
|---|---|
| ID / nombre | TA-021 — Comparar FF/BF/WF sobre una instancia idéntica |
| Estado | **Reviewed** |
| Sprint / módulo | Sprint 2 / Optimization |
| Responsable / revisor | Pendientes de asignación formal |
| Fecha | 25/10/2026 |
| Rama documental | `docs/TA-021-comparacion-metodos` |
| Base auditada | `da550d0`, árbol inicialmente limpio |
| PLAN | [PLAN-TA-021-comparacion-metodos.md](PLAN-TA-021-comparacion-metodos.md) |
| Estimación de referencia | Backlog comunicado: 1 SP = 6 h; no se modifica el backlog. |
| Fases | T01: infraestructura común + FF/WF; T02: BF integrado y validación FF/BF/WF. |

Estado Reviewed por autorización documental del solicitante. El revisor y la
revisión cruzada real permanecen pendientes; no se atribuye una revisión no
realizada ni se declara Implemented o Verified. Se mantienen los 20 CA y el
alcance incremental: T01 no cierra TA-021 y T02 requiere integrar TA-018 real.

## 1. Identidad, fuentes y objetivo

Antes de crear esta SPEC se inspeccionaron referencias TA-021 en el repositorio,
mensajes de commits y nombres históricos de archivos de las referencias Git
locales. No se encontró otra SPEC/PLAN TA-021 autoritativa ni una asignación en
conflicto. La [SPEC HU-017](SPEC-HU-017-proceso-visual-optimizacion.md) Reviewed y
su [PLAN](PLAN-HU-017-proceso-visual-optimizacion.md) Approved ya la definen como
comparación/orquestación de FF/BF/WF sobre la misma instancia, sin selección del
ganador. Esta SPEC desarrolla ese alcance; no sustituye el backlog externo.

Se revisaron también [TA-019](SPEC-TA-019-worst-fit.md), su
[PLAN](PLAN-TA-019-worst-fit.md), el core de Optimization, preparación/stock,
snapshots, métricas y `/runs`. No se encontraron SPEC/PLAN propios de TA-018,
TA-022, TA-025, TA-026 o TA-037 en la documentación/historial local consultados.
Su separación de responsabilidades se adopta del alcance comunicado y de las
referencias disponibles; no se inventan sus implementaciones o aprobaciones.

**Objetivo:** ejecutar una colección variable de heurísticas sobre una misma
instancia lógica y entregar resultados identificados, técnicamente comparables,
sin que la ejecución de un método altere las condiciones de otro.

```text
Instancia lógica común → colección de métodos disponibles → resultados por método
T01:                    FF / WF                           → comparación parcial
T02:                    FF / BF / WF                       → validación final
```

Las fases son entregas incrementales de TA-021, no variantes incompatibles.
**T01 no cierra TA-021. TA-018 bloquea T02 y el cierre, pero no bloquea T01.**

## 2. Alcance

### Incluye

- Orquestación/comparación backend en memoria para N métodos disponibles, sin
  codificar el mecanismo exclusivamente para dos heurísticas.
- Captura/preparación única de las condiciones comunes y aislamiento de estado.
- Identidad inequívoca de método y resultados completos o parciales.
- Reutilización de métricas existentes aplicables bajo reglas comunes.
- Reproducibilidad por método, independencia del orden y preservación FF/WF.
- Incorporación de BF real después de TA-018, mediante el mismo mecanismo.
- Contrato de resultados consumible posteriormente, sin implementar sus consumidores.

### Fuera de alcance

- Elegir un ganador, ordenar resultados por conveniencia, ponderar métricas o
  aplicar desempates entre métodos: corresponde a **TA-025**.
- Nuevas fórmulas/métricas de **TA-022** o benchmarks estadísticos de algoritmos.
- Nueva persistencia experimental/multimétodo, exportación durable o migraciones:
  corresponde a **TA-026**.
- UI, cambios frontend y streaming visual/NDJSON de **HU-017**.
- Reimplementar, ajustar o duplicar FF/BF/WF, geometría, rotaciones o stock.
- Confirmar, reservar/consumir inventario, cambiar estados de pedidos o invocar
  el ciclo transaccional de `/runs` por cada método.
- Paralelismo obligatorio, infraestructura distribuida, registro dinámico de
  plugins o políticas automáticas de resolución/presupuesto.
- Implementar la preparación visual futura de HU-017 o los guardrails de TA-037.

## 3. Actor y precondiciones

**Actor:** caso de uso backend o prueba que solicita comparación; no se agrega
un endpoint o actor UI en esta tarea.

- Instancia validada con pedidos explícitos, geometrías y cantidades expandidas,
  materiales, stock capturado y configuración común completa.
- Métodos solicitados disponibles y con identificador inequívoco. Validar toda
  la colección antes de invocar la primera estrategia: rechazar identificadores
  duplicados, incluso si corresponden a objetos distintos, colección vacía o
  métodos no disponibles. No sustituir BF por FF ni omitirlo silenciosamente.
- Capturar una sola vez, antes de ejecutar las heurísticas, todos los parámetros
  comunes realmente necesarios para resultados/métricas comparables y mantenerlos
  invariantes durante la comparación, además del problema geométrico.
- Entorno, precisión numérica y versión de los componentes comunes equivalentes
  para las ejecuciones contrastadas. No se exige igualdad de tiempo medido.

## 4. Qué significa «misma instancia» en el código existente

No se encontró una clase `ProblemSnapshot`. El contrato geométrico actual es
`OptimizationProblem`; `PieceSnapshot` es una entrada de preparación por pieza
y cantidad. El snapshot durable V1 contiene `result.problem` y metadatos
adicionales: no equivale a una API de comparación multimétodo.

| Condición invariante | Representación actual | Regla de comparación |
|---|---|---|
| Pedidos | `OptimizationProblem.order_ids` | Mismos IDs; preparación existente ordena ascendentemente. |
| Piezas y cantidades | `PieceSnapshot.quantity` antes de expandir; `PieceUnit` con `order_id`, `piece_id`, `unit_index` después | Mismas unidades y metadatos. No inventar `quantity` dentro de `PieceUnit`. |
| Geometría y área | `PieceUnit.geometry`, `area_mm2` | Mismos snapshots canónicos originales, sin relectura ni redondeo distinto por método. |
| Material/espesor | `MaterialGroup.key`, `PieceUnit.material_key`, `StockCandidate.material_key` | Mismos grupos y compatibilidad exacta de tipo/espesor. |
| Orden de piezas | `prepare_group_units` | Área DESC, mayor dimensión bbox DESC, pedido/pieza/unidad ASC. Sin reordenar según el método solicitado. |
| Orden de grupos | `prepare_problem` / `pack` | Mismo orden por tipo/espesor. |
| Stock elegible | `MaterialGroup.stock_candidates` | Misma secuencia capturada una vez por grupo; mismos candidatos, no solo igual área total. |
| Identidad y cantidad física | `StockCandidate.source`, `material_id`, `physical_unit_index` | Mismas unidades expandidas; un retazo es unitario. |
| Dimensiones de fuente | `StockCandidate.geometry`, `area_mm2` | Misma geometría interior potencial, dimensiones y área; no reemplazar retazos por bbox. |
| Orden de fuentes | `InventoryStockAdapter.list_compatible` y partición estable de `pack` | Retazos primero; fecha/ID DESC e índice físico ASC provienen del adaptador. Conservar orden recibido dentro del tipo. |
| Resolución efectiva | `OptimizationConfig.resolution_mm` | Único valor común; no escoger una resolución distinta para favorecer un método. |
| Margen y separación | `OptimizationConfig.margin_mm`, `separation_mm` | Valores idénticos y mismas reglas de conversión conservadora. |
| Rotación | `OptimizationConfig.angular_step_deg`, contrato de `RasterCache.orientations` | Misma configuración, orden/deduplicación y restricciones compartidas. No exigir igual cantidad de intentos entre políticas. |
| Restricciones geométricas | Validación de entrada, rasterizador, `SheetLayout` y guardrails compartidos | Misma versión/reglas; no existe hoy un campo genérico `constraints` que deba inventarse. |
| Configuración de corrida | `OptimizationProblem.config` | Mismos cuatro parámetros geométricos; no agregar campos de selección del ganador. |
| Umbrales de residuales | `minimum_width_mm`, `minimum_height_mm` de `calculate_metrics`; snapshot durable `residual_minimum_width_mm`/`residual_minimum_height_mm` | Captura común si se calculan métricas. No son campos de `OptimizationConfig`; provienen de mínimos de retazo configurados. |

Los términos conceptuales `min_remnant_width` y `min_remnant_height` se corresponden
aquí con los argumentos reales `minimum_width_mm` y `minimum_height_mm`; no se
declaran campos nuevos. La firma actual es `calculate_metrics(result,
minimum_width_mm, minimum_height_mm)`. El resultado aporta placements, geometrías,
áreas y `result.problem.config`; estos datos se derivan por método o pertenecen
al problema común según corresponda. No hay otros argumentos externos de esta
función que deban inventarse como configuración de comparación.

La instancia lógica es el problema preparado con stock y, para su contraste
métrico, todos los parámetros auxiliares comunes realmente utilizados, capturados
una vez antes del primer método e invariantes hasta terminar. Equivalencia significa igualdad de
datos relevantes, no identidad Python de cada objeto ni igualdad de placements
entre heurísticas distintas. Un método puede usar menos fuentes o colocar menos
piezas precisamente por su política; eso no hace diferentes sus entradas.

## 5. Reglas de comparación e independencia

### RN-01 — Capturar una vez y conservar condiciones

Validar/preparar la entrada y capturar el stock una sola vez antes de ejecutar
los métodos. En ese mismo límite capturar y fijar los parámetros comunes para
calcular resultados/métricas, incluidos mínimos de retazo cuando correspondan.
No volver a consultar Orders/Inventory/configuración ni releer esos parámetros
entre estrategias o antes de calcular las métricas de cada una.
Un cambio externo posterior no cambia esa instancia lógica ni garantiza stock
reservado para una futura confirmación.

El adaptador actual lee catálogos por grupo en transacciones de lectura. TA-021
compara el conjunto lógico capturado; no inventa una garantía nueva de snapshot
global SQL/MVCC simultáneo de todos los grupos ni locks de inventario.

### RN-02 — Estado inicial independiente

Compartir solo datos cuyo contrato real sea inmutable. `geometry_snapshot`
desconecta la geometría y usa `MappingProxyType`, con vértices convertidos a
tuplas de tuplas; los modelos del problema son dataclasses frozen con secuencias
tupla y números canónicos/Decimal. No basta copiar un dict/lista superficialmente.

`SheetLayout` es frozen; `place` devuelve otro estado con nuevas filas ocupadas/
bloqueadas. `RasterMask` usa filas tupla. En `pack`, `layouts`, `placements`,
`RasterCache` y contabilidad de memoria nacen dentro de cada llamada. El caché
derivado de `FeasibleCandidate` pertenece a esa ejecución, no al problema. Esta
descripción del código actual no obliga a que todo caché futuro sea exclusivo.

**Debe aislarse:** estado mutable de ejecución, layouts/ocupación, candidatos
mutables o ligados a un layout y acumuladores/contabilidad propios del método.
Un método no recibe como inicial el estado final de otro.

**Puede compartirse:** `OptimizationProblem`, geometrías, configuración congelada,
máscaras y cachés de datos derivados inmutables cuyo contrato permita reutilización
segura. Compartirlos no debe cambiar condiciones, presupuestos efectivos o
decisiones de otro método; no se exige duplicar snapshots/máscaras ni un caché
exclusivo por heurística. No confundir la inmutabilidad de valores de máscara con
seguridad automática de todo `RasterCache`: sus diccionarios y contadores actuales
son mutables. Un caché compartido requiere justificar el contrato real, no basta
una copia superficial o una anotación de tipo.

### RN-03 — Colección variable y preservación de políticas

El mecanismo admite una colección variable de métodos disponibles. Añadir BF
real no debe requerir otro comparador, otra preparación ni un flujo especial
para tres métodos. El contrato técnico mínimo se decide en el PLAN.

- **FF:** mismo orden y primera orientación/posición factible; lazy evaluation y
  salida temprana. No precalcular todos sus candidatos ni forzarlo a puntuar.
- **WF:** prioridad de fuentes, primera orientación/posición factible por fuente,
  score posterior a colocación y desempates actuales sin modificación.
- **BF:** usar solo la implementación/contrato aprobado e integrado de TA-018.
  No se define aquí su score ni se introduce un placeholder como método real.

TA-021 no añade una barrera geométrica nueva ni agota orientaciones para
«igualar» trabajo. Igualdad de condiciones no significa igualdad de operaciones.

### RN-04 — Identidad y contrato de resultados

Entregar una colección identificada por método, con el resultado común o una
adaptación mínima justificable: problema de referencia, placements, completitud,
faltantes y métricas disponibles. Conservar identidad de pedido/pieza/unidad y
fuente física. No inferir método por posición en la colección o por la fuente usada.
La unicidad de identificadores se valida antes de ejecutar, no solo al construir
la salida, para impedir ejecuciones ambiguas o sobrescrituras entre resultados.

Los métodos no pueden confundirse al aplicar métricas o copiar resultados. La
colección debe permitir distinguir fase FF/WF de fase FF/BF/WF por sus métodos
reales; no presentar una colección incompleta como validación final.

### RN-05 — Determinismo y orden de ejecución

Para la misma instancia/configuración, cada método produce el mismo resultado
geométrico repetidamente y conserva ese resultado al cambiar el orden de los
métodos. Contrastar por identidad de método, no por posición de salida.

La equivalencia funcional cubre placements ordenados, fuente física, orientación,
unidades colocadas/no colocadas, completitud y métricas/residuales deterministas
aplicables. Mantener FF→WF frente a WF→FF y las seis permutaciones FF/BF/WF.

Excluir de la igualdad tiempo de ejecución, timestamps, telemetría, IDs externos
de ejecución y cualquier medición naturalmente no determinista; no se excluyen
las identidades funcionales de pedidos, piezas o fuentes. Carga, calentamiento
de caché u orden pueden afectar latencias sin cambiar resultados. TA-021 no es
un benchmark experimental ni exige FF = WF = BF.

### RN-06 — Simulación pura respecto de efectos externos

Comparar no reserva/consume inventario ni modifica pedidos, corridas persistidas,
materiales propuestos o selección de ejecución. La confirmación sigue siendo una
acción separada. No invocar `AcceptRun`/`CalculateRun` repetidamente como sustituto
de una comparación: su ciclo actual crea/actualiza corridas y estados de pedidos.

### RN-07 — Métricas reutilizadas y errores honestos

Reutilizar las métricas comunes existentes y parámetros auxiliares equivalentes;
no duplicar fórmulas ni introducir índices/ponderaciones de comparación. Un GAP
indispensable se deriva a TA-022, sin incorporarlo dentro de TA-021.

SIN_SOLUCION, piezas no colocadas o su equivalente de dominio son resultados
válidos de una heurística, no fallos técnicos: conservan diagnóstico y pueden
formar parte de una comparación que ejecutó todos los métodos solicitados. No
confundir solución parcial de un método con comparación incompleta. Si no se colocó ninguna
pieza, `metrics=None` según el contrato actual; no inventar porcentajes o cero
para un denominador inexistente. Una métrica parcial no acredita solución completa.

Un fallo de precisión/recursos/cálculo es técnico, no NO_FIT ni peor rendimiento.
Una excepción técnica inesperada de una estrategia debe identificar inequívocamente
el método que falló y conservar su causa para diagnóstico. El mismo principio
aplica si falla el cálculo de métricas de ese método. Un conjunto al que falten
ejecuciones solicitadas no se presenta como una comparación válida completa.

Ni el fallo ni su manejo pueden modificar inventario, pedidos o el estado inicial
lógico de los demás métodos. Conservar las garantías de aislamiento aun cuando
no se complete la colección. No se exige un framework nuevo de reintentos,
rollback de estrategias ajenas o persistencia de fallos.

### RN-08 — Comparar no selecciona

No elegir automáticamente mayor aprovechamiento, menor merma/tiempo ni una
combinación ponderada. No marcar un `winner`, `selected_method` o ejecución
preferida, ni ordenar por calidad. TA-025 recibe los resultados después;
TA-026 los persiste cuando su contrato exista y HU-017 los visualiza después.

## 6. Métricas y límites de responsabilidad

| Dato actual | Fuente y tratamiento |
|---|---|
| Aprovechamiento, merma | `OptimizationMetrics.utilization_pct`, `waste_mm2`; mismas fórmulas y redondeo de `calculate_metrics`. |
| Planchas y retazo recuperable | `new_sheets_used`, `recoverable_remnant_mm2`; mismas unidades físicas y mínimos de ancho/alto comunes. |
| Áreas base | `material_area_mm2`, `placed_piece_area_mm2`; se refieren a material usado/piezas colocadas por cada método. |
| Tiempo | `OptimizationResult.computation_time_ms`; si se mide, usar una frontera común equivalente a optimización + métricas, excluyendo I/O de stock y entrega de eventos. No es determinista ni un benchmark estadístico. |
| Completitud y faltantes | Propiedades existentes de `OptimizationResult`; acompañan cualquier contraste para no confundir una parcial con una solución completa. |

No se encontró SPEC propia TA-022 local; las fórmulas actuales sí existen.
TA-021 puede reutilizarlas sin esperar una implementación nueva. Cambios o
métricas adicionales pertenecen a TA-022. El score local WF de capacidad libre
posterior no se convierte en una métrica global común entre algoritmos.

El esquema SQL admite FF/BF/WF, pero snapshot/HTTP/ciclo de ejecución actuales
están especializados en FF. `run_snapshot.decode` reconstruye `OptimizationResult`
base y no preserva por sí solo la especialización WF. No usar ese camino como
clonado multimétodo ni generalizarlo aquí: TA-026 es la dependencia posterior.

## 7. Flujo principal y alternativas

1. Recibir problema preparado validado, condiciones métricas comunes si aplican
   y colección de métodos disponibles.
2. Validar toda la colección e identidades únicas antes de ejecutar.
3. Conservar una única instancia lógica y los parámetros métricos comunes ya
   capturados, sin relecturas o modificaciones entre métodos.
4. Ejecutar cada método con estado inicial independiente y sus reglas intactas.
5. Aplicar métricas comunes cuando correspondan, conservando identidad del método.
6. Entregar resultados identificados sin persistir, seleccionar ni visualizar.

Alternativas: entrada/colección inválida o BF no disponible → error explícito;
stock vacío/no fit → resultado parcial con faltantes; error técnico → no anunciar
una comparación final completa y señalar el método que falló, sin efectos
externos ni contaminación. Orden de métodos distinto → resultados funcionales
iguales por método, excluyendo tiempo, timestamps, telemetría y mediciones
naturalmente no deterministas.

## 8. Criterios de aceptación

| CA | Criterio verificable | Fase de evidencia |
|---|---|---|
| CA-01 | Admite colección variable de heurísticas disponibles, sin mecanismo rígido para dos métodos. | T01/T02 |
| CA-02 | Todos reciben una instancia lógica equivalente y los parámetros comunes realmente utilizados para resultados/métricas, capturados una sola vez antes de ejecutar e invariantes durante la comparación. | T01/T02 |
| CA-03 | Unidades/cantidades, orden relevante y configuración geométrica son equivalentes. | T01/T02 |
| CA-04 | Stock físico disponible, dimensiones, compatibilidad y orden contractual son equivalentes. | T01/T02 |
| CA-05 | Ningún método modifica la entrada lógica ni el estado inicial de otro; se aísla el estado mutable de ejecución, permitiendo reutilizar datos/cachés inmutables de forma segura. | T01/T02 |
| CA-06 | Comparar no consume/reserva inventario ni altera pedidos. | T01/T02 |
| CA-07 | Cada resultado tiene identificador inequívoco de método; identificadores duplicados se rechazan antes de invocar cualquier estrategia. | T01/T02 |
| CA-08 | FF conserva comportamiento, lazy evaluation y salida temprana. | T01/T02 |
| CA-09 | WF conserva fuentes, colocación canónica, score posterior y desempates. | T01/T02 |
| CA-10 | T01 ejecuta FF/WF correctamente, dejando TA-021 abierta. | T01 |
| CA-11 | BF se incorpora mediante el mismo mecanismo sin rediseño estructural. | T01 diseño / T02 validación |
| CA-12 | La fase final ejecuta FF/BF/WF reales integrados sobre condiciones equivalentes. | T02, bloqueante del cierre |
| CA-13 | Misma entrada/configuración produce resultados funcionales deterministas por método, excluyendo tiempo, timestamps, telemetría y mediciones naturalmente no deterministas. | T01/T02 |
| CA-14 | FF→WF y WF→FF, y las seis permutaciones finales FF/BF/WF, conservan placements, fuentes, orientaciones, unidades colocadas/no colocadas y métricas derivadas deterministas por método. | T01/T02 |
| CA-15 | No selecciona, pondera ni clasifica métodos por calidad para elegir ganador. | T01/T02 |
| CA-16 | Reutiliza métricas comunes sin introducir fórmulas pertenecientes a TA-022. | T01/T02 |
| CA-17 | No introduce nueva persistencia multimétodo de TA-026. | T01/T02 |
| CA-18 | No introduce UI o streaming visual de HU-017. | T01/T02 |
| CA-19 | No modifica políticas internas de FF/WF/BF ni geometría compartida. | T01/T02 |
| CA-20 | Contrato común con completitud/faltantes y métricas disponibles: SIN_SOLUCION o equivalente es resultado válido; una excepción técnica identifica el método fallido, no presenta el conjunto incompleto como comparación válida completa y no altera inventario/pedidos/entrada de otros métodos. | T01/T02 |

Son objetivos de implementación futura, no una matriz PASS actual. T01 solo
aporta evidencia parcial del alcance final; CA-11/12 y los CA aplicables a BF
deben demostrarse con TA-018 real antes de declarar TA-021 Closed.

## 9. Dependencias

| Dependencia | Clasificación y condición |
|---|---|
| FF y TA-019 | Base disponible para T01; reutilizar entradas y regresiones. |
| TA-016 | Contrato común actual disponible. Evoluciones coordinadas no bloquean T01 mientras mantengan equivalencia/identidad; una incompatibilidad real debe resolverse antes de validar ese contrato. |
| TA-018 | Bloqueante de T02 y del cierre; no bloquea T01 FF/WF. BF no encontrado en la base local auditada, en desarrollo según contexto. |
| TA-022 | Coordinación no bloqueante si las métricas existentes son suficientes; un GAP indispensable o cambio de semántica requiere su definición antes de esa validación métrica. |
| TA-025 | Consumidor posterior y dueño de reglas de selección; no bloquea cálculo/comparación. |
| TA-026 | Persistencia posterior; no bloquea contrato en memoria. |
| HU-017 | Consumidor visual futuro; no bloquea pruebas backend ni impone resolver DG-01 de streaming en TA-021. |
| TA-037 | Coordinación de carga/guardrails, no implementación propia. Si el conjunto excede límites actuales y no existe política aprobada, bloquear esa carga, no simular igualdad omitiendo métodos. |

## 10. Pruebas y evidencia previstas

- Una preparación/lectura de stock por conjunto comparado, no por método.
- Misma entrada completa verificada antes/después de cada ejecución, incluida
  geometría anidada, unidades y orden de fuentes.
- Métodos ejecutados directamente frente al comparador: mismo resultado por
  método, aunque FF/WF produzcan patrones distintos entre sí.
- FF→WF y WF→FF; después las seis permutaciones FF/BF/WF, con repeticiones.
- Multipedido/multimaterial, cantidad física, retazo/fallback, rotación necesaria,
  margen/separación, geometría irregular, no stock y resultados parciales.
- Métricas comunes y ausencia de métricas para cero colocadas; mismos mínimos.
- Regresión de lazy FF y WF; no prueba de carga masiva ni OOM.
- Slice de lectura real con inventario/pedidos/tablas intactos, sin `/runs`.
- BF simulado para probar extensibilidad no valida CA-12 ni cierra T02.

Evidencia futura: `docs/evidence/sprint-02/TA-021/`, con revisión/instancia común,
métodos realmente integrados, órdenes, comandos y resultados reales por fase.
No se ejecutan pruebas ni se genera evidencia funcional en esta entrega documental.

## Historial de estado

| Fecha | Estado | Nota |
|---|---|---|
| 25/10/2026 | Draft | Alcance compatible con HU-017; T01 FF/WF y T02 con BF. Sin implementación ni aprobación automática; cierre requiere tres métodos. |
| 25/10/2026 | Draft | Precisados parámetros métricos invariantes, error técnico identificado por método, unicidad previa, equivalencia funcional por orden y posibilidad de compartir cachés/datos inmutables seguros. Sin implementación ni cambio de estimación. |
| 25/10/2026 | Reviewed | Cambio de estado autorizado documentalmente; revisor/revisión cruzada pendientes. Sin implementación ni verificación, con 20 CA y alcance T01/T02 intactos. |
