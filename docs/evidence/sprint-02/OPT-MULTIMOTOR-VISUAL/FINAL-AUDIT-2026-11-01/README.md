# Auditoría final FF / BF / WF — 01/11/2026

Auditoría local de `feature/optimization-multimotor-visual`, HEAD
`5e836cdd9cc61eb212402d90dbe94a6776afcc75`, conservando los cambios pendientes.
La referencia remota de integración es
`afd5f85f9dd1495e4237e1029555f7e56cd53f30`. Ambas referencias se contrastaron
con `git ls-remote`: integración es ancestro y la rama tiene 23 commits propios.
No se hicieron commits, push, merge, rebase, cambios de rama ni despliegues.

Se ejecutó Python **3.11.9 en Ubuntu WSL2**, PostgreSQL **18 efímero y loopback**,
Node **22.23.2**, Chromium real, React/Vite y FastAPI. Las mutaciones,
confirmaciones, fallos inducidos y experimentos usan exclusivamente datos y
clústeres propios de pruebas. La base remota de pruebas solo se consultó con
transacción **READ ONLY**, filtro del usuario y los trabajos que este identificó;
no se publicaron configuraciones ni se confirmó ningún corte remoto.

## A. Estado de los algoritmos y contrato formal

### Fuentes de verdad

Se revisaron SPEC **y PLAN** de SP-002, TA-016, TA-018, TA-019, TA-020,
TA-021, TA-027 y S1 First Fit; SPEC TA-005/006 y TA-007; contratos
`run-v1`, `comparison-v1`, visualización y configuración, y límites TA-037.
La matriz de 20 reglas de SP-002 complementa su SPEC. Algunas SPEC conservan
estado documental Draft: esta auditoría verifica sus criterios técnicos y
no inventa aprobación humana ni cambia sus estados.

Referencias principales:

- [SP-002](../../../../specs/SPEC-SP-002-reglas-comunes-heuristicas.md),
  [PLAN](../../../../specs/PLAN-SP-002-reglas-comunes-heuristicas.md) y
  [matriz de reglas](../../SP-002/README.md).
- [TA-016 rotación](../../../../specs/SPEC-TA-016-rotacion-compartida.md),
  [TA-018 BF](../../../../specs/SPEC-TA-018-best-fit.md),
  [TA-019 WF](../../../../specs/SPEC-TA-019-worst-fit.md),
  [TA-020 prioridad](../../../../specs/SPEC-TA-020-retazo-priority.md),
  [TA-021 comparación](../../../../specs/SPEC-TA-021-comparacion-metodos.md),
  [TA-027 experimentos](../../../../specs/SPEC-TA-027-casos-experimentales.md).
- [PLAN First Fit, §§8 y 10](../../../../specs/PLAN-S1-optimization-first-fit.md)
  y [contrato comparativo](../../../../contracts/optimization/comparison-v1.md).
