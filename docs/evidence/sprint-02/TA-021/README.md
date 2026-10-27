# TA-021 — Comparación FF/BF/WF sobre la misma instancia

Fecha: 27/10/2026. Responsable: Fabricio Melendez Quezada, con Codex.
SPEC v1.1 Reviewed y PLAN Approved antes del desarrollo; aprobación registrada
en `a665115`. Rama `feature/TA-021-comparacion-metodos`, destino exclusivo
`integration/sprint-01`. Base integrada actualizada a `2fc228d` (PR #75,
documentación TA-020; motor idéntico a la base auditada `0424f30`).

**Estado: implementación T01/T02 y validación técnica local completadas.**
Revisión cruzada de implementación e integración pendientes; no se atribuye
una aprobación humana ni se declara Closed/Verified o se modifica Notion.

## Entregas y uso

- T01: `5af647f`, infraestructura genérica y FF/WF, 45 pruebas nuevas.
  [Registro de fase](T01.md): esta entrega no cerró TA-021.
- T02: BF real de TA-018 añadido únicamente por composición; el servicio sigue
  siendo el mismo bucle genérico. Pruebas finales: 60, incluidas las anteriores.

Punto de entrada: `backend/app/modules/optimization/application/comparison.py`.
El consumidor prepara pedidos/piezas con `prepare_persisted_problem`, captura
stock con `with_compatible_stock` y obtiene los dos mínimos una sola vez antes
de llamar al servicio. El servicio recibe únicamente esos valores:

```python
from app.modules.optimization.application.comparison import compare_methods

entries = compare_methods(
    problem_with_captured_stock,
    minimum_width_mm=captured_minimum_width,
    minimum_height_mm=captured_minimum_height,
)
# Tupla en orden FF, BF, WF. Cada entrada expone method, result y residuals.
# result mantiene complete, unplaced_units, placements, metrics y computation_time_ms.
```

También admite una colección explícita ordenada de pares `(código, factoría)`.
Se valida completa, incluidos duplicados/disponibilidad, antes de ejecutar.
No requiere otro comparador para una colección de uno, dos, tres o más métodos.
Cada invocación construye las estrategias; cada `optimize` mantiene el estado
local existente del motor. P y geometrías profundamente inmutables se comparten
sin serialización/copia JSON ni precálculo exhaustivo que altere FF.

Las métricas llaman a la función existente con los mismos mínimos capturados.
Se verifica `result.method` antes/después de métricas; no se reetiqueta FF como
BF/WF. Tiempo individual: optimización + métricas; excluye preparación, stock,
construcción de estrategias y callbacks (no se ofrecen en este contrato).
No usar estos tiempos como benchmark estadístico ni criterio de selección.

Una solución parcial o vacía es válida; se ejecutan los otros métodos. Cero
colocadas conserva `metrics=None`. Un error técnico detiene la comparación con
`ComparisonFailed.method`, `.stage` y causa encadenada; no devuelve éxito parcial.
Errores de entrada/disponibilidad son `ValueError` previos a la optimización.

## Instancias y resultados observados

Todos los casos nuevos son sintéticos y pequeños. El paso operativo es 5°;
la compatibilidad con otras configuraciones conserva el contrato del motor.
El caso explícito de integración BF usa una pieza 2×2, tres planchas ordenadas
6×4 (ID 1), 4×4 (ID 2), 3×3 (ID 3), vidrio 1 / espesor 6, resolución 1 mm,
margen/separación 0, mínimos 1×1 mm. Resultado real:

| Método | Plancha física | Completo | Aprovechamiento % | Merma mm² | Retazo recuperable mm² |
|---|---|---|---|---|---|
| FF | 1 / unidad 1 | Sí | 16.667 | 4 | 16 |
| BF | 3 / unidad 1 | Sí | 44.444 | 2 | 3 |
| WF | 1 / unidad 1 | Sí | 16.667 | 4 | 16 |

La tabla describe decisiones de cada política, no una selección de ganador.
BF conserva `BestFitResult` antes y después de métricas.

`representative_cases()` añade prioridad de retazos, fallback, agotamiento de
unidades físicas, varios pedidos/materiales/espesores, rotación necesaria,
margen/separación, polígono, parcial y stock vacío. Cada uno se contrasta con
las llamadas directas a las estrategias y métricas. Se repiten tres veces las
seis permutaciones: FF/BF/WF, FF/WF/BF, BF/FF/WF, BF/WF/FF, WF/FF/BF,
WF/BF/FF. Igualdad funcional por método incluye problema completo, placements,
fuentes/orientaciones, colocadas/faltantes, métricas y residuales; solo se retira
`computation_time_ms` de la igualdad. Los dos órdenes FF/WF siguen cubiertos.

## Validación reproducible

Python 3.11.9 y dependencias existentes; desde `backend/`:

```bash
PYTHON_DOTENV_DISABLED=1 .venv/bin/python -m pytest tests/unit/optimization/test_comparison.py tests/integration/optimization/test_comparison_slice.py -q
# 60 passed in 6.46s
```

