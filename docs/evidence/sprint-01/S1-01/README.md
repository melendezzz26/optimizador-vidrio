# S1-01 — Vista previa sin transición de estado

Fecha: 21/10/2026, America/Lima. Rama: `fix/S1-01-preview-first-fit`. Base: `8a624a6`.

Corrección exclusiva del [hallazgo S1-01](../../../reviews/S1-pre-S2-technical-audit.md#s1-01--previsualización-histórica-bloquea-la-ejecución-first-fit), autorizada después del análisis. No se modifica la evidencia histórica de HU-015, que documenta el comportamiento original con transición.

## Contrato corregido

`POST /api/optimization/start` conserva el request con id_pedido y las validaciones de pendiente, piezas válidas, pertenencia, geometría y presupuesto inicial. Responde 200 con estado PENDIENTE, incluso al repetirse, sin mutación, ejecución ni inventario. `/rasterize` acepta PENDIENTE y conserva lectura de EN_OPTIMIZACION; rechaza OPTIMIZADO/CONFIRMADO/CANCELADO. La preparación de la UI es local y sus respuestas obsoletas se cancelan/ignoran.

First Fit sigue aceptando exclusivamente pendientes, creando su ejecución/snapshot y cambiando el lote a EN_OPTIMIZACION dentro de su propia transacción. El resultado completo lleva a OPTIMIZADO y solo confirmar consume stock y lleva a CONFIRMADO. No cambia código productivo de First Fit, confirmación, Orders, RBAC ni inventario.

## Verificación

PostgreSQL se ejecutó mediante el harness existente, con clúster/bases temporales exclusivos en loopback, credenciales sintéticas y esquema existente; no se usó la base del .env ni se crearon migraciones. Para evitar skips se fijó `NEWGLASS_REQUIRE_POSTGRES=1`. Los servicios E2E temporales quedaron detenidos al finalizar. El Python del entorno backend y los procesos de frontend/navegador se ejecutaron fuera del sandbox por las restricciones locales de Windows.

| Validación final | Resultado | Registro |
|---|---:|---|
| Backend: unitarias Optimization, dominio raster, API Optimization, integración Optimization y permisos de endpoints | **604 passed**, sin skips | [backend-tests.txt](backend-tests.txt) |
| Componentes frontend de Optimization, incluidos HU-015, parser, First Fit y confirmación | **135 passed**, 10 archivos | [frontend-components.txt](frontend-components.txt) |
| Unitarias frontend First Fit e inspección raster | **12 passed**, sin skips | [frontend-unit.txt](frontend-unit.txt) |
| E2E HU-015 y S1-01, escritorio y móvil, API/PostgreSQL reales | **8 passed**, sin skips | [browser-tests.txt](browser-tests.txt) |
| Build frontend | **Correcto** | [frontend-build.txt](frontend-build.txt) |
| ESLint sobre los 7 archivos JS/JSX modificados | **Correcto**, sin salida | Comando abajo |
| `git diff --check` | **Correcto**, sin salida | Ejecutado al cierre |

Total de pruebas aprobadas en las corridas finales: **759**. La selección backend conserva los casos existentes de rollback y concurrencia de confirmación. Advertencias observadas: deprecación existente Starlette/httpx y NO_COLOR/FORCE_COLOR en Playwright; no se modifican dependencias para ocultarlas. Durante el ajuste inicial se corrigió el payload de una prueba nueva de edición (PUT no admite id_cliente) y expectativas antiguas de UI; los registros enlazados corresponden a las corridas finales aprobadas.

Comandos desde raíz, salvo los indicados en frontend:

```powershell
$env:NEWGLASS_REQUIRE_POSTGRES='1'
& .\backend\venv\Scripts\python.exe -m pytest -q backend/tests/unit/optimization backend/tests/optimization backend/tests/api/optimization backend/tests/integration/optimization backend/tests/api/authorization/test_endpoint_permissions.py
npm.cmd --prefix frontend run test:component -- src/features/optimization/__tests__
node --test frontend/tests/unit/firstFitModel.test.js frontend/tests/unit/rasterInspection.test.js
git diff --check
```

Desde frontend, con PATH apuntando al Python del venv, `PYTHON_DOTENV_DISABLED=1`, `NEWGLASS_REQUIRE_POSTGRES=1` y las credenciales sintéticas del harness (`HU015_E2E_USERNAME`/`HU015_E2E_PASSWORD`):

```powershell
node node_modules/@playwright/test/cli.js test --grep 'HU-015|S1-01' --workers=1
npm.cmd run build
node node_modules/eslint/bin/eslint.js src/features/optimization/useOptimization.js src/features/optimization/optimizationApi.js src/features/optimization/Hu015Rasterization.jsx src/features/optimization/__tests__/optimizationApi.test.jsx src/features/optimization/__tests__/Hu015Rasterization.test.jsx tests/e2e/hu015-rasterization.spec.js tests/e2e/s1-optimization-ui.spec.js
```

La invocación directa de Playwright con Node evita que el lanzador cmd de Windows interprete el filtro como una tubería. Las capturas/DTO auxiliares del navegador se generan en frontend/test-results, ignorado por Git; no se exporta sobre evidencia histórica.

La regresión API integrada cubre N=1 y N=2: preparar dos veces → rasterizar → igualdad de tablas persistidas → aceptar First Fit (observa EN_OPTIMIZACION antes del cálculo) → stock intacto → GET de resultado persistido sin recalcular → confirmación con movimientos trazables → segunda confirmación rechazada sin doble consumo. También cubre histórico EN_OPTIMIZACION sin normalización y rechazo de `/runs` sin efectos parciales.

## Límites

El valor de estado en la respuesta histórica cambia: desplegar backend/frontend coordinadamente; no se ha demostrado ausencia de consumidores externos al repositorio. La máscara es una consulta de los datos del momento, no una reserva; después de editar, los nuevos cálculos releen las piezas persistidas. Los históricos retenidos requieren diagnóstico y autorización separados: esta corrección no los modifica ni crea scripts de reconciliación. S1-02/S1-03 y otros hallazgos quedan fuera de alcance.
