# SPEC-SP-005 — Heurística adicional M5 (Best Residual Fit)

Estado: Reviewed
PBI relacionado: SP-005 (T01)
Responsable: Ibañez Herrera Luis Anthony
Fecha: 01/11/2026
Versión: 1.0

---

## 1. Objetivo

Investigar, especificar, fundamentar técnicamente y experimentar una cuarta heurística de optimización de corte (**M5: Best Residual Fit - BRF**) compatible con el motor de corte rasterizado 2D de NewGlass. La heurística debe evaluarse en Google Colab y en el entorno local sobre los casos experimentales congelados (`EXP-SMALL-001`, `EXP-MEDIUM-001` y `EXP-COMPLEX-001`), bajo exactamente las mismas 20 reglas comunes y condiciones del baseline (`FF`, `BF`, `WF`), documentando sus ventajas, limitaciones y dejando resultados reproducibles antes de su incorporación al sistema productivo.

---

## 2. Alcance

### Incluye:
- **Fundamentación técnica de M5**: Definición matemática del criterio de selección basado en la maximización del retazo rectangular recuperable libre ($\text{largest\_rectangle}$) y la minimización de la merma fragmentada no recuperable.
- **Compatibilidad total con el motor rasterizado**: Operación directa sobre la función compartida `packing.pack()` de NewGlass mediante un selector desacoplado (`BestResidualFitSelector`).
- **Condiciones experimentales idénticas al baseline**:
  - Casos congelados: `EXP-SMALL-001`, `EXP-MEDIUM-001`, `EXP-COMPLEX-001` (definidos en TA-027).
  - Resolución raster: $1\text{ mm/píxel}$.
  - Granularidad angular: $5^\circ$ (72 orientaciones teóricas con deduplicación por huella digital de máscara).
  - Prioridad de stock: `RETAZO` antes que `PLANCHA` (política TA-020).
  - Margen y separación: $0\text{ mm}$ en caso pequeño, $1\text{ mm}$ en mediano y complejo.
  - Dimensiones residuales mínimas: $1 \times 1\text{ mm}$ para retazo recuperable.
- **Métricas estandarizadas**: Piezas colocadas/totales, planchas nuevas consumidas, utilización porcentual (%), merma no recuperable ($\text{mm}^2$), retazo recuperable ($\text{mm}^2$), tiempo de cómputo ($\text{ms}$) y memoria pico ($\text{KB}$).
- **Artefactos reproducibles**:
  - Cuaderno Google Colab interactivo y autocontenido (`SP_005_Heuristica_M5_Colab.ipynb`).
  - Script local reproducible (`experimento_m5.py`).
  - Resultados crudos en CSV y JSON.
  - Registro formal de evidencia técnica según la Sección 15 del Estándar de Ingeniería.

### Fuera de alcance:
- Integración al pipeline HTTP `/runs` o modificación del esquema de base de datos relacional (alcance de tareas posteriores de integración).
- Modificaciones en la interfaz visual frontend o streaming NDJSON (alcance de HU-017).
- Cambios en las 20 reglas comunes auditadas en SP-002 (la heurística no altera el rasterizado, la rotación ni la preparación).

---

## 3. Actor y precondiciones

- **Actor**: Desarrollador / Investigador de algoritmos de optimización de NewGlass.
- **Precondiciones**:
  - Instancias de prueba congeladas de TA-027 (`EXP-SMALL-001`, `EXP-MEDIUM-001`, `EXP-COMPLEX-001`) sin alteración.
  - Baseline de comparación (`FF`, `BF`, `WF`) disponible y verificado según TA-021.
  - Entorno de ejecución con Python 3.11 y Google Colab operativo.

---

## 4. Entradas / datos

Las entradas se consumen directamente desde los fixtures JSON de TA-027 mediante `loader.load_problem(case_id)`:

