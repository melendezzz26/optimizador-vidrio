# SPEC-TA-049 — Presupuesto de tiempo de la optimización

| Campo | Valor |
|---|---|
| ID | TA-049 |
| Tareas | T01 — Definir contrato de deadline · T02 — Implementar y probar deadline |
| Sprint | Sprint 2 |
| Estado | **Draft** |
| Responsable | Fabricio Aguilar |
| Rama | `feature/S2-TA049-presupuesto-tiempo` |
| Base | `origin/integration/sprint-01` en `3f27cd7` |
| Fecha | 04/11/2026 |
| Referencias | SPEC-TA-037 §7.3 (L-12); `docs/contracts/optimization/comparison-v1.md` (presupuestos); SPEC-OPT-MULTIMOTOR-VISUAL |

## 1. Objetivo

Que toda corrida de optimización tenga un tiempo máximo y que, al alcanzarlo, termine de forma
controlada: la ejecución queda en un estado final claro, los procesos se detienen, la capacidad
se libera, el inventario no cambia y los pedidos se pueden volver a calcular. Las ejecuciones
normales no cambian.

## 2. Alcance

**Incluye:** los dos flujos de cálculo: la corrida de un solo motor (First Fit,
`/api/optimization/runs`) y la comparación de tres motores (`/api/optimization/comparisons`).

**Fuera de alcance:** cambiar los valores de los presupuestos; los límites de memoria y de carga
(TA-037, TA-044); el destino de los pedidos ante otras fallas (`CALCULATION_FAILED`,
`EXECUTION_INTERRUPTED`, `RESULT_SAVE_FAILED`), que siguen como están.

## 3. Situación actual (auditoría, 04/11/2026)

| Flujo | Presupuesto | Implementado en | Estado |
|---|---|---|---|
| Corrida First Fit | 120 s de cálculo, sin contar la entrega de eventos (TA-037 L-12) | `presentation/run_stream.py` | Se detiene en el siguiente hito, la corrida queda `FALLIDA` con `TIME_BUDGET_EXCEEDED` y se libera la capacidad. Probado en `test_run_concurrency.py`. |
| Comparación | Arranque 30 s; cálculo por motor 120 s; global 180 s | `infrastructure/comparison_runner.py`, `application/comparison_limits.py` | Cada motor se detiene en un hito; el supervisor termina todos los procesos al llegar a 180 s. Probado a nivel de proceso en `test_comparison_runner.py`. |

**Huecos encontrados:**

- **G-01 (defecto):** en la corrida First Fit, después de `TIME_BUDGET_EXCEEDED` los pedidos
  quedan en `EN_OPTIMIZACION` y no existe ningún mecanismo que los devuelva: no se pueden volver
  a calcular. TA-037 §7.3 dejó esa decisión a TA-038, que solo se resolvió para la comparación.
  La interfaz lo refleja: «los pedidos de este trabajo requieren revisión antes de volver a
  calcularse».
- **G-02 (prueba faltante):** el presupuesto de la comparación solo está probado a nivel de
  procesos; no hay una prueba por la API que verifique el estado final, los pedidos, el
  inventario y una ejecución posterior.

## 4. Contrato del deadline (T01)

### 4.1 Medición

| Flujo | Qué se mide | Dónde se corta |
|---|---|---|
| Corrida First Fit | Tiempo de cálculo desde que arranca el hilo, descontando la entrega de eventos al navegador. | En el siguiente hito del motor (pieza colocada o grupo iniciado/terminado). |
| Comparación, por motor | Tiempo de cálculo de cada motor, descontando pausas. | En el siguiente hito del motor. |
| Comparación, arranque | Tiempo hasta que los tres procesos están listos. | El supervisor termina los procesos. |
| Comparación, global | Tiempo total desde que empieza la comparación. | El supervisor termina los procesos aunque estén en medio de un cálculo. |

### 4.2 Estados y respuesta

