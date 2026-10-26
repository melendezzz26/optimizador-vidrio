# PLAN-TA-021 — Comparar FF/BF/WF sobre una instancia idéntica

## Información general

| Campo | Valor |
|---|---|
| Estado | **Approved** |
| SPEC | [SPEC-TA-021-comparacion-metodos.md](SPEC-TA-021-comparacion-metodos.md), Reviewed |
| Responsable / revisor | Pendientes de asignación formal |
| Fecha / base | 25/10/2026 / `da550d0` |
| Rama | `docs/TA-021-comparacion-metodos` |
| Estimación de referencia | 1 SP / 6 h, backlog comunicado; sin actualización del backlog. |
| División preliminar | T01 0.5 SP / 3 h; T02 0.5 SP / 3 h. |
| Restricción de cierre | TA-018 integrada y FF/BF/WF reales validados; T01 sola no cierra TA-021. |

## 1. Autoridad, objetivo y auditoría de alcance

Este PLAN deriva de la SPEC Reviewed y pasa a Approved por autorización
documental del solicitante. Revisor y revisión cruzada real pendientes; la
aprobación no declara implementadas ni verificadas sus capacidades.

Se mantienen T01 como infraestructura genérica + FF/WF y T02 como incorporación
de BF real después de integrar TA-018. TA-021 permanece abierta tras T01. Los
20 CA, 0.5 SP por tarea y total de 1 SP / 6 h no cambian; siguen fuera de alcance
UI, persistencia, selección de ganador y nuevas métricas.

La inspección previa confirmó rama/árbol limpio y no encontró SPEC/PLAN TA-021
en conflicto. HU-017 ya define ese ID como comparación/orquestación, sin ganador;
TA-019 excluye selección TA-025 y persistencia TA-026. No se modifica ninguna de
esas fuentes ni se atribuyen estados externos de backlog no comprobados.

No existe una clase `ProblemSnapshot` local ni un comparador de estrategias
integrado. Se encontró infraestructura suficiente para una orquestación pequeña
en memoria; no es necesario extender `/runs`, UI o SQL para demostrar T01.

## 2. Infraestructura real y mínimo faltante

Los caminos backend de esta sección parten de `backend/app/modules/optimization/`.

| Componente inspeccionado | Reutilización / límite |
|---|---|
| `domain/first_fit.py`, `worst_fit.py` | Ambos exponen `optimize(problem, on_event=None)`. WF devuelve especialización de `OptimizationResult` con `method="WF"`; FF devuelve el tipo base con método FF. |
| `domain/packing.py` | Recorrido común con `select` opcional, candidatos perezosos y, actualmente, estado/cachés nuevos por llamada. Es descripción de la base, no prohibición de compartir datos/cache inmutables seguros. No cambiar selectores para comparar. |
| `domain/problem.py` | Problema/configuración/unidades/stock inmutables; `geometry_snapshot` copia y congela geometrías. `OptimizationResult.method` hoy contempla FF/WF, no BF. Coordinar identidad BF con TA-018. |
| `domain/preparation.py`, `application/preparation.py` | Validación y expansión de `PieceSnapshot.quantity`; orden y grupos compartidos. No hay `quantity` en unidades expandidas. |
| `application/stock.py`, `infrastructure/stock_adapter.py` | Lectura compatible y orden estable, cantidad física expandida y caché por grupo de una preparación. Llamar una vez, no una vez por método. |
| `domain/placement.py`, `raster_mask.py`, `rotation.py` | Layouts/máscaras inmutables, caché raster actual con mapas/contadores mutables. Aislar ocupación/estado por método; máscaras o cachés de derivados inmutables pueden compartirse si su contrato es seguro. |
| `domain/metrics.py` | Calcula métricas/residuales comunes sin escrituras. Necesita mínimos de ancho/alto externos al problema geométrico. Preserva WF mediante `replace`. |
| `infrastructure/run_snapshot.py` | JSONB V1, `decode` reconstruye tipo base FF. No es clonador genérico de resultados WF/BF ni debe extenderse aquí. |
| `application/runs.py`, `calculation.py`, `infrastructure/run_uow.py` | Aceptación/persistencia/transición de pedidos y selección de ejecución FF. No reutilizar el ciclo completo como comparador puro. |
| `presentation/run_routes.py`, `run_stream.py`, `run_schemas.py` | `/runs`, GET, NDJSON y confirmación actuales especializados en FF. Mantenerlos intactos; futuro consumo no exige integración HTTP ahora. |
| SPEC/PLAN TA-019 y evidencia | Reglas WF y regresiones de aislamiento/no consumo ya disponibles; no trasladar sus PASS a una comparación aún inexistente. |
| HU-017 | Consumidor futuro visual, con DG-01 propia. TA-021 no decide A/B de streaming ni implementa su UI. |

