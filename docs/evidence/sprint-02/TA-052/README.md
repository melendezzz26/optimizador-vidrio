# Evidencia TA-052 — Implementar heurística M5 en el sistema

**PBI / Tarea:** TA-052 (T01 — Implementar M5 / T02 — Crear pruebas de M5)
**Responsable:** Equipo NewGlass (Taller Integrador II)
**Fecha:** 03/11/2026
**Entorno:** Local (Windows 11 / Python 3.11.1)
**Base:** `integration/sprint-01` tras merge del Spike SP-005 (PR #93)

---

## 1. Entrada y configuración

- **Componente implementado:** Heurística de selección M5 (Best Residual Fit / BRF).
- **Módulos backend creados:**
  - `backend/app/modules/optimization/domain/best_residual_fit.py`
  - `backend/app/modules/optimization/application/best_residual_fit.py`
  - `backend/app/modules/optimization/domain/problem.py` (adición de `"M5"`)
  - `backend/app/modules/optimization/application/comparison.py` (exportación de `BestResidualFitOptimizer`)
- **Suite de pruebas:**
  - `backend/tests/unit/optimization/test_best_residual_fit.py`
  - `backend/tests/unit/optimization/test_sp005_m5.py`

---

## 2. Procedimiento de verificación

Desde el directorio `backend`:
```powershell
python -m pytest tests/unit/optimization/test_best_residual_fit.py tests/unit/optimization/test_sp005_m5.py -q -ra
```

---

## 3. Resultado esperado vs. resultado obtenido

### 3.1 Contratos de dominio y selección M5
- **Esperado:** `BestResidualFitSelector` selecciona la fuente que maximiza el área del mayor rectángulo libre inscribible (`largest_rectangle`), desempata por mínima merma fragmentada y aplica el orden determinista canónico `(stock_rank, orientation_rank, row, column)`. **Las pruebas operan 100% sobre geometría y dominio reales (sin objetos simulados, sin mocks ni `SimpleNamespace`), cubriendo rectángulos, círculos y polígonos convexos**.
- **Obtenido:** 29 pruebas unitarias y de integración sobre entidades reales pasan satisfactoriamente. **PASS**.

### 3.2 Contrato de resultado
- **Esperado:** `OptimizationResult.method == "M5"`, preservando el valor tras `calculate_metrics()`.
- **Obtenido:** Verificado en `test_normal_chooses_largest_residual_source_and_keeps_m5_method`. **PASS**.

### 3.3 Reglas comunes de NewGlass y geometría real
- **Esperado:**
  - Paso angular de $5^\circ$ con componente compartido `RasterCache.iter_orientations`.
  - Prioridad estricta `RETAZO` $\to$ `PLANCHA`.
  - Inmutabilidad de inventario durante simulación.
  - Gestión segura de piezas no colocables y multi-material real sin mezclar grupos incompatibles.
  - Soporte de formas reales: `RECTANGULO`, `CIRCUNFERENCIA`, `POLIGONO_CONVEXO`.
- **Obtenido:** Verificado en pruebas unitarias con geometrías reales. **PASS**.

---

## 4. Registro de ejecución de pruebas

```text
============================= test session starts =============================
platform win32 -- Python 3.11.1, pytest-8.3.4, pluggy-1.5.0
rootdir: C:\Users\liban\Desktop\rework-vidrio\optimizador-vidrio\backend
configfile: pyproject.toml
collected 29 items

tests/unit/optimization/test_best_residual_fit.py ..................     [ 62%]
tests/unit/optimization/test_sp005_m5.py ...........                     [100%]

============================== 29 passed in 1.34s ==============================
```

---

## 5. Conclusión técnica

La implementación de M5 (Best Residual Fit) en el backend productivo satisface plenamente los criterios de aceptación de la SPEC-TA-052. El código respeta la arquitectura hexagonal del módulo de optimización, no introduce efectos colaterales sobre inventario, sus pruebas están 100% fundamentadas en el dominio geométrico real sin simulaciones sintéticas ni mocks, y queda disponible para su consumo por el servicio de comparación y los clientes del sistema.
