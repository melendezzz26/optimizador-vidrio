# SPEC-TA-052 — Implementar heurística M5 (Best Residual Fit) en el sistema

Estado: Implemented
PBI relacionado: TA-052 (T01 y T02)
Responsable: Equipo NewGlass (Taller Integrador II)
Fecha: 03/11/2026
Versión: 1.0

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
  - `application/comparison.py`: Exportación e integración de `BestResidualFitOptimizer` y `EXTENDED_METHODS`.
- **T02 — Crear pruebas de M5:**
  - `tests/unit/optimization/test_best_residual_fit.py`: Cobertura exhaustiva de selección normal, desempate lexicográfico completo, rotación canónica a 5°, no colocables, prioridad de retazos, inmutabilidad y pruebas de aplicación.
  - Validación de compatibilidad con las pruebas existentes en `tests/unit/optimization/test_sp005_m5.py`.
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

- **RN-01 (Criterio de Selección M5):** Selecciona el candidato factible que maximiza el área del mayor rectángulo inscribible (`largest_rectangle`) del layout post-colocación.
- **RN-02 (Desempate por merma fragmentada):** En caso de empate en el área del retazo recuperable, minimiza las celdas libres no aprovechables (`fragmented_cells = free_cells - remnant_cells`).
- **RN-03 (Desempate determinista estable):** En caso de empate en merma, desempata estrictamente por `(stock_rank, orientation_rank, row, column)` en orden ascendente.
- **RN-04 (Identidad del método):** `OptimizationResult.method` devuelve `"M5"`.
- **RN-05 (Inmutabilidad de inventario):** La simulación no consume stock, no bloquea láminas en BD y no tiene efectos colaterales.

---

## 6. Flujo principal

1. `calculate_best_residual_fit()` prepara el problema inmutable con las piezas del pedido y el stock compatible.
2. `BestResidualFitOptimizer.optimize()` invoca `packing.pack()` inyectando `BestResidualFitSelector().select`.
3. Para cada unidad, el selector evalúa los candidatos canónicos de cada fuente en el nivel activo (`RETAZO`, luego `PLANCHA`).
4. Se calcula el layout resultante y el rectángulo libre máximo.
5. Se elige el candidato óptimo y se retorna `BestResidualFitResult`.

---

## 7. Criterios de aceptación

- **CA-01:** `BestResidualFitOptimizer().optimize(problem).method == "M5"`.
- **CA-02:** En presencia de múltiples fuentes, el selector elige la que maximiza el retazo libre inscribible.
- **CA-03:** Ante igual área de retazo, el selector elige la que minimiza la merma fragmentada.
- **CA-04:** Comparte el componente de rotación a 5° (`RasterCache.iter_orientations`) sin lógica angular ad-hoc.
- **CA-05:** Respeta la prioridad `RETAZO` antes que `PLANCHA` (las planchas no se evalúan si hay retazos factibles).
- **CA-06:** La suite de pruebas `test_best_residual_fit.py` y `test_sp005_m5.py` pasa 100% en verde con 0 fallos.
- **CA-07:** Las pruebas unitarias no usan simulaciones sintéticas ni mocks para la geometría (`SimpleNamespace`); operan 100% sobre entidades de dominio reales (`PieceUnit`, `StockCandidate`, `SheetLayout`, `FeasibleCandidate`) cubriendo rectángulos, círculos y polígonos convexos.

---

## 8. Impacto técnico

- `backend/app/modules/optimization/domain/best_residual_fit.py` (nuevo)
- `backend/app/modules/optimization/application/best_residual_fit.py` (nuevo)
- `backend/app/modules/optimization/domain/problem.py` (actualizado con `"M5"`)
- `backend/app/modules/optimization/application/comparison.py` (actualizado con importación y `EXTENDED_METHODS`)
- `backend/tests/unit/optimization/test_best_residual_fit.py` (nuevo)