No se hallaron SPEC/PLAN propios de TA-018/022/025/026/037 en los archivos e
historial local consultados. BF no existe en el core de la base inspeccionada;
usar su contrato real cuando TA-018 se integre, no un supuesto score BF.

## 3. Diseño mínimo propuesto: N métodos, una entrada

### 3.1 Alternativas de orquestación

| Alternativa | Evaluación |
|---|---|
| Colección de estrategias/factorías identificadas | Recomendada: FF/WF ya comparten firma de entrada/salida. Una iteración genérica basta; una factoría por invocación evita depender de estado futuro del optimizador. |
| Registro global/factory con descubrimiento de plugins | Innecesario para métodos conocidos y colección pequeña; añade estado/configuración sin requisito. |
| Nuevo protocolo/clase base obligatoria | No existe un protocolo de optimizadores en la base. No crearlo solo para dos clases ya compatibles; evaluar una anotación mínima solo si el tipado ayuda sin cambiar sus políticas. |

**Propuesta, no código implementado:** servicio en `application/comparison.py`
que reciba `OptimizationProblem` ya preparado con stock, colección ordenada
de pares `(código, factoría del optimizador)` y parámetros métricos comunes.
Validar toda la colección y códigos únicos/disponibles antes de invocar la primera
estrategia; dos estrategias con el mismo código se rechazan sin ejecutar ninguna.
Ejecutar
secuencialmente para no multiplicar memoria de trabajo ni introducir concurrencia.

T01 registra/recibe FF y WF; T02 incorpora la factoría BF entregada por TA-018.
No hay `run_ff()` + `run_wf()` ni un segundo flujo para tres métodos. La colección
puede tener distinto tamaño; el orden solicitado solo determina orden de entrega,
no ranking por mérito. Un doble de prueba adicional puede demostrar extensibilidad,
pero no representa BF real ni completa T02.

### 3.2 Preparación y aislamiento

```text
Lecturas/snapshots y configuración comunes
  → prepare_persisted_problem (una vez)
  → with_compatible_stock (una vez)
  → OptimizationProblem inmutable P + parámetros métricos comunes capturados una vez
  → iterar colección de métodos, cada uno con estado local nuevo
  → resultados identificados, en memoria, sin ganador
```

Compartir P validado es suficiente: geometrías desconectadas y profundamente
inmutables, tuplas y dataclasses frozen. No usar dicts originales mutables de
Orders ni afirmar que `copy()` resuelve aislamiento. No usar serialización de
snapshots V1 o `deepcopy` indiscriminado de `MappingProxyType` como clonador.

Cada factoría crea el optimizador para su invocación; el `pack()` actual crea
`RasterCache`, `layouts`, `placements` y contabilidad locales. No imponer un caché
exclusivo por estrategia: la obligación es aislar layouts/ocupación, candidatos
mutables y acumuladores propios del método. No pasar `layout_after` del anterior
como estado inicial de otro.

P, geometrías, configuración congelada, máscaras y cachés de derivados inmutables
pueden reutilizarse cuando el contrato existente lo permita sin contaminación.
El `RasterCache` actual no se considera automáticamente compartible por almacenar
máscaras inmutables: también tiene mapas/contadores mutables. No rediseñarlo para
esta tarea ni compartir estado que altere condiciones, límites o decisiones de
otro método. Las diferencias naturales de latencia no forman parte de la igualdad
funcional. Los resultados normalizan/copian contenedores mediante `replace`;
comprobar igualdad lógica del problema, no que `result.problem is P`.

