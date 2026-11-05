# TA-043 / B02 — Compatibilidad histórica y evolución del esquema

**Resultado: COMPLETADO en el alcance técnico autorizado de B02.** Detenerse para
revisión de Fabricio; B03–B11 y el cierre de TA-043 no están autorizados.
SPEC y PLAN siguen Draft. Fecha: 03/11/2026, America/Lima.

[SPEC](../../../../specs/SPEC-TA-043-integracion-seis-motores.md),
[PLAN / B02 y ST-INC-02](../../../../specs/PLAN-TA-043-integracion-seis-motores.md),
[contrato v2](../../../../contracts/optimization/comparison-v2.md).

## Preflight y alcance

- Inicio con árbol limpio en `feature/TA-043-integracion-seis-motores`, HEAD
  `f65292f9c0da706f88b2d87ca12194486e6c990c`; presentes B01 `5dcc316`, `8ab8eaa`,
  `f65292f`. Base oficial `integration-02`, `d85a8d3c4fa2ba1b3f70c401ed947adcfbe2470b`.
- Revisados RF-11/13/14, CA-11/13/14, B02, ST-INC-02 y E0/D0/P0/L0; catálogos,
  DTO, schemas, codecs y pruebas B01. Sin incompatibilidad relevante que requiera
  cambiar el contrato. Se reutilizan los artefactos B01, no se regeneran fixtures.
- HEAD Alembic anterior único `s2cmp01a1b2c`; inspección de PostgreSQL aislado y
  comparación con ORM sin divergencias. Existían CHECK de tres métodos, UNIQUE
  `(id_optimizacion, metodo)`, FK de ejecución al agregado y FK de selección.
- No se hicieron fetch/merge/rebase/push en B02 ni cambios en `integration-02`.
  Todas las migraciones y escrituras de prueba fueron en PostgreSQL temporal propio.

Commits locales de producto, posteriores a las validaciones:

- `4ed83fddf8327fced63b10e29c16655fcfc3763a` — migración/ORM y contratos de esquema.
- `66a54c9efa339b98cf3ba950243b2d0ff973ad11` — persistencia y pruebas T-02.

Los ensayos se realizaron sobre el árbol de trabajo antes de esos commits;
[validation.json](validation.json) y [smoke/cleanup.json](smoke/cleanup.json)
identifican los bytes realmente ensayados y comprueban su correspondencia con
el código final. El commit posterior registra smoke y evidencias. La validación
documental conserva exactamente requisitos, CA y matriz, y verifica enlaces,
sintaxis Python, `git diff --check`, puertos libres y ausencia de raíces temporales.

## Archivos y diseño entregado

| Archivo / grupo | Cambio B02 |
|---|---|
| `backend/alembic/versions/s2cmp02d4e6f8_six_method_catalog.py` | Nueva revisión hija de `s2cmp01a1b2c`, solo amplía el CHECK y protege downgrade |
| `backend/app/models.py` | Alinea únicamente `ck_ejecuciones_metodo` con seis códigos |
| `application/comparison_persistence_contracts.py` | Vistas durables v2 y referencias visuales con propietario completo |
| `infrastructure/comparison_v2_uow.py` | Repositorio/UoW optativo, seis registros, versiones, estados, resultados/diagnósticos, lectura compatible y propiedad |
| `infrastructure/comparison_uow.py` | El lector v1 rechaza explícitamente un agregado v2; conserva su lectura histórica |
| `backend/tests/comparison_history.py` | Fingerprints SQL de historia independientes de la configuración de aplicación |
| `backend/tests/integration/optimization/test_comparison_v2_{migration,persistence}.py` | 28 casos PostgreSQL de T-02, incluida historia real anterior al upgrade |
| `backend/tests/model_contracts.py`, pruebas de comparación/migración, bootstrap, clientes e inventario | Congela metadata anterior y actualiza expectativas del nuevo HEAD; no cambia funcionalidad de esos módulos |
| `backend/tests/optimization_b02_upgrade.py` | Utilidad de smoke restringida al clúster local propio del servidor E2E |
| `backend/tests/optimization_b01_smoke.py`, `backend/tests/e2e_server.py` | Reutiliza arnés B01 con `--block B02`, esquema anterior optativo y TMPDIR propio |
| `frontend/tests/e2e/optimization-comparison.spec.js` | ST-INC-02 en el spec crítico existente, escritorio/móvil; ninguna UI productiva modificada |
| Contrato v2, SPEC, PLAN y este directorio | Composición durable, autorización/evidencia limitada a B02; requisitos y matriz conservados |

