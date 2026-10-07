# HU-005: matriz de prueba funcional API/BD

## Objetivo y procedencia

Registrar un caso válido y dos inválidos de T03, con entrada, resultado esperado, resultado obtenido y estado. Los resultados corresponden a pruebas funcionales manuales sobre la API y PostgreSQL/Supabase.

## Matriz de resultados

| Caso | Entrada | Esperado | Obtenido | Estado |
|---|---|---|---|---|
| 1. Alta válida | `RET-HU005-002`; Incoloro; `id_tipo_vidrio = 1`; `espesor_mm = 6`; `RECTANGULO` de `600 × 300` mm | HTTP 201, área `180000 mm²` y persistencia. | HTTP 201; área `180000.00`; persistido y recuperado mediante GET. | PASS |
| 2. Dimensión inválida | Código `RET-HU005-INV-DIM`; `RECTANGULO` con `width_mm = 0` | HTTP 422 y sin persistencia. | HTTP 422; la comprobación posterior confirmó que no quedó persistido. | PASS |
| 3. Espesor incompatible | Código `RET-HU005-INV-ESP`; Tipo Espejo, `id_tipo_vidrio = 6`; espesor `8 mm`, incompatible con catálogo | HTTP 422 y sin persistencia. | HTTP 422; la comprobación posterior confirmó que no quedó persistido. | PASS |

## Comprobación posterior

- `INVALIDOS_PERSISTIDOS: 0`.
- `GET /api/inventory/retazos` recuperó nuevamente `RET-HU005-002` con los mismos datos.
- Estado: **PASS**.

La matriz no afirma resultados de integración desde React ni incorpora capturas no observadas. La integración React → API corresponde a TA-011.
