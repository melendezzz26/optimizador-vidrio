# HU-015-T1 — Implementación backend y contratos

Base auditada: `e98c646`, rama `feature/HU-015-interfaz-rasterizacion`; implementación sin commit. Autor: Fabricio Melendez. SPEC permanece **Reviewed** y PLAN **Approved**; esta evidencia no marca HU-015 completa ni Verified. La preparación del staging se registra al final de la auditoría.

## Base y arquitectura

`git fetch origin --prune` se completó tras repetir fuera de la restricción de red del sandbox. HEAD inicial `e98c646b2dafeb4a3efaff96a2ff157122f7ebdb`; `origin/integration/sprint-01` sigue `728c1dd9020f6c562419620bbcaa1c1ca0545757`. `HEAD..origin/integration/sprint-01` vacío; la rama solo añade los tres commits documentales HU-015. No merge/rebase.

No existe `backend/tests/orders/`; las pruebas reales de Orders están en `tests/unit/modules/orders`, `tests/api/orders` y `tests/integration/modules/orders`. Se revisaron esos contratos/fixtures, el dominio raster, modelos/checks, autenticación/permisos y las dependencias reales. No hay framework UnitOfWork ni lint/format backend configurados en CI; los controles son pytest, pruebas de capas/import lazy y revisión de diff.

Optimization/Application usa su puerto `OptimizationOrders`; Infrastructure compone el contrato público `OrderOptimizationPort` y el validador de piezas persistidas de Orders. No accede a ORM/SQL de Pedido/Pieza directamente ni duplica entidades. La composición concreta se realiza en dependencies reutilizando el repositorio y la sesión de petición existentes. Domain raster/placement quedan intactos.

### Decisión real de concurrencia

Se eligió **compare-and-set (CAS)**, dentro de Orders:

```sql
UPDATE pedidos SET estado = 'EN_OPTIMIZACION'
WHERE id_pedido = :id_pedido AND estado = 'PENDIENTE'
RETURNING id_pedido;
```

Una fila devuelta identifica el único candidato al éxito; cero filas se traduce a ausencia (`404`) o conflicto (`409`). La actualización obtiene el bloqueo de escritura de cabecera, compatible con los bloqueos de update/cancel actuales. Después del CAS tentativo se releen las piezas con populate_existing y se validan en la misma transacción, **antes del commit**. Esto evita validar una versión anterior a una edición concurrente. Un error de precondición/commit revierte el estado tentativo; ninguna otra petición observa un inicio válido sin commit. No se agrega SELECT FOR UPDATE ni un protocolo de locking propio a start.

La unidad de trabajo conceptual del PLAN se concreta en un método atómico del repositorio de Orders que acepta un callback de validación puro, y administra commit/rollback como sus otras mutaciones. Se evita crear un framework UoW/contexto separado sin consumidores adicionales. El callback recibe solo dicts, no sesión/SQL, no escribe ni rasteriza. La sesión de autenticación puede tener autobegin; se adopta la misma sesión sin Session.begin anidado. Domain/Application no conocen el mecanismo SQL.

Pruebas PostgreSQL reales coordinan dos requests HTTP y mantienen al ganador en validación hasta observar en `pg_stat_activity` que el otro espera un bloqueo. Al liberar: exactamente `200`/`409`, estado final EN_OPTIMIZACION desde otra sesión, una pieza/cantidad conservadas y cero registros Optimization/ejecución/inventario. También se prueban ambos órdenes de carrera con update/cancel y rollback por validación/commit. Los parches solo coordinan los hilos; las operaciones de BD y HTTP no se simulan.

## Contratos efectivos

| Operación | Request | Éxito / reglas |
|---|---|---|
| POST /api/optimization/start | `{"id_pedido":10}` | `200 {"id_pedido":10,"estado":"EN_OPTIMIZACION"}` tras commit efectivo; PENDIENTE y todas sus piezas válidas; no rasteriza. |
| POST /api/optimization/rasterize | `{"id_pedido":10,"id_pieza":25,"resolution_mm":5.0}` | `200` con pieza/geometría efectiva, material/espesor, cantidad, resolución, filas/columnas/celdas y spans_by_row. Solo EN_OPTIMIZACION; cero escrituras. |

