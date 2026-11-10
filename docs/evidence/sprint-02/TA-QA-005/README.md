# Informe de Evidencia — TA-QA-005: Usabilidad y Accesibilidad

## 1. Información General y Alcance
- **Tarea**: `TA-QA-005 — Usabilidad y accesibilidad`
- **Módulos evaluados**: Pedidos, Inventario y Optimización.
- **Responsable**: Luis Anthony Ibañez Herrera (QA Engineer)
- **Metodología**: Spec-Driven Development (SDD)
- **Especificaciones**:
  - [`SPEC-TA-QA-005`](../../../specs/SPEC-TA-QA-005-usabilidad-accesibilidad.md)
  - [`PLAN-TA-QA-005`](../../../specs/PLAN-TA-QA-005-usabilidad-accesibilidad.md)
  - [`TASKS-TA-QA-005`](../../../specs/TASKS-TA-QA-005-usabilidad-accesibilidad.md)
- **Mandato estricto**: Ejecución con conexiones 100% REALES (PostgreSQL Supabase en la nube + backend FastAPI + React 19). Cero mocks ni APIs simuladas.

---

## 2. Entorno de Ejecución y Condiciones de Prueba
| Parámetro | Detalle Técnico |
|---|---|
| **Sistema Operativo** | Windows 11 Pro 64-bit |
| **Base de Datos** | PostgreSQL 15 en Supabase Cloud (`aws-0-us-east-1.pooler.supabase.com:5432/postgres`) |
| **Backend** | FastAPI 1.0.0, Python 3.11.9, SQLAlchemy 2.0.40, Psycopg 3 |
| **Frontend** | React 19.2.8, Vite 8.3.1, Lucide React 1.48.0 |
| **Motor de Automatización** | Microsoft Edge Chromium 157.0 vía Playwright 1.63.0 |
| **Usuario de Prueba** | `A74000010` (Administrador real en Supabase, ID 5) |
| **Viewport Desktop** | 1440 × 900 px |
| **Viewport Móvil** | 375 × 667 px (iPhone SE, estándar WCAG 2.1) y 390 × 844 px |

---

## 3. Escenarios Ejecutados y Resultados de Usabilidad

### 3.1 Módulo Pedidos
- **T-PED-01: Autocompletado accesible de cliente**: Búsqueda reactiva mediante teclado ingresando "Kispe" (cliente real en Supabase) y confirmación con tecla `Enter`. Tiempo de respuesta: **4.85 s**. Errores: **0**. Completitud: **100%**.
- **T-PED-02: Creación de polígono convexo y validación de convexidad**: Configuración por teclado de un polígono de 3 lados (300, 400 y 500 mm). El algoritmo matemático validó en tiempo real la convexidad (`✓ Figura configurada`). Tiempo: **0.51 s**. Errores: **0**.
- **T-PED-03: Envío de pedido por teclado y confirmación**: Inserción de piezas y envío con `Enter`. La petición `POST /api/orders` retornó **HTTP 201 Created** en Supabase, mostrando el mensaje de feedback accesible `Pedido registrado correctamente`. Tiempo: **1.53 s**. Errores: **0**.

### 3.2 Módulo Inventario
- **T-INV-01: Filtrado de existencias**: Filtrado por tipo de vidrio y espesor con actualización reactiva de la tabla de stock y región `aria-live`. Tiempo: **2.82 s**. Errores: **0**.
- **T-INV-02: Modal de registro de plancha**: Despliegue de `RegistrarPlanchaForm`, navegación secuencial con `Tab` y comprobación de que el foco permanece retenido sin fugarse al cuerpo del documento. Cancelación y restauración de foco verificadas. Tiempo: **0.03 s**. Errores: **0**.
- **T-INV-03: Diálogo de baja (`WriteoffDialog`)**: Apertura de modal de baja, selección de motivos (Rotura, Merma) y cierre instantáneo con tecla `Escape`, con restauración automática del foco al botón disparador original. Tiempo: **0.04 s**. Errores: **0**.

### 3.3 Módulo Optimización
- **T-OPT-01: Inspección de espacio de trabajo**: Visualización de pedidos en estado `PENDIENTE` en Supabase, agrupación por material y revisión de piezas. Tiempo: **1.04 s**. Errores: **0**.
- **T-OPT-02: Métodos de corte y confirmación**: Navegación accesible entre métodos de ajuste y auditoría del diálogo de confirmación con salvaguarda de corte. Tiempo: **0.00 s**. Errores: **0**.