- TA-022, [T01 — Normalizar métricas comparables](https://app.notion.com/p/2f9e0c471a44835b940d019d6905c8b2):
  exige las mismas fórmulas, nombres y unidades para los tres métodos; no contiene
  otra fórmula que sustituya R4/PLAN. La página permanece Open.
- `CONTRIBUTING.md`, `docs/testing/README.md` y las propuestas locales de
  estándares de ingeniería, estrategia/plan de pruebas y diseño UI/UX v1.0
  facilitadas en Downloads. Se distinguen propuestas de aprobaciones registradas.

### Reglas comunes, sin cambiar el orden de piezas entre métodos

`preparation.prepare_group_units` ordena por **área DESC**, mayor dimensión del
bbox DESC, pedido ASC, pieza ASC, unidad ASC. `prepare_problem` expande cantidad
en identidades `(piece_id, unit_index)` y ordena grupos por vidrio/espesor.
`InventoryStockAdapter.list_compatible` conserva, dentro de cada tipo de fuente,
fecha DESC, ID DESC y unidades físicas ASC. No se introduce un orden por tamaño
para BF o WF. En una fuente, el candidato canónico es su **primera orientación
factible**, seguida de su **primera posición factible por fila/columna**.

El paso efectivo del snapshot comparativo es **5°**, común para los tres:
`0,5,…,355`; el círculo tiene una orientación. Se eliminan máscaras equivalentes
conservando el primer representante. La orientación y el contorno local ya
transformado se conservan juntos; el cliente no debe rotarlos otra vez.

Para cada pieza se busca primero el nivel **RETAZO**; solo si no contiene ningún
candidato factible se evalúa **PLANCHA**. La prioridad es elegibilidad, no un
peso que una plancha grande pueda superar. La compatibilidad exige el mismo
vidrio y espesor; no mezcla materiales.

Definición exacta de score para un candidato `c`:

```text
L' = layout después de colocar temporalmente el candidato canónico
score(c) = Σ bit_count(L'.usable[fila] & ~L'.blocked[fila])
tie(c) = (stock_rank, orientation_rank, row, column)
```

Incluye margen erosionado y bloqueo por separación. Es **capacidad raster libre
posterior**, posiblemente fragmentada, no área del bbox, área geométrica restante,
capacidad anterior ni búsqueda global de posiciones/ángulos.

| Método | Política formal dentro del primer nivel factible | Implementación real | Evidencia y veredicto |
|---|---|---|---|
| FF | Primer candidato factible en el recorrido estable; salida temprana, sin puntuar fuentes posteriores. | `domain/first_fit.py:FirstFitOptimizer.optimize` → `packing.pack(select=None)` → `next(candidates, None)`. | A coincide legítimamente; B elige A; regresión API/E2E del FF original. **Conforme**. |
| BF | Mínimo `(score, *tie)` entre todos los candidatos canónicos de ese nivel. | `domain/best_fit.py:BestFitSelector.select` y `BestFitOptimizer.optimize` → mismo `pack`. | B elige B y no A; C/D/E y TA-027 demuestran otras diferencias. **Conforme**. |
| WF | Mínimo `(-score, *tie)`, equivalente a mayor capacidad libre posterior. No hay prioridad adicional de planchas abiertas. | `domain/worst_fit.py:WorstFitSelector.select` y `WorstFitOptimizer.optimize` → mismo `pack`. | Casos WF-15/16, retazo primero, scores y reproducción del caso real. **Conforme; puede dispersar mucho**. |

Las rutas anteriores son relativas a
`backend/app/modules/optimization/`. El generador único es
`domain/packing.py:_feasible_candidates`; el score pertenece a
`FeasibleCandidate.remaining_free_cells_after_placement`. Los tres reutilizan
`SheetLayout`, `RasterCache`, `prepare_run_geometry` y las mismas restricciones.
BF/WF comparan fuentes, **no todas las posiciones ni todos los ángulos**.
TA-019 RN-02/RN-03/RN-05 lo establece explícitamente. Cambiarlo para reducir las
planchas de WF sería cambiar su política, no reparar un alias.

### Registro, aislamiento y recorrido efectivo

`infrastructure/comparison_runner.py:ENGINES` registra clases distintas bajo
`FF`, `BF`, `WF`. `calculation_worker` utiliza `ENGINES[method]`, sin default FF.
`ComparisonProcessRunner` arranca tres procesos `spawn`; cada uno decodifica el
mismo payload canónico y devuelve su método. El nuevo test comprueba tres PID
distintos y el mismo hash del snapshot **realmente persistido**. Los contratos
son inmutables; caché, layouts y selección pertenecen a cada ejecución. La
evaluación de un candidato no incorpora su layout si no gana.

`CalculateComparison.execute` asocia y guarda por ejecución/método en UoW
independientes; `SqlComparisonRepository.save_result` valida identidad. Los GET
por `/comparisons/{id}/executions/{execution_id}` devuelven el método propio.
En React, `comparisonController` indexa resultados por `execution_id`;
`ComparisonWorkspace.EnginePanel` recibe esa ejecución y
`api.forExecution({execution_id, method})`. No existe reutilización de FF para BF.
El E2E nuevo verifica el contraejemplo B con fuentes diferentes en la pantalla.

Comparado con integración, `first_fit.py`, `best_fit.py`, `worst_fit.py`,
rotación, colocación y métricas no cambiaron. En dominio, la rama solo añade el
hecho visual `ordering_ready` y su campo/variante de evento. **Esta auditoría no
modificó código productivo, heurísticas, contratos, recursos ni transacciones.**

## B. Casos diferenciales reproducibles

[CASE-RESULTS.md](CASE-RESULTS.md) contiene las 30 filas de métricas por ejecución.
[differential-results.json](differential-results.json) contiene **toda** la entrada,
ID de comparación/ejecución, piezas expandidas, fuentes/unidades físicas,
candidatos factibles, score/ranks, fuente ganadora, x/y, ángulo, geometría original
y orientada, máscara RLE hexadecimal sin pérdida y hash, no colocadas, métricas,
tiempo y reporte de recursos. Los IDs son de clústeres efímeros; se pueden repetir
entre casos. No representan cuentas ni inventario remoto.

Cada caso pasa por POST real → runner real → tres persistencias → GET; luego
se repite directamente sobre otra entrada equivalente para contrastar determinismo.
La normalización conserva fuentes, unidades, piezas, coordenadas, contornos,
ángulos, no colocadas y métricas. Solo aparta identidad del trabajo/ejecución,
duración y etiqueta del método para preguntar si el **patrón** es igual. Los
métodos y sus IDs se verifican por separado y nunca se borran del artefacto.

| Experimento | Entrada y criterio relevante | Patrón FF = BF | Aprovechamiento FF / BF / WF | Planchas FF / BF / WF |
|---|---|---|---|---|
| A | 6×4; retazos A 7×5 y B 10×7, A primero; scores 11 y 46. | Sí | 68.571 / 68.571 / 34.286% | 0 / 0 / 0 |
| B | 600×400 mm; A 1000×700 antes de B 700×500, ambos factibles. | **No** | 34.286 / 68.571 / 34.286% | 0 / 0 / 0 |
| C | 9 unidades rectangulares de tamaños variados, dos materiales, separación 1 mm; una fuente obliga 90°. | No | 45.960 / 45.960 / 45.960% | 0 / 0 / 0 |
| D | 4 triángulos convexos asimétricos; raster 0.5 mm, margen 0.5, separación 1.25 mm. | No | 38.333 / 38.333 / 38.333% | 0 / 0 / 0 |
| E | 6 unidades: rectángulos, círculos y pentágonos; retazo irregular; margen/separación 1 mm. | No | 22.554 / 22.554 / 11.226% | 1 / 1 / 3 |
| WF-15 | 15 piezas 1×1; nueve unidades físicas de plancha 4×4. | Sí | 93.750 / 93.750 / 10.417% | 1 / 1 / 9 |
| WF-16 | 16 piezas 1×1; diez unidades físicas de plancha 4×4. | Sí | 100.000 / 100.000 / 10.000% | 1 / 1 / 10 |
| F pequeño | TA-027 `EXP-SMALL-001`, original, 3 unidades. | Sí | 60.000 / 60.000 / 60.000% | 1 / 1 / 1 |
| F mediano | TA-027 `EXP-MEDIUM-001`, original, 9 unidades. | No | 28.413 / 28.413 / 18.584% | 1 / 1 / 2 |
| F complejo | TA-027 `EXP-COMPLEX-001`, original, 24 unidades. | No | 29.598 / 29.598 / 25.309% | 3 / 3 / 4 |

Todos colocaron todas sus unidades, sin faltantes. No se alteraron los tres
fixtures TA-027; los siete nuevos casos están en
`experiments/optimization/final_audit_cases.py`, fuera de su carpeta de baselines.

**A:** la primera fuente es también el mínimo: FF y BF usan A a `(0,0,0°)`.
WF usa B. Una coincidencia legítima no demuestra igualdad de implementaciones.

**B, contraejemplo mínimo solicitado:** resolución 1 mm, margen/separación 0,
paso 5°, mismo vidrio y espesor, ambas fuentes en el nivel retazo. Los márgenes
nulos son una configuración **del clúster aislado**, no un cambio de la base del
usuario. Los dos candidatos se colocan a `(0,0,0°)`; quedan
`700000 − 240000 = 460000` celdas en A y
`350000 − 240000 = 110000` en B. FF elige A, BF B, WF A. Es un cambio de fuente,
no una reordenación de piezas. La API y los E2E desktop/móvil comprobaron estos
IDs y contornos diferentes. No se necesitó alterar ningún algoritmo.

**C:** una unidad de otro material 3×2 entra en retazo 2×3 a 90°. La separación
y el grupo material se respetan. FF/BF tienen las mismas áreas agregadas y
diferentes asignaciones/posiciones; WF tiene distinta merma/recuperación.

**D:** vértices `[(0,0),(9,0),(2,5)]` y `[(0,0),(6,1),(1,8)]`, dos de cada uno.
FF/BF usan 0°/180° y distintos placements. WF incluye **295° y 305°**; demuestra
granularidad real de 5°, no solo cuartos de giro. La separación efectiva es
`ceil(1.25/0.5)=3` celdas, de manera conservadora. Ser triángulos no obliga a
que todas las heurísticas difieran en todas las entradas.

**E:** áreas de círculos por πr², polígonos por shoelace, geometría original
intacta y contorno orientado contrastado. FF/BF vuelven a coincidir en métricas,
sin coincidir en todos sus placements. WF puede utilizar más planchas.

**F:** se ejecutaron los tres casos originales dentro del presupuesto sin
recortarlos ni aumentar límites. El complejo utiliza 55°/65°/90° según el método.
Tiempos de esta corrida: pequeño 17/16/19 ms; mediano 28/36/26 ms; complejo
154/161/150 ms (FF/BF/WF). Son observaciones funcionales de una corrida,
**no** un benchmark estadístico ni una garantía de rendimiento en otra máquina.

### Contraste privado de casos reales

Se contrastaron resultados completos mediante una lectura privada y una
reproducción local supervisada de snapshots equivalentes. Se comprobaron
coincidencias legítimas de FF/BF y dispersión de WF conforme al contrato.
Un caso histórico carecía de resultado FF persistido; la reproducción local
no se presenta como reparación ni persistencia retroactiva de ese resultado.

Los identificadores, cantidades operativas, áreas de inventario, scores y
registros detallados de los casos reales permanecen exclusivamente en archivos
locales ignorados. La evidencia pública reproducible es la de los fixtures
sintéticos A–F y WF-15/WF-16. No se modificaron registros de la base remota.

## C. Worst Fit y las nueve/diez planchas

**Comportamiento legítimo de la política vigente, con calidad de solución baja
para estas entradas; no se encontró duplicación de fuentes ni un alias.**
TA-019 RN-02 dice que no se introduce prioridad de planchas abiertas frente a
sin usar. Dentro de PLANCHA, una nueva unidad vacía suele conservar más celdas
libres tras la colocación que una ya ocupada. El mayor score gana antes del
desempate por rank. Por eso cambiar el orden no elimina el efecto salvo empates.

Dentro de cada nivel se comparan unidades físicas ya usadas y disponibles.
La capacidad libre posterior de una unidad vacía puede superar la de una
ocupada. La prioridad de retazos se vuelve a comprobar para cada pieza: si un
retazo vuelve a resultar factible para una pieza menor, debe utilizarse antes
de evaluar planchas. Las métricas cuentan todas las fuentes realmente usadas,
una vez por unidad física, y no las fuentes meramente evaluadas.

Los fixtures públicos WF-15 y WF-16 reproducen exactamente el fenómeno 1 frente
a 9/10 planchas, sin datos del usuario. En una plancha 4×4 con piezas 1×1,
una unidad vacía deja 15 celdas; otra con una pieza deja 14 tras colocar otra.
WF elige vacías hasta agotarlas y después desempata/reutiliza. FF/BF llenan la
primera. Se verificaron identidades únicas, determinismo, retazo primero,
separación/margen, suma de áreas y ausencia de consumo. No corresponde
«optimizar» WF cambiando esta regla dentro del PR.

## D. Métricas, máscaras y representación 2D/3D

`domain/metrics.py:calculate_metrics` y R4/PLAN First Fit §§8/10 definen:

```text
material = suma área nominal de las fuentes físicas UTILIZADAS, una vez por unidad
piezas = suma área nominal de cada unidad COLOCADA
recuperable = suma de un rectángulo libre máximo admisible por fuente utilizada
merma = material − piezas − recuperable
aprovechamiento = ROUND_HALF_UP(100 × piezas / material, 3 decimales)
planchas nuevas = número de unidades físicas PLANCHA utilizadas
retazos usados = número de unidades físicas RETAZO utilizadas
```

El recuperable no es toda celda libre ni toda región conectada: se conserva un
rectángulo máximo por fuente, sujeto a mínimos. Desempata por área DESC,
fila ASC, columna ASC, ancho DESC, alto DESC. No se añaden retazos al stock al
simular. Tras confirmar se refleja lo realmente registrable según el contrato
vigente; la regresión `test_unpersistable_residual_is_not_shown_as_reusable_after_confirmation`
comprueba ese caso. Si no se coloca ninguna unidad no hay denominador: métricas
`None`, no porcentaje artificial. Cantidad colocada + faltante = cantidad expandida.

Se añadió un oráculo **de pruebas**, no un segundo motor productivo:

- áreas analíticas independientes para rectángulos, círculos y polígonos;
- transformación rígida por sin/cos contrastada con contorno y dimensiones,
  tolerancia del contrato de coordenadas, y ángulos múltiplos de 5°;
- comprobación de bits traducidos dentro de la máscara erosionada del material,
  sin colisión con otras piezas ni sus separaciones; coordenadas en la grilla;
- recuperable independiente por intersección exhaustiva de intervalos de filas
  comprimidas, en vez del algoritmo histograma productivo;
- sumas Decimal, balance de áreas, unidades físicas, porcentajes y no colocadas.

Se reutiliza deliberadamente la rasterización canónica TA-005/006: no se duplica.
Por tanto esta auditoría valida los invariantes del contrato **raster**, no
certifica tolerancias de fabricación, kerf real, ni sustituye las pruebas propias
del rasterizador o una validación industrial continua del contorno.

Tiempo: `calculation_worker` mide preparación, búsqueda y métricas con reloj
monótono, descontando envío IPC/eventos. No incluye persistencia, red ni
renderizado; `elapsed_ms_including_ipc_and_cleanup` es otra magnitud del runner.
Se conserva el valor por ejecución; no es criterio de desempate geométrico.

Los cuatro E2E nuevos (B y mixto, desktop/móvil) solicitan resultados reales por
GET y recorren **cada fuente usada de cada motor**. Contrastan `viewBox`, número
de piezas, x/y y ancho/alto/radio/vértices del SVG 2D. En 3D contrastan cada vértice
proyectado con una fórmula de cámara superior independiente, incluyendo los 96
segmentos de display del círculo. No calculan empaquetado en el frontend ni
interceptan el POST/GET con datos fabricados. El E2E existente de rotación
comprueba además que el contorno no se gira dos veces.

[Capturas](screenshots/) proceden de Chromium y datos sintéticos del backend.
Son apoyo visual; la prueba numérica y la comprobación de máscaras son la
evidencia de exactitud. La profundidad 3D es ilustrativa; XY conserva la
colocación. No se certificó toda cámara/perspectiva posible.

Se confirma la mejora pendiente de formato: `40000.000000` mm² es un valor
interno correcto pero excesivo para display; en móvil puede invadir su tarjeta.
Proponer formateo por magnitud/plural sin redondear ni modificar el contrato
interno. Se conserva como UI/UX fuera de esta auditoría algorítmica.

## E. Regresiones: persistencia, autorización, supervisión y confirmación

| Riesgo / criterio | Prueba vigente ejecutada y evidencia | Resultado |
|---|---|---|
| Tres persistencias/GET; simulación intacta | `test_final_multimethod_audit.py` (10 entradas), `test_real_comparison_preserves_entire_inventory_and_returns_three_owned_results` | Tres IDs/métodos, snapshots equivalentes, inventario completo idéntico, workers detenidos. |
| Fallo de persistencia parcial | `test_comparison_calculation.py` y E2E «FF falla al persistir…» con trigger de fallo sintético PostgreSQL | FF fallido, BF/WF conservados; BF confirmable una sola vez. El traceback sintético es esperado. |
| Pool/RBAC | `test_comparison_connection_lifecycle.py`, pools 1/5 y lectores concurrentes; suites auth/RBAC completas | Sin agotamiento bajo carga admitida; checkout devuelto antes del repositorio/UoW; decisiones 401/403 conservadas. |
| FF preexistente | `test_legacy_ff_and_comparison_ff_persist_identical_placements_on_the_same_sixteen_piece_input`, E2E `s1-optimization-ui` | Colocaciones iguales al FF legado; confirmación original y vistas conservadas. |
| Memoria individual/acumulada, tiempos, IPC | `test_comparison_runner.py`: motores reales, worker que excede asignación, startup detenido, deadline global, deadline por motor, aborto RSS acumulado, cierre del consumidor | Rechazos y limpieza efectivos. Los límites pequeños de ciertos tests son **más estrictos**, no ampliaciones productivas. |
| Sobrecarga y admisión | `test_busy_comparison_has_no_accepted_work_and_runs_after_capacity_is_released`, preflight RAM, exclusión FF/comparador | Rechazo antes de aceptar; cupo liberado y nueva solicitud posible. |
| Configuración angular | API de publicación en clúster efímero y pruebas `sprint2_angles`; A–F | Snapshot 5° común; versión histórica no sobreescrita; ninguna publicación remota en esta auditoría. |
| Reinicio y recuperación | `test_runtime_restart_expires_visual_buffers_but_preserves_all_three_results` y reconciliación de supervisor | GET durable conservado; recursos visuales temporales pueden responder 410. |
| Selección/confirmación | `test_comparison_confirmation.py`, API HTTP y E2E de confirmación | Elegir no consume. Confirmar bloquea/revalida stock y pedidos, aplica todo en una transacción; rollback de fallo, carreras y doble envío cubiertos. |
| UX posterior a confirmar | `ComparisonLifecycle.test.jsx`, comparación E2E desktop/móvil | Éxito visible, selección/resultados/recovery limpios, selector actualizado; historia por ID; respuestas tardías no restauran trabajo. Fallo conserva contexto. |
| Dashboard/inventario/usuarios | Suites backend completas, 526 componentes y E2E por roles | Guardas, fuentes, navegación y lecturas pasan; no se rediseñan esos módulos. |

Se conservan `RLIMIT_AS=256 MiB` por worker, RSS supervisor 240 MiB,
RSS acumulado 1024 MiB con reserva 16 MiB, startup 30 s, cálculo 120 s,
global 180 s, colas/paquetes/retención acotadas. No se cambiaron valores.
RSS es un umbral **muestreado**, no un límite duro de kernel; RLIMIT_AS limita
espacio virtual. El reporte conserva picos y separación máxima entre muestras.
Linux/WSL2/procfs/prctl siguen siendo requisitos. No hay fallback ilimitado.
La admisión es local al proceso: mantener **un proceso web**, sin escalar workers
independientes contra la misma base como si compartieran admisión.

Los `GET /api/orders` tienen causas finitas: Dashboard consulta tres estados;
Pedidos pagina; pendientes pagina hasta 100 por página y se refresca **15 s
después de terminar** la lectura anterior. El mecanismo busy/generation/abort
evita solapamiento y respuestas obsoletas; confirmar fuerza una actualización.
Cambiar pestaña no inicia otro cálculo ni un bucle de pedidos. Las pruebas del
source y las cuentas por rol del Dashboard pasan. React StrictMode en desarrollo
puede iniciar/cancelar el montaje inicial dos veces; los logs por sí solos no
prueban un ciclo. Este polling es una decisión vigente, no una nueva optimización.

## F. Pruebas y reproducibilidad

Los comandos reales, estados por caso, categorías y hashes del JUnit están en
[backend-results.json](backend-results.json). El inventario de colección actual
y las tres revisiones está en `collection-*.json`. El resultado E2E definitivo
se registra en `e2e-results.json`; los comandos de frontend y advertencias se
registran en `validation-summary.json`.

| Grupo ejecutado | Recopiladas | PASS | FAIL | SKIP |
|---|---:|---:|---:|---:|
| Backend general: unitarias | 1223 | 1223 | 0 | 0 |
| Backend general: integración | 489 | 489 | 0 | 0 |
| Backend general: API | 622 | 622 | 0 | 0 |
| Backend general: invariantes/optimización | 137 | 137 | 0 | 0 |
| Supervisor, proceso pytest separado | 14 | 14 | 0 | 0 |
| **Backend total** | **2485** | **2485** | **0** | **0** |
| Frontend unitarias Node | 175 | 175 | 0 | 0 |
| Frontend componentes Vitest (50 archivos) | 526 | 526 | 0 | 0 |
| E2E del repositorio (dos proyectos) | 126 | 126 | 0 | 0 |
| Recorrido UI adicional de evidencia previa (dos proyectos) | 2 | 2 | 0 | 0 |

La suite general tardó 303.05 s y el supervisor 3.71 s. E2E completo:
383.44 s, 0 flaky, 0 retries. Incluye cuatro pruebas nuevas de políticas/2D/3D.
Estas cuatro también pasaron focalizadas (34.3 s); los diez experimentos y
cinco diagnósticos pasaron focalizados (14.97 s y 5.75 s). Son subconjuntos o
repeticiones; **no se suman de nuevo** a los totales. Lint, build y
`git diff --check`: PASS. No se calculó porcentaje de cobertura de líneas.

El runner local completo también encontró `ui-audit.spec.js`, copiado durante
la auditoría anterior para generar evidencia; esas dos ejecuciones adicionales
no se atribuyen a la colección CI del repositorio. El reporter estaba configurado,
pero no estaba activa la variable CI/gate en ese proceso local. Se aplicó después
la función productiva `evaluateE2EGate` a **todos los resultados reales** del JSON:
PASS, sin omisiones, 13 specs críticos exitosos en ambos proyectos. No se presenta
esa comprobación posterior como un gate que hubiera estado activo durante el
proceso. En CI la variable `CI=true` sí lo activa.

### Comandos

En el backend Linux, con dependencias instaladas y PostgreSQL de pruebas:

```bash
export PYTHON_DOTENV_DISABLED=1 NEWGLASS_REQUIRE_POSTGRES=1
export NEWGLASS_TEST_PG_BIN=/usr/lib/postgresql/18/bin
unset DATABASE_URL SECRET_KEY
.venv/wsl/bin/python -m pytest tests --ignore=tests/unit/optimization/test_comparison_runner.py -q -ra --tb=short --junitxml=.venv/final-backend-general.xml -o junit_family=legacy
.venv/wsl/bin/python -m pytest tests/unit/optimization/test_comparison_runner.py -q -ra --tb=short --junitxml=.venv/final-supervisor.xml -o junit_family=legacy
```

Para repetir solo los experimentos y capacidad:

```bash
.venv/wsl/bin/python -m pytest tests/api/optimization/test_final_multimethod_audit.py -q -ra --junitxml=.venv/final-differential.xml -o junit_family=legacy
.venv/wsl/bin/python -m pytest tests/api/optimization/test_final_capacity_diagnostic.py -q -ra --junitxml=.venv/final-capacity.xml -o junit_family=legacy
```

Las fixtures inician su propio PostgreSQL y nunca leen `.env` con esas variables.
Se usó una copia de archivos con los mismos hashes en filesystem Linux para
evitar la penalización I/O de `/mnt/c`; no se creó ni cambió otra rama.

Desde `frontend/` de Windows:

```powershell
npm.cmd run test:unit
npm.cmd run test:component -- --maxWorkers=2
npm.cmd run lint
npm.cmd run build
```

Desde un frontend con dependencias **Linux** y Python 3.11 en PATH:

```bash
export PATH="$(realpath ../backend/.venv/wsl/bin):$PATH"
export PYTHON_DOTENV_DISABLED=1 NEWGLASS_REQUIRE_POSTGRES=1 PLAYWRIGHT_CHANNEL=chromium
export NEWGLASS_TEST_PG_BIN=/usr/lib/postgresql/18/bin
unset DATABASE_URL SECRET_KEY
npx playwright test tests/e2e/optimization-policy-audit.spec.js
export NEWGLASS_E2E_GATE=1
npx playwright test
```

En esta máquina el comando completo empleó una configuración local efímera
que conserva los proyectos y el gate original, cambia Vite a **5187** y mantiene
FastAPI de pruebas en **8017**, ambos con `reuseExistingServer:false`. No tocó los
servidores del usuario en 5173/8000. El archivo de configuración y las rutas
exactas del comando quedan en `validation-summary.json`. La prueba focalizada
usa solo el spec nuevo y no activa el gate de colección completa.

### Colección histórica, sin inferir cobertura por la suma

| Referencia archivada con `git archive` | Recopiladas | Node IDs ausentes hoy |
|---|---:|---:|
| `4e35bc8c34536284b1c9303a80fc7e69af538ac3` (evidencia PR64 de 2068) | 2068 | 1 renombrado |
| integración `afd5f85` | 2364 | 1 renombrado |
| HEAD `5e836cd` | 2453 | 1 renombrado |
| working tree auditado | 2485 | — |

El único node ID ausente es
`tests/unit/shared/test_config.py::test_engine_defaults_only_enable_pre_ping`.
Su reemplazo es
`test_postgres_pool_defaults_keep_base_capacity_without_overflow`: conserva
`pool_pre_ping`, añade pool 5/overflow 0 y comprueba el modo sin pool. El diff
es explícito; no es cobertura eliminada para ocultar un fallo. Los otros **2067**
node IDs históricos siguen presentes. Frente a HEAD hay 33 IDs nuevos y ese
reemplazo: incremento neto 32 (17 de correcciones previas y 15 de esta auditoría).
El resultado 2470 previo no se utilizó para inferir continuidad histórica.

CI ejecuta los **dos grupos backend**. No se relajan límites: el segundo proceso
evita que el RSS acumulado de la colección general de pytest se confunda con el
del supervisor real. `test_ci_contract` exige ambos comandos. La prueba real del
supervisor sigue ejecutándose; el 503 Windows y la falta de RAM también tienen
pruebas con mocks **solo para esos rechazos**, claramente distintas de los
workers reales que prueban spawn, presupuesto, aislamiento y limpieza.

Durante el desarrollo del oráculo hubo dos intentos rojos: una igualdad textual
de hash no toleraba escalas Decimal normalizadas por PostgreSQL, y una primera
versión del verificador comparaba una fila con la dilatación de otra fila de la
misma pieza. Se corrigieron **las pruebas**, contrastando semántica de entrada y
hash real de workers, y validando la máscara completa antes de añadir su bloqueo.
No eran defectos del motor; no se cambiaron políticas para obtener verde.

## G. Git, archivos y alcance del PR

[initial-state.json](initial-state.json) conserva status/hash inicial de los 96
archivos que ya estaban pendientes (21 modificados y 75 nuevos). Los 13 hashes
productivos del cierre anterior coincidían al iniciar esta auditoría. El
[manifiesto Git](git-review.json) registra clasificación por archivo, hashes,
procedencia y comprobación de conservación. No se sobrescribió ninguno de esos
96 archivos. Los scripts privados, clústeres, cachés, XML brutos y datos remotos
permanecen bajo `.venv`/caché, ignorados.

| Clasificación | Archivos / finalidad |
|---|---|
| Imprescindibles del PR ya en la rama | Comparador aplicación/infraestructura/API, migración `s2cmp01a1b2c`, metadatos de ejecución, observación `ordering_ready`, API/controller/workspace React y cableado. Integración ya contiene las heurísticas; no se vuelven a implementar. |
| Correcciones pendientes imprescindibles | `dependencies.py`, `run_auth.py`, pool acotado en config, correlación del fallo de persistencia, diagnóstico Linux/WSL2 y `dev_server.py`, controller/source/workspace posterior a confirmar. Se justifican por persistencia FF y estabilidad del flujo, con regresiones aisladas. |
| Pruebas/CI necesarias | Tests de conexión/persistencia, supervisor, configuración, launcher, API y componentes; dos grupos en `ci.yml`; comparación E2E; ajustes de expectativa Dashboard; registro del nuevo spec crítico. |
| Añadido por esta auditoría | `final_audit_cases.py`, `final_audit_support.py`, `test_final_multimethod_audit.py`, `test_final_capacity_diagnostic.py`, `optimization-policy-audit.spec.js`, entrada en `criticalSpecs.js` y este paquete de evidencia. **Cero cambios productivos nuevos**. |
| Documentación | SPEC/PLAN y contratos comparativos ya comprometidos; README backend/testing, guía WSL2 y evidencias 503/409/persistencia/UX/final. Las referencias históricas se conservan y no se presentan como pruebas recién ejecutadas. |
| Temporales excluidos | `.venv`, `.env`, logs privados, snapshots de Supabase, clústeres/SQL, paquetes Node, configs/cache de ejecución local, builds y reportes brutos privados. No incluir mediante `git add -f`. |
| Mejoras posteriores | Accesibilidad/normalización UI, formato de métricas, capacidad de piezas/stock grandes, admisión distribuida y durabilidad de animaciones. No se amplía a M4/M5/M6. |

Las modificaciones de migraciones de **pruebas** actualizan el head/conteo por la
nueva revisión comparativa (13→14); no suprimen pruebas ni reescriben migraciones
históricas. La corrección `minmax(0,1fr)` del editor de piezas está limitada al
reflow móvil del recorrido real que inicia el comparador. No es un rediseño de
Pedidos. El guard RBAC compartido evita retención también en Inventario/Dashboard;
la ampliación está justificada por la misma causa de saturación, no por una nueva
funcionalidad de esos módulos.

El escaneo de patrones de secretos y lectura de nuevos textos/JSON solo señala
URLs **ficticias** de localhost en pruebas de configuración. No hay `.venv`, `.env`,
credenciales ni bases temporales entre los archivos propuestos. Los PNG nuevos
son capturas de datos sintéticos. La revisión no constituye certificación de
ausencia de todo secreto posible. Antes del commit futuro, revisar el staging
con el manifiesto; esta auditoría no prepara ni confirma un staging automático.

Trazabilidad de regresiones:

| PBI/SPEC/criterio | Caso | Resultado/evidencia | Relación con PR |
|---|---|---|---|
| SP-002 CA-02–05; TA-018; TA-019 RN-02–08; TA-020 CA-01–06 | A–F, WF-15/16, trazas y pruebas existentes de desempate | `differential-results.json`, `CASE-RESULTS.md`, backend resultados | Verificar políticas integradas; sin cambio algorítmico. |
| OPT-MULTIMOTOR-VISUAL: resultados independientes/GET/aislamiento | Fallo real de guardado FF; pools 1/5 y lectores | `test_comparison_connection_lifecycle.py`, suite de cálculo/API, evidencia previa F-01/F-03 | Mantener corrección persistencia/RBAC. |
| OPT-MULTIMOTOR-VISUAL: observación y selección manual | Contraste API↔DOM/2D/3D B/mixto | Spec E2E nuevo, screenshots y reporte de gate | Evitar etiqueta BF sobre resultado FF. |
| Confirmación transaccional y flujo explícito | Doble envío/carreras/rollback, éxito limpio/contexto de error | Suites confirmación, ComparisonLifecycle y E2E comparación | Mantener corrección F-02, sin tocar transacción. |
| TA-037 admisión y límites; diagnóstico de capacidad solicitado | Cinco escenarios acotados | `capacity-diagnostic.json` | Caracterizar pendiente, no incrementar capacidad en este PR. |
| Plataforma/recursos OPT-MULTIMOTOR-VISUAL | Spawn real, RAM/deadlines/cierre; Windows rechazado | 14 pruebas runner, guía WSL2 | No presentar mocks como supervisión real. |

No existe PR nuevo: la última columna es trazabilidad para el PR **por crear**,
no una afirmación de revisión/aprobación externa. Los archivos ya provenientes
de integración se distinguen de los cambios propios mediante el diff contra
`origin/integration/sprint-01` y los manifiestos de colección.

## H. Riesgos y pendientes separados

### Capacidad grande — diagnóstico únicamente

[capacity-diagnostic.json](capacity-diagnostic.json) documenta cinco escenarios,
sin asignar rasters por encima del límite:

| Escenario | HTTP / estado real | Momento y efecto |
|---|---|---|
| Pieza 5×5 frente a stock 4×2, sin orientación factible | 201 → SIN_SOLUCION | No es fallo técnico; motores completos con colocación parcial/vacía. Pedido vuelve pendiente, inventario intacto. |
| Pieza 4001×1 con raster 1 mm | 422 INVALID_INPUT | Rechazo por extensión antes de trabajo/pedidos bloqueados. |
| 51 unidades compatibles en un material | 422 LOAD_LIMIT_EXCEEDED, máximo 50 | Rechazo de admisión antes de expansión/cálculo. |
| Stock compatible 4001×1 **además** de fuente 4×2 válida | 201 → FALLIDA, tres EXECUTION_FAILED | `prepare_run_geometry` valida todas las fuentes antes de buscar. Una fuente fuera del límite invalida todo el snapshot. Ocurre después de aceptar/transicionar pedidos; luego se liberan, sin consumir stock. |
| Doce figuras grandes distintas, estimación raster 853293760 bytes | 422 LOAD_LIMIT_EXCEEDED, máximo 67108864 | Estimador P3 rechaza antes de crear trabajo/asignar máscaras. |

El frontend distingue rechazos TA-037 y conserva selección, pero el cuarto caso
queda con fallo técnico genérico, sin precisar la fuente fuera de capacidad. Es
un pendiente de diagnóstico/admisión; no se afirma que todo rechazo preceda al
bloqueo. Los pedidos se comprobaron PENDIENTE y la admisión en cero al terminar.

Trabajo posterior: decidir con SPEC si filtrar fuentes no utilizables es admisible
y cómo informar exclusiones sin ocultar stock; validar extensión y memoria de
fuentes antes de aceptar; códigos de capacidad accionables; estimar orientación,
fuentes y layouts conjuntamente; medir perfiles antes de proponer representación
por bloques/streaming o ejecución por lotes. Cualquier nueva capacidad exige
presupuestos justificados, invariantes, fallos y limpieza probados. No se debe
subir máximos ni ignorar el stock grande silenciosamente en esta rama.

### Otros pendientes

- WF no garantiza pocas planchas ni óptimo global. BF solo compara fuentes con
  candidato canónico; no es búsqueda exhaustiva de posiciones ni comparación
  entre todos los giros. Son límites del contrato vigente, no algoritmos rotos.
- El [backlog UI/UX](../FF-PERSISTENCE-UX-2026-11-01/UI-UX-AUDIT.md) conserva
  A-01/A-02 (contraste de foco/texto), borradores de pedido, foco de navegación,
  tokens/jerarquía y formato de magnitudes. No se declara certificación WCAG ni
  aprobación humana de esas deudas. Resolver accesibilidad antes de declarar
  conformidad AA; no se rediseñó transversalmente el producto.
- Reiniciar expira animación/máscaras en memoria; resultados/recibos permanecen
  consultables. La ejecución web es de un proceso; despliegue multiproceso exige
  admisión/coordinación compartida previamente diseñada.
- Build advierte un chunk >500 kB; pytest advierte deprecación de TestClient/httpx.
  No fallan los checks ni se cambian dependencias dentro de esta auditoría.
- La verificación no sustituye revisión por otro integrante, CI remoto del futuro
  commit ni pruebas de fabricación. No se simula una aprobación de PR.

## I. Veredicto

**LISTO PARA PR**, con el alcance de comparación multimétodo y cargas admitidas
documentado; todavía requiere la revisión humana y CI del commit futuro antes
de merge. No hay prueba requerida fallida ni un incumplimiento demostrado de las
políticas que justifique cambiar FF/BF/WF. FF/BF son estrategias diferentes;
pueden coincidir legítimamente y se obtuvo un contraejemplo mínimo por API y UI.
Las nueve/diez planchas de WF responden al criterio aprobado que esta auditoría
contrastó con su implementación. Geometría raster, métricas, persistencia,
aislamiento, supervisión y confirmación conservan sus regresiones.

Este veredicto **no declara** resuelta la capacidad de stock fuera del raster,
conformidad WCAG AA, soporte Windows nativo ni despliegue multiproceso. Son los
pendientes expresos de H; no se ocultan con límites mayores, fuentes omitidas,
datos simulados presentados como backend ni pruebas eliminadas. No se hizo
commit ni se creó/publicó un PR.

Para comprobar localmente sin consumir inventario: seguir
[la guía WSL2](../../../../development/optimization-wsl2.md), iniciar FastAPI con
`.venv/wsl/bin/python -m scripts.dev_server` y Vite con `VITE_API_URL` apuntando
a `http://127.0.0.1:8000`. Seleccionar pedidos pequeños y comparar: comprobar
201, `comparison-v1`, tres IDs propios y sus GET; consultar las pestañas.
Confirmar es una operación distinta y solo se probó sobre PostgreSQL aislado.
