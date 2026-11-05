# TA-043 / B01 — Catálogo y contratos de seis motores

**Veredicto: COMPLETADO en el alcance técnico de B01; puerta de revisión humana
pendiente.** No autoriza B02/B03 ni acredita la integración pública de seis motores.

Responsable: Fabricio Meléndez. Fecha: 03/11/2026, America/Lima.
[SPEC](../../../../specs/SPEC-TA-043-integracion-seis-motores.md),
[PLAN / B01](../../../../specs/PLAN-TA-043-integracion-seis-motores.md),
[contrato comparison-v2](../../../../contracts/optimization/comparison-v2.md).
SPEC y PLAN generales permanecen Draft; no se atribuye aprobación humana del código.

## Base, autorización y código probado

- Rama única: `feature/TA-043-integracion-seis-motores`.
- Inicio limpio en `1d20a70b1f1371f347fe60e63430812f786654a7`; planificación previa
  en `9ef0001` y `1d20a70`.
- `git fetch origin --prune` al iniciar B01: `origin/integration-02` sigue en
  `d85a8d3c4fa2ba1b3f70c401ed947adcfbe2470b`, sin avances sobre la base documentada.
  No se hizo merge, rebase, cherry-pick ni push.
- Fabricio autorizó exclusivamente catálogo, contratos, fixtures, pruebas
  T-01/T-07 pertinentes, ST-INC-01 y commits locales; detenerse en la puerta B01.
- Código/contratos probados y registrados en el commit
  `5dcc3164c0ff323eee2119f075cf92233f3823a3` —
  `feat(TA-043): define six-engine comparison contracts`.
- Refuerzo posterior de la identidad de máscaras v2 aisladas:
  `8ab8eaa2859f9382f87b5a2bd9972d39faef3215` —
  `fix(TA-043): validate standalone comparison mask ownership`. Las 49 pruebas
  B01 se repitieron sobre ese refuerzo; el smoke final también incluye sus bytes.
- Las ejecuciones ocurrieron sobre el árbol de trabajo antes de registrar los
  commits. [validation.json](validation.json) y [smoke/cleanup.json](smoke/cleanup.json)
  conservan hashes de los archivos realmente ensayados. Los artefactos de prueba
  y la actualización documental se registran en el commit local posterior.

## Archivos y alcance entregado

Rutas relativas a `backend/app/modules/optimization/`:

| Archivo nuevo | Responsabilidad B01 |
|---|---|
| `application/comparison_catalog.py` | Catálogos v1/v2 separados, orden, nombres, clases de motor/resultado y capacidades reales |
| `application/comparison_v2_contracts.py` | DTO inmutable de entrada, resultado y diagnóstico; validación de identidad/completitud/causa |
| `infrastructure/comparison_v2_snapshot.py` | Codecs puros de entrada 2 y resultado 3; lectura compatible de resultados 1/2, sin acceso DB |
| `presentation/comparison_v2_schemas.py` | Resúmenes, resultados, acciones, eventos, máscaras y validaciones de ciclo/identidades |
| `presentation/comparison_v2_serialization.py` | Proyección pura de layout v2 reutilizando geometría/R4, sin ejecutar ni persistir |

Otros archivos nuevos:

- `frontend/src/features/optimization/comparisonV2Contract.js`: catálogo y parsers
  optativos de v2, sin transporte ni conexión a la UI actual.
- `backend/tests/unit/optimization/test_comparison_v2_contract.py` y
  `comparison_v2_support.py`: pruebas y generador del fixture con motores reales directos.
- `frontend/src/features/optimization/__tests__/ComparisonV2Contract.test.jsx`:
  fixture compartido, compatibilidad, rechazos y scopes, sin implementar B07.
- `backend/tests/optimization_b01_smoke.py`: arnés Linux de ST-INC-01 con copia y
  TMPDIR propios; reutiliza runtimes/dependencias instalados, no instala ni usa BD compartida.
- `docs/contracts/optimization/comparison-v2.md` y `comparison-v2.json`:
  contrato y ejemplos con procedencia explícita.
