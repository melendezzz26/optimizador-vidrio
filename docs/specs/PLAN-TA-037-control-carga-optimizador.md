# PLAN-TA-037 — Control de carga del optimizador

## Información general

| Campo | Valor |
|---|---|
| ID | TA-037 |
| SPEC | [SPEC-TA-037-control-carga-optimizador.md](SPEC-TA-037-control-carga-optimizador.md) (v1.1) |
| Estado | **Draft** |
| Responsable | Fabricio Aguilar |
| Fecha | 26/10/2026 |
| Base | `integration/sprint-01` en `b7b9caa` (después del PR #64, paso angular de 5°) |

## 1. Secuencia y estado

| Tarea | SP | Depende de | Entrega | Estado al 26/10 |
|---|---:|---|---|---|
| T01 — Definir presupuesto y contrato de errores | 0,5 | HU-015, TA-021 | Lunes 26/10, 12:00 | v1.0 integrada (PR #62). v1.1 recalibrada a 5°; **pendiente de aprobación** de los valores de §5 de la SPEC |
| T02 — Implementar guardrails previos a la expansión | 1,5 | T01 | Martes 27/10 | Diseño de código y pruebas listos (§3); falta implementar |
| T03 — Limitar concurrencia y controlar ejecución | 1 | T01, T02 | Martes 27/10 | Diseño en la SPEC (§5.1, §7.2, §7.3). L-12 pasa a ser protección principal |
| T04 — Probar límites y feedback | 1 | T02, T03 | Martes 27/10 | Casos definidos en la SPEC (§9, §12) |

T01 se considera cerrada cuando el equipo apruebe (o ajuste) los valores de la v1.1 y
la SPEC pase de `Draft` a `Reviewed`, con la aprobación anotada en el historial. Si
un valor cambia, solo cambia la constante y su justificación: los puntos de
validación y el contrato no dependen del número.

## 2. T01 — Qué quedó definido

- Límites vigentes de la v1.1: L-01, L-03 a L-05, L-07, L-09 a L-13, cada uno con su
  base medida a 5° (SPEC §3 y §5). L-02, L-06 y L-08 quedan retirados con su motivo.
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
| `backend/app/modules/optimization/presentation/run_routes.py` | Presentation | Inyecta el contador; mapea `LOAD_LIMIT_EXCEEDED` a 422 e incluye `limit` en `detail`. |

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
    max_layout_bytes: int = 128 * 1024 * 1024  # L-09, mismo valor que packing.py
    max_raster_bytes: int = 64 * 1024 * 1024   # L-13, mismo valor que rotation.py

class LoadLimitExceeded(RunError):
    # code="LOAD_LIMIT_EXCEEDED"; details={"limit": {...}} según SPEC §7.1
    def __init__(self, name: str, maximum: int, actual: int, scope: dict | None = None): ...

def check_selection(order_ids, budget) -> None: ...                     # P1: L-01
def check_pieces(rows, config, budget) -> dict[key, GroupLoad]: ...     # P3: L-03, L-04, L-05, L-13
def estimate_raster_bytes(geometries, config) -> int: ...               # L-13, misma fórmula que RasterCache._raster
def check_stock(groups: dict[key, GroupLoad], counts, config, budget) -> None: ...  # P4: L-07, L-09
```

- `check_pieces` recorre **filas**, nunca unidades. `GroupLoad` acumula, por
  material, las unidades y el área total con `Decimal`.
- La suma de `cantidad` se corta en cuanto supera `max_units`, para no depender de
  sumas enormes. `actual` informa la suma exacta, porque con pocas filas es barata.
- La geometría se verifica con la **misma** `RasterCache().check_geometry` que hoy
  usa `runs.py`, una vez por fila. `RasterPreparationError` sigue terminando en el
  mismo `INVALID_INPUT`, para no cambiar la respuesta actual.
- `estimate_raster_bytes` agrupa por geometría canónica (como la huella de
  `RasterCache`) y suma, por orientación válida, la fórmula de SPEC §5.1. No
  rasteriza ni guarda máscaras.
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
                    config, self.budget)                          # P4
    problem = prepare_persisted_problem(ids, pieces, config)      # igual que hoy
    ...
```

`stock_counter=None` mantiene compatibles las pruebas que construyen `AcceptRun` con
un solo argumento. En producción, `run_routes.py` siempre lo inyecta.

### 3.4 Pruebas de T02

| Archivo | Casos |
|---|---|
| `tests/unit/optimization/test_load_budget.py` | Exacto y + 1 de L-01, L-03, L-04, L-05, L-07, L-09 y L-13 (parametrizado); orden cuando se violan dos límites; `scope` correcto; cantidad 2 147 483 647 sin asignación grande; `estimate_raster_bytes` coincide con lo que suma `RasterCache`; mensajes sin SQL ni rutas. |
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

1. `docs(TA-037): recalibrate load budget for 5 degree rotation` (v1.1: SPEC, PLAN, evidencia y script)
2. `feat(TA-037): reject oversized runs before expansion` (T02: código)
3. `test(TA-037): cover exact and over-limit run budgets` (T02: pruebas)

## 4. T03 y T04 — Pendientes del martes

- **T03:** puerto `RunAdmission` con `try_acquire(user_id) -> Lease | None` y una
  implementación en proceso (`threading.Lock` y contadores), usada en `start_run`
  antes de `AcceptRun`. El `Lease` se libera en el `finally` de `produce()` y, si el
  hilo nunca arrancó, en el `finally` de `lines()`. La liberación es idempotente.
  L-12 se verifica en `milestone` con un reloj inyectable. Como en la v1.1 L-12
  reemplaza a L-08, T03 es necesaria para cerrar el peor caso de stock.
- **T04:** pruebas de concurrencia (admitida, rechazada y liberación), stock
  voluminoso sin OOM, y feedback en `useFirstFit.js` / `OptimizationPage.jsx` con
  Vitest y Playwright.

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