# SPEC-TA-QA-009 — Seguridad Operacional del Corte

## Información general

| Campo | Valor |
|---|---|
| ID | TA-QA-009 |
| Tarea | Seguridad Operacional del Corte de Vidrio y Validación de Patrones Inválidos |
| Sprint | Sprint 2 |
| Prioridad / Tipo | Crítica / QA & Seguridad Operacional Industrial |
| Estado | Verified (Completado y Verificado al 100% contra Supabase) |
| Responsable | Luis Anthony Ibañez Herrera |
| Reviewer | Fabricio Melendez Quezada |
| Rama | `qa/TA-QA-009-seguridad-operacional-corte` |
| Base | `integration-02` |
| Fecha de inicio | 10/11/2026 |
| Dependencias | Dominio de Optimización (`placement.py`, `confirmation.py`), Dominio de Pedidos (`geometry.py`), Supabase Cloud PostgreSQL |
| Evidencia | `docs/evidence/sprint-02/TA-QA-009/README.md` y `Notion/TA-QA-009/Evidencia_Notion_TA-QA-009.docx` |

---

## 1. Objetivo

Asegurar la **integridad física de los operarios, de la maquinaria de corte (cabezales de diamante y mesas) y de los materiales de vidrio** mediante:
1. El diseño de casos de prueba rigurosos para **patrones de corte geométrica y operativamente inválidos**.
2. El registro formal de los **riesgos físicos y operacionales** asociados a la ejecución de cortes erróneos.
3. La verificación mediante pruebas automatizadas sobre el **backend real y base de datos PostgreSQL en Supabase** de que el **100% de los casos problemáticos son rechazados antes de su ejecución o confirmación**.
4. La elaboración de una **Matriz de Riesgos Operacionales** (Severidad × Probabilidad) acompañada de medidas preventivas tanto en software como en taller.

---

## 2. Alcance y Mandato Técnico

- **Alcance**: Evaluación integral de las capas de validación geométrica de pedidos (`orders/domain/geometry.py`), validación raster y colocación (`optimization/domain/placement.py`, `optimization/application/resource_policy.py`), integridad transaccional de confirmación de corte (`optimization/domain/confirmation.py`, `optimization/application/confirmation.py`) y endpoints REST reales de FastAPI (`/api/orders`, `/api/optimization`).
- **Mandato de conexiones reales**: Queda estrictamente prohibido simular respuestas de validación. Toda prueba se ejecuta directamente contra la lógica de dominio del backend real y la base de datos compartida en **Supabase Cloud**.

---

## 3. Reglas de Seguridad Operacional (RN-SEC)

| Regla | Título | Descripción Técnica y Justificación Física |
|---|---|---|
| **RN-SEC-01** | Tolerancia Cero a Superposiciones | Dos piezas jamás pueden compartir una misma celda raster (`SUPERPOSICION`). Evita el pasaje múltiple de la cuchilla de diamante y fractura destructiva. |
| **RN-SEC-02** | Protección de Margen Perimetral | Ninguna pieza puede posicionarse invadiendo el margen mínimo de seguridad al borde bruto del material (`MARGEN_INSUFICIENTE`). Previene grietas de borde por tensiones de recocido. |
| **RN-SEC-03** | Reserva Obligatoria de Kerf / Separación | Entre dos piezas vecinas debe respetarse estrictamente la separación mínima (`SEPARACION_INSUFICIENTE`). Evita el colapso de puentes estrechos durante el quiebre. |
| **RN-SEC-04** | Contención Absoluta en Material | Todas las celdas de una pieza deben quedar dentro del área útil (`FUERA_DE_LIMITE`). Evita que el cabezal corte al vacío o impacte contra la mesa. |
| **RN-SEC-05** | Prohibición de Geometrías No Convexas / Autointersecantes | Toda pieza o retazo poligonal debe ser estrictamente convexo y simple (`GeometryValidator`). Cortar vértices cóncavos sin línea de desahogo concentra tensiones que estallan el cristal. |
| **RN-SEC-06** | Integridad Atómica en Confirmación de Corte | No se permite confirmar patrones incompletos (`NOT_CONFIRMABLE`), re-confirmar trabajos (`ALREADY_CONFIRMED`), ni usar retazos duplicados (`REMNANT_COLLISION`). |
| **RN-SEC-07** | Validación Inmutable de Geometría Almacenada | Antes de descontar stock real en Supabase, `validate_stored_geometry` recalcula ángulos y máscaras para impedir alteraciones de patrón o coordenadas manipuladas. |
| **RN-SEC-08** | Control de Presupuesto Raster Anti-Bloqueo | Las piezas con vértices o escalas absurdas (`RasterBudgetExceeded`) deben ser rechazadas antes de agotar la memoria del servidor de optimización. |