Ambos: permiso vigente EJECUTAR_OPTIMIZACION (Administrador/Operario); `401` sesión ausente/no válida, `403` rol no autorizado, `404` pedido/pieza ausente o pieza ajena (sin revelar geometría), `409` estado incorrecto, `422` schema/geometría/presupuesto, `500` general sin SQL/stack trace. Segundo start devuelve 409. Inputs estrictos, campos extra prohibidos, resolución finita positiva y IDs positivos. Valores no finitos en JSON producen 422 serializable, sin devolver el input inválido.

Respuesta raster incluye geometría canónica: rectángulo width_mm/height_mm, círculo radius_mm y polígono vertices_mm. Los enteros persistidos se conservan sin coerción a float; espesor Decimal mantiene serialización decimal de Orders. Tramos de row_runs `[inicio, fin_exclusivo)`, todas las filas consecutivas, fila vacía con runs vacío y sin matriz booleana ni filas como enteros JS. Una PIEZA con cantidad 5 llama al dominio una vez y devuelve una máscara con cantidad 5; no quintuplica filas/spans.

Presupuesto y mediciones: [benchmark-limite.md](benchmark-limite.md). No se crea migración: models.py y migración R1 ya admiten EN_OPTIMIZACION; geometría/cantidad/material existen. No se crea Optimizacion, EjecucionOptimizacion, métrica, preview, movimiento, reserva/consumo de stock o resultado heurístico. No se altera frontend ni NewGlass-Notion.

## Verificación ejecutada

Desde raíz, con Python del entorno backend (fuera del sandbox porque el alias Windows Store no podía iniciar dentro):

```powershell
& .\backend\venv\Scripts\python.exe -m pytest -q backend/tests/unit/optimization backend/tests/api/optimization backend/tests/integration/optimization
```

Corrida focalizada de implementación, anterior a la auditoría final: **93 passed, 1 warning en 34.18 s**, sin skips. Incluye pruebas unitarias de orquestación/preflight/serialización/capas, API con PostgreSQL temporal y siete pruebas de integración/concurrencia. La advertencia es StarletteDeprecationWarning de TestClient/httpx vigente, sin añadir/cambiar dependencias para ocultarla.

Regresión focalizada previa (antes de las últimas comprobaciones adicionales de schema/error/espera real):

```powershell
& .\backend\venv\Scripts\python.exe -m pytest -q backend/tests/unit/optimization backend/tests/api/optimization backend/tests/integration/optimization backend/tests/optimization backend/tests/unit/modules/orders backend/tests/api/orders backend/tests/integration/modules/orders backend/tests/api/test_require_permission.py backend/tests/api/test_auth_api.py
```

**428 passed, 1 warning en 69.35 s**, sin skips. No se presenta como ejecución de pruebas añadidas después de esa corrida.

Regresión completa desde `backend/`:

```powershell
& .\venv\Scripts\python.exe -m pytest tests -q -ra
```

**1564 passed, 1 warning en 296.19 s**, sin skips. Esta corrida había iniciado antes de la última guarda y caso adicional para geometría persistida con un campo extra de tipo inválido; ese ajuste puntual se comprobó después en la corrida focalizada final de 93 casos, sin repetir toda la suite. No se atribuye ese caso nuevo a la cifra 1564. La suite completa incluye regresión geométrica, Orders, autenticación, import lazy, arquitectura, persistencia y migraciones existentes con bases aisladas; no se creó ni aplicó una migración nueva de HU-015.

### Hallazgos y correcciones reales

- Python del venv no podía iniciar dentro del sandbox (alias Windows Store); funcionó con Python 3.11.9 al ejecutar el mismo entorno fuera de esa restricción. No se sustituyó ni instaló un Python nuevo.
- La primera ampliación de regresión falló en colección por colisión entre módulos test_use_cases de Orders/Optimization. Se agregaron `__init__.py` a los nuevos paquetes de pruebas; las corridas posteriores recogen ambos módulos.
- Un test inicial de redondeo reveló un comportamiento **preexistente** del dominio: radio `10.0000002` y resolución 5 puede dar diámetro redondeado 20, mientras un span ocupa columna 5 y el dominio levanta RasterizationError. No se cambia TA-005/006 en T1. El test de estimación usa un caso aceptado por ese dominio, y un caso API explícito conserva el hallazgo: devuelve `422` seguro y deja el pedido EN_OPTIMIZACION. **Limitación pendiente de seguimiento geométrico**, no una corrección del rasterizador ni un éxito fabricado.
- La revisión del DTO detectó que un schema float podía redondear coordenadas enteras persistidas grandes. Se corrigió el schema para preservar int/float originales y se añadió prueba con origen 9007199254740993; la cota de payload también contempla esos enteros. Se volvió a ejecutar el benchmark con el schema final.