Las rutas `application/` e `infrastructure/` de la tabla son relativas a
`backend/app/modules/optimization/`. No se modifican heurísticas, codecs B01,
contrato/fixture v1, runner, coordinador, admisión ni frontend productivo.

### Esquema y downgrade

Anterior: `metodo IN ('FF', 'BF', 'WF')`.
Nuevo: `metodo IN ('FF', 'BF', 'WF', 'HF', 'M5', 'M6-BS')`.

No hay nuevas tablas, columnas ni backfill; no se editan migraciones anteriores.
FK, unicidad, índices y demás CHECK permanecen. PostgreSQL rechaza método
desconocido, método duplicado y agregado inexistente. El downgrade toma bloqueos
de tablas para serializar su comprobación con escritores, inspecciona perfil,
versiones de agregado/resultado y métodos y rechaza incompatibilidades **antes de
cualquier DDL**. Las pruebas comparan esquema, versión Alembic y datos tras el
rechazo. Vacío e historia FF/v1 compatibles permiten volver al padre y re-upgrade.
Rollback operativo futuro: deshabilitar creación v2 manteniendo lectores; no
eliminar historia v2 para forzar un downgrade.

### Persistencia y límites de lo demostrado

El agregado conserva el sobre B01 de entrada versión 2, sus seis métodos y hash,
con metadata runtime separada. `comparison_version` sigue siendo optimista SQL.
Cada ejecución conserva identidad de dueño, despacho y resultado snapshot 3,
completitud, diagnóstico y residuales. No se cambia el significado de estados SQL
históricos. Referencias visuales/máscaras se resuelven por comparación, ejecución
y método; guardar metadata no promete disponibilidad de bitmap/eventos retenidos.

La creación es idempotente bajo el mismo bloqueo por actor/clave que v1; entrada
incompatible o perfil ajeno falla. Actualizaciones usan bloqueo y versión esperada.
La lectura compatible conserva los DTO originales de FF y v1, sin inventar tres
ejecuciones adicionales ni recalcular. Los resultados directos de seis motores se
usan para comprobar el almacenamiento; **no se ejecuta un coordinador v2**.
Las cuatro razones M6 se ensayan como diagnósticos tipados persistidos: no son
mediciones de agotamiento real ni sustituyen B03/B04.

El repositorio no inicia procesos ni consume/reserva stock, no transiciona pedidos
para iniciar cálculos y no expone selección/confirmación v2. Acepta una entrada ya
congelada; la captura consistente y el ciclo de pedidos pertenecen a B05. La marca
interna de parada persiste un hecho observado, pero B05 debe obtener la prueba real
de parada antes de invocarla/liberar admisión; no habilita aquí una API de cierre.

## Entorno y comandos reproducibles

WSL Ubuntu, Python 3.11.9, PostgreSQL 18.6, Node 22.23.2 y Chromium real instalado
por Playwright. Dependencias ya instaladas; no se cambiaron versiones ni presupuestos.
Desde `backend/`, con `.venv/wsl/bin` en PATH:

```sh
export PYTHON_DOTENV_DISABLED=1 NEWGLASS_REQUIRE_POSTGRES=1
export NEWGLASS_TEST_PG_BIN=/usr/lib/postgresql/18/bin
python -m pytest tests/integration/optimization/test_comparison_v2_persistence.py tests/integration/optimization/test_comparison_v2_migration.py -q -ra --tb=short
python -m pytest tests/integration/optimization/test_comparison_v2_persistence.py tests/integration/optimization/test_comparison_v2_migration.py tests/integration/optimization/test_comparison_migration.py tests/integration/optimization/test_comparison_persistence.py tests/integration/optimization/test_comparison_confirmation.py tests/integration/test_staging_bootstrap.py tests/integration/test_clients_migration.py tests/integration/inventory/test_repository.py tests/unit/optimization/test_comparison_v2_contract.py -q -ra --tb=short --junitxml=../docs/evidence/sprint-02/TA-043/B02/regression-junit.xml
python -m pytest tests/unit/optimization/test_comparison_snapshot.py tests/unit/optimization/test_comparison_contract.py tests/api/optimization/test_run_contract.py tests/api/optimization/test_comparisons_api.py -q -ra --tb=short --junitxml=../docs/evidence/sprint-02/TA-043/B02/legacy-contract-junit.xml
python -m pytest tests/integration/optimization/test_comparison_v2_migration.py::test_history_created_before_upgrade_preserves_ff_snapshot1_and_comparison_snapshot2 -q -ra --tb=short --junitxml=../docs/evidence/sprint-02/TA-043/B02/historical-final-junit.xml
python -m tests.optimization_b01_smoke --block B02 --runtime-root /home/fabri/.cache/newglass-validation.SXhCMM
```