---

## 4. Casos de Prueba para Patrones de Corte Inválidos

| ID Caso | Patrón Inválido Evaluado | Mecanismo de Inyección Real | Código de Rechazo Esperado |
|---|---|---|---|
| **CP-SEC-01** | Piezas superpuestas en coordenadas coincidentes | Colocación de dos máscaras sobre la misma región en `SheetLayout.place()` | `PlacementIssue.OVERLAP` (`SUPERPOSICION`) / `PlacementError` |
| **CP-SEC-02** | Pieza ubicada invadiendo el margen de seguridad al borde | Colocación en `(0, 0)` con `margin_mm > 0` configurado en layout real | `PlacementIssue.MARGIN` (`MARGEN_INSUFICIENTE`) / `PlacementError` |
| **CP-SEC-03** | Piezas adyacentes con distancia inferior a la separación/kerf | Colocación contigua a `d < separation_mm` respecto a pieza existente | `PlacementIssue.SEPARATION` (`SEPARACION_INSUFICIENTE`) |
| **CP-SEC-04** | Pieza cuyas dimensiones exceden el largo/ancho de la plancha | Pieza de 3500×2500 mm contra plancha estándar o colocación fuera de límites | `PlacementIssue.OUT_OF_BOUNDS` (`FUERA_DE_LIMITE`) |
| **CP-SEC-05** | Polígono cóncavo en forma de "L" o estrella y polígono autointersecante | Envío real vía `POST /api/orders` con vértices cóncavos/cruzados | `HTTP 422 Unprocessable Entity` (`El polígono no es convexo` / `se intersecta`) |
| **CP-SEC-06** | Confirmación de patrón alterado o solución incompleta | Inyección de `OptimizationResult` con unidades faltantes o contorno alterado | `ValueError` / `RunError("NOT_CONFIRMABLE")` |
| **CP-SEC-07** | Reutilización física duplicada de un mismo retazo único | Invocación de `consumption_groups` asignando el mismo `REMNANT` dos veces | `ValueError("A remnant is one physical unit.")` |
| **CP-SEC-08** | Explosión de rejilla raster (resolución ínfima o 200 vértices) | Solicitud a `RasterBudget.check()` / endpoint `/api/optimization/rasterize` | `RasterBudgetExceeded` / `HTTP 422` |

---

## 5. Criterios de Aceptación (CA)

- **CA-01**: Los 8 casos de prueba para patrones inválidos (**CP-SEC-01** a **CP-SEC-08**) deben estar automatizados y documentados.
- **CA-02**: El **100%** de los patrones problemáticos deben ser rechazados explícitamente sin persistir órdenes inválidas ni confirmar cortes corruptos en Supabase.
- **CA-03**: Debe registrarse formalmente el impacto y riesgo operacional físico/económico asociado a cada fallo de corte.
- **CA-04**: Debe generarse la **Matriz de Riesgos Operacionales** completa con severidad, probabilidad, barrera lógica en software y medida preventiva en planta.
- **CA-05**: La evidencia visual completa (capturas de terminal, código, base de datos y respuestas HTTP) debe compilarse en Word para Notion (`Evidencia_Notion_TA-QA-009.docx`) y publicarse mediante commits incrementales en GitHub.
