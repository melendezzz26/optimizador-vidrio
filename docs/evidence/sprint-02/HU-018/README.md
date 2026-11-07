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
| T02–T05 | `HU018-pruebas-backend-verde.png` | Suite de pruebas del backend en verde. |

La verificación de T02 a T05 (componentes, E2E en escritorio y móvil) está en los
checks del PR #96. Las capturas de la interfaz se agregarán en un PR posterior.

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