# Diagnóstico y validación local Windows / WSL2 — 2026-11-01

Rama: `feature/optimization-multimotor-visual`.
Commit base: `5e836cdd9cc61eb212402d90dbe94a6776afcc75`.
Working tree inicialmente limpio. No se descartaron cambios ni se hicieron
commit, push, merge o despliegue. Python de Windows y de validación WSL2:
3.11.9. Node: 22.23.2. PostgreSQL de pruebas: 18.6.

## Causa del 503

Recorrido: `comparison_routes.start` → `ComparisonRuntime.reserve` →
`ComparisonProcessRunner.preflight` → `check_environment`.
En Windows, `sys.platform == "win32"` activa el rechazo explícito de Linux:

```text
ValueError: Linux procfs required
The above exception was the direct cause of:
RunError: La plataforma no permite ejecutar los tres motores con supervisión de recursos.
```

`RunRoute.safe` convierte el código `RESOURCE_UNAVAILABLE` a HTTP 503.
Sucede antes de aceptar el lote y crear workers. No es un fallo de geometría,
autenticación, CORS ni un límite de memoria ya excedido por un cálculo.
`OPTIONS` 200 solo acredita CORS. El supervisor usa spawn, `/proc`,
`resource.RLIMIT_AS` y `prctl(PR_SET_PDEATHSIG)`; instalar un paquete de Python
o sustituir fork no proporciona estas garantías en Windows.

La corrección operativa es usar WSL2. El cambio de producción añade al error
la plataforma requerida y la indicación de WSL2; conserva el código HTTP y la
causa encadenada. El diagnóstico CLI imprime plataforma/presupuestos sin DB.
No se modificaron políticas de motores, geometría, límites ni inventario.

Linux también puede rechazar antes de aceptar si no puede acceder a procfs o
RLIMIT_AS, hay menos de 1 GiB disponible o el supervisor supera 240 MiB RSS.
La sobrecarga de admisión tiene otro código: `OPTIMIZER_BUSY`, también 503.
Los fallos de workers después del 201 se persisten por ejecución: arranque,
memoria, tiempo, IPC, interrupción o persistencia; no son este rechazo inicial.

## Verificación del entorno y CI

La API activa en 8000 publicó el endpoint esperado en OpenAPI (versión global
1.0.0). El módulo servido por Vite en 5173 contenía
`VITE_API_URL=http://127.0.0.1:8000`. El proceso que escuchaba en 8000 era
Python Windows con Uvicorn y `--reload`. La versión global OpenAPI no identifica
un commit: el contrato de comparación es `comparison-v1`, schema 1.
Desde WSL2 la base configurada respondió a **solo SELECT 1**; no se imprimió
su destino ni credenciales, ni se consultaron datos de negocio.
También se comprobó Windows → localhost WSL2 con una sonda HTTP loopback de
una sola solicitud: HTTP 200, plataforma Linux y preflight disponible. La
sonda se cerró al responder. Esto verifica el acceso desde Windows que usará
el frontend al sustituir el backend nativo.

CI ejecuta el backend en Ubuntu 24.04 y Python 3.11 con PostgreSQL aislado.
`test_comparison_runner.py` crea procesos spawn reales, y los tests API y
`test_comparison_calculation.py` verifican el supervisor y PostgreSQL reales.
Las pruebas con mocks de fallos y las fixtures de componentes no sustituyen
esas pruebas de sistema. Que CI Linux pase no acredita soporte Windows.

## Pruebas ejecutadas

Desde `backend/` en WSL2:

```bash
export PYTHON_DOTENV_DISABLED=1 NEWGLASS_REQUIRE_POSTGRES=1
export NEWGLASS_TEST_PG_BIN=/usr/lib/postgresql/18/bin
.venv/wsl/bin/python -m scripts.check_comparison_environment
.venv/wsl/bin/python -m pytest tests/unit/optimization tests/integration/optimization tests/api/optimization -q -ra --junitxml=.venv/validation/backend.xml -o junit_family=legacy
.venv/wsl/bin/python -m pytest tests/api/optimization/test_comparisons_api.py::test_busy_comparison_has_no_accepted_work_and_runs_after_capacity_is_released -q -ra --junitxml=.venv/validation/overload.xml -o junit_family=legacy
```

Resultado: **845 + 1 aprobadas, 0 fallidas y 0 omitidas**. La prueba adicional
de sobrecarga se añadió después de recolectar la suite inicial: 503 unitarias,
151 de integración y 192 de API en total. Incluyen la regresión First Fit,
arranque conjunto, entradas idénticas, fidelidad de FF/BF/WF, aislamiento de
fallo de BF, límite duro de memoria, tiempo por motor y global, RSS acumulado,
limpieza al cerrar el consumidor, exclusión entre First Fit y comparación,
retención visual acumulada, idempotencia y confirmación.

Las pruebas nuevas comprueban rechazo accionable en Windows, ausencia de
escrituras al rechazar, liberación de admisión, tres resultados reales con
inventario idéntico y recuperación después de `OPTIMIZER_BUSY` con
`Retry-After: 15`. Los casos de timeout/RSS acumulado usan procesos reales con
un worker sintético bloqueado para provocar el límite; los positivos ejecutan
los motores reales. El caso de memoria individual provoca una asignación
mayor que RLIMIT_AS en BF y conserva los otros resultados.

En Windows, desde `backend/`:

```powershell
.\venv\Scripts\python.exe -m scripts.check_comparison_environment
.\venv\Scripts\python.exe -m pytest tests/unit/optimization/test_comparison_runner.py -q -k unsupported_platform
```