No precalcular orientaciones/materiales para «nivelar» número de operaciones ni
duplicar máscaras solo para cumplir aislamiento. Sus resultados
acumulados sí ocupan memoria proporcional a métodos/placements: no prometer
memoria constante de todo el conjunto.

### 3.3 Contrato de salida propuesto y métricas

Una colección en memoria con entrada por código de método, `OptimizationResult`
y residuales devueltos por el cálculo común. Puede resolverse con una dataclass
pequeña inmutable dentro del mismo módulo si es necesario; los nombres son
propuestas nuevas, no campos ya existentes del problema.

Mantener un único problema lógico de referencia y no serializarlo/copiarlo por
cada máscara. Verificar correspondencia entre código y `result.method` cuando
el contrato del optimizador lo informa. Rechazar discrepancias en vez de
reetiquetar FF como BF/WF. La identidad BF y cualquier adaptación mínima se
resuelven en T02 con el contrato real; no modificar anticipadamente `problem.py`.

Usar `calculate_metrics(result, minimum_width_mm, minimum_height_mm)` con todos
los parámetros comunes capturados una sola vez antes de ejecutar heurísticas e
invariantes hasta terminar. `min_remnant_width`/`min_remnant_height` son nombres
conceptuales de esos dos argumentos reales, no campos nuevos de P ni de
`OptimizationConfig`. La función actual no recibe otros argumentos externos:
usa además datos del resultado y su configuración común ya congelada.

**Solución mínima elegida en el PLAN:** recibir P y los dos valores comunes
inmutables como argumentos explícitos del servicio. Capturarlos una vez en su
límite de entrada y reutilizarlos por método. No crear obligatoriamente una clase
`ComparisonContext`, añadir campos al problema o inventar parámetros de métricas.
No abrir un UoW/releer configuración por método. Probar que un cambio de la fuente
externa después de la captura no cambia esos argumentos ni la comparación.

Si se mide `computation_time_ms`, cronómetro fresco por método con la frontera
actual optimización + métricas, excluyendo captura de stock, persistencia y
entrega de callbacks. Para validar igualdad funcional excluir tiempo, timestamps,
telemetría y toda medición naturalmente no determinista. Comparar placements,
fuente/orientación, colocadas/no colocadas y métricas derivadas deterministas;
no garantizar independencia del orden para latencias ni convertir TA-021 en
benchmark experimental.

### 3.4 Errores y consumidores

- Validar previamente todos los identificadores. Colección vacía, código duplicado
  entre estrategias o método no disponible: rechazo antes de ejecutar cualquiera.
- SIN_SOLUCION, no colocadas o equivalente del dominio: resultado funcional válido
  que se conserva; continuar con los demás métodos. Si todos se ejecutaron,
  la comparación puede estar completa aunque algún resultado sea una solución parcial.
- Excepción técnica inesperada: propuesta mínima fail-fast, con envoltura de error
  en `application/comparison.py` que identifique el método y encadene/conserve la
  causa original. Aplicar también a fallos al calcular sus métricas. No hace falta
  un framework de errores nuevo ni una tabla persistida.
- No devolver el conjunto incompleto como comparación válida completa, ni
  transformar la excepción en NO_FIT/SIN_SOLUCION. Los resultados anteriores,
  si se conservan para diagnóstico, no acreditan ejecución de los métodos faltantes.
- El fallo y su manejo no escriben inventario/pedidos ni modifican el problema,
  parámetros comunes o estado inicial lógico de otros métodos. Descartar solo
  estado local de ejecución; no invocar aceptación, confirmación o rollback de
  estrategias externas como parte del comparador.
- No almacenar eventos completos. T01 puede entregar solo resultados finales;
  si se exponen callbacks posteriormente, deben ir identificados por método e
  instancia, sin resolver NDJSON, replay o UI dentro de esta tarea.
