# PLAN-TA-QA-009 — Plan de Pruebas de Seguridad Operacional del Corte

## 1. Arquitectura de Evaluación (Sin Mocks ni APIs Simuladas)

La verificación se ejecuta sobre dos planos integrados y conectados a infraestructura real:
1. **Plano de Dominio y Reglas Físicas** (`backend/app/modules/optimization/domain/` y `backend/app/modules/orders/domain/`):
   - Validación directa contra `SheetLayout` (`placement.py`), `GeometryValidator` (`geometry.py`), `RasterBudget` (`resource_policy.py`) y `consumption_groups` / `validate_stored_geometry` (`confirmation.py`).
2. **Plano de Persistencia e Integración HTTP Real** (FastAPI `TestClient` / HTTP real + **PostgreSQL Supabase Cloud**):
   - Obtención de credenciales y roles reales (`A74000010`) mediante `/api/auth/login`.
   - Lectura de planchas reales en la tabla `planchas` y clientes reales en `clientes`.
   - Inyección de órdenes y peticiones con patrones peligrosos/inválidos verificando el rechazo HTTP 422/409 antes de tocar la base de datos.

---

## 2. Escenarios y Cobertura Operacional

| Bloque | Escenarios Cubiertos | Objetivo Principal |
|---|---|---|
| **A. Integridad de Colocación** | `CP-SEC-01`, `CP-SEC-02`, `CP-SEC-03`, `CP-SEC-04` | Comprobar rechazo exacto por bits de colisión, margen perimetral, kerf de separación y desbordamiento de plancha. |
| **B. Seguridad Geométrica HTTP** | `CP-SEC-05`, `CP-SEC-08` | Comprobar que peticiones HTTP reales a la API bloqueen polígonos cóncavos, autointersecciones y ataques de memoria raster antes de llegar a Supabase. |
| **C. Integridad Transaccional** | `CP-SEC-06`, `CP-SEC-07` | Verificar el bloqueo de confirmaciones incompletas, alteradas o que intenten consumir un mismo retazo físico más de una vez. |

---

## 3. Mitigación de Riesgos durante la Prueba Real
- **Prevención de datos basura en Supabase**: Al validar que la API rechaza peticiones inválidas con códigos `422` y `409`, ninguna pieza corrupta se insertará en la tabla `piezas_pedido`. Para las verificaciones de confirmación o lectura de planchas existentes, todas las pruebas operan en modo **solo lectura o rollback garantizado** sobre el stock real.
- **Trazabilidad visual continua**: Cada ejecución automatizada imprimirá códigos estructurados y generará capturas de evidencia de alta resolución para el documento Word de Notion.
