# Informe de Evidencia — TA-QA-009: Seguridad Operacional del Corte

## 1. Información General y Alcance
- **Tarea**: `TA-QA-009 — Seguridad operacional del corte`
- **Responsable**: Luis Anthony Ibañez Herrera (QA Engineer)
- **Metodología**: Spec-Driven Development (SDD)
- **Especificaciones asociadas**:
  - [`SPEC-TA-QA-009`](../../../specs/SPEC-TA-QA-009-seguridad-operacional-corte.md)
  - [`PLAN-TA-QA-009`](../../../specs/PLAN-TA-QA-009-seguridad-operacional-corte.md)
  - [`TASKS-TA-QA-009`](../../../specs/TASKS-TA-QA-009-seguridad-operacional-corte.md)
  - [`RISK-MATRIX-TA-QA-009`](../../../specs/RISK-MATRIX-TA-QA-009.md)
- **Mandato de conexiones reales**: Ejecución verificada con FastAPI, dominio de optimización y pedidos real y clúster PostgreSQL en **Supabase Cloud**.

---

## 2. Entorno Real Utilizado en la Evaluación
- **Autenticación**: Cuenta real de Administrador `A74000010` (`/api/auth/login`, HTTP 200 OK).
- **Plancha real extraída de Supabase**: ID `#8` (`2240.00 × 3300.00 mm`, espesor `5.5 mm`, stock activo).
- **Cliente real extraído de Supabase**: ID `#1` (`Kispe`).
- **Script ejecutor**: [`backend/scripts/test_ta_qa_009_safety.py`](../../../../backend/scripts/test_ta_qa_009_safety.py).
- **Resultados guardados**: [`backend/scripts/results_ta_qa_009.json`](../../../../backend/scripts/results_ta_qa_009.json).

---

## 3. Resultados de Verificación de Rechazo de Patrones Inválidos

| ID Caso | Riesgo Asociado | Patrón Problemático Inyectado | Mecanismo de Rechazo Verificado | Estado |
|---|---|---|---|---|
| **CP-SEC-01** | **R-01** Colisión de cuchilla / doble rayado | Dos piezas superpuestas en coordenadas coincidentes sobre plancha real #8 | `PlacementIssue.OVERLAP` (`SUPERPOSICION`) + `PlacementError` | **RECHAZADO (PASS)** |
| **CP-SEC-02** | **R-02** Desportillamiento perimetral por tensión | Pieza ubicada en `(0, 0)` invadiendo margen de `15.0 mm` | `PlacementIssue.MARGIN` (`MARGEN_INSUFICIENTE`) + `PlacementError` | **RECHAZADO (PASS)** |
| **CP-SEC-03** | **R-03** Colapso de puente intermedio y astillamiento | Segunda pieza colocada invadiendo separación/kerf de `10.0 mm` | `PlacementIssue.SEPARATION` (`SEPARACION_INSUFICIENTE`) + `PlacementError` | **RECHAZADO (PASS)** |
| **CP-SEC-04** | **R-04** Corte al vacío e impacto contra mesa CNC | Pieza de `2740 × 3800 mm` excediendo plancha real #8 (`2240 × 3300 mm`) | `PlacementIssue.OUT_OF_BOUNDS` (`FUERA_DE_LIMITE`) + `PlacementError` | **RECHAZADO (PASS)** |
| **CP-SEC-05** | **R-05** Estallido incontrolado en vértices cóncavos | Petición real `POST /api/orders` con polígono en "L" cóncavo y reloj de arena autointersecante | `HTTP 422 Unprocessable Entity` (*El polígono no es convexo / se intersecta a sí mismo*) | **RECHAZADO (PASS)** |
| **CP-SEC-06** | **R-06** Corte incompleto / mezcla de espesor incompatible | Resultado sin todas las piezas colocadas y mezcla de espesor `5.5 mm` vs `7.5 mm` | `ValueError` (`Confirmation requires every requested unit placed` / `incompatible materials`) | **RECHAZADO (PASS)** |
| **CP-SEC-07** | **R-07** Doble corte sobre retazo único agotado | Asignación de retazo físico único con `physical_unit_index = 2` | `ValueError` (`A remnant represents exactly one physical unit`) | **RECHAZADO (PASS)** |
| **CP-SEC-08** | **R-09** Agotamiento de memoria / congelamiento en turno | Geometría de `3000 × 3000 mm` a resolución de `0.5 mm` (36M celdas > límite 1M) | `RasterBudgetExceeded` (`HTTP 422`, límite seguro de rasterización) | **RECHAZADO (PASS)** |

**Métricas de Seguridad Operacional**:
- **Total de casos inválidos inyectados**: **8**
- **Casos rechazados preventivamente**: **8**
- **Fugas de seguridad operacional**: **0**
- **Tasa de Rechazo Seguro**: **100.0%**

---

## 4. Síntesis de Matriz de Riesgos y Medidas Preventivas
El análisis completo (Matriz 4×4 de Severidad × Probabilidad, impacto mecánico/humano y protocolos de EPP en planta) se encuentra formalizado en [`RISK-MATRIX-TA-QA-009.md`](../../../specs/RISK-MATRIX-TA-QA-009.md). Destacan:
- **Riesgos de Nivel ALTO (12)**: Superposición (`R-01`), invasión de margen (`R-02`), puente inferior al kerf (`R-03`) y ángulos cóncavos (`R-05`). Todos bloqueados por software antes del corte y mitigados físicamente mediante uso obligatorio de gafas ANSI Z87.1+, guantes nivel A5, petos anticorte, saneamiento de bordes y perforaciones de alivio.
- **Riesgos de Nivel MEDIO-ALTO / MEDIO (6–9)**: Piezas fuera de límites (`R-04`), retazos frágiles $< 100\text{ mm}$ (`R-08`), doble consumo de retazos (`R-07`) y órdenes incompletas (`R-06`).

---

## 5. Documentación Visual para Notion y Entregables
- **Documento Word completo**: [`Notion/TA-QA-009/Evidencia_Notion_TA-QA-009.docx`](../../../../Notion/TA-QA-009/Evidencia_Notion_TA-QA-009.docx)
- **Galería de capturas PNG**: `Notion/TA-QA-009/img/`
- **Resultados JSON en bruto**: `Notion/TA-QA-009/safety_results.json`
