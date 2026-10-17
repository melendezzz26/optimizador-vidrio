# Sprint 1 — resultados finales reproducibles

Fecha local: **2026-10-16, America/Lima**. Código probado: `e1faf3e`; cierre
documental previo: `cbfa6ad`. Estos resultados provienen de las ejecuciones de
integración funcional anteriores al saneamiento documental. **No se volvieron a
ejecutar suites ni se modificó código para consolidar esta evidencia.**

| Verificación | Resultado | Evidencia conservada |
|---|---|---|
| Backend completo previo | 1976 passed, 1 warning | [Log original](../logs/backend-final.log) |
| Orders focalizado previo | 163 passed | Estado validado del equipo; [informe de cierre](../../../../../reviews/S1-final-integration.md). No se fabrica un log ausente. |
| Optimization backend posterior | 379 passed, 1 warning | [Salida focalizada](backend-optimization.txt) |
| Frontend unit | 159 passed, 0 failed, 0 skipped | [Salida TAP](unit.txt) |
| Frontend component | 453 passed, 0 failed, 0 skipped | [Reporte por archivo/caso](component.json) |
| ESLint | 0 errors, 0 warnings, exit 0 | [Salida](lint.txt) |
| Build | OK, exit 0 | [Salida Vite](build.txt) |
| E2E | 86 passed, 0 failed, 0 skipped, 0 flaky | [Reporte por caso/viewport](e2e.json) |
| Alembic | Una head: `s1opt02b4c6d` | Verificación previa en el informe; no se ejecutaron migraciones para esta consolidación. |

[Resumen estructurado](results.json). Los subconjuntos y las revalidaciones no se
suman como pruebas únicas. Los timestamps E2E originales están en UTC: el inicio
`2026-10-17T02:08:02.695Z` corresponde al 16/10/2026 a las 21:08 de Lima.

Los reportes component/E2E conservan nombre, archivo, estado, duración y viewport
cuando corresponde. Se excluyeron configuración de ejecución, stdout repetido,
warnings de terminal y rutas personales; los logs se normalizaron de UTF-16LE a
UTF-8 y sin ANSI. Se omitió el userinfo de una URL sintética usada como nombre de
test; no se alteraron resultados. El índice de consolidación registra SHA256 de
los reportes fuente, de cada evidencia retirada y de su reemplazo documental.

## Reproducir con los archivos del producto

Usar Node/npm y el lockfile del frontend, Python 3.11 con las dependencias backend,
Chrome instalado y PostgreSQL local con `initdb`/`pg_ctl`. Preparación general:
[frontend](../../../../../../frontend/README.md),
[backend](../../../../../../backend/README.md) y
[pruebas](../../../../../testing/README.md).

En `frontend/`:

```text
npm run test:unit
npm run test:component
npm run lint
npm run build
npm run test:e2e
```

En Windows PowerShell puede usarse `npm.cmd` sin cambiar la política del sistema.
Activar `backend/venv` (o el virtualenv local equivalente) para que `python` en
PATH resuelva sus dependencias. `frontend/playwright.config.js` inicia Vite en
5173 y `python -m tests.e2e_server` en 8017, y ejecuta el teardown de su PostgreSQL
temporal. No usar una base de datos compartida ni reutilizar servicios ajenos.

Para ejecutar todos los casos, proporcionar en el entorno del proceso
`HU015_E2E_USERNAME/PASSWORD` y
`TA_DASHBOARD_E2E_{ADMIN,OPERATOR,WAREHOUSE}_{USERNAME,PASSWORD}` con las cuentas
**sintéticas** que define `backend/tests/e2e_server.py`. Consultar esos valores en
el archivo del producto; no copiarlos a documentación, reportes ni comandos
versionados. Son cuentas del clúster efímero, nunca credenciales de desarrollo o
producción. Sin esas variables, algunas suites existentes omiten escenarios;
esa ejecución no equivale al resultado final de 86/86.

Definir `NEWGLASS_REQUIRE_POSTGRES=1` y, si los binarios no están en la ubicación
predeterminada, `NEWGLASS_TEST_PG_BIN`. Para que las capturas de Dashboard se
guarden fuera de la evidencia histórica, definir `NEWGLASS_E2E_EVIDENCE_DIR` a un
directorio temporal. Optimization usa el directorio de resultados de Playwright
salvo exportación explícita con `NEWGLASS_OPTIMIZATION_EVIDENCE_DIR`.

Ejemplo de salida temporal en PowerShell, después de configurar el entorno:

```powershell
$env:NEWGLASS_E2E_EVIDENCE_DIR = Join-Path $env:TEMP 'newglass-dashboard-review'
$env:PLAYWRIGHT_JSON_OUTPUT_FILE = Join-Path $env:TEMP 'newglass-e2e-review.json'
npm.cmd run test:e2e -- --reporter=line,json --output="$env:TEMP/newglass-e2e-review"
```

Los filtros específicos usan las configuraciones versionadas
`frontend/playwright.optimization.config.js` y `frontend/playwright.hu015.config.js`.
No se conserva una segunda copia de runner/config dentro de evidencia.

En `backend/`, con el mismo Python y PostgreSQL aislado:

```text
python -m pytest tests/unit/optimization tests/api/optimization tests/integration/optimization -q
python -m alembic heads
```

La ejecución completa previa usa `python -m pytest -q`; sus 1976 casos son un
baseline histórico, no una nueva corrida declarada para este commit.

## Procedencia y cobertura visual

Las capturas y respuestas de [integración real](../README.md) pertenecen a la
entrega UI anterior, identificada por `70a6c36`/`c5baa8a`, conservada sin retocar
imágenes ni fabricar resultados. No se presentan como capturas nuevas del cierre
Orders. Los expedientes por escenario preservan los payloads originales con sus
IDs locales. La regresión completa posterior a Orders es el reporte de 86 E2E
enlazado arriba. Ver [auditoría de consolidación](../../../../../reviews/S1-evidence-consolidation.md).
