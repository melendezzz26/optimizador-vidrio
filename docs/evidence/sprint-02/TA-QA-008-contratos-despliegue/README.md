# Evidencia TA-QA-008 — Contratos y despliegue reproducible

| Campo | Valor |
|---|---|
| Tarea | TA-QA-008 (parte de contratos y despliegue reproducible) |
| SPEC | [SPEC-TA-QA-008-contratos-despliegue.md](../../../specs/SPEC-TA-QA-008-contratos-despliegue.md) |
| Responsable | Fabricio Danniel Aguilar Chavez (`fabrilar1`) |
| Rama de la evidencia | `docs/S2-TA-QA-008-contratos-despliegue` (repo `optimizador-vidrio`) |
| Código medido | `newglass-backend` `main` en `2a9653a`; `newglass-frontend` `main` en `d8ec96e` |
| Carpeta de los clones limpios | `C:\Users\Usuario\Desktop\Repo Taller 1\clean-install\` (separada de los repositorios de trabajo) |
| Fecha | 11/11/2026 |
| Estado | CA-01 a CA-04 con resultados. Instalación limpia completa (MD-01 = 9/9). |

## Qué se entregó

- Verificación de contratos frontend/backend/BD con MI-01 a MI-04 (CA-01).
- Enlace a la evidencia de escritorio y móvil de Andro (CA-02).
- Instalación limpia sin BD, variables documentadas y procedimiento de Staging no ejecutado,
  con MD-01 y MD-02 (CA-03).
- Límites de adaptación y carga con su fuente (CA-04).
- Entregables complementarios: hallazgos de documentación, observación de review del PR #113
  y riesgos.

No se modificó código, base de datos, Heroku, Supabase ni Pages, ni se crearon pruebas
(SPEC D-01, D-06).

## CA-01 — Contratos API validados

| ID | Métrica | Medición | Valor | Meta | Estado |
|---|---|---|---|---|---|
| MI-01 | Sincronía de contratos publicados | Hash git de los 4 archivos de `docs/contracts/optimization/` en los dos clones limpios | **4/4 = 100 %** (`cc8155a`, `6a049ea`, `1f57167`, `9dda657` en ambos) | 100 % | ✅ Cumple |
| MI-02 | Desfase del backend fijado para el E2E | `git diff --stat` entre `.github/backend-e2e.sha` del frontend (`5ebab8c`) y `main` del backend (`2a9653a`) en `app/`, `main.py`, `alembic/`, `requirements.txt` y `Procfile` | **10 archivos** de `app/modules/optimization/` (146 inserciones y 25 eliminaciones), todos de TA-047 | 0 | ❌ No cumple (SPEC R-02) |
| MI-03 | Cobertura de contrato publicado | Recursos `/api/...` usados en `src/` del frontend frente a `docs/contracts` | **2/12 = 16,7 %** (solo `comparisons` y `comparisons-v2`) | Línea base | Registrado (SPEC R-06) |
| MI-04 | ORM ↔ esquema migrado | `Backend CI` del push a `main` en `2a9653a`, fase `general` (pruebas de `compare_metadata` y de head único); `alembic heads` en el clon limpio | **0 diferencias y 1 head** (`s2cmp02d4e6f8`) | 0 y 1 | ✅ Cumple |

**MI-02, archivos que difieren** entre el SHA fijado y `main`:
`application/comparison_acceptance_v2.py`, `application/comparisons.py`,
`application/geometric_preflight.py`, `application/runs.py`,
`infrastructure/in_process_admission.py`, `infrastructure/run_uow.py`,
`presentation/comparison_routes.py`, `presentation/comparison_supervision_v2.py`,
`presentation/run_routes.py` y `presentation/run_schemas.py` (todos bajo
`app/modules/optimization/`). Incluyen un esquema de respuesta (`run_schemas.py`), así que el E2E
del frontend no ejercita el contrato vigente del backend hasta que se actualice el SHA.

**MI-03, recursos usados por el frontend:** `/api/auth`, `/api/clients`, `/api/inventory`,
`/api/optimization/comparisons`, `/api/optimization/comparisons-v2`,
`/api/optimization/rasterize`, `/api/optimization/runs`, `/api/optimization/start`,
`/api/orders`, `/api/permissions`, `/api/roles` y `/api/users`.

**Pruebas de contrato existentes en verde:**

| Lado | Pruebas | Resultado |
|---|---|---|
| Backend | `tests/unit/optimization/test_comparison_contract.py`, `test_comparison_v2_contract.py` y pruebas de OpenAPI (SPEC §4.2) | Incluidas en la suite del clon limpio: 2736 passed, 0 failed |
| Frontend | Pruebas de componentes que importan `docs/contracts/optimization/*.json` (`ComparisonContract`, `ComparisonV2Contract`, `ComparisonApiV2`, entre otras) | Incluidas en `npm run test:component`: 61 archivos y 626 pruebas passed |
| BD | `compare_metadata` en el head y head único | CI de `main`: fase `general` con 3654 aprobadas, 0 fallidas, 0 omitidas |

## CA-02 — Casos escritorio/móvil documentados

Acreditado con la evidencia de Andro, sin volver a medirla (SPEC D-10):
[newglass-frontend `docs/evidence/sprint-02/TA-QA-008/README.md`](https://github.com/melendezzz26/newglass-frontend/blob/d8ec96e4dc052fb1a64b16760b5f9a2b2c171d32/docs/evidence/sprint-02/TA-QA-008/README.md)
(integrada por el PR #4, `39faf93`).

| Dato | Valor en la evidencia de Andro |
|---|---|
| Navegadores | Chrome 157 y Edge 157, reales, en Windows |
| Viewports | 1920×1080 y 1366×768 (escritorio); 768×1024 y 390×844 (emulados) |
| Flujos | CF-01 a CF-06: login, pedidos, inventario, optimización, comparación y navegación |
| MC-01 | 8/8 combinaciones = 100 % |
| MC-02 | 56/56 observaciones sin pérdida de acceso ni overflow horizontal = 100 % |
| MC-03 | 48/48 flujos = 100 % |
| Límites declarados | Sin Firefox ni dispositivos físicos; no certifica legibilidad ni todos los controles |

## CA-03 — Configuración de despliegue reproducible

### MD-01 — Instalación limpia sin BD

| Paso | Acción | Resultado | Estado |
|---|---|---|---|
| 1 | Clonar `newglass-backend` en `clean-install` | `2a9653a` (`main`, igual a `origin/main`) | ✅ |
| 2 | Venv nuevo con Python 3.11 e instalar `requirements.txt` | Python 3.11.9; `pip install` sin errores | ✅ |
| 3 | Suite con `pytest tests` y los tres `--ignore` | **2736 passed, 947 skipped, 0 failed**, 1 warning, en 61,46 s | ✅ |
| 4 | Clonar `newglass-frontend` en `clean-install` | `d8ec96e` (`main`, igual a `origin/main`) | ✅ |
| 5 | `npm ci` con Node 22 | Node v22.20.0, npm 10.9.3; sin errores | ✅ |
| 6 | `npm run test:unit` | **215 pass, 0 fail**, 0 cancelled, 0 skipped (`node --test`) | ✅ |
| 7 | `npm run test:component` | **61 archivos y 626 pruebas passed**, en 31,08 s | ✅ |
| 8 | `npm run lint` | `eslint .` sin errores ni avisos | ✅ |
| 9 | `npm run build` | **Build correcto** (Vite 8.3.1, 2013 módulos, 824 ms), con el aviso conocido de un chunk de más de 500 kB | ✅ |

**MD-01 = 9/9 = 100 %** (meta 100 %): todos los pasos se completaron siguiendo solo los
README de cada repositorio, sin `.env` real, sin BD y sin intervención no documentada.

### MD-02 — Variables de entorno documentadas

| Repo | Leídas por el código | En `.env.example` | Valor | Falta |
|---|---|---|---|---|
| `newglass-backend` | 13 | 12 | **92,3 %** | `NEWGLASS_COMPARISON_LARGE_SECONDS` (SPEC H-03) |
| `newglass-frontend` | 1 (`VITE_API_URL`) | 1 | **100 %** | — |

Meta: 100 % por repo. El backend no cumple por una variable.

### Procedimiento de despliegue a Staging

Documentado en la SPEC §5.4 con los dos escenarios del backend (desde `optimizador-vidrio` o desde
`newglass-backend`) y la publicación de Pages. **No se ejecutó ningún paso** (SPEC D-01).

## CA-04 — Límites de adaptación y carga registrados

Los límites, con su valor y el archivo de donde salen, están en la SPEC §4.5 y se verificaron
sobre `newglass-backend` `2a9653a` y `newglass-frontend` `d8ec96e`.

| Tipo | Límite | Valor |
|---|---|---|
| Adaptación | Navegadores y viewports evaluados | Chrome y Edge; 1920, 1366, 768 y 390 px (CA-02) |
| Adaptación | Comparador | Solo Linux (`/proc`); en Windows, WSL2 |
| Adaptación | API de Staging | HTTPS obligatorio; base `/newglass-frontend/` |
| Carga | Pedidos / unidades / vértices / stock por material | 20 / 800 / 128 / 50 |
| Carga | Corridas por proceso / por usuario | 2 / 1 |
| Carga | Corrida | 120 s |
| Carga | Comparación: arranque / motor / global | 30 / 120 / 900 s; comparación grande (≥ 200 unidades) con tope de 900 s, ajustable con `NEWGLASS_COMPARISON_LARGE_SECONDS` |
| Carga | Memoria de la comparación | 240 / 256 / 1024 MiB por defecto; el `Procfile` los ajusta a un dyno de 512 MiB |
| Carga | Procesos web | 1 (`--workers 1`) |
| Carga | Pool de BD | 5 conexiones, sin desborde, 30 s |

La capacidad observada bajo carga es de TA-QA-002 (MP-06).

## Entregables complementarios

| Entregable | Dónde | Estado |
|---|---|---|
| Hallazgos de documentación H-01 a H-03 y observación O-01 | SPEC §9.1 | Registrados; se avisa a Fabricio Melendez en el PR |
| Observación de review del PR #113 | SPEC §9.2 | Para Andro; no se resuelve en esta tarea |
| Riesgos R-01 a R-06 | SPEC §9.3 | Registrados; R-02 confirmado por MI-02 |
| Modelo de calidad (V-13 y V-14) | `docs/quality/ISO-25010-modelo-calidad.md` | Pendiente (última fase, SPEC D-11) |

## Salidas de comandos

Comandos ejecutados por el responsable en Windows (PowerShell) el 11/11/2026. Se registra el
resumen de cada salida; no se adjuntan capturas (SPEC D-14).

### Backend: clon limpio y suite

```powershell
# Desde C:\Users\Usuario\Desktop\Repo Taller 1\clean-install
git clone https://github.com/melendezzz26/newglass-backend
cd newglass-backend
git log --oneline -1
py -3.11 -m venv venv
.\venv\Scripts\python.exe --version
.\venv\Scripts\python.exe -m pip install -q -r requirements.txt
.\venv\Scripts\python.exe -m pytest tests -q --ignore=tests/unit/optimization/test_comparison_runner.py --ignore=tests/unit/optimization/test_sequential_runner.py --ignore=tests/unit/optimization/test_resource_profile.py
.\venv\Scripts\python.exe -m alembic heads
```

```text
git log --oneline -1:  2a9653a (HEAD -> main, origin/main) Merge pull request #2 from melendezzz26/fix/S2-TA047-preflight-geometrico
python --version:      Python 3.11.9
pip install:           sin errores
pytest:                2736 passed, 947 skipped, 1 warning in 61.46s (0:01:01)
- 0 failed
- 947 skipped: pruebas de API e integración que necesitan PostgreSQL (las corre el CI)
- 1 warning: StarletteDeprecationWarning de fastapi/testclient (preexistente)
alembic heads:         s2cmp02d4e6f8 (head)
```

### Frontend: clon limpio

```powershell
# Desde C:\Users\Usuario\Desktop\Repo Taller 1\clean-install
git clone https://github.com/melendezzz26/newglass-frontend
cd newglass-frontend
git log --oneline -1
node --version
npm --version
npm ci
npm run test:unit
npm run test:component
npm run lint
npm run build
```

```text
git log --oneline -1:  d8ec96e (HEAD -> main, origin/main) Merge pull request #6 from melendezzz26/fix/S2-TA047-rechazo-preflight
node / npm:            v22.20.0 / 10.9.3
npm ci:                sin errores
test:unit:             node --test tests/unit/*.test.js: tests 215, pass 215, fail 0, cancelled 0, skipped 0, duration_ms 633.6413
test:component:        Test Files 61 passed (61); Tests 626 passed (626); Duration 31.08s
lint:                  eslint . sin salida (sin errores ni avisos)
build:                 vite v8.3.1; 2013 modules transformed; built in 824ms
- dist/assets/index-CtqZE_OT.js 590.19 kB (gzip 173.09 kB)
- Aviso: some chunks are larger than 500 kB after minification (conocido)
```

### Mediciones MI-01, MI-02, MI-03 y MD-02

```powershell
# Desde C:\Users\Usuario\Desktop\Repo Taller 1\clean-install
foreach ($f in "comparison-v1.json","comparison-v1.md","comparison-v2.json","comparison-v2.md") { $b = git -C newglass-backend rev-parse --short "HEAD:docs/contracts/optimization/$f"; $r = git -C newglass-frontend rev-parse --short "HEAD:docs/contracts/optimization/$f"; "MI-01 $f backend=$b frontend=$r" }
$sha = (Get-Content newglass-frontend\.github\backend-e2e.sha -Raw).Trim()
"MI-02 backend-e2e.sha = $sha"
git -C newglass-backend diff --stat $sha HEAD -- app main.py alembic requirements.txt Procfile
Get-ChildItem newglass-frontend\src -Recurse -Include *.js,*.jsx | Where-Object FullName -notmatch '__tests__' | Select-String -CaseSensitive -Pattern '/api/(optimization/)?[a-z0-9-]+' -AllMatches | ForEach-Object { $_.Matches.Value } | Sort-Object -Unique
$leidas = Get-ChildItem newglass-backend\app -Recurse -Filter *.py | Select-String -CaseSensitive -Pattern '(required_value|integer_value|getenv)\("([A-Z_]+)"|''(NEWGLASS_[A-Z_]+)''' -AllMatches | ForEach-Object { $_.Matches } | ForEach-Object { ($_.Groups[2,3] | Where-Object Success).Value } | Sort-Object -Unique
$documentadas = Select-String -CaseSensitive -Path newglass-backend\.env.example -Pattern '^#? ?([A-Z][A-Z0-9_]+)=' | ForEach-Object { $_.Matches[0].Groups[1].Value } | Sort-Object -Unique
"MD-02 backend: leidas=$($leidas.Count) documentadas=$(($leidas | Where-Object { $documentadas -contains $_ }).Count)"
$leidas | Where-Object { $documentadas -notcontains $_ }
Get-ChildItem newglass-frontend\src -Recurse -Include *.js,*.jsx | Where-Object FullName -notmatch '__tests__' | Select-String -CaseSensitive -Pattern 'VITE_[A-Z_]+' -AllMatches | ForEach-Object { $_.Matches.Value } | Sort-Object -Unique
Select-String -CaseSensitive -Path newglass-frontend\.env.example -Pattern '^#? ?(VITE_[A-Z_]+)='
```

```text
MI-01 comparison-v1.json backend=cc8155a frontend=cc8155a
MI-01 comparison-v1.md backend=6a049ea frontend=6a049ea
MI-01 comparison-v2.json backend=1f57167 frontend=1f57167
MI-01 comparison-v2.md backend=9dda657 frontend=9dda657
MI-02 backend-e2e.sha = 5ebab8c7ace33324e6a4a465678979b554c8b57d
 .../application/comparison_acceptance_v2.py        | 46 +++++++++++-----
 .../optimization/application/comparisons.py        |  6 +-
 .../application/geometric_preflight.py             | 64 +++++++++++++++++++++-
 app/modules/optimization/application/runs.py       | 12 +++-
 .../infrastructure/in_process_admission.py         | 22 +++++---
 app/modules/optimization/infrastructure/run_uow.py |  2 +
 .../optimization/presentation/comparison_routes.py |  9 +++
 .../presentation/comparison_supervision_v2.py      |  6 ++
 .../optimization/presentation/run_routes.py        |  3 +
 .../optimization/presentation/run_schemas.py       |  1 +
 10 files changed, 146 insertions(+), 25 deletions(-)
MI-03:
/api/auth
/api/clients
/api/inventory
/api/optimization/comparisons
/api/optimization/comparisons-v2
/api/optimization/rasterize
/api/optimization/runs
/api/optimization/start
/api/orders
/api/permissions
/api/roles
/api/users
MD-02 backend: leidas=13 documentadas=12
NEWGLASS_COMPARISON_LARGE_SECONDS
MD-02 frontend: VITE_API_URL leída; VITE_API_URL presente en newglass-frontend\.env.example (línea 1)
```

### CI del backend (MI-04)

En el CI, `NEWGLASS_REQUIRE_POSTGRES=1` hace que una prueba de PostgreSQL **falle en lugar de
omitirse** si falta el clúster. Por eso, 0 fallidas y 0 omitidas en la fase `general`
demuestran que las pruebas de `compare_metadata` y de head único se ejecutaron y pasaron.

```text
Run de GitHub Actions: https://github.com/melendezzz26/newglass-backend/actions/runs/42959351368
Disparador:            push a main, commit 2a9653a (fabrilar1)
Resultado:             Success, 8 min 28 s
Diagnóstico seguro de backend:
- general: 3654 aprobadas, 0 fallidas, 0 errores, 0 omitidas.
- comparison-calculation: 8 aprobadas, 0 fallidas, 0 errores, 0 omitidas.
- comparison-supervision: 28 aprobadas, 0 fallidas, 0 errores, 0 omitidas.
- sequential-runner: 26 aprobadas, 0 fallidas, 0 errores, 0 omitidas.
- comparison-runner: 14 aprobadas, 0 fallidas, 0 errores, 0 omitidas.
```

## Hallazgos

| ID | Hallazgo | Tratamiento |
|---|---|---|
| — | **No se encontró ningún defecto de contrato**: los contratos publicados coinciden entre repos y el ORM coincide con el esquema migrado. | — |
| R-02 | El E2E del frontend prueba un backend anterior a `main` (MI-02 = 10 archivos, por TA-047). | Lo actualizan los dueños del frontend; se avisa en el PR. |
| H-03 | `NEWGLASS_COMPARISON_LARGE_SECONDS` falta en `.env.example` (MD-02 = 92,3 %). | No se corrige (SPEC D-08); se avisa a Fabricio Melendez. |
| H-01, H-02, O-01 | Documentación desactualizada tras el corte y llamadas a la API desde componentes. | SPEC §9.1. |

## Limitaciones

- La instalación limpia es **sin BD**: la suite del backend omite 947 pruebas de PostgreSQL, que
  cubre el CI (SPEC D-05).
- El procedimiento de Staging **no se ejecutó**; no consta desde qué repositorio despliega Heroku
  (SPEC D-01, D-04).
- MI-03 solo mide contratos publicados en `docs/contracts`; el resto de la API depende del
  OpenAPI generado en ejecución.
- CA-02 se apoya en la medición de Andro, que no incluye Firefox ni dispositivos físicos.

## Cómo reproducir

1. Crear una carpeta vacía y clonar ahí los dos repositorios (sección "Salidas de comandos").
2. Backend: venv nuevo con Python 3.11, `pip install -r requirements.txt`, la suite con los tres
   `--ignore` y `alembic heads`.
3. Frontend: `npm ci`, `test:unit`, `test:component`, `lint` y `build` con Node 22.
4. Desde la carpeta de los clones, correr los comandos de MI-01, MI-02, MI-03 y MD-02.
5. Revisar el resumen "Diagnóstico seguro de backend" del `Backend CI` del último push a `main`.
