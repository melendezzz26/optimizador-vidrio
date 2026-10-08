# SPEC-T03 — Capa de Persistencia y Modelos ORM (HU-006)

## Información general

| Campo | Valor |
|---|---|
| Estado | Implemented |
| PBI relacionado | HU-006 (Módulo Nuevo Pedido) |
| Responsable | Luis Anthony Ibañez Herrera |
| Reviewer | Equipo de Base de Datos / Backend |

## 1. Objetivo
Configurar los modelos ORM de SQLAlchemy y la lógica del caso de uso para asegurar la persistencia transaccional de los pedidos y sus piezas en PostgreSQL.

## 2. Alcance
### Incluye
- Mapeo de modelos ORM para tablas `pedidos` y `piezas`.
- Lógica en `RegistrarPedidoUseCase`.
- Asignación UTC de `fecha_registro`.

### Fuera de alcance
- Modificación de esquemas históricos de Alembic.

## 3. Actor y precondiciones
**Actor:** Caso de Uso del Sistema.
**Precondiciones:** Tablas `pedidos` y `piezas` migradas previamente.

## 4. Entradas y datos
| Campo / dato | Tipo / formato | Regla |
|---|---|---|
| estado | String | Por defecto "PENDIENTE" |
| fecha_registro | Datetime | Obligatorio, UTC |
| id_usuario_registro | Entero | Obtenido de la sesión |

## 5. Reglas de negocio
- RN-01: Cumplimiento de restricciones de nulos y llaves foráneas.
- RN-02: Atomicidad transaccional.

## 6. Flujo principal
1. Recepción de datos validados y usuario.
2. Instanciación del modelo ORM con marca temporal.
3. Persistencia en base de datos mediante transacción atómica.

## 7. Flujos alternativos y errores
- Rollback automático ante fallos de integridad relacional.

## 8. Criterios de aceptación
- CA-01: Registros almacenados exitosamente en PostgreSQL.

## 9. Impacto técnico
- **Módulos:** `backend/app/modules/orders/application/use_cases.py`, `backend/app/modules/orders/infrastructure/models.py`

## 10. Pruebas previstas
- Pruebas de integración ORM mediante Pytest.

## 11. Evidencias requeridas
- Logs de ejecución de pruebas backend.

## Historial de estado
- Draft -> Reviewed -> Implemented -> Verified