El diagnóstico salió con código **1**, `RESOURCE_UNAVAILABLE` y recomendación
WSL2. Las dos pruebas de plataforma pasaron (12 deseleccionadas).
En WSL2 el diagnóstico salió con código **0**, `available: true`.

En Windows, desde `frontend/`:

```powershell
npm.cmd run test:unit
npm.cmd run test:component -- src/features/optimization
npm.cmd run lint
npm.cmd run build
```

Resultado: **175 unitarias y 173 de componentes (17 archivos) aprobadas**;
lint y build aprobados. Advertencias existentes: deprecación de httpx en el
TestClient de Starlette y tamaño de chunk mayor a 500 kB en build.

## Comparación real e inventario

[real-comparison.json](real-comparison.json) contiene la ejecución capturada
del endpoint: dos pedidos sintéticos, cuatro unidades rectangulares, FF/BF/WF
con execution_id 1/2/3 y cuatro piezas colocadas cada uno. Los PID fueron
5104, 5106 y 5108. El RSS acumulado observado, incluida reserva auxiliar,
alcanzó 247820288 bytes (236.34 MiB), debajo de 1 GiB. El runner registró
`all_workers_stopped: true`; la admisión quedó en cero después del join.

Se compararon todas las filas y columnas de planchas, retazos y movimientos
antes y después, sin confirmar: idénticas. Los resultados se recuperaron por
GET con su método e identificador propios. Las confirmaciones de otras pruebas
solo modificaron sus bases sintéticas, nunca la base de desarrollo configurada.

## E2E reales: escritorio y móvil

Se utilizó una copia del código y Python 3.11.9 en Linux, con dependencias npm
Linux, Chromium y PostgreSQL temporal. Vite de prueba usó 5187 y la API de
prueba 8017, sin reemplazar los servicios de desarrollo en 5173/8000. La
configuración temporal deriva de `playwright.config.js`: selecciona únicamente
`optimization-comparison.spec.js`, conserva proyectos, assertions y timeouts,
cambia puerto/baseURL/CORS a 5187 y guarda un reporte JSON. Dotenv está
deshabilitado. No se interceptan respuestas para simular resultados.

Comando exacto usado, desde la raíz en PowerShell (el script de trabajo queda
bajo `.venv/validation`, ignorado por Git):

```powershell
wsl -d Ubuntu --cd 'C:\Users\fabri\Documents\TALLER INTEGRADOR I\optimizador-vidrio\backend' --exec bash .venv/validation/run-e2e.sh
```

Invocación subyacente, desde el frontend de esa copia Linux:

```bash
npx playwright test --config=playwright.wsl.config.mjs
```

Resultado final: **6 aprobadas, 0 fallidas, 0 omitidas y 0 retries**, en 63.43 s.
Verifican cuatro pestañas, tres procesos reales, eventos y máscaras por motor,
rotación real de 90°, cambio de pestañas sin recalcular, métricas reales,
inventario intacto antes de confirmar, selección BF, una confirmación y permisos
de consulta. Los hashes de supervisor, motores, workspace y spec de la copia
coinciden con este checkout; constan en
[validation-summary.json](validation-summary.json).

Se conserva también el resultado del intento inicial: las seis pruebas sobre
el backend/intérprete en `/mnt/c` aceptaron los POST con 201, pero excedieron
la espera de UI de 5 s antes de terminar. En el sistema de archivos Linux las
mismas pruebas pasaron sin cambiar esperas ni presupuestos operativos. Una
preparación intermedia en `/tmp` se perdió al cerrarse la instancia: esta
distribución monta `/tmp` como tmpfs. La repetición final usó una caché Linux
persistente. No se presenta aquel primer intento como aprobado.

## Consultas repetidas a pedidos

`pendingOrdersSource.js` tiene polling cada 15000 ms después de completar la
petición anterior, páginas de 100 y refrescos explícitos al aceptar, confirmar,
liberar y reiniciar. Evita solapamientos con `busy`; cancela al desmontar e
ignora respuestas del montaje anterior de StrictMode. La fuente/controlador
del workspace se mantienen con useMemo. La suite frontend probó paginación,
reintentos espaciados, cancelación y reinicio de StrictMode. No se encontró un
ciclo de renderizado que dispare solicitudes continuas. El polling continúa
aunque el intento de comparación sea rechazado: es independiente del 503.

## Archivos y límites de la entrega

Cambios: `backend/README.md`,
`backend/app/modules/optimization/infrastructure/comparison_runner.py`,
`backend/scripts/check_comparison_environment.py`,
`backend/tests/unit/optimization/test_comparison_runner.py`,
`backend/tests/api/optimization/test_comparisons_api.py`,
`docs/development/optimization-wsl2.md` y los tres archivos de esta evidencia.

El arranque habitual sigue en la [guía local WSL2](../../../../development/optimization-wsl2.md).
El servicio nativo de desarrollo no se reemplazó: para usar comparación en la
aplicación hay que detenerlo e iniciar el backend WSL2 con el comando indicado.
Se requiere un único proceso web y capacidad disponible. La supervisión RSS es
muestreada; RLIMIT_AS es el límite duro de espacio virtual por worker. El soporte
nativo Windows sigue sin implementarse; no existe fallback sin supervisión.
Los servidores de prueba quedaron cerrados. El clúster vacío `18/main` creado
por la instalación de PostgreSQL se dejó detenido y su servicio desactivado;
los binarios permanecen disponibles para las fixtures aisladas. Se retiró el
enlace temporal de Python que apuntaba a `/tmp`. Los entornos persistentes
Linux y los servidores Windows existentes se conservaron.
