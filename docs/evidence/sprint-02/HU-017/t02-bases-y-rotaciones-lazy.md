# HU-017 T02 — Bases previas y rotaciones compartidas bajo demanda

## Contexto y alcance

27/10/2026. Base local `2653a4b`, derivada de `4bcf54d` de
`integration/sprint-01`. Misma rama `feature/HU-017-proceso-visual-optimizacion`.
Continuación autorizada por el solicitante, con commits locales; sin push, PR ni
merge. La SPEC conserva sus 26 CA y no se declara HU-017 Verified/cerrada.

- [SPEC, RN-01/RN-03 y CA](../../../specs/SPEC-HU-017-proceso-visual-optimizacion.md).
- [PLAN T02 y DG-01](../../../specs/PLAN-HU-017-proceso-visual-optimizacion.md).
- `51e3dc6`: diseño de la barrera y evolución compatible del componente TA-016.
- `7c7a1cd`: pruebas previas de preparación, precisión, presupuesto y laziness.
- `1291d65`: preparación compartida, rotaciones lazy, checkpoints y regresiones.

## Implementación

`domain/run_geometry.py` incorpora `PreparedRunGeometry`: el problema y su
configuración inmutables, bases de piezas por pedido/pieza, bases de materiales
por identidad física y reglas RN-04 existentes. Todas las geometrías y sus
límites se validan antes de asignar bases; después se preparan las máscaras necesarias,
compartidas por unidades y geometrías idénticas. La barrera se completa dentro
del recorrido común antes de crear layouts o evaluar la primera posición.

La configuración aceptada ya era un snapshot inmutable. Se reutiliza sin leer
ajustes nuevos de UI ni sustituir la resolución: una sola resolución efectiva
alimenta bases, orientaciones, materiales y placements. No se introduce mínimo,
selección automática de precisión ni un nuevo esquema persistido.

TA-016 incorpora `RasterCache.iter_orientations`, una vista reiterable que genera
solo los ángulos solicitados y conserva orden/deduplicación por máscara completa.
Cada fuente vuelve al primer ángulo; fallar en un retazo no agota las rotaciones
de una plancha posterior. La base a 0° se reutiliza como la misma orientación que
consume la búsqueda. `orientations()` conserva su tupla histórica para métricas,
confirmación y consumidores actuales. No hay rotación propia de BF/WF ni de UI.

FF mantiene el primer candidato factible y no calcula scores ni examina otras
fuentes después del ganador. BF/WF mantienen la colocación canónica, capacidad
libre posterior, prioridad de retazos y desempates. Preparar una máscara de
material no equivale a evaluar esa fuente: las regresiones que antes espiaban
`RasterCache.material` ahora observan la consulta del material durante búsqueda
o `first_position`, conservando los mismos límites de evaluación. Se comprueba
también que cantidades/fuentes con la misma forma comparten una asignación.

`CalculateRun` recibe un checkpoint cooperativo del stream. Preparación,
orientaciones y búsqueda lo consultan entre operaciones geométricas; timeout o
desconexión abortan sin falsificar NO_FIT. Se conserva la cola/ack y la exclusión
de tiempo de entrega. No se añade un evento/campo V1 ni pausa para animar, y no
se promete cancelación en cada celda. La preparación ocurre fuera de sesiones
DB largas; las pruebas observan que no haya transacciones abiertas al rasterizar.

## Recursos y fidelidad

- Cache raster: conserva el presupuesto contabilizado de 64 MiB, comprobado antes
  de asignar cada máscara base u orientación solicitada. Layouts usados: 128 MiB.
- TA-037 conserva admisión, límites y estimador angular previo. Este incremento
  no amplía las cargas aceptadas; esa política puede seguir rechazando un lote
  que un recorrido lazy concreto consumiría con menos memoria.
- Los límites de preview HU-015 no se usan para el cache del cálculo.
- Geometría normalizada y máscara se contrastan con el rasterizador backend real,
  incluidas coordenadas negativas, material irregular y resolución fraccionaria.
- El handle es interno y exclusivo de cada cálculo; no persiste ni publica
  máscaras. Descriptores HTTP, correlación pública por corrida, retención y
  visualización autoritativa siguen en T03/T04. La UI conserva el estado honesto
  de máscara no disponible hasta disponer de ese contrato.

## Verificación reproducible

Desde `backend/`, con `.venv` existente y PostgreSQL temporal propio:

```bash
.venv/bin/python -m pytest tests/unit/optimization/test_run_geometry.py -q
# Antes de implementar: 15 failed, 5 passed (20 casos).
.venv/bin/python -m pytest tests/unit/optimization -q
# Después: 398 passed, 4.30 s.
NEWGLASS_TEST_PG_BIN=/tmp/hu016-tools/root/usr/lib/postgresql/17/bin NEWGLASS_REQUIRE_POSTGRES=1 .venv/bin/python -m pytest tests/api/optimization/test_run_geometry_api.py -q
# 5 passed, 1 warning previo de TestClient/httpx, 3.29 s.
```

Las cinco pruebas API adicionales verifican configuración cambiada tras aceptar,
ausencia de transacciones durante rasterización, timeout durante bases o una
rotación, agotamiento de memoria y desconexión durante la primera base. El
resultado es consultable como FALLIDA, no confirmable, sin movimiento/consumo de
inventario. Se mantiene EN_OPTIMIZACION para reconciliación, sin inventar rollback
de pedidos. Se ejecutaron además las regresiones reales de streaming/admisión:
44 passed antes de ampliar el archivo nuevo con dos casos adicionales.

