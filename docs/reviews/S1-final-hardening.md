# Hardening final de Sprint 1

Fecha: 2026-10-16 (America/Lima). Rama: `chore/S1-final-integration`.
Complementa el [cierre funcional previo](S1-final-integration.md). Sin push ni PR.

El [hardening comercial posterior](S1-commercial-cut-hardening.md) registra la
corrección P0 del límite raster y la validación más reciente del corte completo.

## Configuración inicial reproducible

El seed optativo utiliza los valores de `backend/tests/optimization_e2e_data.py`
empleados en los E2E aprobados: separación 0 mm, margen 0 mm, resolución 1 mm,
paso angular 90° y retazo mínimo 10 × 10 mm. Son valores para desarrollo/demo.

Desde `backend/`, con el destino de base autorizado configurado y una cuenta
activa existente:

```text
python -m alembic upgrade head
python seed.py --optimization-demo --responsable USUARIO_EXISTENTE
python seed.py --optimization-demo --responsable USUARIO_EXISTENTE
```

Ambas ejecuciones deben conservar el mismo ID y versión. No se asume un ID de
usuario. La [guía del backend](../../backend/README.md#configuración-inicial-de-corte-para-desarrollodemo)
describe cómo preparar el primer administrador si aún no existe.

- Una vigente completa se conserva, aunque sus valores difieran de los demo.
- Sin vigente, se crea una versión nueva con un responsable activo real.
- Se rechazan responsables inexistentes/inactivos, varias vigentes y una vigente
  incompleta/inválida con un mensaje claro. No se elige ni repara arbitrariamente.
- No se alteran versiones históricas ni sus optimizaciones. Los intentos
  concurrentes se serializan mediante un bloqueo transaccional en PostgreSQL.
- No se añadieron ni modificaron migraciones. No se ejecutó el seed contra Supabase.

## Interfaz de trabajo

`Optimización de corte` reúne `Distribución de corte` y `Vista previa de piezas`.
Se conserva la API real, el progreso NDJSON, las vistas 2D/3D y el detalle de
piezas, RBAC independiente para consultar/ejecutar/confirmar, y la confirmación
explícita con mensajes específicos para conflictos de estado e inventario.

Los rótulos visibles describen el trabajo de vidriería. First Fit aparece como
información secundaria del método. Los vidrios se identifican mediante el
catálogo real, también en resultados recuperados. Se muestran cantidades y
pedidos por vidrio/espesor. `Material #ID` queda como respaldo tras una consulta
correcta sin ese ID; una consulta fallida muestra un aviso y permite reintentar.

El conflicto de configuración muestra:

> No se puede calcular el corte porque faltan los parámetros de trabajo. Solicita al administrador revisar la configuración.

El detalle técnico queda en el registro de errores. Un POST rechazado antes de
crear el trabajo retira el progreso y el estado de ejecución, conserva los
pedidos revisados y permite reintentar explícitamente. La regresión automatizada
comprueba dos intentos y la ausencia de escrituras a pedidos/inventario.
Si se interrumpe una conexión ya aceptada, se retira el indicador de procesamiento
y se conserva el número del trabajo para recuperar su resultado sin reenviarlo.

Orders conserva cliente → vidrio/espesor → piezas. Cada vidrio es una sección
plegable con cantidad total y estado de completitud; sus piezas usan filas con
separadores. Agregar otro vidrio pliega los grupos completos. En edición se
inician plegados y se abren con teclado. El footer sticky conserva Cancelar y
Guardar cambios dentro del modal, comprobado en escritorio y móvil con varias
piezas y desplazamiento. Se mantienen geometrías, cantidades y payload.

## Validación de este hardening

| Comprobación | Resultado final |
| --- | --- |
| Backend seed + API de runs | **35 passed, 1 warning** (27.81 s) |
| `npm run test:unit` | **159 passed, 0 failed, 0 skipped** |
| `npm run test:component` | **458 passed**, 40 archivos |
| `npm run lint` | **0 errors, 0 warnings** |
| `npm run build` | **OK** |
| E2E focalizados, escritorio y móvil | **38 passed, 0 failed, 0 skips** (1.7 min) |
| Reverificación del optimizador tras el último ajuste visual | **20 passed, 0 failed, 0 skips** (1.1 min; subconjunto de los 38 anteriores) |
| `python -m alembic heads` | Única head **`s1opt02b4c6d`** |
| `git diff --check` | **OK** |

El warning backend es la deprecación existente de `httpx` en Starlette TestClient.
No se repitió el backend completo: el cambio backend se limita al seed optativo.
El baseline previo de 1976 passed y los 86 E2E completos pertenecen al cierre
anterior; no se presentan como una corrida nueva.

Comandos reproducibles desde `backend/`:

```text
python -m pytest tests/integration/optimization/test_configuration_seed.py tests/api/optimization/test_runs_api.py -q
python -m alembic heads
```

Desde `frontend/`, con el Python del venv backend en PATH y las credenciales
sintéticas de HU-015 definidas según `tests/e2e/hu015-rasterization.spec.js`:

```text
npm run test:unit
npm run test:component
npm run lint
npm run build
npm run test:e2e -- hu007-order-integration.spec.js hu012-client-order.spec.js s1-optimization-ui.spec.js hu015-rasterization.spec.js
```

Playwright usa su configuración existente: PostgreSQL temporal aislado, backend
en loopback y Vite local. El primer intento de iniciar Python bajo el sandbox de
Windows falló con código 101; la corrida final se realizó con los permisos locales
necesarios. Los logs, JSON y capturas de verificación quedaron en el directorio
temporal del sistema, sin regenerar la evidencia histórica del repositorio.

En Windows también se observaron avisos `NO_COLOR`/`FORCE_COLOR` y
`ConnectionResetError [WinError 10054]` del servidor local al cerrar conexiones.
PowerShell los clasificó como `NativeCommandError` al redirigir stderr. Se
verificó explícitamente `$LASTEXITCODE`: Playwright terminó con **código 0**,
20/20 casos aprobados y `errors: []` en su informe JSON. No se silenciaron los avisos.

Archivos entregados: [manifiesto final](S1-final-integration-files.txt).

Commits funcionales: `94382d7` (seed), `e571939` (Orders), `3924f3c`
(módulo de corte y rechazo del inicio), `668d380` (interrupción del progreso).
