# TA-043 / B07 — Interfaz, visualización y progreso

**Estado: COMPLETADO en su alcance técnico; revisión de Fabricio pendiente.**
El bloqueo original se resolvió durante B08: ST-INC-07 pasó realmente en Chromium
escritorio y móvil, con PostgreSQL aislado, FastAPI y Vite. Fecha: 04/11/2026.
Los resultados locales iniciales se conservan debajo como antecedentes.

[SPEC](../../../../specs/SPEC-TA-043-integracion-seis-motores.md) ·
[PLAN](../../../../specs/PLAN-TA-043-integracion-seis-motores.md) ·
[contrato comparison-v2](../../../../contracts/optimization/comparison-v2.md) ·
[evidencia B06](../B06/README.md)

## Alcance implementado

- Se extiende el workspace FF/BF/WF existente con selector explícito de perfil.
  Comparison-v1 conserva sus tres métodos y acciones actuales; comparison-v2
  usa seis métodos del catálogo B01 y no ofrece selección ni confirmación B08.
- Se agregan transporte, parsers y recuperación v2 independientes en
  `comparisonApiV2.js` y `comparisonController.js`. El usuario puede iniciar,
  consultar por ID, recuperar por clave idempotente, seguir eventos, cargar
  resultados durable y pedir manifiestos/máscaras con propiedad por ejecución.
- Las pestañas se derivan de las ejecuciones recibidas. Una sola vista existente
  reutiliza `RunVisualization`, `PlacementCanvas` y `PlacementScene3D`.
- La tabla compara cobertura, aprovechamiento, merma, material recuperable,
  planchas, retazos, piezas colocadas/no colocadas, tiempo y completitud sin
  ordenar motores ni convertir ausencia de datos en cero.
- M6 presenta `search_progress` como provisional y solo muestra placements del
  resultado durable. Los fallos y parciales conservan su causa y estado.
- Se evita duplicar el control Pausar dentro del mismo workspace, manteniendo el
  valor predeterminado de `RunVisualization` para sus otros consumidores.

No se modificaron SPEC/PLAN, backend de producto, contratos B01, B02, B04/B05,
algoritmos, límites, confirmación v2 ni coordinación. Se conservan 36 requisitos,
36 criterios de aceptación, la matriz y B01–B11.

## Archivos de B07

- `frontend/src/features/optimization/comparisonApiV2.js` (nuevo)
- `frontend/src/features/optimization/comparisonController.js`
- `frontend/src/features/optimization/ComparisonWorkspace.jsx`
- `frontend/src/features/optimization/ComparisonWorkspace.css`
- `frontend/src/features/optimization/RunVisualization.jsx`
- `frontend/src/features/optimization/__tests__/ComparisonApiV2.test.jsx` (nuevo)
- `frontend/src/features/optimization/__tests__/ComparisonWorkspaceV2.test.jsx` (nuevo)
- `frontend/tests/e2e/optimization-comparison.spec.js`
- `backend/tests/optimization_b01_smoke.py` (amplía el harness privado para B07)

## Validación local ejecutada

| Selección | Archivos | Resultado |
|---|---:|---|
| Workspace comparison-v1 | 1 | 8/8 PASS |
| Workspace/API/contratos comparison-v2 | 4 | 30/30 PASS |
| Lifecycle, RunVisualization y contratos/estado visual | 4 | 27/27 PASS |
| PlacementScene3D y visualizaciones existentes | 2 | 15/15 PASS |
| **Total de pruebas de componentes distintas** | **11** | **80/80 PASS** |

Comandos desde `frontend/`:

```powershell
npm.cmd run test:component -- src/features/optimization/__tests__/ComparisonWorkspace.test.jsx --reporter=dot --maxWorkers=1
npm.cmd run test:component -- src/features/optimization/__tests__/ComparisonWorkspaceV2.test.jsx src/features/optimization/__tests__/ComparisonApiV2.test.jsx src/features/optimization/__tests__/ComparisonV2Contract.test.jsx src/features/optimization/__tests__/ComparisonContract.test.jsx --reporter=dot --maxWorkers=1
npm.cmd run test:component -- src/features/optimization/__tests__/ComparisonLifecycle.test.jsx src/features/optimization/__tests__/RunVisualization.test.jsx src/features/optimization/__tests__/VisualContract.test.jsx src/features/optimization/__tests__/VisualState.test.jsx --reporter=dot --maxWorkers=1
npm.cmd run test:component -- src/features/optimization/__tests__/PlacementScene3D.test.jsx src/features/optimization/__tests__/OptimizationVisualizations.test.jsx --reporter=dot --maxWorkers=1
npm.cmd run lint
npm.cmd run build
npm.cmd run test:e2e -- --list --grep "TA-043 B07"
```

