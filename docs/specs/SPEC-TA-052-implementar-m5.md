# SPEC-TA-052 — Implementar heurística M5 (Best Residual Fit) en el sistema

Estado: Implemented (v2)
PBI relacionado: TA-052 (T01 y T02)
Autor: Luis Anthony Ibáñez Herrera
Revisor esperado: Andro Joseph Quispe Cesias (aprobación formal pendiente)
Fecha: 03/11/2026 (v1.0) · 07/11/2026 (v2)
Versión: 2 — regla de fuentes en uso (RN-01, RN-06, flujo paso 3, CA-02, CA-08); ver historial

---

## 1. Objetivo

Llevar al sistema de producción de NewGlass de forma canónica y reproducible la heurística de optimización de corte **M5 (Best Residual Fit - BRF)** validada experimentalmente en el Spike SP-005, asegurando total compatibilidad con los contratos inmutables del dominio, la preservación de las 20 reglas comunes y la cobertura de pruebas unitarias y de integración.

---

## 2. Alcance

### Incluye:
- **T01 — Implementar M5 en el backend:**
  - `domain/best_residual_fit.py`: `BestResidualFitSelector`, `BestResidualFitResult` (con `method="M5"`), `BestResidualFitOptimizer`.
  - `application/best_residual_fit.py`: Función `calculate_best_residual_fit(...)` para simulación de solo lectura sobre inventario.
  - `domain/problem.py`: Extensión del tipo `OptimizationResult.method` para admitir `"M5"`.
  - `application/comparison.py`: Lista opcional `EXTENDED_METHODS` con M5. `DEFAULT_METHODS` permanece en FF/BF/WF; el registro público de M5 corresponde a TA-043.
- **T02 — Crear pruebas de M5:**
  - `tests/unit/optimization/test_best_residual_fit.py`: Cobertura exhaustiva de selección normal, desempate lexicográfico completo, rotación canónica a 5°, no colocables, prioridad de retazos, inmutabilidad y pruebas de aplicación.
  - 18 pruebas nuevas en `test_best_residual_fit.py` ejercitan directamente el motor productivo; 11 pruebas heredadas en `test_sp005_m5.py` aún ejercitan el optimizador experimental de SP-005. La selección conjunta contiene 29 pruebas, sin convertir las 11 heredadas en pruebas productivas directas.
  - Registro de evidencia formal en `docs/evidence/sprint-02/TA-052/README.md`.

### Fuera de alcance:
- Alterar el ciclo de vida HTTP productivo de confirmación de órdenes de corte (`/runs` permanece en First Fit).
- Modificaciones en esquemas de base de datos relacionales o migraciones Alembic.

---

## 3. Actor y precondiciones