## Auditoría final previa a commit

Durante la auditoría se revisaron los cuatro diffs versionados y los 24 archivos entonces untracked, sin staging/commit/push y sin modificar frontend, dominio raster, SPEC, modelos, migraciones o NewGlass-Notion. HEAD sigue e98c646 y la rama es feature/HU-015-interfaz-rasterizacion. El PLAN se restauró posteriormente durante la preparación de commit, como se registra más abajo.

**Veredicto técnico: sin BLOQUEANTES de implementación detectados; hallazgos MENOR de política de recursos y de concreción del diseño.** Esta auditoría no convierte las guardas técnicas en reglas de dominio ni aprueba sus valores como requisitos funcionales nuevos.

### Matriz de hallazgos

| Área | Estado | Hallazgo | Acción |
|---|---|---|---|
| PLAN modificado durante la auditoría | MENOR | Había 11 líneas añadidas sobre el texto aprobado. En preparación del commit se restauró únicamente el PLAN a e98c646; la concreción del UoW como método atómico de Orders con callback permanece en esta evidencia. | Mantener visible esta concreción; cualquier futura actualización del PLAN requiere revisión correspondiente. |
| MAX_RASTER_CELLS | OK | Corte técnico de 1.000.000 informado por mediciones; no frontera universal de seguridad ni SLA. | Conservar el millón. |
| 2440/eje | MENOR | Celdas por eje, no milímetros. No hay regla previa de dominio que lo imponga; es el extremo medido, sin evidencia de que 2441 sea inseguro. | Discutir/ratificar el valor técnico; no modificarlo automáticamente. |
| 128 vértices | MENOR | La complejidad cuadrática justifica una guarda; el número exacto no procede de una regla de NewGlass. | Discutir/ratificar el valor y sus rechazos de geometría válida. |
| 256 KiB | MENOR | Cota previa, no medición del JSON final. Puede rechazar un resultado real menor que 256 KiB. | Revisar conservadurismo y redundancia con los otros límites; sin cambio automático. |
| CAS/transacción | OK | UPDATE condicional/RETURNING dentro de Orders, con un solo ganador confirmado. | Conservar. |
| Rollback | OK | Vacío/corrupción/presupuesto/fallo del callback o commit dejan PENDIENTE; probado en PostgreSQL aislado. | Cobertura real existente suficiente. |
| Start | OK | Contrato mínimo 200/401/403/404/409/422; sin raster ni escrituras excluidas. | Conservar. |
| Rasterize | OK | Solo EN_OPTIMIZACION, lectura persistida y pertenencia, sin escrituras. | Conservar. |
| Spans | OK | row_runs [inicio, fin_exclusivo), filas completas y suma igual a occupied_cells; cobertura >53 bits y fila vacía. | No duplicar test equivalente. |
| Cantidad >1 | OK | Una llamada al rasterizador, una máscara y cantidad 5 en DTO. | Conservar. |
| Benchmark | OK | 10 casos × 5 resoluciones = 50 combinaciones; 5 muestras = 250 muestras cronometradas. | Mantener separadas combinaciones/muestras y limitaciones de memoria/latencia. |
| Radio 10.0000002 | MENOR | Defecto preexistente del dominio, activable por una pieza válida; HU-015 no lo introduce ni empeora. | Deuda geométrica separada; test de seguridad sin congelar el error como requisito. |
| Untracked | OK | 24 archivos esperados; mayor archivo, resultados JSON de 94.415 bytes. | Versionables por alcance; excluir cachés/salidas ignoradas. |
| Secretos | OK | No se detectaron credenciales/JWT/URLs privadas en nuevos/modificados. | Conservar fixtures locales con secretos generados en ejecución. |

### Presupuesto, respaldo y contraejemplos