- TA-025 consume resultados para seleccionar; TA-026 para persistir; HU-017 para
  representar. Ningún resultado retornado cambia `id_ejecucion_seleccionada`.

## 4. T01 — Infraestructura común + FF/WF

| Aspecto | Plan de ejecución futuro |
|---|---|
| Objetivo | Probar colección genérica, entrada idéntica, independencia y resultados FF/WF preservados. |
| Capas/archivos probables | Nuevo `application/comparison.py`; nuevas pruebas `tests/unit/optimization/test_comparison.py` y `tests/integration/optimization/test_comparison_slice.py`. Nombres ajustables. |
| Estrategia | Servicio secuencial y colección de factorías; P y parámetros métricos comunes capturados una vez; datos/cachés inmutables compartibles y estado mutable aislado; identidad y fallos por método. |
| Riesgos | Relecturas, aliasing mutable, pérdida de identidad WF, usar el ciclo `/runs`, convertir FF en exhaustivo. |
| Dependencias | FF/TA-019 y contratos actuales de geometría/métricas disponibles. TA-018 no bloquea. TA-037 se coordina para carga representativa, sin implementar guardrails nuevos. |
| Evidencia | Instancia pequeña común, resultados directos/frente a comparador, ambos órdenes, pruebas de no consumo/mutación y diff sin políticas/SQL/UI. |
| Condición de cierre de T01 | FF/WF validados, contrato genérico listo, regresiones correctas y evidencia de fase 1; **TA-021 sigue abierta**. |
| Estimación preliminar | **0.5 SP / 3 h**, sobre alcance mínimo descrito. |

Pruebas T01:

1. Colecciones de un método y FF/WF; vacío/duplicado/desconocido rechazados antes
   de llamar optimizadores. Dos objetos distintos con el mismo identificador
   deben rechazarse con cero invocaciones. Doble de extensibilidad distinto de BF.
2. Pieza 2×2, fuentes ordenadas 4×4 y 6×4: FF elige primera, WF la mayor capacidad
   posterior. El comparador reproduce cada ejecución directa; no iguala políticas.
3. FF→WF frente a WF→FF y repetición, por código de método; comparar placements,
   fuente, orientación, colocadas/no colocadas y métricas/residuales deterministas.
   Excluir tiempo, timestamps, telemetría y mediciones naturalmente no deterministas.
4. Entrada congelada antes/después, intento de mutar geometría anidada rechazado;
   mismo problema reutilizado sin contaminación y fuentes vírgenes por método.
5. Retazos, cantidad física, multipedido/multimaterial, rotación, margen/separación,
   irregular y parcial; reutilizar helpers/casos pequeños existentes sin duplicar
   exhaustivamente la suite geométrica.
6. Cero colocadas mantiene `metrics=None`; SIN_SOLUCION/parcial es un resultado
   válido. Capturar mínimos una vez antes de los métodos; cambiar su fuente externa
   después no altera el contraste. Métricas iguales a la llamada directa con esos valores.
7. Slice real de lectura con preparación/stock una vez, todas las tablas y estados
   de pedidos intactos. Reutilizar patrón SQLite de TA-019, sin migraciones.
8. Regresiones existentes FF/WF, incluidos lazy/early exit y retención acotada.
9. Inyectar una excepción técnica de estrategia o métricas: error identifica el
   método y conserva causa; no entrega comparación válida completa. Verificar
   P/parámetros comunes, inventario, pedidos y estado inicial de otros métodos
   sin cambios; no aceptar una colección truncada como éxito.

No imponer en las pruebas identidades distintas de caché por método: comprobar
aislamiento del estado de ejecución. Si la infraestructura utilizada comparte
datos/cache inmutables, probar que el reúso no altera resultados o condiciones;
no es requisito implementar un caché compartido nuevo.

## 5. T02 — Incorporar BF y cerrar comparación

