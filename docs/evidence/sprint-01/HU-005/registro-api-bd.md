# HU-005: registro mediante API y comprobación en base de datos

## Objetivo y procedencia

Documentar la verificación de T02 para el alta de un retazo mediante API y su persistencia en PostgreSQL/Supabase. La comprobación se realizó con una cuenta técnica real con rol `Almacenero`.

No se documentan contraseña, hash ni JWT. La evidencia API/BD es independiente del formulario React; la integración React → API corresponde a TA-011.

## Catálogo consultado

El catálogo real se consultó mediante `GET /api/inventory/tipos-vidrio`.

## Solicitud oficial de creación

Endpoint: `POST /api/inventory/retazos`.

Payload enviado:

```json
{
  "codigo": "RET-HU005-002",
  "id_tipo_vidrio": 1,
  "espesor_mm": 6,
  "geometria": {
    "type": "RECTANGULO",
    "width_mm": 600,
    "height_mm": 300
  }
}
```

El área no fue enviada por el cliente; fue calculada por el backend.

Resultado observado: **HTTP 201**.

| Campo | Valor observado |
|---|---|
| `id_retazo` | 2 |
| `area_mm2` | `180000.00` |
| `estado` | `true` |
| `id_ejecucion_origen` | `null` |

## Consulta posterior y persistencia

Una consulta posterior mediante `GET /api/inventory/retazos` devolvió los mismos datos del caso oficial `RET-HU005-002`.

PostgreSQL/Supabase confirmó la persistencia del registro. `RET-HU005-001` puede considerarse únicamente una prueba preliminar de persistencia; el caso oficial documentado aquí es `RET-HU005-002`, porque en este se observó explícitamente el HTTP `201`.

No se inventan capturas, logs ni rutas de archivos que no hayan sido observados.
