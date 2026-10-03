# Convenciones de pruebas

Las pruebas verifican comportamiento o contratos del código incorporado a la
aplicación. Los experimentos exploratorios se mantienen en
[`experiments/raster/`](../../experiments/raster/README.md).

## Backend

| Directorio | Propósito |
|---|---|
| `backend/tests/unit/` | Unidades aisladas, sin infraestructura externa real. |
| `backend/tests/api/` | Rutas, validación, respuestas y contratos HTTP. |
| `backend/tests/integration/` | Interacción entre componentes o adaptadores con recursos de prueba controlados. |
| `backend/tests/optimization/` | Casos geométricos y de rasterización incorporados al módulo; evitar duplicarlos en otra categoría. |

Organizar por módulo dentro de estas carpetas cuando sea útil. Conservar por
ahora `backend/tests/test_auth.py`, `backend/tests/test_permissions.py` y
`backend/tests/unit/test_database_structure.py` en sus ubicaciones actuales.
Las pruebas nuevas no deben utilizar por defecto la base remota compartida.

Desde `backend/`, con el entorno preparado según su [README](../../backend/README.md):

```bash
python -m pytest -q
```

## Frontend

Desde `frontend/`, con las dependencias instaladas según su [README](../../frontend/README.md):

```bash
npm run lint
npm run build
```

Todavía no hay un script `npm test`. Lint comprueba reglas de código y build
comprueba la generación del sitio; no equivalen a pruebas del comportamiento UI.

## Registro de validación

Guardar los resultados reales en `docs/evidence/sprint-01/<ID>/`, siguiendo las
[convenciones de evidencia](../evidence/README.md). Incluir el comando, directorio
de ejecución y contexto del código probado. No declarar una prueba aprobada si
no se ejecutó ni repetir resultados anteriores como si fueran una nueva ejecución.
