# SPEC TA-047 — Preflight de optimización

Autor y revisor académico: Andro Joseph Quispe Cesias. Sin aprobación de GitHub atribuida.

El preflight responde si cada pieza distinta puede ubicarse individualmente en alguna fuente compatible; no resuelve el pedido ni garantiza que todas sus unidades puedan colocarse juntas. `PreflightResult` contiene errores estables y expone `can_optimize` y `affected_piece_ids`. Los errores son `EMPTY_ORDER`, `NO_COMPATIBLE_STOCK` y `PIECE_DOES_NOT_FIT`, con identificador de pieza cuando corresponde. El proveedor filtra por tipo de vidrio y espesor conjuntamente: la ausencia de material y la ausencia de espesor producen el mismo código porque esta interfaz no permite distinguirlas sin otra consulta.

La validación previa de pedidos y `prepare_persisted_problem` ya comprueba cantidades y geometría; `geometry_snapshot` admite rectángulos, circunferencias y polígonos convexos. Fallos de raster o presupuesto se propagan, no se convierten en imposibilidad. Se usan `RasterCache`, la grilla angular configurada y `SheetLayout.first_position` sobre una fuente vacía; los círculos solo se rasterizan a 0°. El margen erosiona la fuente conforme al motor. La separación afecta a otras piezas, no al borde; se mantiene configurable y no se introduce una separación estándar.

En `/runs`, `AcceptRun` usa el adaptador de stock disponible antes de crear la corrida y responde con `INVALID_INPUT` y `preflight_errors`, siguiendo la convención HTTP 422 existente. Los clientes directos heredados sin proveedor completo conservan su contrato y no ejecutan esta comprobación. La consulta es de solo lectura: no reserva stock, que puede cambiar antes del cálculo posterior. La comprobación de comparación queda pendiente de TA-043.
