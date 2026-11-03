# Evidencia TA-052 — Implementar heurística M5 en el sistema

**PBI / Tarea:** TA-052 (T01 — Implementar M5 / T02 — Crear pruebas de M5)
**Autor:** Luis Anthony Ibáñez Herrera
**Revisor esperado:** Andro Joseph Quispe Cesias (aprobación formal pendiente)
**Fecha:** 03/11/2026
**Entorno:** Local (Windows 11 / Python 3.11.1)
**Base:** `integration/sprint-01` tras merge del Spike SP-005 (PR #93)

---

## 1. Entrada y configuración

- **Componente implementado:** Heurística de selección M5 (Best Residual Fit / BRF).
- **Módulos backend creados o modificados:**
  - `backend/app/modules/optimization/domain/best_residual_fit.py`
  - `backend/app/modules/optimization/application/best_residual_fit.py`
  - `backend/app/modules/optimization/domain/problem.py` (adición de `"M5"`)
  - `backend/app/modules/optimization/application/comparison.py` (lista opcional `EXTENDED_METHODS`; `DEFAULT_METHODS` sigue con FF/BF/WF)
- **Suite de pruebas:**
  - `backend/tests/unit/optimization/test_best_residual_fit.py`
  - `backend/tests/unit/optimization/test_sp005_m5.py`

---

## 2. Procedimiento de verificación

Desde el directorio `backend`:
```powershell
python -m pytest tests/unit/optimization/test_best_residual_fit.py -q -ra
python -m pytest tests/unit/optimization/test_best_residual_fit.py tests/unit/optimization/test_sp005_m5.py -q -ra
```

La primera suite ejercita directamente el motor productivo M5: **18 passed, 0 failed, 0 skipped**. La selección conjunta: **29 passed, 0 failed, 0 skipped**. De ellas, 18 son productivas directas y 11 son heredadas de SP-005; estas últimas todavía importan el optimizador experimental del Spike. Los conteos son selecciones solapadas, no se suman.

---

## 3. Resultado esperado vs. resultado obtenido

### 3.1 Contratos de dominio y selección M5
- **Esperado:** `BestResidualFitSelector` selecciona la fuente que maximiza el área del mayor rectángulo libre inscribible (`largest_rectangle`), desempata por mínima merma fragmentada y aplica el orden determinista canónico `(stock_rank, orientation_rank, row, column)`. Los casos geométricos usan entidades reales y cubren rectángulos, círculos y polígonos convexos.
- **Obtenido:** 18 pruebas productivas directas y 11 heredadas del Spike pasan en la selección conjunta de 29. Las heredadas prueban componentes experimentales, no el motor productivo de TA-052. **PASS**.

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
configfile: pyproject.toml
collected 29 items

tests/unit/optimization/test_best_residual_fit.py ..................     [ 62%]
tests/unit/optimization/test_sp005_m5.py ...........                     [100%]

============================== 29 passed in 1.34s ==============================
```

La revisión posterior sobre el merge de prueba de GitHub confirmó 18/18 pruebas productivas y 29/29 en la selección conjunta. También pasaron las regresiones portables: FF/BF/WF y prioridad 102, M4 43, auditoría M4 7, placement/raster 143, geometría/rotación 78, reglas/métricas 36, TA-027 23 y comparación portable 80. Son selecciones distintas y no se presentan como un total aditivo.

Una ejecución local en Windows que incluyó `test_comparison_runner.py` obtuvo **84 passed, 10 failed**: los diez casos fallidos requieren Linux con `procfs` y límites de recursos. Este resultado se conserva como limitación del entorno Windows, no como regresión M5; el check backend del PR pasó en CI Linux. Frontend y e2e también pasaron en CI.

---

## 5. Conclusión técnica

La implementación de M5 (Best Residual Fit) en el backend usa el motor y el raster oficiales, conserva la semántica de SP-005 y no consume inventario en la simulación. Puede ejecutarse por su entrada de aplicación o mediante la lista opcional `EXTENDED_METHODS`. No forma parte del flujo multimétodo público por defecto: `DEFAULT_METHODS` continúa con FF/BF/WF. M5 queda lista para ser registrada posteriormente en el coordinador multimétodo mediante TA-043. La decisión experimental de SP-005 sigue siendo **GO CONDICIONADO**.