- Este directorio: reportes, intentos de prueba, capturas y comprobación de limpieza.

Archivos existentes modificados:

- `frontend/tests/e2e/optimization-comparison.spec.js`: un smoke B01 adicional
  dentro del spec ya incluido en el gate TA-040; no se altera el gate ni sus pruebas previas.
- SPEC y PLAN TA-043: autorización limitada, progreso/evidencia y parada B01;
  no se cambian requisitos, CA, matriz, agrupaciones, dependencias ni decisiones.

No se modificaron motores, runner/runtime productivos, UoW, ORM, migraciones,
contratos/fixtures v1, parsers legacy ni componentes visuales de producción.

## Catálogo y formatos revisables

Orden: **FF → BF → WF → HF → M5 → M6-BS**; etiquetas visibles
**FF, BF, WF, HF, BRF, BS-2**. Las clases asociadas son FirstFitOptimizer,
BestFitOptimizer, WorstFitOptimizer, HoleFillingOptimizer,
BestResidualFitOptimizer y BeamSearchOptimizer, respectivamente.
M6-BS queda ligado al ancho 2. Códigos desconocidos, aliases y duplicados se rechazan;
el orden de una respuesta no identifica por sí solo una ejecución.

Versiones independientes: HTTP/eventos/máscaras/layout v2 = schema_version 2;
entrada geométrica = input_version 1; entrada congelada del agregado =
comparison_snapshot_version 2; resultado durable = snapshot_version 3.
Versión optimista y versión de configuración permanecen separadas.

Los resultados conservan COMPLETE/PARTIAL/FAILED y diagnóstico explícito. M6
conserva sus cuatro motivos de recurso; una unidad interrumpida usa RESOURCE_LIMIT,
no NO_FIT. La primera versión visual solo define contadores de búsqueda provisionales,
sin ramas dibujadas; colocaciones M6 requieren FINAL_REPLAY de la solución final.
El adaptador/progreso real de seis motores sigue pendiente de B03/B05/B07.

## Pruebas y resultados reales

Entornos: Python **3.11.9 en Ubuntu WSL2**, Node **22.23.2**; pruebas frontend
de contrato en Windows. Smoke en Linux con PostgreSQL **18.6**, FastAPI, Vite y
Chromium real, proyectos escritorio y móvil. Dependencias de los lockfiles actuales.

| Selección | Resultado | Evidencia |
|---|---|---|
| Backend final: B01, codecs/schemas v1, run-v1 y regresión de seis motores | **266 passed, 0 failed, 0 skipped** | [texto](backend-final-tests.txt), [JUnit](backend-final-contracts.xml) |
| Pruebas nuevas B01 tras el refuerzo final de identidad de máscaras | **49 passed**; selección solapada con las 266 anteriores, no sumar | [texto](backend-ownership-final.txt), [JUnit](backend-ownership-final.xml) |
| Frontend: ComparisonV2Contract, ComparisonContract, VisualContract, ContractRunUI | **44 passed**, cuatro archivos | [texto](frontend-tests.txt) |
| Lint frontend | **PASS**, exit 0 | [texto](frontend-lint.txt); ESLint focal del último test añadido también exit 0 |
| Build frontend | **PASS**, exit 0; aviso no bloqueante de chunk >500 kB | `npm.cmd run build`, 1.54 s y 1997 módulos en la ejecución de esta sesión; no se cambian límites del build |
| ST-INC-01 | **2 passed**, escritorio/móvil | [ejecución](smoke/execution.txt), [reporte](smoke/playwright-report.json), [limpieza](smoke/cleanup.json) |

Un intento ampliado anterior dio **265 passed, 1 failed** al leer los mínimos
métricos serializados como strings sin conversión explícita a Decimal. Se corrigió
solo el codec nuevo y la selección completa de 266 pasó después. Se conservan
[salida inicial](backend-tests.txt) y [JUnit inicial](backend-contracts.xml); no son
el resultado final ni se suman a los conteos. La primera generación del fixture
también requirió usar la conversión JSON de Decimal ya existente, sin cambiar motores.
Las salidas conservadas solo normalizan espacios finales y saltos de línea para
cumplir `git diff --check`; resultados y trazas no se sustituyen por resúmenes.

