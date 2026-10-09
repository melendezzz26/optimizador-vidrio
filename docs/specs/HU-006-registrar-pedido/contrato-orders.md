# Orders: contrato multimaterial objetivo

Estado: definición funcional vigente; HTTP y persistencia pendientes de adaptación.
No confundir los ejemplos siguientes con el contrato actualmente desplegado.

## Creación objetivo

`POST /api/orders`, JWT real y permiso `GESTIONAR_PEDIDOS` (Administrador/Operario).
La raíz contiene `piezas`, con al menos un elemento. Material y espesor son
obligatorios en CADA pieza. La cabecera no los recibe.

Ejemplo con IDs ilustrativos, que deben resolverse desde el catálogo real:

```json
{
  "piezas": [
    {"id_tipo_vidrio": 1, "espesor_mm": 6, "tipo_forma": "RECTANGULO", "cantidad": 2, "width_mm": 1000, "height_mm": 500},
    {"id_tipo_vidrio": 6, "espesor_mm": 4, "tipo_forma": "CIRCUNFERENCIA", "cantidad": 1, "radius_mm": 250},
    {"id_tipo_vidrio": 2, "espesor_mm": 5.5, "tipo_forma": "POLIGONO_CONVEXO", "cantidad": 3, "vertices_mm": [[0, 0], [500, 0], [500, 300], [0, 300]]}
  ]
}
```

No se fijan IDs por nombre. Obtener tipos activos y sus `espesores_mm` mediante
`GET /api/inventory/tipos-vidrio` (TA-013). No aceptar TRIANGULO como discriminante.
Validar cantidades enteras positivas y medidas/coordenadas finitas, geometría
válida y cada pareja contra catálogo. El servidor deriva `dimensiones`,
`geometria` y `area_mm2`; no aceptar área o geometría derivada impuesta por el cliente.
El usuario registrador procede de la sesión; ID, fecha y estado los asigna el servidor.

Respuesta conservada: HTTP 201, `{"id_pedido": 42, "estado": "PENDIENTE"}`.
Conservar 401, 403, 422 y 500 seguro, sin stack trace. Una pieza inválida rechaza
el pedido completo, sin escrituras parciales. Conservar la guardia frontend contra
doble envío y el borrador ante fallos de guardado.

## Lectura y consumidor pre-raster

La recuperación completa exigida por CA-02 sigue pendiente. El contrato de lectura
deberá incluir la cabecera y piezas con `id_pieza`, `id_pedido`, `id_tipo_vidrio`,
`espesor_mm`, `tipo_forma`, `cantidad`, `dimensiones`, `geometria`, `area_mm2`.
El endpoint concreto y el alcance de recuperación durante edición deben concretarse
antes de implementar esa tarea; no se incorpora ahora CRUD, autosave ni orden persistente.

Geometría persistida conservada de HU-007:

| Forma | dimensiones | geometria |
|---|---|---|
| RECTANGULO | Objeto `type`, `width_mm`, `height_mm` | Mismo objeto tipado |
| CIRCUNFERENCIA | Objeto `type`, `radius_mm` | Mismo objeto tipado |
| POLIGONO_CONVEXO | SQL NULL | Objeto `type`, `vertices_mm` |

Longitudes en mm y área por pieza en mm². Rasterización podrá agrupar por pareja
material/espesor y utilizar cantidad sin alterar este contrato. No incorpora
colocación, heurísticas o métricas de optimización.

## Compatibilidad temporal

La API actual conserva `id_tipo_vidrio` y `espesor_mm` en la raíz y solo soporta
una pareja por pedido. La nueva UI bloquea combinaciones distintas antes de hacer
POST y adapta únicamente el caso comprobado de pareja única. No acepta silenciosamente
el contrato nuevo en el backend ni simula que ya se migró la BD.

El [plan de migración y preservación](../../database/convergencia-orders-multimaterial.md)
es parte obligatoria de la implementación posterior. HU-006 no está Verified.
