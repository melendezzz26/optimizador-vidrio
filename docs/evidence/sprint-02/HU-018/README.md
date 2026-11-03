# Evidencia HU-018 — Importación masiva de piezas

SPEC: [`docs/specs/SPEC-HU-018-importacion-masiva.md`](../../../specs/SPEC-HU-018-importacion-masiva.md)
Rama: `feature/S2-HU018-importacion-masiva`

## Archivo de ejemplo

[`piezas_prueba.csv`](piezas_prueba.csv): los ejemplos de la SPEC §10. Resultado esperado:
16 filas, 7 válidas y 9 observadas (una por cada causa de §10).

## Capturas

| Tarea | Archivo | Qué muestra |
|---|---|---|
| T01 | `HU018-dominio-rojo.png` | Pruebas del dominio fallando antes de implementar las reglas de fila. |
| T01 | `HU018-dominio-verde.png` | Las mismas pruebas en verde. |
| T02 | `HU018-T02-backend-rojo.png` / `-verde.png` | Lectura CSV/XLSX y API de vista previa: rojo y verde. |
| T02 | `HU018-T02-frontend-rojo.png` / `-verde.png` | Panel de importación: rojo y verde. |
| T02 | `HU018-T02-vista-previa.png` | Tabla con resumen y filas observadas resaltadas. |
| T02 | `HU018-T02-material.png` | Vidrio y espesor elegidos después de cargar el archivo. |
| T03/T04 | `HU018-T03-T04-rojo.png` / `-verde.png` | Corrección, revalidación y agregar al pedido: rojo y verde. |
| T03 | `HU018-T03-bloqueado.png` | "Agregar al pedido" deshabilitado con filas observadas. |
| T03 | `HU018-T03-revalidado.png` | Filas corregidas y revalidadas: 16 de 16 válidas. |
| T04 | `HU018-T04-piezas-agregadas.png` | Piezas importadas en el grupo de su material. |
| T04 | `HU018-T04-pedido-registrado.png` | Pedido registrado una sola vez. |
| T05 | `HU018-T05-ci.png` | Checks del PR en verde (backend, frontend y E2E en escritorio y móvil). |

Las capturas no muestran URLs de base de datos, contraseñas ni tokens.

## Cómo reproducir

Desde `backend/`:

```bash
python -m pytest tests/unit/modules/orders tests/api/orders/test_import_preview_api.py tests/integration/optimization/test_hu018_imported_order.py -q
```

Desde `frontend/`:

```bash
npm run test:unit
npx vitest run src/features/orders/__tests__/BulkImportPanel.test.jsx src/features/orders/__tests__/BulkImportAddToOrder.test.jsx
npx playwright test hu018-bulk-import.spec.js
```

Las pruebas de API y el E2E necesitan PostgreSQL de pruebas; en el CI corren siempre.