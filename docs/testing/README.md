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
npm test
```

| Script / ubicación | Nivel y alcance |
|---|---|
| `test:unit` / `tests/unit/geometryScaling.test.js` | Unitarias con `node:test`; las 38 pruebas geométricas originales. |
| `test:component` / `src/features/orders/__tests__/CustomPieceEditor.test.jsx` | Componentes con Vitest + React Testing Library + user-event; editor y geometría reales en jsdom. |
| `test:e2e` / `tests/e2e/hu007-custom-piece.spec.js` | E2E del flujo visible frontend con Playwright, escritorio y móvil emulado. |
| `test` | Ejecuta las tres suites anteriores, una vez, deteniéndose si falla una. |

La estrategia frontend es **Component + E2E**, complementada por las unitarias
geométricas existentes. Caja negra y caja blanca/límites son técnicas de diseño,
no niveles separados. Los componentes verifican el comportamiento visible; las
unitarias verifican reglas internas e invariantes geométricos.

Playwright administra su propio Vite en el puerto 5173 y reutiliza
`/hu007-t01.html`, sin Login ni servicios externos. El puerto debe estar libre.
En Windows local usa Google Chrome estable instalado mediante `channel: 'chrome'`
por defecto, sin descargar Chromium ni configurar una ruta al ejecutable.
Una futura CI podrá instalar Chromium oficial con
`npx playwright install --with-deps chromium` y usar `PLAYWRIGHT_CHANNEL=chromium`;
esta alternativa no se ha validado aquí. Si conserva el canal predeterminado,
CI necesitará Chrome instalado.
Para versiones de Node y comandos de selección de navegador, consultar el
[README frontend](../../frontend/README.md#pruebas-hu-007-t01t02).
El E2E completo Operario → Orders/API → PostgreSQL → registro definitivo queda
para cuando esos componentes estén integrados y estabilizados.

Para HU-007 T01/T02, integración backend, API, PostgreSQL/Supabase, repositorios,
migraciones Alembic, persistencia, smoke post-deploy y benchmark:
**No aplica al alcance actual**, que es frontend + geometría local. No representan
pruebas faltantes. No se simula una API para declarar integración.

Casos manuales y capturas existentes son evidencia complementaria, sin sustituir
resultados automatizados. La [matriz HU-007](../evidence/sprint-01/HU-007/t01-t02-pruebas-frontend.md)
separa resultados nuevos de antecedentes. Lint comprueba reglas de código y build
comprueba la generación del sitio; no equivalen a pruebas de comportamiento UI.

## Registro de validación

Guardar los resultados reales en `docs/evidence/sprint-01/<ID>/`, siguiendo las
[convenciones de evidencia](../evidence/README.md). Incluir el comando, directorio
de ejecución y contexto del código probado. No declarar una prueba aprobada si
no se ejecutó ni repetir resultados anteriores como si fueran una nueva ejecución.