| Campo | Tipo / Unidad | Regla de validación |
|---|---|---|
| `case_id` | Cadena (`EXP-SMALL-001`, `EXP-MEDIUM-001`, `EXP-COMPLEX-001`) | Debe ser uno de los 3 casos congelados. |
| `resolution_mm` | Decimal / $\text{mm}$ | Exactamente $1\text{ mm}$. |
| `angular_step_deg` | Decimal / grados | Exactamente $5^\circ$. |
| `margin_mm` | Decimal / $\text{mm}$ | $0\text{ mm}$ (Small) / $1\text{ mm}$ (Medium y Complex). |
| `separation_mm` | Decimal / $\text{mm}$ | $0\text{ mm}$ (Small) / $1\text{ mm}$ (Medium y Complex). |
| `residual_limits` | Objeto (`minimum_width_mm`, `minimum_height_mm`) | $1 \times 1\text{ mm}$ en todos los casos. |
| `pieces` | Lista de geometrías (rectángulos, círculos, polígonos) | Snapshots inmutables de piezas con área calculada. |
| `stock` | Lista de candidatos (Retazos y Planchas) | Retazos con cantidad 1, planchas $1..N$. |

---

## 5. Reglas de negocio y algoritmo M5

- **RN-01 (Invarianza de las 20 reglas comunes)**: M5 debe compartir con FF, BF y WF todas las etapas de preparación, ordenamiento de piezas (área DESC, dimensión máxima DESC, ID pedido ASC, ID pieza ASC, índice unidad ASC), rotación a $5^\circ$, deduplicación de máscaras, y prioridad estricta `RETAZO` $\to$ `PLANCHA`.
- **RN-02 (Criterio de Selección M5 - Best Residual Fit)**:
  Dado el conjunto de candidatos factibles $\mathcal{C}$ producidos en el nivel de material activo:
  1. Para cada candidato $c \in \mathcal{C}$, se evalúa su layout resultante `c.layout_after`.
  2. Se obtiene el rectángulo libre máximo $\mathcal{R}(c) = (x, y, w, h)$ mediante el algoritmo de histograma `largest_rectangle()`.
  3. Si $w \ge W_{\min}$ y $h \ge H_{\min}$, el área del retazo recuperable es $A_{\text{rem}}(c) = w \cdot h$. En caso contrario, $A_{\text{rem}}(c) = 0$.
  4. Se calcula la merma residual fragmentada: $A_{\text{frag}}(c) = \text{FreeCells}(c) - A_{\text{rem}}(c)$.
  5. Se selecciona el candidato que minimice la tupla de ordenamiento:
     $$\text{score}(c) = \big( -A_{\text{rem}}(c), \; A_{\text{frag}}(c), \; c.\text{stock\_rank}, \; c.\text{orientation\_rank}, \; c.\text{row}, \; c.\text{column} \big)$$
- **RN-03 (Determinismo estricto)**: Dos ejecuciones sucesivas sobre la misma instancia deben generar exactamente los mismos placements, coordenadas, orientaciones y métricas.
- **RN-04 (Desempate canónico)**: Si dos ubicaciones dejan idéntico retazo recuperable y merma fragmentada, el desempate se resuelve por:
  1. `stock_rank` ASC (orden original del material en stock).
  2. `orientation_rank` ASC (primera orientación factible probada).
  3. `row` ASC (posición más superior).
  4. `column` ASC (posición más a la izquierda).

---

## 6. Flujo principal

1. Cargar el problema inmutable congelado desde su definición JSON mediante `loader.load_problem(case_id)`.
2. Instanciar el optimizador M5 (`BestResidualFitOptimizer`) con su selector de retazo residual.
3. Invocar el motor central `packing.pack(problem, select=BestResidualFitSelector().select)`.
4. El motor evalúa piezas en orden decreciente de área.
5. Para cada pieza, recorre los niveles de fuente (`RETAZO`, luego `PLANCHA`).
6. Si hay candidatos factibles en el nivel, `BestResidualFitSelector` calcula el área del retazo máximo post-colocación y selecciona el óptimo.
7. Se actualiza el layout inmutable del material seleccionado y se registra el `Placement`.
8. Al terminar todas las piezas, se computan las métricas oficiales con `calculate_metrics(result, **residual_limits)`.
9. Se registran tiempos de ejecución y memoria pico.
10. Se exportan los resultados a los formatos reproducibles estructurados (CSV y JSON).

---

## 7. Flujos alternativos y errores

- **FA-01 (Sin retazo recuperable disponible)**: Si una colocación no deja ningún rectángulo que supere los límites mínimos ($1 \times 1\text{ mm}$), $A_{\text{rem}}(c) = 0$. El selector pasa a desempatar por mínima merma fragmentada (equivalente a BF), asegurando robustez ante espacios reducidos.
- **FA-02 (Pieza no colocable)**: Si una unidad no cabe en ninguna lámina disponible, se añade a `unplaced_units` y el algoritmo continúa con la siguiente pieza sin interrumpir la ejecución ni alterar el estado de las láminas ya colocadas.
- **FA-03 (Límite de memoria de layout)**: Si la retención de layouts supera el presupuesto de $128\text{ MiB}$, se genera un `RasterPreparationError` defensivo según la regla del core de NewGlass.