| Aspecto | Plan de ejecución futuro |
|---|---|
| Objetivo | Incorporar BF real al mismo mecanismo y demostrar comparación FF/BF/WF completa. |
| Capas/archivos probables | Entrada/factoría BF en composición de comparación; ampliar los dos archivos de pruebas/evidencia. Adaptador mínimo solo si el contrato TA-018 lo requiere. |
| Estrategia | Inspeccionar TA-018 integrada, firma/resultado/identidad/métricas y registrar BF sin rediseñar el servicio. No definir ni copiar su score. |
| Pruebas | Tres métodos, seis órdenes posibles, repeticiones y resultados funcionales directos por método; misma entrada/configuración/stock/parámetros métricos; independencia/no consumo, fallos identificados; excluir tiempo/timestamps/telemetría. |
| Riesgos | Contrato BF incompatible o etiqueta incorrecta, diferencias de preparación, mezcla de ramas y un doble BF confundido con integración real. |
| Dependencias | **Bloqueada hasta integrar TA-018** y confirmar su contrato. T01 debe estar validada; cambios comunes TA-016 coordinados. |
| Evidencia | Revisión/commit que incorpora BF real, las seis permutaciones, matriz final de los 20 CA y suites reales por fase. |
| Condición de cierre | FF/BF/WF reales validados con todos los CA aplicables, evidencia y revisión. Solo entonces puede cerrarse TA-021; no por terminar T01. |
| Estimación preliminar | **0.5 SP / 3 h**, condicionada a compatibilidad del contrato TA-018. |

No preparar T02 mediante una implementación BF propia. Si BF devuelve otra forma
de resultado o requiere políticas distintas de preparación, documentar la
incompatibilidad antes de cambiar contratos: una discrepancia de implementación
no autoriza rebajar igualdad de condiciones ni refactorizar heurísticas desde TA-021.

## 6. Validación planificada y trazabilidad

| CA | Evidencia prevista |
|---|---|
| CA-01 | Colecciones de distinto tamaño; doble de extensibilidad; mecanismo genérico. |
| CA-02 | Problema y parámetros métricos capturados una vez antes de ejecutar; sin relecturas, iguales antes de cada llamada. |
| CA-03 | Unidades/cantidades/orden/configuración iguales, sin lecturas por método. |
| CA-04 | Tuplas completas de stock físico/dimensiones/orden iguales. |
| CA-05 | Entrada/datos compartidos inmutables, estado mutable aislado y resultados directos/por permutación iguales; sin exigir cachés exclusivos. |
| CA-06 | Snapshot de tablas de inventario/pedidos antes/después del slice sin cambios. |
| CA-07 | Identificadores únicos validados antes de cualquier invocación; duplicados rechazados, WF preservado y BF real en T02. |
| CA-08 | Regresión FF y prueba de no score/early exit, ejecución directa vs comparador. |
| CA-09 | Regresión WF de score posterior/desempates, ejecución directa vs comparador. |
| CA-10 | Evidencia de fase 1 FF/WF, estado TA-021 abierto. |
| CA-11 | Adición BF por composición sin rediseño estructural; validación real T02. |
| CA-12 | Tres métodos integrados, igualdad de condiciones demostrada; bloquea cierre. |
| CA-13 | Repeticiones funcionales por método, excluyendo tiempo/timestamps/telemetría y toda medición naturalmente no determinista. |
| CA-14 | Dos órdenes T01 y seis permutaciones T02; placements, fuente/orientación, colocadas/no colocadas y métricas deterministas iguales por método. |
| CA-15 | Salida sin ganador/ranking/ponderaciones; sin selección persistida. |
| CA-16 | Llamada a fórmulas comunes y mismos mínimos; ninguna métrica nueva. |
| CA-17 | Diff sin persistencia/SQL/migraciones; no llamadas a `save_result`. |
| CA-18 | Diff sin frontend ni contrato visual/HTTP nuevo. |
| CA-19 | Diff y suites prueban políticas intactas; incorporación BF desde TA-018. |
| CA-20 | Resultado parcial/SIN_SOLUCION válido; excepción técnica identifica método/causa, no éxito de conjunto incompleto y no modifica inventario/pedidos/estado inicial ajeno. |