Lint terminó sin errores. Build terminó correctamente; Vite informó que el bundle
JS principal supera 500 kB minificado. Playwright enumeró el nuevo smoke para
Chromium escritorio y móvil, pero enumerar no ejecuta esos escenarios.
`git diff --check` no reportó errores. Una primera selección agrupada de suites
tuvo un timeout de 5 s en un test v1 existente bajo carga concurrente; el archivo
se repitió de forma aislada y sus 8 casos pasaron.

## ST-INC-07 — estado del smoke real

**Antecedente de la entrega inicial: BLOQUEADO / NO EJECUTADO.** El smoke
debe ejecutarse con el harness en Linux/WSL2, PostgreSQL privado, FastAPI, Vite y
Chromium reales. En este host, `wsl.exe` respondió
`Wsl/Service/CreateInstance/E_ACCESSDENIED`; Docker está instalado pero su daemon
no está disponible. Aunque existe PostgreSQL 18 para Windows, no se usó porque no
cumple el entorno E0 ni prueba el control de procesos Linux requerido por B04/B05.
No se inició ningún servicio ni se crearon datos; por ello no hay capturas E2E,
reporte Playwright de ejecución, ni limpieza de recursos de smoke que declarar.

El escenario B07 ya está definido en
`frontend/tests/e2e/optimization-comparison.spec.js`: inicia v2 desde la UI,
verifica seis resultados/diagnósticos y métricas contra API, navega las siete
pestañas, valida los layouts 2D/3D y las referencias visuales disponibles,
recupera por clave y tras recarga sin segundo POST, comprueba comparación v1,
`/runs`, inventario y layout adaptable. El harness
`backend/tests/optimization_b01_smoke.py --block B07` ejecutará únicamente ese
caso en escritorio y móvil en un runtime válido. La interfaz v2 de selección y
confirmación continúa pendiente de B08. ST-INT permanece pendiente de B09–B11.

El resultado del entorno queda detallado en [environment.json](environment.json).

### Recuperación autorizada durante B08

La denegación `E_ACCESSDENIED` corresponde al sandbox del ejecutor. Un comando
Linux mínimo y el arnés funcionaron al ejecutarse con la elevación autorizada;
no se reinstaló WSL ni se cambiaron permisos globales, servicios o seguridad de
Windows. No se utilizó Docker ni PostgreSQL compartido.

**Resultado vigente: ST-INC-07 PASS, 2/2 escenarios reales.**
[Reporte Playwright](smoke/playwright-report.json), [salida](smoke/execution.txt)
y [limpieza/manifiesto de fuentes](smoke/cleanup.json). Se verificaron seis
resultados completos y las siete pestañas, seis layouts 2D/3D con geometrías
mixtas a 5°, métricas contra API, máscaras, recuperación por clave y recarga sin
otro POST, historia v1 de tres métodos y `/runs`. Simular/consultar conservó
inventario y movimientos. Hay capturas separadas de escritorio/móvil en `smoke/`.

El primer intento real falló por buscar radios fuera de la pestaña Comparación;
se conserva en [attempts/01-tab-context-failure.txt](attempts/01-tab-context-failure.txt)
y [su limpieza](attempts/01-cleanup.json). Se corrigió el contexto de pestaña,
el selector del panel y la comparación histórica contra el estado v1 terminal,
sin aceptar una enumeración de Playwright como ejecución. Los radios incorporados
por B08 se comprueban sin selección automática y con confirmación deshabilitada.
ST-INC-07 no realiza confirmación: esa evidencia pertenece a B08.

Desde la raíz del repositorio, PowerShell externa o ejecución WSL autorizada:

```powershell
wsl.exe -e bash -lc 'cd backend && /home/fabri/.cache/newglass-validation.SXhCMM/backend/.venv/wsl/bin/python -m tests.optimization_b01_smoke --block B07 --runtime-root /home/fabri/.cache/newglass-validation.SXhCMM'
```

El arnés conserva hashes de las fuentes ejecutadas, detiene sus servicios y
elimina únicamente su copia temporal. `runner_exit: 0`, `processes_after: []`,
`temporary_copy_removed: true`. SPEC/PLAN siguen Draft y ST-INT permanece pendiente.