### Comandos reproducibles

Desde `backend/` en Linux/WSL2 con el venv preparado:

```bash
export PYTHON_DOTENV_DISABLED=1
.venv/wsl/bin/python -m tests.unit.optimization.comparison_v2_support
.venv/wsl/bin/python -m pytest tests/unit/optimization/test_comparison_v2_contract.py tests/unit/optimization/test_comparison_snapshot.py tests/unit/optimization/test_comparison_contract.py tests/api/optimization/test_run_contract.py tests/unit/optimization/test_first_fit.py tests/unit/optimization/test_best_fit.py tests/unit/optimization/test_worst_fit.py tests/unit/optimization/test_hole_filling.py tests/unit/optimization/test_best_residual_fit.py tests/unit/optimization/test_beam_search.py tests/unit/optimization/test_beam_search_t02.py -q -ra --junitxml=../docs/evidence/sprint-02/TA-043/B01/backend-final-contracts.xml
.venv/wsl/bin/python -m tests.optimization_b01_smoke --runtime-root /home/fabri/.cache/newglass-validation.SXhCMM
```

El último comando requiere una carpeta Linux con `node-v22.23.2-linux-x64/bin/node`,
`backend/.venv/wsl/bin/python`, dependencias frontend y Chromium previamente
instalados. Ese runtime se reutiliza; la aplicación se copia desde el checkout
actual a `/tmp/newglass-ta043-b01-*`, excluyendo `.env`, venv y salidas generadas.
Vite utiliza cacheDir propio y carga nativa de config. Backend/Chromium/PostgreSQL
usan TMPDIR dentro de esa copia. Puertos 8017/5188 deben estar libres.
Se aplican únicamente las migraciones existentes sobre PostgreSQL efímero propio;
no se crean migraciones ni se toca Supabase/Heroku. No se cambian los presupuestos.

En `frontend/`, PowerShell/Node Windows para los contratos:

```powershell
npm.cmd run test:component -- src/features/optimization/__tests__/ComparisonV2Contract.test.jsx src/features/optimization/__tests__/ComparisonContract.test.jsx src/features/optimization/__tests__/VisualContract.test.jsx src/features/optimization/__tests__/ContractRunUI.test.jsx
npm.cmd run lint
npm.cmd run build
```

El smoke usa Playwright con `--grep 'TA-043 B01'` en ambos proyectos y el spec
comparativo real. Es una selección local explícita, no el gate integral de CI.
El arnés rechaza ejecutarse como sustituto de ese gate si CI/gate están habilitados.
No utiliza mocks de red ni motores, ni credenciales/BD de `.env`.

### Qué acredita ST-INC-01

- Arranque de FastAPI, frontend y PostgreSQL propio; comunicación/login reales.
- OpenAPI conserva `/comparisons` y `/runs`; aún no expone `/comparisons-v2`.
- UI y API aceptan y consultan tres ejecuciones FF/BF/WF completas; cuatro pestañas.
- Liberación sin confirmar y nuevo cálculo FF por `/runs`, con resultado visible.
- Stock controlado de planchas/retazos sin consumo tras ambas simulaciones.
- Cero errores de navegador y cleanup con `processes_before: []`,
  `processes_after: []`, `runner_exit: 0`, `temporary_copy_removed: true`.

La copia y el clúster propios se destruyeron al terminar; los PID se comprobaron
con tiempo de inicio. No se dejaron servicios de esta ejecución ni se limpiaron
procesos por nombre. Los JSON de comparación/FF y capturas están en
`smoke/chromium-desktop/` y `smoke/chromium-mobile/`.

Esto no acredita seis ejecuciones públicas, CA-S01–CA-S10 completos, rollback
v2, recursos/concurrencia v2 ni el orden supervisor/admisión de B05. ST-INT y las
funcionalidades futuras permanecen pendientes, sin PASS anticipado.

## Criterios de B01 y continuidad

