# Convergencia de Orders: material y espesor por pieza

Estado: implementado localmente y probado en PostgreSQL temporal aislado; no aplicado a Supabase.
Fecha: 2026-10-08. Rama: `integration/HU-006-convergencia`.

## Contrato funcional vigente

Un pedido puede contener piezas de distintos tipos de vidrio y espesores. El encabezado PEDIDO conserva `id_pedido`, `fecha_registro`, `estado` e `id_usuario_registro`. Cada PIEZA conserva `id_pedido`, `id_tipo_vidrio`, `espesor_mm`, `tipo_forma`, `cantidad`, dimensiones, geometría y `area_mm2`. Las formas válidas son `RECTANGULO`, `CIRCUNFERENCIA` y `POLIGONO_CONVEXO`; no existe `TRIANGULO` independiente.

La pareja `(id_tipo_vidrio, espesor_mm)` de cada pieza referencia `tipos_vidrio_espesores` con la FK compuesta `fk_piezas_tipo_espesor`. La pertenencia al catálogo es una regla de integridad; para nuevas altas Application también exige que el tipo esté activo. No se agrega `piezas.orden`: aún no existe requisito aprobado de orden persistente.

El commit del compañero `80a4fa4` se conserva en la historia, incorporado por el merge `6eff9e0`; los cambios de convergencia son posteriores.

## Revisión Alembic implementada

La cabeza comprobada antes del cambio fue `1c8754481a08`. La revisión añadida es `d6e7f8a9b0c1` (`down_revision = 1c8754481a08`), en `backend/alembic/versions/d6e7f8a9b0c1_hu006_material_por_pieza.py`.

El upgrade bloquea las tablas involucradas, comprueba piezas huérfanas, pedidos sin piezas, parejas históricas nulas o ajenas al catálogo y conteos; agrega nullable las dos columnas en PIEZA; copia el material histórico desde PEDIDO; vuelve a verificar preservación y consistencia; establece NOT NULL; crea la FK compuesta; descubre y retira las FK antiguas de material en PEDIDO; y elimina las columnas de cabecera sin `CASCADE`. Las comprobaciones abortan la transacción con un diagnóstico ante datos incompatibles. Los tipos inactivos históricos se preservan si la pareja sigue en el catálogo: la condición de actividad se aplica a altas nuevas, no al backfill.

La migración no inventa piezas ni borra pedidos históricos sin piezas: detectarlos aborta el upgrade y deja la decisión de tratamiento al equipo. Las pruebas verifican BD vacía, backfill, preservación de IDs/cantidades/dimensiones/geometría/área, constraints, rollback y dependencias externas. Se conserva una copia congelada del contrato ORM TA-013 para comparar el esquema histórico sin confundirlo con el modelo actual.

### Downgrade

El downgrade solo se permite cuando cada pedido tiene piezas y todas sus piezas comparten una misma pareja material/espesor. Si hay un pedido vacío o multimaterial, aborta antes de cambiar el esquema; nunca escoge arbitrariamente la primera pieza. Así puede restaurar pedidos homogéneos y bloquear una reducción semánticamente destructiva. Un retorno fiel tras datos multimaterial requiere respaldo o procedimiento manual revisado.

## HTTP y capas

`POST /api/orders` recibe `piezas`, con material, espesor, forma, cantidad y geometría/dimensiones por pieza; ya no recibe material en la cabecera. Application valida todas las parejas y piezas antes de persistir, y el repositorio conserva la transacción. `GET /api/orders/{id_pedido}` recupera el pedido y sus piezas autosuficientes; ambos endpoints usan autenticación y permiso `GESTIONAR_PEDIDOS`.

Orders entrega piezas con ID, material, espesor, forma, cantidad, dimensiones, geometría en mm y área por pieza en mm². Esto permite agrupar después por `(id_tipo_vidrio, espesor_mm)`. Esta fase no implementa rasterización, colocación, métricas ni heurísticas.

## Verificación ejecutada

Pruebas específicas antes de la regresión completa:

| Suite | Resultado |
|---|---:|
| Migración multimaterial en PostgreSQL temporal | 13 passed |
| Orders Application unit tests | 34 passed |
| Orders repository integration | 6 passed |
| Orders API | 54 passed |

Estos tests no usan la base compartida. La migración no se aplicó a Supabase. Los resultados de la suite global se registrarán tras completar la ejecución.

## Interfaz temporal y pendientes

La pantalla canónica vive en `frontend/src/features/orders/NuevoPedido.jsx`; la UI permite lista mixta, pero su puente temporal solo permite guardar cuando todas las piezas comparten una pareja, mientras el contrato backend antiguo esté activo. La fase backend presente ya cambia el contrato local a multimaterial; falta completar y validar la pantalla frontend sin esa restricción. HU-006 no queda Verified por esta implementación backend aislada.

La lectura se ofrece mediante la capa Application; Optimization deberá consumir después un contrato propio, sin depender de ORM o schemas HTTP de Orders. Rasterización corresponde al Sprint 1. First Fit, Best Fit y Worst Fit corresponden al Sprint 2.