La captura funcional previa de los ocho casos representativos TA-021, aplicada a
FF/BF/WF, coincide byte a byte tras el cambio: **24/24 resultados** con placements,
geometría, configuración, métricas y residuales iguales. SHA256 conjunto:
`30a085ef9230d4eb0c559ee52ccc65b2c3d83cfd6e9829763731c22114dab558`.
Las pruebas TA-021 conservan además sus seis órdenes y repeticiones.

Desde `frontend/`, misma instancia aislada y cuenta sintética de
`backend/tests/e2e_server.py`, sin credenciales del usuario:

```bash
PATH="/workspace/optimizador-vidrio/backend/.venv/bin:$PATH" NEWGLASS_TEST_PG_BIN=/tmp/hu016-tools/root/usr/lib/postgresql/17/bin NEWGLASS_REQUIRE_POSTGRES=1 PYTHON_DOTENV_DISABLED=1 PLAYWRIGHT_CHANNEL=chromium PLAYWRIGHT_BROWSERS_PATH=/tmp/hu016-tools/browsers HU015_E2E_USERNAME=O70000001 HU015_E2E_PASSWORD=Orders-test-2026! npm run test:e2e -- hu017-unified-flow.spec.js s1-optimization-ui.spec.js hu015-rasterization.spec.js
# 34 passed (2.9m), 0 skips, retries: 0; Chromium local 154.
```

Son 17 escenarios en escritorio y móvil: flujo unificado, preview histórico,
multipedido/multimaterial, rotación, retazos, cantidad/unidad física,
SIN_SOLUCION, permisos, conflictos, confirmación explícita y no consumo previo.
El gate permanente de skips no cambia; esta ejecución no cierra TA-040.

Suite backend completa desde `backend/`:

```bash
NEWGLASS_TEST_PG_BIN=/tmp/hu016-tools/root/usr/lib/postgresql/17/bin NEWGLASS_REQUIRE_POSTGRES=1 .venv/bin/python -m pytest -q
# 2270 passed, 1 warning previo de TestClient/httpx, 314.36 s; sin skips.
```

Incluye las 2245 pruebas existentes y 25 adicionales (20 unitarias y 5 API),
sin eliminar regresiones. `git diff --check` correcto.
No se atribuyen resultados de CI remota a esta rama local. El frontend no cambia
en T02: no se repiten lint/build/componentes ya correctos de T01.

## Medición exploratoria de memoria

Script reproducible: [hu017_preparation_benchmark.py](../../../../experiments/raster/scripts/hu017_preparation_benchmark.py).
Python 3.11.9, resolución 1 mm, paso 5°, sin DB/HTTP/inventario. Comparación contra
el backend de `2653a4b`, con `tracemalloc` activo durante `optimize`. Una pasada
por caso en este entorno, con otras comprobaciones concurrentes; no es un SLO
ni una prueba de carga de producción. Los hashes funcionales coinciden en los
tres casos y cada material se rasteriza una sola vez por cálculo.

| Entrada | Colocadas | Máscaras de piezas antes → después | Pico Python MiB antes → después | Cache contabilizado MiB antes → después |
|---|---:|---:|---:|---:|
| 8 rectángulos idénticos 400×300, plancha 2140×3300 | 8/8 | 72 → 1 | 5.069 → 2.379 | 4.561 → 1.068 |
| Rectángulo 1200×600, fuente 800×1800; requiere rotación | 1/1 | 72 → 17 | 12.884 → 3.583 | 15.812 → 3.967 |
| 3 geometrías, 3 unidades de cada una, plancha 2140×3300 | 9/9 | 216 → 3 | 14.061 → 2.565 | 16.015 → 1.157 |

El pico Python excluye la entrada ya construida y no es RSS del proceso. El cache
contabilizado es la estimación conservadora del motor; no se suman ambas columnas
ni se atribuye un presupuesto global nuevo que cubra API/DB/DOM.

Desde la raíz del repositorio:

```bash
mkdir -p /tmp/hu017-t02-baseline-src
git archive 2653a4b backend/app | tar -x -C /tmp/hu017-t02-baseline-src
backend/.venv/bin/python experiments/raster/scripts/hu017_preparation_benchmark.py /tmp/hu017-t02-baseline-src/backend
backend/.venv/bin/python experiments/raster/scripts/hu017_preparation_benchmark.py /workspace/optimizador-vidrio/backend
```

## Trazabilidad y pendientes

CA-03/04: barrera, única resolución y configuración inmutable; CA-05: fallo
explícito en límite exacto/+1 del cache; CA-14/15/16/18: invariancia funcional,
salida temprana, políticas y distancias; CA-21: inventario intacto en simulación y
fallos. CA-11/26 tienen cobertura interna de no modificar decisiones y máscara
real, pero requieren contrato/UI y pruebas de T03/T04/T06 para su cierre completo.

DG-01 sigue abierta. T03 no se implementa en este incremento: antes se debe
registrar la estrategia compatible de streaming y los límites/recuperación de
máscaras. T04/T05 y la cobertura transversal restante de T06 siguen pendientes.