El arnés smoke verifica runtimes, puertos, copia privada y destinos loopback;
rechaza su uso como sustituto del gate CI completo. El runtime-root es una caché
local de esta máquina; en otra máquina se debe indicar la instalación Linux
equivalente. No apunta a `.env`, Supabase, Heroku ni servicios compartidos.

Desde `frontend/`, usando `npm.cmd` en PowerShell:

```sh
npm run test:component -- src/features/optimization/__tests__/ComparisonV2Contract.test.jsx src/features/optimization/__tests__/ComparisonContract.test.jsx src/features/optimization/__tests__/VisualContract.test.jsx
npm run lint
```

El comando capturado de componentes incluyó también el filtro inexistente
`RunContract.test.jsx`; Vitest seleccionó **tres** archivos existentes, 27 casos.
No se acredita ese filtro como prueba ejecutada. El comando anterior reproduce
la misma selección real.

## Resultados y trazabilidad

| Ejecución | Resultado real | Evidencia |
|---|---|---|
| T-02 inicial | 23 PASS / 3 FAIL, interferencia de revisión entre casos; corrección descrita abajo | Registro de incidencia de esta sección; salida original observada, sin log completo archivado |
| T-02 tras corrección, antes de dos casos adicionales | 26 PASS | [b02-tests.txt](b02-tests.txt), [JUnit](b02-junit.xml) |
| T-02 final + B01 + persistencia v1/migraciones afectadas | 172 PASS, 0 skip, incluida T-02 de 28 casos y B01 de 49 | [regression-tests.txt](regression-tests.txt), [JUnit](regression-junit.xml) |
| Contratos/snapshots históricos y API v1/legacy | 77 PASS, 0 skip | [legacy-contract-tests.txt](legacy-contract-tests.txt), [JUnit](legacy-contract-junit.xml) |
| Repetición final de historia FF calculada antes de migrar | 1 PASS, repetido; no se suma | [historical-final.txt](historical-final.txt), [JUnit](historical-final-junit.xml) |
| Contratos frontend B01/v1/visual | 27 PASS, tres archivos | [frontend-contracts.txt](frontend-contracts.txt) |
| ESLint | PASS | [frontend-lint.txt](frontend-lint.txt) |
| ST-INC-02 final | 2 PASS, escritorio/móvil, sin skip | [smoke/execution.txt](smoke/execution.txt), [Playwright](smoke/playwright-report.json) |

Son **249 casos backend distintos**, más repeticiones explícitas, no la suma de
todas las corridas. No se ejecutó toda la suite del repositorio ni el gate E2E
completo. Advertencias existentes: deprecación Starlette/httpx y `record_property`
con JUnit xunit2; no son omisiones ni fallos. Los logs de texto se guardan en UTF-8
y sin espacios finales; se conserva su contenido de resultados.

| Requisito / criterio | Prueba y evidencia B02 |
|---|---|
| RF-11 / CA-11 | Historia FF snapshot 1 y comparación v1 con resultado 2 creadas antes del upgrade, lectura sin recálculo, hash SQL intacto, API/UI y `/runs` |
| RF-13 / CA-13 | Upgrade vacío/con historia, schema contra ORM, FK/unicidad, seis códigos, downgrade permitido y rechazos sin DDL/datos alterados |
| RF-14 / CA-14, alcance persistencia | B01 sin cambios, seis filas propias, catálogo congelado, round-trip resultado 3/diagnósticos; corrupción/duplicados/pertenencia rechazados |
| SM-01/08, ST-INC-02 | Servicios reales, cuatro resultados históricos (tres v1 y un FF), consulta API/UI y limpieza; no acredita los diez SM ni seis motores públicos |