| Criterio TA-043 | Verificación B01 | Pendiente integral |
|---|---|---|
| CA-02 / RF-02 | Catálogo exacto, nombres, IDs, clases, orden, duplicados/desconocidos y respuestas reordenadas: PASS contractual | Creación de seis ejecuciones reales en B02/B05 |
| CA-11 / RF-11 | Fixtures/lectores históricos intactos y smoke v1/legacy real: PASS del alcance B01 | Historia antes/después de migración en B02 |
| CA-12 / RF-12 | Perfil/schemas/codecs/parser v2 y rechazo de perfiles incorrectos; sin endpoint incompleto: PASS contractual | API funcional y conflictos de acceso cruzado en B06 |
| CA-14 / RF-14 | Registro optativo, tipos de resultado y contratos de seis sin ampliar globales v1: PASS contractual | Consumo por runner/UoW/runtime/frontend en sus bloques |

## Inventario de supuestos de tres y dependencias

Rutas backend relativas a `backend/app/modules/optimization/` y frontend a
`frontend/src/features/optimization/`. Se identifican, **no se sustituyen** en B01.

| Punto vigente | Supuesto / siguiente bloque |
|---|---|
| `application/comparison_contracts.py:METHODS` | FF/BF/WF; separar agregado por perfil al integrarlo en B05 |
| `application/comparison.py:DEFAULT_METHODS/EXTENDED_METHODS` | Tres por defecto y M5 interno opcional; adaptación de entrada de ejecución en B03 |
| `domain/problem.py:OptimizationResult.method` | Anotación base no enumera HF/M6; subclases conservan identidad; revisar contratos de adaptadores B03 sin cambiar políticas |
| `presentation/comparison_schemas.py` | Literal de tres y cardinalidad tres en resumen/Accepted; conservar para v1, usar modelos v2 al conectar B06 |
| `infrastructure/comparison_snapshot.py:RESULT_TYPES` | Tres tipos; lectores antiguos intactos, codec nuevo optativo para B02 |
| `infrastructure/comparison_uow.py:create/get` | Crea METHODS y exige tres filas; B02/B05 deben distinguir perfil almacenado |
| `backend/app/models.py:ck_ejecuciones_metodo` | CHECK solo FF/BF/WF; migración futura B02 |
| `infrastructure/comparison_runner.py` | ENGINES de tres, terminal<3 y barrera==3; B03/B04/B05 |
| `presentation/comparison_runtime.py` | Tres contextos/sesiones visuales; B05/B07 bajo presupuesto total |
| `infrastructure/comparison_confirmation.py` | Nombres de tres y contexto elegido; B08 |
| `comparisonApi.js` | METHODS/nombres/cardinalidad tres; conservar v1 y usar parser v2 desde B07 |
| `ComparisonWorkspace.jsx` / controlador | Pestañas desde catálogo v1, selección y carga actuales; B07/B08 |
| `OptimizationPage.jsx` | Etiquetas de tres en vista legacy; no duplicar UI en B07 |
| `runContract.js`, `visualContract.js` | Defaults FF y contratos congelados; reutilización explícita por perfil, no ampliar defaults |

Los `len(vertices)<3`, rotaciones `<360` y el total de piezas de un fixture no son
cardinalidades de motores; no deben reemplazarse con seis.

B02 debe acordar composición de entrada congelada y metadatos runtime, migración
aditiva/lectura histórica y rechazo seguro de downgrade. B03 debe adaptar M6
`run()`/callbacks/diagnósticos sin TypeError por on_visual ni pérdidas de razones,
y preservar las políticas HF/BRF/BS-2. La concurrencia/180 s sigue pendiente de
viabilidad en B04 y la parada segura de B05 sigue siendo requisito, no resultado
de B01. No se modifica HU-018 ni se incorporan sus commits.

**Parada obligatoria:** Fabricio debe revisar catálogo, versiones, estados,
diagnósticos/eventos M6, compatibilidad y resultados de prueba antes de autorizar
consumidores dependientes. No se inició B02, B03 ni ningún otro bloque.