| Flujo | Estado de la ejecución | Respuesta |
|---|---|---|
| Corrida First Fit | Corrida `FALLIDA`, no confirmable. | El stream termina con `optimization_failed`, `code = TIME_BUDGET_EXCEEDED` y un mensaje con el tiempo máximo. La corrida ya fue aceptada (201), así que no hay otro código HTTP. |
| Comparación | Cada motor afectado queda `FALLIDA` con `failure_code = TIME_BUDGET_EXCEEDED` y no elegible. Si ningún motor tiene un resultado elegible, la comparación termina `FALLIDA`; si otro motor terminó, termina `COMPLETADA` e `incomplete`, y solo se puede elegir el resultado completo. | Estado terminal consultable por `GET`; la interfaz muestra «El motor superó el tiempo de cálculo». |

Superar el tiempo nunca se informa como «sin solución» (`SIN_SOLUCION`).

### 4.3 Condiciones de cancelación

Al alcanzar el deadline, en ambos flujos:

1. Los procesos o hilos de cálculo se detienen y, en la comparación, se esperan (`join`) antes de
   liberar nada.
2. La capacidad del optimizador (admisión) se libera.
3. **El inventario no cambia:** las planchas y retazos solo se consumen al confirmar, y una
   ejecución `FALLIDA` no se puede confirmar.
4. **Los pedidos vuelven a `PENDIENTE`** y se pueden volver a calcular (D-01).
5. No queda ninguna ejecución en un estado intermedio (`EN_EJECUCION`).

Una ejecución que termina dentro del tiempo no se ve afectada.

## 5. Decisiones

- **D-01:** en la corrida First Fit, cuando el código de falla es `TIME_BUDGET_EXCEEDED`, los
  pedidos pasan de `EN_OPTIMIZACION` a `PENDIENTE` en la misma transacción que marca la corrida
  `FALLIDA`. Es seguro porque esa transacción la ejecuta el propio hilo de cálculo después de
  detenerse, con la corrida bloqueada (`FOR UPDATE`) y todavía `EN_EJECUCION`; no se consumió
  inventario. Así se iguala el comportamiento de la comparación. Las otras fallas no cambian
  (fuera de alcance).
- **D-02:** no se cambian los valores de los presupuestos (120 s, 30/120/180 s); su ajuste
  corresponde a TA-044 con mediciones.

## 6. Diseño técnico (T02)

Sin cambios de esquema ni migraciones.

| Archivo | Cambio |
|---|---|
| `optimization/infrastructure/run_uow.py` | `fail`: con `TIME_BUDGET_EXCEEDED`, devuelve los pedidos a `PENDIENTE` (D-01). |
| `frontend/.../optimization/optimizationModel.js` | El aviso de tiempo máximo indica que los pedidos volvieron a pendientes y se pueden recalcular en lotes más pequeños. |

## 7. Criterios de aceptación

| CA | Tarea | Criterio |
|---|---|---|
| CA-01 | T01 | Quedan documentados el deadline de cada flujo, los estados finales, la respuesta y las condiciones de cancelación (§4). |
| CA-02 | T02 | Una corrida First Fit que supera el tiempo termina `FALLIDA` con `TIME_BUDGET_EXCEEDED`, libera la capacidad, no modifica el inventario y deja los pedidos en `PENDIENTE`; una nueva corrida de los mismos pedidos se completa. |
| CA-03 | T02 | Una comparación que supera el tiempo por motor o el global termina en un estado final sin ambigüedad, con los tres motores en `TIME_BUDGET_EXCEEDED`, los procesos detenidos, la capacidad libre, el inventario intacto y los pedidos en `PENDIENTE`; una comparación posterior se completa. |
| CA-04 | T02 | Las ejecuciones normales y las suites existentes siguen en verde. |

## 8. Pruebas previstas

- `backend/tests/api/optimization/test_run_time_budget.py`: CA-02 (regresión de G-01: falla sin
  el cambio).
- `backend/tests/api/optimization/test_comparison_time_budget.py`: CA-03, por cálculo y por
  deadline global.
- Frontend: la prueba existente del aviso de tiempo máximo se ajusta al nuevo texto.

## 9. Evidencia requerida

`docs/evidence/sprint-02/TA-049/`: auditoría (§3), pruebas y checks del PR.

## Historial de estado

| Fecha | Versión | Estado | Cambio |
|---|---|---|---|
| 04/11/2026 | 0.1 | Draft | Auditoría de los dos flujos, contrato del deadline (§4), hueco G-01 y decisión D-01. |<>