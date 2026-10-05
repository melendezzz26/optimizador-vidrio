# HU-004: registro mediante API y comprobación en base de datos

## Objetivo y procedencia

Documentar el caso válido de T02, asociado a CA-04, CA-05 y CA-06 de la [SPEC HU-004](../../../specs/SPEC-HU-004-registrar-plancha.md).

Los resultados siguientes corresponden a la ejecución manual realmente realizada y reportada por el usuario para incorporar a esta evidencia. El usuario confirmó la verificación de T01, T02, T03 y T04 el 05/10/2026. No se repitieron solicitudes HTTP ni consultas a Supabase durante la redacción. No se recibió un hash del backend desplegado; no se atribuye uno.

La documentación se prepara en `feature/HU-004-registrar-plancha`, con cambios sin commit. El caso verifica API y persistencia de forma independiente del formulario React; no acredita la integración E2E de TA-011.

## Catálogo consultado

La consulta `GET /api/inventory/tipos-vidrio` confirmó el catálogo TA-013 según la verificación reportada. Para el caso válido se seleccionó:

| Dato | Valor observado |
|---|---|
| Tipo | Espejo |
| `id_tipo_vidrio` | 6 |
| Espesores admitidos | 2, 3, 4 y 6 mm |

El ID 6 corresponde al entorno de esta ejecución, no a una constante que deba incorporarse al formulario.

## Solicitud de creación

Endpoint: `POST /api/inventory/planchas`.

```json
{
  "ancho_mm": 3210,
  "alto_mm": 2250,
  "espesor_mm": 6,
  "cantidad": 2,
  "id_tipo_vidrio": 6
}
```

Resultado: **HTTP 201**.

| Campo devuelto | Valor reportado |
|---|---|
| `id_plancha` | 1 |
| `ancho_mm` | 3210 |
| `alto_mm` | 2250 |
| `espesor_mm` | 6 |
| `cantidad` | 2 |
| `estado` | true |
| `id_tipo_vidrio` | 6 |
| `fecha_registro` | `2026-10-05T18:47:51.333095Z` |

La tabla recoge los valores reportados, no una transcripción del JSON bruto de respuesta.

## Consulta posterior y persistencia

`GET /api/inventory/planchas` devolvió la misma plancha con `id_plancha = 1`.

La comprobación directa reportada en Supabase/PostgreSQL mostró:

| Campo | Valor observado en BD |
|---|---|
| `id_plancha` | 1 |
| `ancho_mm` | 3210.00 |
| `alto_mm` | 2250.00 |
| `espesor_mm` | 6.0 |
| `cantidad` | 2 |
| `estado` | true |
| `id_tipo_vidrio` | 6 |
| Tipo | Espejo |

El alta válida quedó persistida y fue recuperada por la API. La [matriz funcional](prueba-funcional.md) registra también el rechazo de dos altas inválidas y la consulta final sin registros adicionales.

## Captura y límites

El usuario informa que existe una captura manual de Supabase para incorporar a la evidencia si el equipo decide guardarla. La captura no se adjunta en esta entrega y no se inventa una ruta para ella. Antes de incorporarla se deben excluir credenciales y datos sensibles.

Este documento no contiene JWT, credenciales ni secretos. La verificación manual del formulario en navegador ya fue reportada y se documenta en [formulario-plancha.md](formulario-plancha.md). Utilizó fixtures locales `900001–900004` y envío a consola, distintos del ID real 6 utilizado en este caso API/BD. El montaje temporal fue retirado de `App.jsx`. El flujo E2E React → API → PostgreSQL sigue pendiente para TA-011. Lighthouse no se ejecutó.