### 3.4 Responsividad Móvil (375 px)
- **T-MOB-01: Responsividad en Viewport de 375 px**: Evaluación mediante script en tiempo de ejecución: `document.documentElement.scrollWidth` = 375 px, `window.innerWidth` = 375 px. Desbordamiento horizontal: **0 px** (`hasOverflow: false`). La tabla de pedidos utiliza `.orders-management-table-wrap` con scroll horizontal encapsulado, preservando íntegra la navegación móvil. Tiempo: **1.39 s**. Errores: **0**.

---

## 4. Tabla Consolidada de Métricas Cuantitativas

| ID Tarea | Módulo | Tarea Evaluada | Tiempo $T$ | Errores $E$ | Completitud $C\%$ | Foco OK |
|---|---|---|---|---|---|---|
| **T-PED-01** | Pedidos | Selección de cliente mediante autocompletado accesible | 4.85 s | 0 | 100% | PASS |
| **T-PED-02** | Pedidos | Creación de polígono convexo con validación en tiempo real | 0.51 s | 0 | 100% | PASS |
| **T-PED-03** | Pedidos | Envío de pedido exclusivo por teclado (HTTP 201) | 1.53 s | 0 | 100% | PASS |
| **T-INV-01** | Inventario | Filtrado dinámico de existencias por tipo y espesor | 2.82 s | 0 | 100% | PASS |
| **T-INV-02** | Inventario | Navegación secuencial por teclado en registro de plancha | 0.03 s | 0 | 100% | PASS |
| **T-INV-03** | Inventario | Diálogo modal de baja, escape y restauración de foco | 0.04 s | 0 | 100% | PASS |
| **T-OPT-01** | Optimización | Inspección de disposición de piezas y tablero de corte | 1.04 s | 0 | 100% | PASS |
| **T-OPT-02** | Optimización | Selección de métodos y confirmación de corte seguro | 0.00 s | 0 | 100% | PASS |
| **T-MOB-01** | Móvil | Adaptabilidad a 375 px sin desbordamiento horizontal | 1.39 s | 0 | 100% | PASS |

**Resumen Global**:
- **Tasa de Completitud de Tareas ($C\%$)**: **100%** (9 de 9 tareas completadas exitosamente)
- **Tasa de Error ($E$)**: **0.0%** (0 fallas durante la interacción)
- **Cumplimiento de Teclado (WCAG 2.1 - 2.1.1)**: **100%**
- **Contención y Restauración de Foco (WCAG 2.1 - 2.4.3)**: **PASS**
- **Desbordamiento Horizontal a 375 px (WCAG 2.1 - 1.4.10)**: **0 px (PASS)**

---

## 5. Matriz de Hallazgos y Propuestas de Mejora

| ID | Módulo | Severidad | Fricción / Barrera Identificada | Propuesta Concreta de Mejora de Ingeniería |
|---|---|---|---|---|
| **OBS-01** | Pedidos | Media | La lista desplegable de clientes en el autocompletado no tiene `aria-expanded` dinámico en el input de búsqueda. | Incorporar `aria-expanded={isOpen}` y `aria-controls="client-suggestions"` en el input para anunciar el estado del menú desplegable a lectores de pantalla (NVDA/JAWS). |
| **OBS-02** | Inventario | Baja | Las alertas de éxito (`FeedbackMessage`) no ofrecen un mecanismo explícito de descarte por teclado antes del refresco. | Agregar botón de cierre `(X)` con soporte de `Escape` y timeout automático de 6 segundos en `FeedbackMessage`. |
| **OBS-03** | Optimización | Media | El checkbox "Seleccionar todos" en pedidos pendientes no expone estado indeterminado visual en accesibilidad. | Vincular la propiedad de DOM `input.indeterminate = isPartial` y el atributo `aria-checked="mixed"` cuando la selección de pedidos sea parcial. |
| **OBS-04** | Móvil | Baja | Los botones de acción en filas de tablas tienen un área táctil de 36 × 36 px en pantallas ultra compactas. | Fijar un área mínima de contacto táctil de 44 × 44 px (`min-width: 44px; min-height: 44px`) cumpliendo holgadamente el criterio WCAG 2.1 - 2.5.5. |

---

## 6. Documentación para Notion y Entregables
- **Documento Word compilado**: [`Evidencia_Notion_TA-QA-005.docx`](../../../../Notion/TA-QA-005/Evidencia_Notion_TA-QA-005.docx)
- **Galería de capturas PNG**: `Notion/TA-QA-005/img/` (14 capturas de alta resolución cubriendo desde la creación de rama hasta la auditoría móvil a 375 px).
- **Métricas en bruto**: `Notion/TA-QA-005/metrics_summary.json`
- **Script de prueba automatizado**: `frontend/scripts/run_ta_qa_005_real.mjs`
