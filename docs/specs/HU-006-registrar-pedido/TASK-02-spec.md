# SPEC-T02 — API Endpoints y Esquemas de Presentación (HU-006)

## Información general

| Campo | Valor |
|---|---|
| Estado | Reviewed |
| PBI relacionado | HU-006 (Módulo Nuevo Pedido) |
| Responsable | Luis Anthony Ibañez Herrera |
| Reviewer | Equipo de Backend / Arquitectura |

## 1. Objetivo
Implementar el router de FastAPI y los esquemas de validación en Pydantic para recibir, validar y procesar las solicitudes HTTP del módulo de pedidos en el backend.

## 2. Alcance
### Incluye
- Adaptación del router existente `POST /api/orders`.
- Evolución de schemas canónicos `CreateOrderRequest`, `PiezaSchema` y `CreateOrderResponse`, sin duplicarlos.
- Dependencias HTTP en Presentation, preservando imports diferidos de BD.
- Recuperación CA-02 pendiente: concretar endpoint y alcance de edición sin inventar autosave o CRUD.

### Fuera de alcance
- Reimplementación de JWT: reutilizar authentication y seguridad existentes.

## 3. Actor y precondiciones
**Actor:** Cliente HTTP / Frontend React.
**Precondiciones:** FastAPI configurado en `main.py` y entorno virtual activo.

## 4. Entradas y datos
| Campo / dato | Tipo / formato | Regla |
|---|---|---|
| piezas[].id_tipo_vidrio | Entero | Obligatorio por pieza, pareja de catálogo |
| piezas[].espesor_mm | Decimal | Obligatorio por pieza, pareja TA-013 |
| piezas | Lista | Al menos una pieza por pedido |

## 5. Reglas de negocio
- RN-01: Toda petición debe estar autenticada.
- RN-02: Los datos deben ajustarse estrictamente a los esquemas Pydantic (HTTP 422 si hay discrepancias).

## 6. Flujo principal
1. Envío de petición `POST` a `/api/orders`.
2. Validación de esquemas y permisos.
3. Procesamiento y respuesta HTTP 201 Created.

## 7. Flujos alternativos y errores
- HTTP 422 por datos malformados.
- HTTP 500 por error interno de persistencia.

## 8. Criterios de aceptación
- CA-01: El endpoint procesa pedidos multimaterial según [contrato objetivo](contrato-orders.md) y retorna el ID; pendiente. La API actual conserva material en cabecera.

## 9. Impacto técnico
- **Módulos:** `backend/app/modules/orders/presentation/router.py`, `backend/app/modules/orders/presentation/schemas.py`

## 10. Pruebas previstas
- Pruebas de integración con `TestClient` (`backend/tests/api/orders/test_orders_api.py`).

## 11. Evidencias requeridas
- Resultados en verde de Pytest.

## Historial de estado
- Estado anterior: Implemented, correspondiente al aporte previo a la convergencia.
- Estado actual: Reviewed; contrato multimaterial definido, implementación completa y verificación pendientes.
- La cobertura previa HU-007 acredita la versión histórica, no el contrato nuevo.