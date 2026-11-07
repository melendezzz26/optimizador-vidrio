# Comparación FF/BF/WF local desde Windows

El supervisor actual exige Linux: procfs (`/proc`), `resource.RLIMIT_AS` y
`prctl(PR_SET_PDEATHSIG)`. Python nativo de Windows rechaza la admisión con
HTTP 503 `RESOURCE_UNAVAILABLE`, antes de crear ejecuciones o bloquear pedidos.
`OPTIONS` 200 comprueba CORS, no la disponibilidad del supervisor.

Se utiliza `multiprocessing` con **spawn**, no fork. Cambiar el método de
arranque o instalar una dependencia Python no aporta los controles del kernel
ausentes en Windows. Un soporte nativo exigiría otro adaptador con Job Objects,
límites duros, contabilidad acumulada, identidad de procesos y limpieza probada
al morir el supervisor. WSL2 permite conservar la implementación Linux y las
protecciones ya verificadas en CI. El frontend puede continuar en Windows.

Referencias: [resource de Python](https://docs.python.org/3.11/library/resource.html),
[PR_SET_PDEATHSIG](https://man7.org/linux/man-pages/man2/PR_SET_PDEATHSIG.2const.html),
[acceso localhost de WSL2](https://learn.microsoft.com/en-us/windows/wsl/networking).

## Preparación

En PowerShell, comprobar WSL2 y entrar al backend del checkout:

```powershell
wsl --list --verbose
wsl -d Ubuntu --cd 'C:\Users\fabri\Documents\TALLER INTEGRADOR I\optimizador-vidrio\backend'
```

Los siguientes comandos son de **Bash en WSL2**. Se necesita Python 3.11 con
venv o [uv](https://docs.astral.sh/uv/getting-started/installation/).
Con uv, el intérprete y el entorno Linux pueden guardarse dentro de `.venv`,
ignorado por Git. No reutilizar `venv/Scripts/python.exe`, que es Windows.

```bash
export UV_PYTHON_INSTALL_DIR="$PWD/.venv/python"
uv python install 3.11.9
uv venv .venv/wsl --python 3.11.9
uv pip install --python .venv/wsl/bin/python -r requirements.txt
.venv/wsl/bin/python --version
.venv/wsl/bin/python -m scripts.check_comparison_environment
```

Sin uv, usar `python3.11 -m venv .venv/wsl` y
`.venv/wsl/bin/python -m pip install -r requirements.txt`.
El diagnóstico no conecta a la base ni imprime variables de entorno.
`available: true` acredita el preflight; las pruebas con spawn que siguen
acreditan el cálculo real y la terminación de procesos.

El backend sigue leyendo `backend/.env`. Comprobar privadamente que su base
de desarrollo es accesible desde WSL2. En red NAT, `127.0.0.1` en WSL2 no
designa al PostgreSQL de Windows; usar la dirección del host o una base Linux.
No cambiar una base compartida, ejecutar migraciones ni seed para resolver
este 503. La base de desarrollo debe tener la migración comparativa y una
configuración vigente válida (paso angular 5°).

## Arranque habitual

Detener con Ctrl+C el Uvicorn nativo que ocupe 8000 y ejecutar en WSL2:

```bash
.venv/wsl/bin/python -m scripts.dev_server
```

Mantener un único proceso web (`--workers` no debe aumentarse: la admisión es
local al proceso). En otra terminal PowerShell, desde `frontend/`:

```powershell
$env:VITE_API_URL = 'http://127.0.0.1:8000'
npm.cmd run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Para desarrollar con recarga usar `.venv/wsl/bin/python -m scripts.dev_server --reload`.
El lanzador excluye los árboles `.venv`, `venv`, `tests`, `scripts`, `alembic` y
`.pytest_cache`, y `seed.py`. Para validar un cálculo usar el comando estable
anterior. Reiniciar o recargar descarta eventos/máscaras en memoria; los
resultados ya persistidos se recuperan por ID, aunque los recursos visuales
temporales devuelvan 410. No utilizar `--reload` sin estas exclusiones para
generar evidencia dentro de `.venv/validation`.

El pool PostgreSQL por proceso queda limitado por defecto a cinco conexiones,
sin overflow (`DB_POOL_SIZE=5`, `DB_MAX_OVERFLOW=0`, `DB_POOL_TIMEOUT=30`). Revisar
solo estas variables si el entorno las sobrescribe; no imprimir `.env`. Esto
reserva margen respecto del límite de 15 sesiones observado, pero otros clientes
también consumen esa cuota. No aumentar límites del proveedor para esta prueba.
La autorización compartida libera su transacción de lectura antes del UoW o
repositorio del endpoint (incluido Inventario);
los workers de cálculo no consultan la base. DNS/conectividad y disponibilidad
del proveedor siguen siendo prerrequisitos externos.

Usar únicamente el backend WSL2 contra esa base: dos instancias compartirían
datos, pero tendrían admisiones independientes. No hace falta abrir el servicio
en `0.0.0.0` para el acceso local de Windows.

En `http://127.0.0.1:8000/openapi.json` debe existir
`POST /api/optimization/comparisons`. El contrato de respuesta es
`profile: comparison-v1`, `schema_version: 1`; la versión global FastAPI
`1.0.0` no identifica el commit. En el navegador comprobar el destino de la
solicitud POST, un 201 y tres `execution_id` diferentes con métodos FF/BF/WF.
Seleccionar pedidos pequeños compatibles y pulsar “Comparar con los tres
motores”. Consultar las tres pestañas y sus respuestas `/executions/{id}`.
La comparación no confirma ni modifica existencias. No pulsar confirmar si
solo se desea simular.

## Validación aislada y reproducible

Desde `backend/`, en WSL2, instalar los binarios de PostgreSQL para pruebas
si faltan (`sudo apt-get install postgresql`). Las fixtures crean y destruyen
su propio clúster loopback; nunca usan la base de `.env`:

```bash
export PYTHON_DOTENV_DISABLED=1
export NEWGLASS_REQUIRE_POSTGRES=1
export NEWGLASS_TEST_PG_BIN="$(pg_config --bindir)"
.venv/wsl/bin/python -m pytest tests/unit/optimization tests/integration/optimization tests/api/optimization --ignore=tests/unit/optimization/test_comparison_runner.py -q -ra
.venv/wsl/bin/python -m pytest tests/unit/optimization/test_comparison_runner.py -q -ra
```

El segundo proceso mantiene independiente el RSS de pytest para probar el límite
real de 240 MiB del supervisor. Se ejecutan ambos grupos, igual que en CI; no se
aumenta el presupuesto ni se omiten las pruebas del runner.

Estas suites incluyen motores spawn reales, fidelidad frente a ejecución
directa, límite duro de memoria, presupuesto RSS acumulado, tiempo global y
por motor, fallo parcial, exclusión de First Fit/comparación y limpieza.
El test `test_real_comparison_preserves_entire_inventory_and_returns_three_owned_results`
captura todas las columnas/filas de planchas, retazos y movimientos antes y
después, y verifica resultados persistidos sin confirmar.

En Windows, desde `frontend/`:

```powershell
npm.cmd run test:unit
npm.cmd run test:component -- src/features/optimization
```

El Playwright estándar inicia el backend con `python`; para E2E de comparación
ejecutarlo en Linux con Python 3.11, PostgreSQL, Node 22 y Chromium disponibles,
y dependencias npm instaladas para Linux. No compartir los `node_modules`
nativos de Windows con Linux: usar una copia o checkout separado para el
frontend Linux, conservando el árbol que utiliza Vite en Windows.
Desde `frontend/` en ese entorno:

```bash
export PATH="$(realpath ../backend/.venv/wsl/bin):$PATH"
export PYTHON_DOTENV_DISABLED=1 NEWGLASS_REQUIRE_POSTGRES=1
export NEWGLASS_TEST_PG_BIN="$(pg_config --bindir)"
export PLAYWRIGHT_CHANNEL=chromium
npm ci
npx playwright install --with-deps chromium
npm run test:e2e -- tests/e2e/optimization-comparison.spec.js
```

El puerto 5173 y el 8017 deben estar libres para ese arnés. Las pruebas de
componentes usan adaptadores/fixtures: prueban UI y contrato. La suite
`optimization-comparison.spec.js` usa HTTP y los tres procesos reales, sin
interceptar la API para inventar resultados.

Para E2E con las esperas originales, guardar código e intérprete en el sistema
de archivos Linux (por ejemplo, bajo `~/newglass-validacion`); el acceso a muchos
archivos desde `/mnt/c` puede demorar el arranque de los workers. Esto no cambia
los límites operativos de 30/120/900 s (el global era 180 s; ver SPEC-TA-037 v1.4
y SPEC-TA-043). La evidencia de esta corrección registra
también el intento inicial que excedió la espera de UI de 5 s sobre `/mnt/c`.

## Diagnóstico de otros rechazos y consultas de pedidos

En Linux, 503 `RESOURCE_UNAVAILABLE` también puede indicar procfs inaccesible,
ausencia de `resource.RLIMIT_AS`, menos de 1 GiB disponible (incluido cgroup v2)
o RSS del supervisor mayor a 240 MiB. `OPTIMIZER_BUSY` es un rechazo distinto
de admisión/concurrencia, con `Retry-After`. Fallos posteriores a aceptar el
trabajo quedan como fallos de ejecución: arranque, memoria, tiempo, IPC,
muerte del worker o persistencia; no equivalen a “sin encaje”.

Se conservan 256 MiB de espacio virtual por worker, 1 GiB RSS acumulado,
240 MiB del supervisor, 16 MiB de reserva auxiliar, 30 s de arranque, 120 s
de cálculo por motor y 900 s globales (antes 180 s; ver SPEC-TA-037 v1.4 y
SPEC-TA-043). El RSS es un umbral muestreado cada
25 ms; el límite duro por worker es de espacio virtual. La admisión se libera
solo después de detener/join los hijos y lectores.

`pendingOrdersSource.js` consulta pedidos pendientes al montar y luego cada
15 segundos **después** de terminar la consulta anterior, con páginas de 100,
deduplicación, exclusión de solicitudes simultáneas y aborto al desmontar.
También refresca al aceptar, confirmar, liberar o preparar otro corte. React
StrictMode puede provocar un montaje inicial adicional en desarrollo. Este
polling explica consultas periódicas; una ráfaga continua sin paginación ni
acciones requeriría revisar sus intervalos y montajes en Network.