Casos negativos adicionales: ejecución faltante, hash/catálogo corruptos, snapshot
de otro dueño, selección ajena detectada por lector, referencias cruzadas/duplicadas,
resultado de método distinto, versión obsoleta, parada con ejecuciones pendientes,
concurrencia con misma clave y aislamiento entre agregados. Se verifica rollback
y conservación del agregado ajeno. No se implementa selección B08 por probar un
valor SQL corrupto: se comprueba la integridad del lector.

## ST-INC-02: escenario, datos y limpieza

El servidor arranca en `s2cmp01a1b2c`, con PostgreSQL temporal loopback, autenticación
real, configuración 5°, FastAPI en 8017, Vite en 5188 y navegador real. Cada caso
crea pedido/fuentes sintéticos nuevos por el flujo real. Antes del upgrade:
comparación FF/BF/WF completa y FF legacy completo en otro pedido; cuatro filas
de ejecución, cuatro métricas, cuatro materiales usados, sin consumir inventario.

Se capturan respuestas e historia SQL, se migra a `s2cmp02d4e6f8` y se comparan
los bytes canónicos completos de cinco tablas, además de respuestas API. Se
recarga la UI, se consulta el ID histórico, se abren las tres pestañas originales
y sus resultados con colocación visible. `/runs/{id}` conserva el resultado FF.
Los hashes antes/después son idénticos en ambos proyectos; las constraints
anteriores/nuevas y los conteos están en cada JSON de migración.

- [Migración escritorio](smoke/chromium-desktop/TA-043-b02-migration.json),
  [historia v1](smoke/chromium-desktop/TA-043-b02-historical-comparison.json),
  [FF](smoke/chromium-desktop/TA-043-b02-historical-ff.json).
- [Migración móvil](smoke/chromium-mobile/TA-043-b02-migration.json),
  [historia v1](smoke/chromium-mobile/TA-043-b02-historical-comparison.json),
  [FF](smoke/chromium-mobile/TA-043-b02-historical-ff.json).
- Capturas `TA-043-b02-history-{First,Best,Worst}-Fit.png` en cada proyecto;
  se inspeccionaron visualmente paneles de escritorio/móvil.
- [Limpieza final](smoke/cleanup.json): procesos propios antes/después vacíos,
  runner exit 0 y copia temporal eliminada. El teardown detiene backend, frontend,
  navegador y PostgreSQL; verifica PID y tiempo de inicio de remanentes antes de
  cualquier terminación de respaldo, limitada a la raíz propia. Se elimina solo
  esa copia privada, incluido TMPDIR/clúster. No se matan procesos por nombre.

PASS exige todas las aserciones y limpieza; no se sustituyeron por mocks ni se
exigió UI de seis motores. El smoke integral permanece pendiente y obligatorio.

## Incidencias conservadas y correcciones

1. T-02 inicial: el caso de historia dejaba el esquema temporal en el padre;
   los tres casos siguientes fallaron (dos CHECK de HF y un downgrade sin nueva
   revisión por recorrer). Se restaura HEAD tras el caso y se asegura al iniciar
   los casos negativos. Repetición 26 PASS y selección final 28 PASS.
2. [Smoke intento 01](smoke-attempt-01/execution.txt): 2 FAIL; utilidad importaba
   un módulo de pruebas que inicializaba ORM/configuración sin DATABASE_URL.
   Se extrajo el lector SQL puro compartido; no se añadió conexión global ni `.env`.
3. Preflight de repetición: puerto en TIME_WAIT, sin listener vivo. Se añadió
   SO_REUSEADDR al probe, conservando rechazo de un listener activo. No se mató
   ningún servicio para liberar el puerto.
4. [Smoke intento 02](smoke-attempt-02/execution.txt): 2 FAIL; consulta manual
   competía con la recuperación automática de UI al recargar. Se espera el estado
   final antes de consultar; no se modificó la UI ni se aumentó el timeout.
   Ambos intentos conservan reportes FAIL y limpieza sin procesos remanentes.
5. `npm` resolvía a `npm.ps1`, bloqueado por ExecutionPolicy local. Se usó
   `npm.cmd` sin modificar políticas ni instalar herramientas.

No queda fallo obligatorio pendiente de B02. B03 debe adaptar callbacks/outcome y
conservar las políticas HF/BRF/BS-2; B04 debe medir temprano seis motores reales
bajo un worker y 180 s globales, sin asumir viabilidad ni elevar cotas. B05 debe
integrar captura/ciclo, parada probada y admisión; B06/B08 conectarán consulta y
confirmación. No se hicieron esos bloques. HU-018 permanece separado/condicionado.