Todos los límites se definen en backend/app/modules/optimization/application/resource_policy.py, líneas 86–89. Se clasifican como **POLÍTICAS TÉCNICAS DE PROTECCIÓN**, no límites funcionales del negocio, dimensiones máximas de una pieza NewGlass ni restricciones de Orders. Son guardas de Application, no reglas añadidas a GeometryValidator ni al dominio raster. El PLAN §6.2 permite presupuestos complementarios sustentados; esa autorización no deduce matemáticamente sus valores exactos. Los valores podrán ajustarse después de revisión técnica sin cambiar la semántica base de rasterización.

| Límite | Naturaleza y respaldo | ¿Rechaza geometría válida? | Necesidad además de un millón de celdas |
|---|---|---|---|
| 2440 por eje | Técnico/defensivo. Benchmark de tiras y costo de filas/recorrido de bits. Sin máximo funcional previo equivalente. | Sí: rectángulo 2441×1 mm a resolución 1; 2441 celdas, JSON real 285 bytes, validación Orders correcta, presupuesto rechazado. | Un presupuesto por forma/aspecto evita extremos de filas/columnas no acotados bien por el área. El valor exacto 2440 sigue siendo una decisión conservadora, no un umbral de degradación demostrado. |
| 128 vértices | Técnico. Orders permite ≥3 sin ese máximo; benchmark muestra validación ~7,95 ms para 128 frente a ~31,14 para 256 en resolución 1. | Sí: convexo de 129 vértices, bbox 100×100, 10.000 celdas y 7941 bytes, rechazado por cantidad de vértices. | Sí conviene acotar complejidad geométrica: el área de rejilla no limita la validación O(n²). No demuestra que 129 sea inseguro. |
| 262144 bytes | Defensivo, aplicado a estimación superior: 96×filas + 640×vértices + 2048. PLAN exige rechazo previo; benchmark mide hasta 67470 bytes admitidos. | Sí: elipse convexa de 128 vértices, bbox 10×2000, 20.000 celdas, JSON real 61242 bytes; cota 275968, rechazada. | Un millón de celdas por sí solo no limita el overhead de filas/metadata. Con los ejes y vértices ya limitados, esta guarda es parcialmente redundante y la cota actual puede ser excesivamente conservadora. |

Los contraejemplos se comprobaron con el validador de Orders, estimación, rasterizador y serializador actuales, sin una nueva corrida de tiempos/benchmark. Se mantuvieron las tres constantes.

Con ejes ≤2440, geometrías convexas (un run por fila) y ≤128 vértices finitos, una cota más ajustada del JSON compacto sería 2440×34 + 128×640 + 2048 = **166928 bytes**, inferior a 256 KiB. Esto explica por qué el rechazo de la elipse es efecto de una estimación holgada, no prueba de que su JSON real exceda el máximo. No se cambió la fórmula: ajustar su conservadurismo es una decisión para revisión.

Se verificaron todas las filas del resultado guardado: total_cells = row_count×columns, cinco muestras por combinación y medianas correctas. Los cuatro hashes de script/dataset/schema/serializador coinciden con los archivos actuales. Aplicando el presupuesto actual, **43 combinaciones admitidas y 7 rechazadas**: comercial a 2/1 mm y los cinco casos del polígono de 256 vértices. Las demás combinaciones del dataset quedan admitidas.

Peor tiempo total observado entre admitidos: polígono de 128 vértices a 1 mm, mediana de sumas por muestra **96,156 ms**, máximo **99,134 ms**, 35245 bytes y pico Python de 1253036 bytes. Máximo payload entre admitidos: **67470 bytes**; máximo pico Python observado: **2481972 bytes**, ambos en tira alta. No son cotas universales ni memoria RSS.

Comercial a 1 mm: 4465200 celdas, mediana total 352,497 ms, JSON 55889 bytes, pico Python 2540572 bytes. La diferencia de memoria frente a la tira alta admitida es pequeña; el millón no garantiza por sí solo un margen uniforme de memoria. Comercial a 2 mm (1116300 celdas) se rechaza aunque su mediana total ~74,554 ms sea menor que la del peor polígono admitido. El corte es una política conservadora informada por datos, no una frontera de tiempos que el benchmark demuestre obligatoria.

### Preflight y flujo transaccional real

