# Orders: contrato multimaterial

Estado: implementado en backend local y cubierto por pruebas unitarias, API e integración PostgreSQL temporal. No implica que la migración se haya aplicado a Supabase ni que HU-006 esté Verified.

## Creación

`POST /api/orders` requiere JWT y permiso `GESTIONAR_PEDIDOS` (Administrador/Operario). Recibe `piezas` no vacío. Cada pieza incluye su material y espesor; no hay material en la cabecera. Ejemplo con IDs ilustrativos que deben resolverse desde el catálogo real:

```json
{
  "piezas": [
    {"id_tipo_vidrio": 1, "espesor_mm": 6, "tipo_forma": "RECTANGULO", "cantidad": 2, "width_mm": 1000, "height_mm": 500},
    {"id_tipo_vidrio": 6, "espesor_mm": 4, "tipo_forma": "CIRCUNFERENCIA", "cantidad": 1, "radius_mm": 250},
    {"id_tipo_vidrio": 2, "espesor_mm": 5.5, "tipo_forma": "POLIGONO_CONVEXO", "cantidad": 3, "vertices_mm": [[0, 0], [500, 0], [500, 300], [0, 300]]}
  ]
}
```

Formas admitidas: `RECTANGULO`, `CIRCUNFERENCIA` y `POLIGONO_CONVEXO`; no `TRIANGULO`. El cliente obtiene tipos activos y sus espesores de `GET /api/inventory/tipos-vidrio`. Application valida las parejas del catálogo y las reglas de actividad, cantidad y geometría antes de cualquier escritura. El servidor deriva dimensiones normalizadas, geometría y área; el usuario registrador proviene de la sesión, y el servidor asigna ID, fecha y estado. La persistencia es transaccional: una pieza inválida rechaza el pedido entero.

Respuesta: HTTP 201 con `{"id_pedido": 42, "estado": "PENDIENTE"}`. Se conservan 401, 403 y 422; los errores inesperados responden 500 sin stack trace. La guardia contra doble envío pertenece al frontend.

## Recuperación completa

`GET /api/orders/{id_pedido}` aplica el mismo permiso `GESTIONAR_PEDIDOS`. Devuelve la cabecera (`id_pedido`, `fecha_registro`, `estado`) y piezas con `id_pieza`, `id_tipo_vidrio`, `espesor_mm`, `tipo_forma`, `cantidad`, `dimensiones`, `geometria` y `area_mm2`. Un pedido inexistente devuelve 404; identificadores inválidos se rechazan. Las parejas históricas inactivas se pueden leer si permanecen en el catálogo.

La geometría se expresa en milímetros y el área es por pieza en mm²:

| Forma | dimensiones | geometria |
|---|---|---|
| RECTANGULO | objeto tipado con `width_mm`, `height_mm` | objeto tipado equivalente |
| CIRCUNFERENCIA | objeto tipado con `radius_mm` | objeto tipado equivalente |
| POLIGONO_CONVEXO | SQL NULL | objeto tipado con `vertices_mm` |

La forma de lectura permite agrupar después por `(id_tipo_vidrio, espesor_mm)` y suministra ID, geometría, dimensiones, cantidad y área para cada pieza. No define rasterización ni estrategia de colocación.

## Persistencia y migración

El modelo SQLAlchemy vigente pone material y espesor en PIEZA, con FK compuesta `fk_piezas_tipo_espesor` a TA-013. La revisión `d6e7f8a9b0c1` desciende de `1c8754481a08`, realiza el backfill desde PEDIDO y aborta ante filas huérfanas, pedidos sin piezas o parejas inválidas. El downgrade se bloquea si no puede reconstruir una única pareja por pedido; no elige arbitrariamente la primera pieza. Véase [convergencia y estrategia de migración](../../database/convergencia-orders-multimaterial.md).

La revisión y el contrato se probaron en PostgreSQL temporal. No se aplicaron a Supabase. El despliegue requiere coordinar migración y backend: versiones anteriores esperan material en la cabecera.
