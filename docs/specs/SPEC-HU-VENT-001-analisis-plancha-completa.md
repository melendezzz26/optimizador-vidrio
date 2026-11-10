# SPEC-HU-VENT-001 — Análisis de Venta por Plancha Completa (v2)

## Información general

| Campo | Valor |
|---|---|
| ID | HU-VENT-001 |
| Historia / Tarea | Análisis de venta por plancha completa |
| Sprint | Sprint 2 |
| Prioridad / Tipo | Media / Análisis Funcional, Comercial y Arquitectónico (v2) |
| Estado | Verified (Análisis Completado y Recomendación Emitida para v2) |
| Responsable | Luis Anthony Ibañez Herrera |
| Reviewer | Fabricio Melendez Quezada |
| Rama | `docs/HU-VENT-001-analisis-plancha-completa` |
| Base | `integration-02` en commit `b964b2b` |
| Fecha de inicio | 10/11/2026 |
| Dependencias | Inspección del modelo real (`backend/app/models.py`), RBAC (`backend/app/core/permissions.py`), módulos Orders, Inventory y Optimization |
| Entregable | [`docs/evidence/sprint-02/HU-VENT-001/README.md`](../evidence/sprint-02/HU-VENT-001/README.md) y `Notion/HU-VENT-001/Evidencia_Notion_HU-VENT-001.docx` |

---

## 1. Propósito y Restricción de Alcance

El presente documento define el marco de análisis para evaluar la viabilidad técnica, operativa y comercial de incorporar la **venta directa por plancha completa** en una futura **versión 2 (v2)** del sistema **NewGlass**.

> **Restricción crítica de alcance (RN-ALC-01):** Esta historia es **estrictamente de análisis arquitectónico y de negocio**. **No se debe implementar** código productivo de backend, migraciones SQL, endpoints ni componentes frontend de un módulo de ventas durante el Sprint 2.

---

## 2. Requerimientos de Análisis (Objetivos de Cumplimiento)

| Código | Requerimiento | Criterio de Cumplimiento |
|---|---|---|
| **REQ-01** | **Diferencias operativas y comerciales** | Contrastar de forma explícita y estructurada la venta de piezas cortadas a medida frente a la venta de plancha comercial completa (unidad de venta, proceso en taller, geometría, merma, tiempos y esquema de precios). |
| **REQ-02** | **Propiedad y ciclo de vida de sobrantes** | Determinar quién conserva los excedentes (`retazos`) y asume la merma (`merma_mm2`) en cada modalidad y cómo impacta el stock físico. |
| **REQ-03** | **Impacto técnico por módulo** | Auditar el código y esquema PostgreSQL vigente para enumerar los cambios exactos necesarios en **Pedidos**, **Inventario**, **Optimización** y **Seguridad/RBAC**. |
| **REQ-04** | **Recomendación estratégica fundamentada** | Emitir un veredicto claro (**Incorporar**, **Postergar** o **Descartar**) respaldado en análisis riesgo/beneficio para la toma de decisión del equipo. |

---

## 3. Reglas de Análisis Base (RN-ANA)

- **RN-ANA-01 (Trazabilidad al código real):** Todo impacto identificado debe referenciar tablas, restricciones `CHECK`, permisos RBAC o archivos reales verificados en `backend/app/` y `frontend/src/`.
- **RN-ANA-02 (Datos reales de stock):** Los ejemplos numéricos y escenarios de formato comercial deben respaldarse en lotes vigentes consultados desde la base real de NewGlass en Supabase.
- **RN-ANA-03 (Separación de ramas):** Esta rama aloja exclusivamente el análisis comercial y técnico de `HU-VENT-001`, sin duplicar ni alterar las evidencias de `TA-QA-002`, `TA-QA-005` ni `TA-QA-009`.