Las 60 pruebas son 54 unitarias y 6 de integración. El slice reutiliza SQLite
aislado, repositorios reales y metadatos clonados, sin Alembic ni base compartida.
Dos pedidos, dos materiales, ocho unidades: preparación única y una captura de
stock por grupo. Cero sentencias SQL durante las seis permutaciones, y todas las
tablas intactas en éxito y fallo técnico de WF/BF o sus métricas. Incluye pedidos,
stock, corridas, propuestas, movimientos y selección persistida por comparar
todas las tablas del modelo. No acredita locking/restricciones PostgreSQL.

Pruebas adicionales verifican cambios externos después de captura sin alterar
geometría/cantidades/stock/mínimos de la comparación; fallos con causa y método
sin ejecutar posteriores; reintento limpio, identidad de resultados, colecciones
variables, validación previa e inmutabilidad. FF visita solo la primera fuente
con 8/80 disponibles (motor + métricas), preservando su evaluación lazy.

La regresión T01 de 508 pruebas y sus comandos están en [T01.md](T01.md).
La regresión completa y CI se consultan en el PR de implementación. El comando
completo, con PostgreSQL temporal obligatorio y sin dotenv, es:

```bash
NEWGLASS_TEST_PG_BIN=/ruta/a/postgresql/bin NEWGLASS_REQUIRE_POSTGRES=1 PYTHON_DOTENV_DISABLED=1 .venv/bin/python -m pytest tests -q -ra
```

La ruta PostgreSQL debe contener `initdb` y `pg_ctl`; en esta sesión es
`/tmp/hu016-tools/root/usr/lib/postgresql/17/bin`. No requiere credenciales ni
variables de entorno del usuario, y no conecta a su base remota.

Resultado local final sobre `fdce92c`, Python 3.11.9 y PostgreSQL 17 temporal:
**2238 passed, 1 warning in 261.07s (0:04:21)**. Sin skips. El warning existente
es `StarletteDeprecationWarning` sobre `httpx` en TestClient; no se modifica
esa dependencia desde TA-021. Incluye las regresiones PostgreSQL de corridas,
concurrencia, límites y confirmación transaccional además de las 60 pruebas nuevas.

## Matriz final de aceptación técnica

Referencias: U = `backend/tests/unit/optimization/test_comparison.py`;
I = `backend/tests/integration/optimization/test_comparison_slice.py`.
PASS significa evidencia técnica propia; no sustituye la revisión cruzada.

| CA | Estado | Evidencia |
|---|---|---|
| 01 | PASS | U: colección individual, FF/WF, FF/BF/WF y extensión EXTRA. |
| 02 | PASS | U: mínimos comunes/cambios externos; I: captura por grupo y cero SQL durante comparación. |
| 03 | PASS | U: problema completo igual a llamadas directas en casos múltiples. |
| 04 | PASS | U: fuentes físicas y compatibilidad; I: stock real capturado y tablas intactas. |
| 05 | PASS | U: entrada profunda inmutable, permutaciones/repeticiones y reintento tras fallo. |
| 06 | PASS | I: todas las tablas iguales antes/después, también ante fallo. |
| 07 | PASS | U: duplicados rechazados previamente; identidad antes/después de métricas y BF real. |
| 08 | PASS | U: FF directo y solo primera fuente con 8/80; regresiones existentes T01. |
| 09 | PASS | U: WF directo en cada caso; políticas distintas y regresiones existentes T01. |
| 10 | PASS | Commit `5af647f` y evidencia T01: FF/WF validados sin cierre anticipado. |
| 11 | PASS | T02 solo añade import/factoría BF a composición, sin otro flujo. |
| 12 | PASS | U/I: tres optimizadores reales de la base integrada, sin BF simulado. |
| 13 | PASS | U: tres repeticiones por permutación; comparación excluye solo tiempo. |
| 14 | PASS | U/I: seis permutaciones completas; U conserva ambos órdenes FF/WF. |
| 15 | PASS | Tupla en orden solicitado sin ganador, puntuación/ranking global ni selección persistida. |
| 16 | PASS | Función de métricas existente, mínimos invariantes; U: igualdad directa y cronómetro. |
| 17 | PASS | Diff sin infraestructura/esquema nuevos; I: cero SQL y todas las tablas intactas. |
| 18 | PASS | Diff sin frontend, HTTP ni streaming visual. |
| 19 | PASS | Diff sin cambios de motores/geometría; igualdad directa y regresiones existentes. |
| 20 | PASS | U: parciales/vacías válidas y errores técnicos con causa/método; I: tablas intactas ante error. |

## Revisión propia, límites y cierre

Se revisa el diff completo contra `origin/integration/sprint-01`: un módulo de
aplicación, dos archivos de pruebas y documentación TA-021. `git diff --check`
correcto. No se modifican motor, rotación, métricas, confirmación, endpoints,
persistencia, frontend, migraciones ni variables de entorno del proyecto.
No se crea ganador, reserva, corrida durable ni selecciona ejecución.

El servicio interno conserva los presupuestos del motor, pero no hereda la
admisión/timeout de `/runs`. Usa cargas controladas y ejecución secuencial; la
política de presupuesto global debe acordarse antes de un consumidor HTTP.
No es benchmark ni garantía de memoria constante del conjunto de resultados.
TA-025 seleccionará, TA-026 persistirá y HU-017 visualizará por separado.

La aprobación de SPEC/PLAN proviene del responsable; la revisión de código aquí
descrita es propia de Codex. Antes de Closed/Verified quedan revisión cruzada y
merge del PR hacia `integration/sprint-01`, seguidos del smoke de integración.