RECTANGULO redondea extensiones a 6 decimales; CIRCUNFERENCIA usa round(2×radio,6); POLIGONO_CONVEXO usa max-min por eje, equivalente a trasladar cada vértice por min y tomar su máximo redondeado. El conteo reproduce max(1,ceil(extensión/resolución - 1e-9)). No se encontró un desacuerdo de dimensiones en los casos auditados, incluidos negativos, traslación, decimales y resolución fraccionaria. Las otras guardas sí pueden rechazar una rejilla menor que un millón, como está explicitado arriba.

Flujo real: router.start_optimization → StartOptimizationUseCase → OptimizationOrders.start_pending → OrdersOptimizationAdapter → OrderOptimizationPort.start_optimization → SQLAlchemyOrderRepository.start_optimization → CAS/lectura/validación/commit o rollback, en la misma sesión de petición. get_order_repository resuelve la implementación en dependencies; no hay ORM/SQL de Orders duplicado en Optimization.

El UPDATE obtiene el bloqueo antes del callback. La transición es tentativa hasta completar validación de piezas y commit. Ante excepción, el repositorio llama rollback y propaga; la API traduce errores seguros. El segundo UPDATE concurrente espera y vuelve a comprobar PENDIENTE; tras commit del ganador devuelve cero filas, se verifica existencia y se responde 409. Si el primero revierte, no dejó una transición confirmada. Pruebas reales existentes cubren estado PENDIENTE tras validación fallida y fallo de commit.

### Correcciones auditadas y cambios de esta auditoría

| Problema | Causa | Corrección | Regresión |
|---|---|---|---|
| Colisión de nombres | test_use_cases de directorios no empaquetados se importaban como el mismo módulo. | __init__.py en nuevos paquetes Optimization. | Colección conjunta Orders/Optimization y corrida completa previa; checks de capas actuales. |
| Coordenadas enteras | Campos float del schema convertían enteros >2^53. | Uniones estrictas int/float en geometría de respuesta. | test_response_preserves_persisted_integer_vertices_without_float_coercion con 9007199254740993. |
| Campo corrupto | Se hacía len sobre vertices_mm extra escalar antes de rechazar formato canónico. | Cota de vértices solo para POLIGONO_CONVEXO; Orders rechaza formato inválido. | test_corrupt_geometry_after_start_is_safe_422, variante vertices_mm=42. |

En esta auditoría **no se cambió producción ni constantes**. Se añadieron cuatro parámetros al test de congruencia preflight/dominio: dos bordes de redondeo de rectángulo a 0,7, círculo a 0,7 y polígono trasladado a 0,35. Era un hueco real: las entradas anteriores solo usaban resoluciones enteras.

Se corrigió test_existing_fractional_circle_rounding_error_is_safe, renombrado test_fractional_circle_has_safe_result_without_changing_state: permite resultado correcto 200 o error de dominio 422 seguro, sin cambio de estado. Ya no obliga a conservar un defecto como requisito HU-015. El origen del defecto está en rasterize_circle existente: diámetro redondeado a 20 con centro/radio no redondeados; un span termina en columna 5 cuando solo hay 4 columnas. El dominio coincide con HEAD e98c646; una pieza creada válidamente con ese radio puede activarlo. No se modifica el rasterizador.

Pruebas finales de auditoría, desde backend/:

~~~powershell
& .\venv\Scripts\python.exe -m pytest -q tests/unit/optimization tests/api/optimization tests/integration/optimization tests/unit/modules/orders/test_layer_dependencies.py tests/api/inventory/test_lazy_db_import.py
~~~

**100 passed, 1 warning en 46.12 s; sin skips**: 97 HU-015 + 2 checks de capas Orders + 1 import lazy. Primera llamada desde raíz: 99 passed y un fallo de import lazy por ModuleNotFoundError de main; se corrigió el directorio de ejecución, sin modificar ese test existente ni producción. Se reutiliza la regresión completa histórica de 1564, con su alcance temporal ya registrado, sin afirmar que se repitió ahora. No se ejecutó de nuevo el benchmark.

### Inventario individual de los 24 archivos nuevos

Estos archivos estaban untracked al auditar; forman parte del staging explícito de la preparación posterior.

Código productivo (10):