---

## 8. Criterios de aceptación

- **CA-01 (Colocación completa en los 3 casos)**:
  - En `EXP-SMALL-001`, M5 coloca 3 de 3 piezas ($100\%$).
  - En `EXP-MEDIUM-001`, M5 coloca 9 de 9 piezas ($100\%$).
  - En `EXP-COMPLEX-001`, M5 coloca 24 de 24 piezas ($100\%$).
- **CA-02 (Condiciones operacionales idénticas)**:
  - Resolución de $1\text{ mm}$, paso angular de $5^\circ$, márgenes y separaciones idénticos al baseline en cada caso.
- **CA-03 (Mejora o paridad en métricas de retazo)**:
  - En `EXP-MEDIUM-001`, M5 genera $170\text{ mm}^2$ de retazo recuperable (superando los $150\text{ mm}^2$ de WF y los $66\text{ mm}^2$ de BF).
  - En `EXP-COMPLEX-001`, M5 genera $318\text{ mm}^2$ de retazo recuperable y reduce la merma no recuperable a $836.72\text{ mm}^2$ frente a los $886.72\text{ mm}^2$ de WF.
- **CA-04 (Determinismo y reproducibilidad)**:
  - Múltiples ejecuciones del experimento en local o en Google Colab producen idénticos hashes y métricas numéricas.
- **CA-05 (Cumplimiento de límites de recursos)**:
  - El tiempo de cómputo de M5 en `EXP-COMPLEX-001` no excede los $2000\text{ ms}$ y la memoria pico se mantiene por debajo de $5\text{ MB}$.
- **CA-06 (Artefactos de investigación completos)**:
  - Existen el informe técnico (`SP-005-informe-investigacion-m5.md`), el cuaderno interactivo (`SP_005_Heuristica_M5_Colab.ipynb`), el script ejecutable (`experimento_m5.py`), los resultados crudos (`resultados_baseline_vs_m5.csv`, `resumen_comparativo.json`) y la evidencia documentada.

---

## 9. Impacto técnico

- **Módulos backend involucrados**: `domain/packing.py`, `domain/metrics.py`, `application/comparison.py`.
- **API**: Ninguna modificación en este Spike (investigación pura antes de integración).
- **BD / Migraciones**: Ninguna modificación de esquema requerida.
- **UI**: Ningún impacto directo. Los resultados quedan listos para conectarse con la visualización de HU-017 en fases posteriores.

---

## 10. Pruebas previstas

1. **Prueba de sanidad y equivalencia**: Ejecutar M5 sobre los casos congelados validando que `OptimizationResult.complete` sea verdadero y que `calculate_metrics()` no lance excepciones geométricas.
2. **Prueba de determinismo**: Repetir la ejecución 5 veces en orden normal e inverso y comprobar igualdad exacta de placements.
3. **Prueba de aislamiento de memoria**: Verificar con `tracemalloc` que la memoria pico permanezca en rangos seguros.

---

## 11. Evidencias requeridas

- Tabla comparativa consolidada en formato CSV (`resultados_baseline_vs_m5.csv`).
- Detalle de ejecución en formato JSON estructurado (`resumen_comparativo.json`).
- Cuaderno Google Colab autoejecutable (`SP_005_Heuristica_M5_Colab.ipynb`).
- Informe de investigación con gráficos y conclusiones de trade-offs (`SP-005-informe-investigacion-m5.md`).
- Documento de evidencia formal en `docs/evidence/sprint-02/SP-005/README.md`.

---

## 12. Decisiones y notas

- **Decisión D-01**: Se adopta **Best Residual Fit (BRF)** como la heurística M5 debido a su alineación directa con el modelo de negocio de NewGlass: en la industria del vidrio, maximizar el tamaño del retazo restante permite reingresarlo al inventario y reutilizarlo en pedidos futuros, reduciendo el costo real de material desperdiciado.
- **Decisión D-02**: El método validado en este Spike y en Google Colab será exactamente el implementado en la siguiente tarea técnica del sistema, garantizando la trazabilidad exigida por el estándar.
