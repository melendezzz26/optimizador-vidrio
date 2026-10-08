# SPEC-T02 — API Endpoints y Esquemas de Presentación (HU-006)

## Información general

| Campo | Valor |
|---|---|
| Estado | Implemented |
| PBI relacionado | HU-006 (Módulo Nuevo Pedido) |
| Responsable | Luis Anthony Ibañez Herrera |
| Reviewer | Equipo de Backend / Arquitectura |

## 1. Objetivo
Implementar el router de FastAPI y los esquemas de validación en Pydantic para recibir, validar y procesar las solicitudes HTTP del módulo de pedidos en el backend.

## 2. Alcance
### Incluye
- Creación del router `POST /api/orders/`.
- Definición de esquemas `PedidoCreate`, `PiezaCreate` y `PedidoResponse` en Pydantic.
- Inyección de dependencias para el caso de uso y seguridad.

### Fuera de alcance
- Implementación interna del módulo de seguridad JWT final (`app.core.security`).

## 3. Actor y precondiciones
**Actor:** Cliente HTTP / Frontend React.
**Precondiciones:** FastAPI configurado en `main.py` y entorno virtual activo.

## 4. Entradas y datos
| Campo / dato | Tipo / formato | Regla |
|---|---|---|
| id_tipo_vidrio | Entero | Obligatorio, clave foránea |
| espesor_mm | Decimal | Obligatorio, positivo |
| piezas | Lista | Al menos una pieza por pedido |

## 5. Reglas de negocio
- RN-01: Toda petición debe estar autenticada.
- RN-02: Los datos deben ajustarse estrictamente a los esquemas Pydantic (HTTP 422 si hay discrepancias).

## 6. Flujo principal
1. Envío de petición `POST` a `/api/orders/`.
2. Validación de esquemas y permisos.
3. Procesamiento y respuesta HTTP 201 Created.

## 7. Flujos alternativos y errores
- HTTP 422 por datos malformados.
- HTTP 500 por error interno de persistencia.

## 8. Criterios de aceptación
- CA-01: El endpoint procesa payloads válidos y retorna el ID del pedido.

## 9. Impacto técnico
- **Módulos:** `backend/app/modules/orders/presentation/router.py`, `backend/app/modules/orders/presentation/schemas.py`

## 10. Pruebas previstas
- Pruebas de integración con `TestClient` (`tests/test_orders.py`).

## 11. Evidencias requeridas
- Resultados en verde de Pytest.

## Historial de estado
- Draft -> Reviewed -> Implemented -> Verified