Archivos existentes de regresión: `test_problem_contract.py`, `test_preparation.py`,
`test_stock.py`, `test_first_fit.py`, `test_worst_fit.py`, `test_metrics.py` y slice
WF dentro de las ubicaciones Optimization ya establecidas. Se referencian como
base; hoy no prueban un comparador que aún no existe.

Comandos propuestos desde `backend/`, solo durante futura implementación:

```powershell
.\venv\Scripts\python.exe -m pytest tests/unit/optimization tests/optimization tests/integration/optimization/test_worst_fit_slice.py tests/integration/optimization/test_comparison_slice.py -q
```

El archivo de comparison todavía no existe. No ejecutar este comando como si
fuera evidencia presente ni activar fixtures que migren bases sin autorización.
Guardar evidencia real por fase en `docs/evidence/sprint-02/TA-021/` con base,
colección, configuración/mínimos, datos sintéticos, orden y resultados por método.
Esta entrega documental no ejecuta suites ni crea evidencia funcional.

## 7. Estimación sin modificar backlog

| Tarea | SP preliminares | Horas |
|---|---:|---:|
| T01 — Infraestructura común + FF/WF | 0.5 | 3 |
| T02 — Incorporar BF y validar los tres | 0.5 | 3 |
| **Total de referencia** | **1** | **6** |

La división es razonable como estimación mínima condicionada: problema/stock
inmutables, firmas FF/WF, métricas y pruebas/slice ya existen; faltan un bucle
genérico, contrato pequeño y pruebas de combinación. No incluye UI, HTTP,
persistencia, ejecución concurrente, nuevos guardrails o fórmulas.

No es una garantía de plazo. Si TA-018 exige conversión no trivial de resultado,
evolución de identidad común o preparación distinta, eso añade trabajo no
demostrado hoy y puede superar las 3 h de T02. Si se exige benchmark global,
persistencia/streaming o múltiples dialectos DB, excede el alcance de 1 SP.
En tales casos informar tarea/horas adicionales para decisión del equipo, sin
actualizar automáticamente el backlog ni ocultarlos dentro de TA-021.

## 8. Dependencias, conflictos y límites

| Dependencia | Tipo / coordinación |
|---|---|
| TA-016 | Contrato común disponible, no bloquea T01 por mera existencia de trabajo paralelo; resolver incompatibilidades reales antes de validar. No modificar `rotation.py` aquí. |
| TA-018 | Bloqueante T02/cierre, no T01. Acordar identidad y contrato de resultado cuando se integre. |
| TA-019 | Base T01; reutilizar WF y sus pruebas, sin cambiar score ni candidatos. |
| TA-022 | No bloqueante con fórmulas actuales; dependencia condicional si aparece métrica indispensable ausente. No nueva métrica dentro del comparador. |
| TA-025 | Consumidor posterior de resultados; la selección empieza donde TA-021 termina. |
| TA-026 | Persistencia posterior. No adaptar `run_snapshot`/`run_uow` para guardar la comparación aquí. |
| HU-017 | Consumidor visual posterior; no bloquea T01/T02 ni impone implementar sus eventos. |
| TA-037 | Coordinar costo acumulado y límites. Ejecución secuencial limita memoria simultánea; no resuelve presupuestos globales por sí sola. |

**Conflictos con TA-018 y trabajo de Quispe:** evitar editar `packing.py`,
`first_fit.py`, `worst_fit.py`, `problem.py` y `rotation.py` para añadir otro
motor o un protocolo obligatorio. La propuesta añade composición y pruebas en
archivos separados. Si TA-018 cambia contrato común, coordinar un adaptador
mínimo con su autor antes de tocarlo desde TA-021.

