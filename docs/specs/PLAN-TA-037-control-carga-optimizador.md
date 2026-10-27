# PLAN-TA-037 — Control de carga del optimizador

## Información general

| Campo | Valor |
|---|---|
| ID | TA-037 |
| SPEC | [SPEC-TA-037-control-carga-optimizador.md](SPEC-TA-037-control-carga-optimizador.md) (v1.3, saneamiento T03) |
| Estado | **Implemented** (T01 a T04) |
| Responsable | Fabricio Aguilar |
| Fecha | 26/10/2026 |
| Base original T02 | `integration/sprint-01` en `4b82af7` (después del PR #65) |
| Base del saneamiento T03 | `integration/sprint-01` en `445886a` |

## 1. Secuencia y estado

| Tarea | SP | Depende de | Entrega | Estado |
|---|---:|---|---|---|
| T01 — Definir presupuesto y contrato de errores | 0,5 | HU-015; coordinación con TA-021 | Lunes 26/10, 12:00 | **Hecha.** v1.0 (PR #62), v1.1 a 5° (PR #65), valores aprobados; SPEC en `Reviewed` (v1.2) |
| T02 — Implementar guardrails previos a la expansión | 1,5 | T01 | Martes 27/10 | **Implementada** en `enabler/TA-037-guardrails` (§3); 55 pruebas nuevas; suite completa en verde |
| T03 — Limitar concurrencia y controlar ejecución | 1 | T01, T02 | Martes 27/10 | **Implementada** en `enabler/TA-037-concurrencia` (§4); 20 pruebas nuevas; suites backend, frontend y E2E en verde |
| T04 — Probar límites y feedback | 1 | T02, T03 | Martes 27/10 | **Implementada** en `enabler/TA-037-feedback`; avisos de frontend, pruebas de peor caso y E2E real (§4) |

T01 quedó cerrada al aprobarse los valores de la v1.1. La SPEC pasa a `Reviewed` en la
v1.2, que además recoge dos correcciones encontradas al implementar T02: L-09 se retira
(no tiene cota inferior segura) y L-05 conserva su `INVALID_INPUT` actual.

## 2. T01 — Qué quedó definido

- Límites vigentes de la v1.2: L-01, L-03 a L-05, L-07 y L-10 a L-13, cada uno con su
  base medida a 5° (SPEC §3 y §5). L-02, L-06, L-08 y L-09 quedan retirados con su motivo.
- La separación entre validación de negocio y límite operativo (SPEC §4).
- El punto exacto donde se valida cada límite (SPEC §6).
- Los contratos 422 `LOAD_LIMIT_EXCEEDED`, 503 `OPTIMIZER_BUSY` y el evento de
  stream `TIME_BUDGET_EXCEEDED` (SPEC §7).
- Los gaps que no se resuelven aquí y a quién se derivan (SPEC §11), incluido el
  GAP-05 (capacidad real a 5°) para TA-016 / HU-017.
- El script de medición reproducible
  `experiments/raster/scripts/ta037_load_benchmark.py` (opción `--paso5`) y sus
  resultados en `docs/evidence/sprint-02/TA-037/`.

**Decisiones a validar con el equipo:**

1. L-03 = 150 unidades y L-07 = 50 unidades de stock por material, medidos a 5°.
2. Retirar L-08 y apoyarse en L-12 (120 s) como protección principal del peor caso.
3. Agregar L-13 (memoria raster estimada, 64 MiB) como rechazo temprano.
4. Mantener los límites como constantes en código, sin la tabla `configuraciones`,
   para no requerir migración ni API nueva.
5. Usar 503 con `Retry-After` para capacidad ocupada.
6. Avisar a los responsables de Orders e Inventory del GAP-02, y a los de TA-016 /
   HU-017 del GAP-05.

## 3. T02 — Diseño de implementación

Rama: `enabler/TA-037-guardrails`, creada desde `integration/sprint-01` actualizado.

### 3.1 Archivos

| Archivo | Capa | Acción |
|---|---|---|
| `backend/app/modules/optimization/application/load_budget.py` | Application | **Nuevo.** `RunLoadBudget` con los límites de tamaño y funciones puras de verificación. |
| `backend/app/modules/optimization/application/errors.py` | Application | `RunError` acepta `details: dict \| None = None`, sin romper las llamadas actuales. |
| `backend/app/modules/optimization/application/ports.py` | Application | Puerto `CompatibleStockCounter.count_compatible(group_key) -> StockCount`. |
| `backend/app/modules/optimization/application/runs.py` | Application | Llamadas a P1, P3 y P4. `AcceptRun(unit_of_work, stock_counter=None, budget=DEFAULT_RUN_LOAD_BUDGET)`. |
| `backend/app/modules/optimization/infrastructure/stock_adapter.py` | Infrastructure | `count_compatible` sin expandir; defensa P5 antes del bucle. |
| `backend/app/modules/optimization/presentation/run_routes.py` | Presentation | `get_stock_counter` reutiliza el adaptador del cálculo; mapea `LOAD_LIMIT_EXCEEDED` a 422 e incluye `limit` en `detail`. |
| `backend/app/modules/optimization/presentation/run_schemas.py` | Presentation | `ErrorDetailV1` acepta `LOAD_LIMIT_EXCEEDED` y el campo opcional `limit` (`LoadLimitV1`), presente solo con ese código. |

Archivos que **no** se tocan: `domain/packing.py`, `domain/first_fit.py`,
`domain/best_fit.py`, `domain/worst_fit.py`, `domain/placement.py`,
`domain/rotation.py`, `domain/preparation.py`, `domain/problem.py`,
`application/calculation.py`, `application/confirmation.py` e
`infrastructure/confirmation_adapter.py`. L-13 usa las funciones **públicas**
`oriented_geometry`, `discrete_angles` y `RasterCache.check_geometry` de
`domain/rotation.py`, sin modificarlas (Application puede depender de Domain).

### 3.2 Contrato de `load_budget.py`

```python
@dataclass(frozen=True)
class RunLoadBudget:
    max_orders: int = 20                       # L-01
    max_units: int = 150                       # L-03
    max_vertices: int = 128                    # L-04
    max_stock_units_per_material: int = 50     # L-07
    max_raster_bytes: int = 64 * 1024 * 1024   # L-13, mismo valor que rotation.py

class LoadLimitExceeded(RunError):
    # code="LOAD_LIMIT_EXCEEDED"; details={"limit": {...}} según SPEC §7.1
    def __init__(self, name: str, maximum: int, actual: int, scope: dict | None = None): ...

def check_selection(order_ids, budget) -> None: ...                     # P1: L-01
def check_pieces(rows, config, budget) -> dict[key, int]: ...           # P3: L-03, L-04, L-05, L-13
def estimate_raster_bytes(snapshots, config) -> int: ...                # L-13, cota inferior de RasterCache
def check_stock(units_by_material, stock_units, budget) -> None: ...    # P4: L-07
```

- `check_pieces` recorre **filas**, nunca unidades, y devuelve las unidades por
  material para P4. Las filas con datos de negocio inválidos no se cuentan: las
  rechaza después la validación existente con `INVALID_INPUT`.
- La suma de `cantidad` se corta en cuanto supera `max_units`, para no depender de
  sumas enormes. `actual` informa la suma exacta, porque con pocas filas es barata.
- La geometría se verifica con la **misma** `RasterCache().check_geometry` que hoy
  usa `runs.py`, una vez por fila. `RasterPreparationError` sigue terminando en el
  mismo `INVALID_INPUT`, para no cambiar la respuesta actual.
- `estimate_raster_bytes` agrupa por la misma huella que `RasterCache` y suma, por
  orientación, la fórmula de SPEC §5.1 con la rejilla redondeada hacia abajo. No
  rasteriza ni guarda máscaras. Una prueba comprueba que queda entre el 90 % y el
  100 % de la caché real del motor.
- El orden de verificación es exactamente el de SPEC §6.

### 3.3 Cambio en `AcceptRun.execute`

```python
ids = ...validación actual...
check_selection(ids, self.budget)                                 # P1
with self.unit_of_work() as uow:
    configuration_id, config = uow.configuration()
    ...validación actual del paso angular de 5° (PR #64)...
    pieces = uow.orders.lock_pending(ids)
    ...validación actual de discrete_angles...
    groups = check_pieces(pieces, config, self.budget)            # P3, antes de expandir
    if self.stock_counter is not None:
        check_stock(groups, {k: self.stock_counter.count_compatible(k) for k in groups},
                    self.budget)                                  # P4
    problem = prepare_persisted_problem(ids, pieces, config)      # igual que hoy
    ...
```

`stock_counter=None` mantiene compatibles las pruebas que construyen `AcceptRun` con
un solo argumento. En producción, `run_routes.py` siempre lo inyecta.

### 3.4 Pruebas de T02

| Archivo | Casos |
|---|---|
| `tests/unit/optimization/test_load_budget.py` | Exacto y + 1 de L-01, L-03, L-04, L-07 y L-13; L-05 conserva su `ValueError`; orden cuando se violan dos límites; `scope` correcto; cantidad 2 147 483 647 sin asignación grande; `estimate_raster_bytes` coincide con lo que suma `RasterCache`; mensajes sin SQL ni rutas. |
| `tests/unit/optimization/test_accept_run_load_limits.py` | Con UoW en memoria: el rechazo no llama a `prepare_persisted_problem`, `runs.create` ni `transition` (espías que fallan si se invocan); la aceptación en el límite exacto produce el mismo `problem` que sin presupuesto; caso H-10 (3 piezas de ~1300 × 1000 rechazadas, 2 aceptadas). |
| `tests/api/optimization/test_run_load_limits.py` | 422 con el `detail` de SPEC §7.1; sin `Location` ni NDJSON; un Operario sin `optimization.execute` sigue recibiendo 403 antes que el límite. |
| `tests/integration/optimization/test_run_load_limits_pg.py` | PostgreSQL: pedidos `PENDIENTE`, cero filas nuevas en las 3 tablas de optimización e inventario idéntico tras el rechazo; una plancha con `cantidad` 1000 se rechaza por conteo. |
| Regresión | Suites existentes de FF, BF, WF, el corte comercial y la confirmación, sin editar sus aserciones. |

Comandos locales antes del push:

```powershell
cd backend
.\venv\Scripts\activate
pytest
cd ..\frontend
npm ci
npm run lint
npm run build
```

Las pruebas de integración necesitan PostgreSQL, y localmente se omiten. CI las
corre: revisar que el job de backend quede en verde.

### 3.5 Commits sugeridos

1. `docs(TA-037): mark load budget spec as reviewed` (v1.2: SPEC y PLAN)
2. `feat(TA-037): reject oversized runs before expansion` (T02: código)
3. `test(TA-037): cover exact and over-limit run budgets` (T02: pruebas)

## 4. T03 y T04 — Implementación original

- **T03 (implementada):**
    - `application/admission.py`: puerto `RunAdmission.acquire(user_id) -> AdmissionLease`
      y error `OptimizerBusy` (503 `OPTIMIZER_BUSY`, `Retry-After: 15`, `limit`).
    - `infrastructure/in_process_admission.py`: `InProcessRunAdmission` con
      `threading.Lock`, L-10 = 2, L-11 = 1 y liberación idempotente al finalizar
      el propietario. La expiración de respaldo de v1.2 se retira en el saneamiento v1.3.
    - `presentation/run_routes.py`: `start_run` toma la plaza antes de `AcceptRun` y la
      libera si la aceptación falla; la confirmación no pasa por la admisión.
    - `presentation/run_stream.py`: la plaza se libera en el `finally` del hilo de
      cálculo, o al cerrar un stream cuyo hilo nunca arrancó; L-12 se verifica en cada
      hito descontando el tiempo de entrega; nuevo código `TIME_BUDGET_EXCEEDED`.
    - `presentation/run_schemas.py` y `frontend/.../runContract.js`: aceptan
      `OPTIMIZER_BUSY` y `TIME_BUDGET_EXCEEDED`.
    - Pruebas: `tests/unit/optimization/test_run_admission.py`,
      `tests/api/optimization/test_run_concurrency.py`, un caso nuevo en
      `frontend/tests/unit/runContract.test.js` y una fixture que da a cada prueba de API
      una admisión limpia. Una prueba de mutación confirmó que las pruebas fallan si se
      quita la liberación, el corte por tiempo o la admisión.
- **T04 (implementada):**
    - `runApi.js`: `RunApiError` conserva `limit` y `Retry-After`.
    - `useFirstFit.js`: un 503 `OPTIMIZER_BUSY` cuenta como rechazo (no se creó la
      ejecución), igual que un 4xx.
    - `optimizationModel.js`: clasifica el error (`load_limit`, `busy`, `time_budget`) y
      `runErrorFeedback` decide título, indicación y variante (SPEC §7.4).
    - `OptimizationPage.jsx` y `.css`: muestran el aviso con `FeedbackMessage` y le dan el
      foco; estilos con los tokens existentes.
    - Pruebas: `__tests__/LoadControlFeedback.test.jsx` (7),
      `tests/api/optimization/test_run_load_stress.py` (4) y la E2E
      `tests/e2e/ta037-load-feedback.spec.js` (escritorio y móvil). Una prueba de mutación
      confirmó que los avisos fallan sin los cambios de T04.
    - Evidencia: `docs/evidence/sprint-02/TA-037/README.md` y capturas en
      `docs/evidence/sprint-02/TA-037/e2e/`.

## Saneamiento T03 — 27/10/2026

Base `445886a` de `integration/sprint-01`; rama `fix/TA-037-admission-lifecycle`.
El trabajo original de Aguilar se conserva. Esta corrección la realiza Fabricio
Melendez Quezada con Codex, antes de comenzar nuevos PBIs. Implementación y
pruebas: `b583870` y `2470100`; resultados reproducibles en la
[evidencia v1.3](../evidence/sprint-02/TA-037/admission-lifecycle.md).

1. Actualizar SPEC §5.1: mantener la plaza hasta la liberación de su propietario;
   retirar la caducidad por reloj sin cambiar L-10/L-11, L-12 ni HTTP/NDJSON.
2. Reproducir el defecto con reloj simulado; sustituir la prueba que esperaba
   expiración por regresiones del límite global y por usuario después de 300 s.
3. Corregir únicamente la admisión en Infrastructure. Mantener el cierre del
   trabajador como propietario de la plaza y la liberación idempotente.
4. Probar contrapresión de un stream real con PostgreSQL, finalización y fallo
   de arranque del trabajador; verificar rechazo sin nuevos pedidos, consumo de
   inventario o movimientos. Conservar regresiones de desconexión, tiempo y confirmación.
5. Ejecutar pruebas focalizadas y regresión backend obligatoria con PostgreSQL;
   revisar el CI de frontend/E2E y registrar evidencia por CA y tarea.
6. Abrir PR hacia `integration/sprint-01`, sin cambios en otras heurísticas ni
   PBIs. Dejar el cierre formal sujeto a revisión e integración del saneamiento.

Entregables de cierre: corrección, pruebas reproducibles, matriz de los 12 CA,
CI y trazabilidad de aportes en `docs/evidence/sprint-02/TA-037/`. Los gaps
TA-038, GAP-03 y GAP-05 mantienen su alcance separado; no bloquean el cierre de
los criterios propios de TA-037 si quedan explícitamente documentados.

## 5. Riesgos

| Riesgo | Mitigación |
|---|---|
| Un límite rechaza trabajo comercial real | Valores medidos a 5° y ajustables con un PR; mensaje que explica cómo dividir el lote. GAP-05 informado a TA-016 / HU-017. |
| Cambiar sin querer el resultado del motor | No se tocan los archivos de dominio; prueba de equivalencia del `problem` aceptado; regresiones existentes. |
| Leer stock dentro de la transacción alarga el bloqueo de pedidos | Solo conteos por material; sin expansión. Se mide en T04. |
| Carrera entre P4 y el cálculo | Defensa P5; recuperación por TA-038. |
| El paso angular vuelve a cambiar | Recalibrar L-03 y L-07 con `--paso5` adaptado al nuevo paso. L-13 se ajusta solo, porque usa el paso vigente. |
| Escalar a varios procesos invalida L-10 y L-11 | GAP-03: requiere ADR antes de escalar. |

## Historial de estado

| Fecha | Estado | Nota |
|---|---|---|
| 25/10/2026 | Draft | T01 redactada; T02 diseñada, sin implementar. |
| 26/10/2026 | Draft | v1.1: valores recalibrados a 5° (PR #64); L-13 agregado; diseño de T02 actualizado. |
| 26/10/2026 | Draft | T02 implementada; SPEC v1.2 en `Reviewed`; L-09 retirado; T03 y T04 pendientes. |
| 26/10/2026 | Draft | T03 implementada (admisión, liberación de plazas y L-12); T04 pendiente. |
| 26/10/2026 | Implemented | T04 implementada; CA-01 a CA-12 en PASS. Pendiente: CI y revisión para Verified. |
| 27/10/2026 | Implemented | Saneamiento implementado: 39 pruebas focalizadas y 717 regresiones de optimización aprobadas con PostgreSQL obligatorio. Se conservan T01/T02/T04 y contratos; CI y revisión del PR pendientes para cierre formal. |