~~~
backend/app/modules/optimization/application/errors.py
backend/app/modules/optimization/application/ports.py
backend/app/modules/optimization/application/resource_policy.py
backend/app/modules/optimization/application/use_cases.py
backend/app/modules/optimization/infrastructure/orders_adapter.py
backend/app/modules/optimization/presentation/dependencies.py
backend/app/modules/optimization/presentation/router.py
backend/app/modules/optimization/presentation/schemas.py
backend/app/modules/optimization/presentation/serialization.py
backend/app/modules/orders/application/persisted_pieces.py
~~~

Tests y fixtures (9):

~~~
backend/tests/api/optimization/__init__.py
backend/tests/api/optimization/conftest.py
backend/tests/api/optimization/test_optimization_api.py
backend/tests/integration/optimization/__init__.py
backend/tests/integration/optimization/conftest.py
backend/tests/integration/optimization/test_start_concurrency.py
backend/tests/unit/optimization/__init__.py
backend/tests/unit/optimization/test_serialization.py
backend/tests/unit/optimization/test_use_cases.py
~~~

Benchmark (2), resultado seleccionado (1) y evidencia (2):

~~~
experiments/raster/cases/hu015-resources.json
experiments/raster/scripts/hu015_resource_benchmark.py
docs/evidence/sprint-01/HU-015/benchmark-resultados.json
docs/evidence/sprint-01/HU-015/benchmark-limite.md
docs/evidence/sprint-01/HU-015/t1-backend.md
~~~

No aparecen temporales, credenciales, dumps o binarios entre esos 24. Las carpetas __pycache__/ y sus .pyc, .pytest_cache/ y experiments/raster/results/hu015/ son salidas ignoradas, no candidatas al commit. El JSON de 94415 bytes es evidencia técnica seleccionada de 50 combinaciones/250 muestras; no un dump de BD. Se revisaron nuevas/modificadas por patrones de credenciales, JWT y URL privada; los únicos passwords/tokens en tests son fixtures o valores producidos en ejecución sobre PostgreSQL temporal loopback.

### Diff histórico del PLAN observado en la auditoría contra e98c646

El siguiente diff se conserva como evidencia histórica de lo observado durante la auditoría; **ya no es el diff actual del working tree ni del staging**. No había líneas eliminadas ni originales reescritas. Durante preparación del commit se restauró únicamente el PLAN a e98c646. El cambio UoW/contexto → operación atómica del repositorio permanece aquí como concreción/desviación técnica declarada; no cambia endpoints, alcance, estados ni dirección de dependencias, y no se atribuye nueva aprobación humana.

~~~diff
diff --git a/docs/specs/PLAN-HU-015-interfaz-rasterizacion.md b/docs/specs/PLAN-HU-015-interfaz-rasterizacion.md
index fdb948c..32f6690 100644
--- a/docs/specs/PLAN-HU-015-interfaz-rasterizacion.md
+++ b/docs/specs/PLAN-HU-015-interfaz-rasterizacion.md
@@ -408,0 +409,10 @@ Este cierre incorpora únicamente el PLAN mediante un commit documental. No se m
+## Registro técnico de T1 — sin cambio de estado del PLAN/SPEC
+
+Durante la implementación autorizada de T1 se concretaron dos decisiones pendientes, con evidencia en [t1-backend.md](../evidence/sprint-01/HU-015/t1-backend.md) y [benchmark-limite.md](../evidence/sprint-01/HU-015/benchmark-limite.md):
+
+- Se eligió compare-and-set en el repositorio de Orders, sin SELECT FOR UPDATE adicional en start. El UPDATE tentativo obtiene el bloqueo de cabecera; la lectura/validación de piezas ocurre después de adquirirlo y antes del commit, con rollback ante error. Esta secuencia evita lecturas obsoletas frente a edición/cancelación y mantiene una sola transición visible. Optimization usa el puerto y el adaptador por composición, sin SQL/ORM propio de Orders.
+- La unidad de trabajo conceptual se materializa como operación atómica del repositorio existente, con callback puro de validación y commit/rollback internos, en lugar de agregar un framework UoW/contexto separado. Se adopta la sesión de petición existente, sin begin anidado. Esta concreción mínima se registra para revisión de la implementación, sin atribuir una nueva aprobación humana.
+- Benchmark ejecutado en 50 combinaciones con resoluciones 20/10/5/2/1, cinco muestras y memoria en pasada separada. Se fija `MAX_RASTER_CELLS = 1_000_000`, con guardas complementarias de 2440 por eje, 128 vértices y cota previa de 262144 bytes JSON. Los valores se centralizan en Application y se comprueban antes de rasterización/serialización excesiva; la evidencia contiene resultados, justificación y límites de la medición local.
+
+El valor técnico de P-01 queda definido por mediciones reales; P-03 cuenta con mecanismo implementado y pruebas PostgreSQL, pendientes de revisión del cambio. P-02 sigue sin resolución histórica. T2/T3 no se implementan, no hay migración ni frontend modificado. La SPEC permanece Reviewed y este PLAN Approved; no se marcan Implemented/Verified. La implementación T1 está sin commit/staging para revisión.
+
@@ -412,0 +423 @@ Este cierre incorpora únicamente el PLAN mediante un commit documental. No se m
+- 13/10/2026 — **Registro técnico T1, sin cambio de estado**: se documentan CAS atómico a través de Orders, concreción mínima de la unidad de trabajo y presupuesto fijado después del benchmark ejecutado. Se enlaza evidencia de implementación/validación para revisión; no se reescriben las aprobaciones anteriores ni se marca la SPEC Implemented/Verified. Sin commit de la implementación.
~~~