- **Actor:** Desarrollador / Motor de Optimización de NewGlass.
- **Precondiciones:**
  - SP-005 validado y mergeado en `integration/sprint-01` (PR #93).
  - Casos congelados TA-027 disponibles e inalterados.

---

## 4. Entradas / datos

El método M5 opera sobre la misma entidad inmutable `OptimizationProblem`:
- Piezas ordenadas por área decreciente (`prepare_group_units`).
- Configuración con `resolution_mm`, `angular_step_deg=5`, `margin_mm`, `separation_mm`.
- Stock agrupado por material con prioridad estricta `RETAZO` $\to$ `PLANCHA`.

---

## 5. Reglas de negocio

- **RN-01 (Criterio de Selección M5, v2):** Entre los candidatos factibles de fuentes **en uso** del nivel permitido (RN-06), selecciona el que maximiza el área del mayor rectángulo inscribible (`largest_rectangle`) del layout post-colocación.
- **RN-02 (Desempate por merma fragmentada):** En caso de empate en el área del retazo recuperable, minimiza las celdas libres no aprovechables (`fragmented_cells = free_cells - remnant_cells`).
- **RN-03 (Desempate determinista estable):** En caso de empate en merma, desempata estrictamente por `(stock_rank, orientation_rank, row, column)` en orden ascendente.
- **RN-04 (Identidad del método):** `OptimizationResult.method` devuelve `"M5"`.
- **RN-05 (Inmutabilidad de inventario):** La simulación no consume stock, no bloquea láminas en BD y no tiene efectos colaterales.
- **RN-06 (Fuentes en uso primero, v2):** Una fuente está *en uso* cuando ya tiene al menos una pieza colocada en el cálculo actual. Dentro del nivel permitido (retazos primero, luego planchas):
  1. Si la pieza cabe en alguna fuente en uso, M5 elige entre ellas según RN-01 a RN-03.
  2. Solo si no cabe en ninguna fuente en uso, abre la fuente sin usar de menor `(stock_rank, orientation_rank, row, column)` (mismo criterio que FF), sin calcular su retazo para decidir.

  Motivo: observación del profesor en la revisión del 04/11/2026. La regla v1 (comparar también las fuentes vacías) abría una plancha nueva por pieza, porque una fuente vacía casi siempre deja el mayor rectángulo libre: con la carga sintética de 46 piezas, M5 usaba 16 planchas (13,7 % de aprovechamiento) frente a 4 de FF (54,9 %). Es la misma regla aplicada a WF en SPEC-TA-019 v2. La versión v1 de RN-01 queda reemplazada.

---

## 6. Flujo principal

1. `calculate_best_residual_fit()` prepara el problema inmutable con las piezas del pedido y el stock compatible.
2. `BestResidualFitOptimizer.optimize()` invoca `packing.pack()` inyectando `BestResidualFitSelector().select`.
3. Para cada unidad, el selector recorre los candidatos canónicos de cada fuente en el nivel activo (`RETAZO`, luego `PLANCHA`) y separa las fuentes en uso de las sin usar (v2).
4. Para las fuentes en uso se calcula el layout resultante y el rectángulo libre máximo.
5. Se elige el candidato óptimo entre las fuentes en uso; si ninguna es factible, se abre la fuente sin usar de menor `stock_rank` (RN-06). Se retorna `BestResidualFitResult`.

---

## 7. Criterios de aceptación

- **CA-01:** `BestResidualFitOptimizer().optimize(problem).method == "M5"`.
- **CA-02 (v2):** En presencia de múltiples fuentes en uso, el selector elige la que maximiza el retazo libre inscribible.
- **CA-03:** Ante igual área de retazo, el selector elige la que minimiza la merma fragmentada.
- **CA-04:** Comparte el componente de rotación a 5° (`RasterCache.iter_orientations`) sin lógica angular ad-hoc.
- **CA-05:** Respeta la prioridad `RETAZO` antes que `PLANCHA` (las planchas no se evalúan si hay retazos factibles).
- **CA-06:** La suite de pruebas `test_best_residual_fit.py` y `test_sp005_m5.py` pasa 100% en verde con 0 fallos.
- **CA-07:** Las pruebas unitarias no usan simulaciones sintéticas ni mocks para la geometría (`SimpleNamespace`); operan 100% sobre entidades de dominio reales (`PieceUnit`, `StockCandidate`, `SheetLayout`, `FeasibleCandidate`) cubriendo rectángulos, círculos y polígonos convexos.
- **CA-08 (v2):** M5 abre una fuente nueva (la sin usar de menor `stock_rank`) solo si la pieza no cabe en ninguna fuente en uso del nivel. Regresión: dos piezas 2×2 que caben en una plancha 4×2 usan una sola plancha (v1 usaba dos).

> Nota v2: `test_sp005_m5.py` ejercita el optimizador experimental del Spike SP-005 (`docs/spikes/sp-005-heuristica-m5/experimento_m5.py`), no el motor productivo; el cambio v2 no lo afecta y el experimento no se modifica.

---

## 8. Impacto técnico

- `backend/app/modules/optimization/domain/best_residual_fit.py` (nuevo)
- `backend/app/modules/optimization/application/best_residual_fit.py` (nuevo)
- `backend/app/modules/optimization/domain/problem.py` (actualizado con `"M5"`)
- `backend/app/modules/optimization/application/comparison.py` (actualizado con importación y `EXTENDED_METHODS`)
- `backend/tests/unit/optimization/test_best_residual_fit.py` (nuevo)
- v2: `domain/best_residual_fit.py` (selector con fuentes en uso), `test_best_residual_fit.py` y `test_engine_execution.py` (expectativa M5 de la primera fuente).

---

## Historial de estado

| Fecha | Versión | Estado | Cambio |
|---|---|---|---|
| 03/11/2026 | 1.0 | Implemented | Implementación inicial de M5 (TA-052 T01/T02). |
| 07/11/2026 | 2 | Reviewed (v2) | Observación del profesor en la revisión del 04/11/2026: M5 puntúa solo fuentes en uso dentro del nivel y abre una nueva (menor `stock_rank`) solo si la pieza no cabe en ninguna (RN-06). Cambian RN-01, flujo paso 3-5 y CA-02; se agrega CA-08. Retazos primero y desempates RN-02/RN-03 se conservan. Cambio hecho por Fabricio Aguilar en `fix/S2-cierre-observaciones`; se avisa al responsable (Luis Ibáñez) en el PR. |
| 07/11/2026 | 2 | Implemented (v2) | Regla v2 implementada en `domain/best_residual_fit.py` con prueba de regresión (falla con v1: `[1, 2] != [1, 1]`). Pasa a Verified después del merge, en un PR `docs/...` aparte. |