Las fuentes históricas S1-OPT-UI/PLAN-S1 mencionan a Quispe como consumidor UI.
No se asume que esa mención le asigne automáticamente TA-018 en Sprint 2.
Coordinar con Quispe la forma de resultados/eventos que vaya a consumir: no
editar `runContract.js`, hooks o pantallas en esta rama. Acordar ownership del
contrato de comparación para no duplicar resultados ni introducir selección
del ganador en HU-017. No se inspeccionó ni se modificó una rama remota ajena.

## 9. Riesgos

| Riesgo | Mitigación propuesta |
|---|---|
| Mutación compartida | Aislar layouts/ocupación/candidatos mutables/acumuladores; compartir datos/cachés inmutables solo si es seguro. Probar invariancia también ante fallo; no confiar en copia superficial. |
| Duplicación innecesaria de snapshot/máscaras | Compartir P inmutable; no serializar/deepcopy por método ni precalcular todas las máscaras. |
| Memoria/CPU multiplicados | Secuencial; sumar costo temporal y tamaño de resultados retenidos, coordinar TA-037. Sin prometer costo constante ni añadir carga masiva. |
| FF deja de ser lazy | No consumir sus candidatos ni compartir ranking con WF; regresión existente y comparación con ejecución directa. |
| Diseño rígido de dos métodos | Colección de factorías, pruebas de cardinalidad y adición BF sin un flujo especial. |
| Conflictos con BF | T02 posterior a integración real, contrato acordado; no inventar su score/adaptación. |
| Duplicación de métricas | Reutilizar `calculate_metrics`, mismos mínimos; GAP a TA-022. |
| Persistencia/selección prematuras | No invocar `/runs`/`save_result` ni establecer ejecución seleccionada; TA-025/026 fuera. |
| Contaminación de inventario/pedidos | Lecturas únicas y slice que compara tablas; no aceptación/confirmación transaccional del lote. |
| Configuración distinta por método | Capturar una vez resolución/margen/separación/rotación y umbrales métricos; comparar valores, no solo IDs. |
| Comparar telemetría como determinista | Excluir tiempo/timestamps/telemetría y mediciones no deterministas; no benchmark experimental ni ganador por velocidad. |
| Confundir parcial/fallo con peor algoritmo | SIN_SOLUCION/parcial es válido; excepción identifica método/causa y no convierte un conjunto incompleto en comparación válida completa. |

## 10. Puerta de cierre de TA-021

- [ ] SPEC/PLAN revisados y responsables/contratos acordados.
- [ ] T01 FF/WF validada con evidencia, sin cierre anticipado de TA-021.
- [ ] TA-018 integrada y BF real incorporado al mismo mecanismo.
- [ ] T02 demuestra los 20 CA sobre FF/BF/WF, incluidas seis permutaciones.
- [ ] Regresiones correctas, misma instancia y cero cambios en inventario/pedidos.
- [ ] Métricas comunes, contrato identificado y ausencia de ganador/SQL/UI confirmadas.
- [ ] Evidencia reproducible de ambas fases y `git diff --check` correcto.

TA-021 **no puede declararse Closed** mientras falte BF real integrado o su
validación conjunta. Las tareas siguen planificadas, no ejecutadas; aprobar
este PLAN no marca CA como PASS ni declara Implemented o Verified. La revisión
cruzada real continúa pendiente.

## Historial de estado

| Fecha | Estado | Nota |
|---|---|---|
| 25/10/2026 | Draft | T01 FF/WF no bloqueada por TA-018; T02 y cierre condicionados a BF real. Referencia 0.5 + 0.5 SP, sin actualizar backlog ni implementar. |
| 25/10/2026 | Draft | Parámetros métricos explícitos invariantes sin clase obligatoria; fallos identificados por método, rechazo previo de IDs duplicados, orden funcional y datos/cachés inmutables compartibles. Se mantiene 1 SP / 6 h y riesgo de reestimación por incompatibilidad TA-018. |
| 25/10/2026 | Approved | Cambio de estado documental autorizado; SPEC Reviewed y revisión cruzada pendiente. T01/T02 sin cambios, 0.5 + 0.5 SP; TA-021 abierta después de T01 y cierre condicionado a BF real integrado. |