## Preparación del commit — 14/10/2026

Por instrucción expresa, se restauró **únicamente** `docs/specs/PLAN-HU-015-interfaz-rasterizacion.md` al contenido aprobado en `e98c646`. La SPEC Reviewed permanece intacta y el PLAN Approved no forma parte del staging. Las concreciones posteriores de CAS, UoW/repositorio atómico, benchmark y análisis de límites se mantienen en esta evidencia y en [benchmark-limite.md](benchmark-limite.md); el diff anterior se conserva solo como registro histórico. Cualquier actualización futura del PLAN requerirá la revisión correspondiente.

Esta decisión documental no alteró código funcional, pruebas, benchmark ni resultados. Se prepara un staging explícito de 27 archivos: 3 backend ya versionados y 24 nuevos intencionales, sin cachés/temporales. Los límites se conservan como POLÍTICAS TÉCNICAS DE PROTECCIÓN: 2440 celdas/eje puede rechazar geometría válida con pocas celdas; 128 vértices puede rechazar un polígono válido de Orders; la estimación de 256 KiB es conservadora y parcialmente redundante. Su ajuste posterior exige revisión técnica, sin cambiar la semántica base de rasterización.

No se vuelven a ejecutar pruebas ni benchmark en esta preparación. Se conservan los resultados auditados **100 passed, 1 warning, 0 skipped** y la regresión previa **1564 passed, 1 warning**, con la limitación temporal ya documentada. No se realiza commit, push, PR, merge ni captura de pantalla.

## Capturas manuales posteriores

No se generan capturas ahora. Para revisión local, mostrar:

1. StartOptimizationUseCase y validación del callback.
2. RasterizeOrderPieceUseCase, lectura persistida y única llamada al dominio.
3. CAS/rollback del repositorio Orders y prueba que observa bloqueo real.
4. Swagger de POST start, schema mínimo y permiso Bearer.
5. Swagger de POST rasterize y schema de spans/geometría.
6. Pedido PENDIENTE antes de start, respuesta 200 y lectura EN_OPTIMIZACION después.
7. Segundo start 409 para ese pedido.
8. Raster RECTANGULO.
9. Raster CIRCUNFERENCIA.
10. Raster POLIGONO_CONVEXO con vertices_mm persistidos.
11. Respuesta spans_by_row, cantidad 5 y una sola máscara.
12. Runner ejecutado y tabla/JSON de benchmark real.
13. Resolución que supera el límite, respuesta 422 y estado sin cambio.
14. Salida de pruebas unitarias/API.
15. Prueba concurrente PostgreSQL, un ganador/un conflicto y estado final.
16. Git diff cached/status del staging preparado, sin commit.

Usar entorno local con datos sintéticos y no mostrar JWT, Authorization, cookies, contraseñas o cadenas de conexión. Las futuras imágenes manuales podrán ir a NewGlass-Notion según la regla vigente; ningún archivo técnico de esta implementación se guarda allí.
