# SPEC-TA-QA-008 — Contratos y despliegue reproducible

## Información general

| Campo | Valor |
|---|---|
| ID | TA-QA-008 (parte de contratos y despliegue reproducible) |
| Nombre | Contratos front/back/BD, despliegue reproducible y límites de adaptación y carga |
| Tipo | Tarea de calidad (auditoría, documentación y medición con comandos; sin cambios de código, de BD ni de despliegue, y sin pruebas nuevas) |
| Sprint | Sprint 2 |
| Versión | 1.0 |
| Estado | **Draft** |
| Responsable | Fabricio Danniel Aguilar Chavez (`fabrilar1`) |
| Reviewer | Andro Joseph Quispe Cesias (distinto del autor) |
| Rama | `docs/S2-TA-QA-008-contratos-despliegue` (repo `optimizador-vidrio`) |
| Base | `integration-02` en `e49a521` |
| Código auditado | `newglass-backend` `main` en `2a9653a`; `newglass-frontend` `main` en `d8ec96e` |
| Fecha | 11/11/2026 |
| Características ISO/IEC 25010 | Compatibilidad: interoperabilidad (§4.3 del modelo de calidad, vacío **V-13**). Flexibilidad: instalabilidad (§4.8, vacío **V-14** en su parte de instalación reproducible). |
| Parte de Andro | Compatibilidad y adaptabilidad: `SPEC-TA-QA-008-compatibilidad-flexibilidad.md` y su evidencia en `newglass-frontend` (PR #4, integrado en `39faf93`); PR #113 de `optimizador-vidrio`, abierto |
| Evidencia | `docs/evidence/sprint-02/TA-QA-008-contratos-despliegue/README.md` (se crea en F2) |
| Referencias | [Modelo de calidad ISO 25010](../quality/ISO-25010-modelo-calidad.md) · [Matriz TA-QA-001](../quality/TA-QA-001-matriz-metricas-iso25023.md) · [staging.md](../infrastructure/staging.md) · [SPEC-TA-DEPLOY-001](SPEC-TA-DEPLOY-001-staging.md) · [SPEC-TA-037](SPEC-TA-037-control-carga-optimizador.md) · [SPEC-ACADEMIC-800](SPEC-ACADEMIC-800-metodos-independientes.md) · [SPEC-TA-QA-004](SPEC-TA-QA-004-fiabilidad-recuperacion.md) |

## 1. Objetivo

Demostrar con comandos reproducibles que **los contratos entre frontend, backend y base de
datos coinciden** (contratos publicados, backend fijado para el E2E del frontend, ORM frente
al esquema migrado), que **la configuración de despliegue se puede repetir desde cero**
(instalación limpia sin BD y procedimiento de Staging documentado sin ejecutar) y dejar
**registrados los límites de adaptación y de carga** del sistema. Las métricas MI-01 a MI-04
(interoperabilidad) y MD-01 y MD-02 (despliegue) cubren los vacíos V-13 y V-14 del modelo de
calidad sin editar la matriz de TA-QA-001.

## 2. Alcance

### Incluye

- Auditoría de contratos: `docs/contracts` en los tres repositorios, OpenAPI del backend,
  consumo de la API desde el frontend (`VITE_API_URL` y servicios) y relación ORM ↔
  migraciones Alembic (§4.2).
- Auditoría del despliegue de cada parte: `Procfile`, workflows de CI y de Pages, nombres de
  variables de entorno (nunca valores) y documentación existente (§4.3, §4.4).
- Registro de límites de adaptación y de carga con su fuente (§4.5).
- Instalación limpia sin BD: clon limpio de `newglass-backend` con su suite en Windows, y clon
  limpio de `newglass-frontend` con `npm ci`, lint y build (§5.3).
- Procedimiento de despliegue a Staging desde cero, **documentado y no ejecutado**, con los dos
  escenarios posibles para el backend (§5.4).
- Métricas MI-01 a MI-04 y MD-01 y MD-02 (§5.2), medidas con comandos en la evidencia.
- Entregables complementarios (§9): hallazgos de documentación, observación de review del
  PR #113, riesgos y actualización de V-13 y V-14 en el modelo de calidad.

### Fuera de alcance

- Cualquier cambio de código, configuración o documentación en `newglass-backend` y
  `newglass-frontend` (D-01, D-08).
- **Pruebas nuevas**: se mide con comandos y con las pruebas existentes (D-06).
- **Heroku, Supabase y GitHub Pages**: no se despliega, no se migra, no se ejecuta seed y no se
  leen Config Vars ni variables de GitHub (D-01, D-04).
- Confirmar desde qué repositorio despliega hoy la app de Heroku (D-04).
- La compatibilidad y adaptabilidad por navegador y viewport (MC-01 a MC-03), que es la parte de
  Andro (D-10).
- Resolver la observación de review del PR #113 (D-03).
- Editar la matriz de TA-QA-001 (D-07).

## 3. Actores y precondiciones

**Actores:** responsable de la tarea (auditoría y medición); Andro (reviewer y autor de la parte
de compatibilidad); Fabricio Melendez (dueño de los repositorios, destinatario de los
hallazgos de documentación).

**Precondiciones:**

- Acceso de lectura a `newglass-backend` y `newglass-frontend` en GitHub.
- Windows con Python 3.11 y Node 22 para la instalación limpia (versiones del CI de cada repo).
- Ninguna BD real: la suite del backend usa SQLite en memoria y omite las pruebas de
  PostgreSQL; el build del frontend no necesita backend.

## 4. Situación actual (auditoría F0)

Auditoría de solo lectura sobre `newglass-backend` `main` en `2a9653a`, `newglass-frontend`
`main` en `d8ec96e` y `optimizador-vidrio` `integration-02` en `e49a521`. Las rutas son
relativas a la raíz de cada repositorio.

### 4.1 Parte de Andro (compatibilidad y adaptabilidad)

| Hecho | Evidencia |
|---|---|
| Chrome y Edge reales en 1920×1080, 1366×768, 768×1024 y 390×844 (los dos últimos emulados), con 6 flujos (login, pedidos, inventario, optimización, comparación y navegación). MC-01 = 8/8, MC-02 = 56/56, MC-03 = 48/48. Firefox y dispositivos físicos no evaluados. | `newglass-frontend`: `docs/evidence/sprint-02/TA-QA-008/README.md`, `docs/specs/SPEC-TA-QA-008-compatibilidad-flexibilidad.md` |
| Integrado en `newglass-frontend` `main` por el PR #4 (`39faf93`), con las pruebas en `tests/compatibility/` y `playwright.ta-qa-008.config.js`. | `git log` de `newglass-frontend` |
| El PR #113 de `optimizador-vidrio` (rama `test/S2-TA-QA-008-compatibilidad-flexibilidad`, base `f46d96d`) contiene la misma evidencia, la corrección D-01 de las fórmulas de TA-QA-001 y pruebas bajo `frontend/` del monorepo. No tiene conflictos con `integration-02`. | `git diff --stat origin/integration-02...origin/test/S2-TA-QA-008-compatibilidad-flexibilidad` |

### 4.2 Contratos

| Contrato | Dónde | Verificación existente | Entorno |
|---|---|---|---|
| Comparación v1/v2 (JSON de ejemplo y guía md) | `docs/contracts/optimization/comparison-v1.json`, `comparison-v1.md`, `comparison-v2.json`, `comparison-v2.md`, en **tres copias**: `newglass-backend`, `newglass-frontend` y `optimizador-vidrio`. Al 11/11/2026 las tres son idénticas (blobs `cc8155a`, `6a049ea`, `1f57167`, `9dda657`). | Backend: `tests/unit/optimization/test_comparison_contract.py` y `test_comparison_v2_contract.py` validan los esquemas contra su copia del JSON. Frontend: pruebas Vitest de `src/features/optimization/__tests__/` (`ComparisonContract`, `ComparisonV2Contract`, `ComparisonApiV2`, `ComparisonWorkspace`, `ComparisonWorkspaceV2`, entre otras) importan su copia. **Ningún control compara las copias entre repositorios.** | Windows y CI de cada repo |
| Resto de la API (`/api/auth`, `/api/users`, `/api/clients`, `/api/inventory`, `/api/orders`, `/api/optimization/runs`, `start`, `rasterize`) | Sin contrato publicado. Solo el OpenAPI que FastAPI genera en ejecución (`/openapi.json`). | Pruebas parciales del OpenAPI: `tests/api/inventory/test_inventory_api.py::test_openapi`, `tests/api/clients/test_clients_api.py::test_openapi_documents_own_schemas_and_bearer_protection`, `tests/api/optimization/test_optimization_api.py::test_openapi_documents_both_contracts`, `tests/api/test_health_api.py::test_db_test_is_removed_from_http_and_openapi`. Sin instantánea exportada. | Windows y CI |
| Consumo desde el frontend | `src/shared/apiUrl.js` lee `VITE_API_URL`: obligatoria en modo staging, `http://127.0.0.1:8000` por defecto en desarrollo. `config/staging.js` exige HTTPS sin localhost, credenciales, query ni fragmento, y fija la base `/newglass-frontend/`. Llamadas en `src/features/*/…Api.js` (authentication, clients, inventory, optimization, users) y en `src/shared/apiRequest.js`; `/api/orders` se llama también desde `src/App.jsx`, `src/features/dashboard/dashboardApi.js`, `src/features/inventory/RegistrarRetazoForm.jsx` y `src/features/optimization/pendingOrdersSource.js`. | E2E de Playwright del CI del frontend contra el backend fijado en `.github/backend-e2e.sha`. | CI del frontend |
| Backend fijado para el E2E del frontend | `.github/backend-e2e.sha` = `5ebab8c`. El README del frontend exige revisar la compatibilidad y actualizar el SHA en un PR del frontend con cada cambio del backend. | Al 11/11/2026, entre `5ebab8c` y `newglass-backend` `main` (`2a9653a`) cambian **10 archivos** de `app/` (TA-047: `runs.py`, `in_process_admission.py`, `run_uow.py`, `comparison_routes.py`, `comparison_supervision_v2.py`, `run_routes.py`, `run_schemas.py`, entre otros). | Comando `git diff --stat` |
| ORM ↔ BD | `app/models.py` y 15 migraciones Alembic; head `s2cmp02d4e6f8`, una sola cadena. | `tests/integration/optimization/test_comparison_v2_migration.py` compara el ORM vigente con el esquema en el head (`compare_metadata` con tipos y defaults = sin diferencias). `tests/integration/test_staging_bootstrap.py::test_single_integrated_head_and_complete_history` y `tests/integration/optimization/test_multipedido_migration.py` verifican un solo head. | Solo CI (PostgreSQL) |

### 4.3 Despliegue

| Parte | Cómo se despliega | Documentado en | Observación |
|---|---|---|---|
| Backend (Heroku) | `Procfile`: `uvicorn main:app --workers 1`, con `NEWGLASS_COMPARISON_SUPERVISOR_MIB`, `NEWGLASS_COMPARISON_WORKER_MIB`, `NEWGLASS_COMPARISON_AGGREGATE_MIB`, `NEWGLASS_DYNO_MEMORY_MIB` y `NEWGLASS_COMPARISON_LARGE_SECONDS` fijadas en la línea. `.python-version` = 3.11. Despliegue manual; sin fase de release, así que las migraciones son manuales. | `docs/infrastructure/staging.md` y `SPEC-TA-DEPLOY-001` (Reviewed), **solo en `optimizador-vidrio`**, con rutas del monorepo (`cd backend`, rama `integration-02`). | El README de `newglass-backend` no tiene sección de Heroku. No consta desde qué repositorio despliega hoy la app (D-04, §5.4). |
| CI del backend | `Backend CI` en PR y push a `main`: Python 3.11, PostgreSQL aislado, suite general y cuatro procesos aislados. | `.github/workflows/ci.yml` | No despliega. |
| Frontend (GitHub Pages) | `Deploy Pages Staging`: solo `workflow_dispatch` desde `main`; reutiliza el CI y luego ejecuta `npm run build:staging`, `npm run check:staging`, sube y publica el artefacto. Environment `github-pages`; variable de GitHub `VITE_API_URL`. | README del frontend ("Build Staging") y `staging.md` del monorepo | Publicación manual. |
| CI del frontend | `Frontend CI and pinned backend E2E` en PR, push a `main`, `workflow_call` y `workflow_dispatch`: unitarias, componentes, lint, build, build de staging sin publicar (con una URL de ejemplo) y E2E de escritorio y móvil contra el backend fijado (Python 3.11, Node 22, PostgreSQL y Chromium). | `.github/workflows/ci.yml` del frontend | El SHA del backend se actualiza a mano. |
| Instalación local | READMEs de los dos repos: venv 3.11, `.env` desde `.env.example`, `alembic upgrade head`, `seed.py`, `scripts.create_first_admin`; `npm ci`. | READMEs | Sin registro de una instalación limpia. El comparador exige Linux (en Windows, WSL2). |

### 4.4 Variables de entorno (solo nombres)

| Repo | Leídas por el código | En `.env.example` | Observación |
|---|---|---|---|
| `newglass-backend` | `DATABASE_URL`, `SECRET_KEY`, `TOKEN_MINUTOS`, `CORS_ORIGINS`, `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT`, `DB_CONNECT_TIMEOUT` (`app/shared/config/__init__.py`, `app/shared/security/tokens.py`); `NEWGLASS_COMPARISON_SUPERVISOR_MIB`, `NEWGLASS_COMPARISON_WORKER_MIB`, `NEWGLASS_COMPARISON_AGGREGATE_MIB`, `NEWGLASS_DYNO_MEMORY_MIB`, `NEWGLASS_COMPARISON_LARGE_SECONDS` (`app/modules/optimization/infrastructure/resource_runtime.py`). Total: 13. | Las 12 primeras. | `NEWGLASS_COMPARISON_LARGE_SECONDS` la fija el `Procfile` y solo la menciona `SPEC-ACADEMIC-800` del monorepo (H-03). Heroku aporta `PORT`, que usa el `Procfile`, no el código. |
| `newglass-frontend` | `VITE_API_URL` (`src/shared/apiUrl.js`, `vite.config.js`). Total: 1. | Sí, con la advertencia de que `VITE_*` es público en el bundle. | En Pages se toma de la variable de GitHub del mismo nombre. |

Esta auditoría es preliminar; MD-02 se mide formalmente con el comando de §5.2 en F2.

### 4.5 Límites de adaptación y carga

| Tipo | Límite | Valor | Fuente |
|---|---|---|---|
| Adaptación | Navegadores evaluados | Chrome y Edge reales; Firefox, Safari y dispositivos físicos no evaluados | Evidencia de Andro (§4.1) |
| Adaptación | Viewports evaluados | 1920×1080, 1366×768, 768×1024 y 390×844 (los dos últimos emulados); E2E del CI en Chromium 1440 px y 390 px | Evidencia de Andro; `playwright.config.js` del frontend |
| Adaptación | Plataforma del comparador | Necesita `/proc` (Linux); en Windows nativo la comparación queda bloqueada a propósito (`RECOVERY_BLOCKED`) y se usa WSL2 | `app/modules/optimization/infrastructure/process_lifecycle.py`; SPEC-TA-QA-004 §4.1 |
| Adaptación | API de Staging | Solo HTTPS, sin localhost ni credenciales en la URL; base `/newglass-frontend/` | `config/staging.js` del frontend |
| Carga | Pedidos por cálculo (L-01) | 20 | `app/modules/optimization/application/load_budget.py` |
| Carga | Unidades por cálculo (L-03) | 800 | `load_budget.py` (ACADEMIC-800) |
| Carga | Vértices por pieza (L-04) | 128 | `load_budget.py` |
| Carga | Unidades de stock por material (L-07) | 50 | `load_budget.py` |
| Carga | Corridas activas por proceso / por usuario (L-10, L-11) | 2 / 1 | `load_budget.py` |
| Carga | Cálculo de una corrida (L-12) | 120 s | `load_budget.py` |
| Carga | Comparación: arranque / cálculo por motor / global | 30 s / 120 s / 900 s | `app/modules/optimization/application/comparison_limits.py` |
| Carga | Comparación grande (≥ 200 unidades) | Tope 900 s; el `Procfile` fija `NEWGLASS_COMPARISON_LARGE_SECONDS` | `comparison_limits.py`; `Procfile` |
| Carga | Memoria de la comparación (supervisor / trabajador / agregado) | 240 / 256 / 1024 MiB por defecto; el `Procfile` los reemplaza para un dyno de 512 MiB | `comparison_limits.py`; `Procfile` |
| Carga | Procesos web | 1 (`--workers 1`); la admisión en memoria solo es válida con un proceso | `Procfile`; `in_process_admission.py` |
| Carga | Pool de BD por proceso | 5 conexiones, sin desborde, 30 s de espera por defecto | `app/shared/config/__init__.py`; README del backend |

La capacidad observada (MP-06) y el desempeño bajo carga son de TA-QA-002; aquí solo se
registran los límites configurados.

## 5. Reglas verificadas, métricas y procedimientos

### 5.1 Reglas verificadas

Comportamiento o convención existente que esta tarea comprueba; no se cambia.

- RN-01: Las copias de `docs/contracts/optimization/` del backend y del frontend son idénticas.
- RN-02: El backend valida sus esquemas de comparación contra su JSON de contrato, y el frontend
  consume el mismo JSON en sus pruebas.
- RN-03: El ORM vigente coincide con el esquema migrado al head y hay un solo head.
- RN-04: El build de staging del frontend exige `VITE_API_URL` HTTPS y no incluye secretos.
- RN-05: Toda variable que lee el código del backend está documentada en `.env.example`.

### 5.2 Métricas

Métricas del proyecto, inspiradas en las medidas de interoperabilidad e instalabilidad de
ISO/IEC 25023; las metas son del proyecto, no de la norma. Se miden con comandos (D-06), sin
editar la matriz de TA-QA-001 (D-07).

| ID | Métrica | Subcaracterística | Fórmula | Meta | Cómo se mide |
|---|---|---|---|---|---|
| MI-01 | Sincronía de contratos publicados | Interoperabilidad | archivos de `docs/contracts/optimization/` con el mismo hash git en `newglass-backend` y `newglass-frontend` ÷ archivos × 100 | 100 % | `git rev-parse` del blob de cada archivo en `main` de los dos repos |
| MI-02 | Desfase del backend fijado para el E2E | Interoperabilidad | archivos de `app/`, `main.py`, `alembic/`, `requirements.txt` y `Procfile` que difieren entre `.github/backend-e2e.sha` del frontend y `main` del backend | 0 | `git diff --stat` entre ambos commits en `newglass-backend` |
| MI-03 | Cobertura de contrato publicado | Interoperabilidad | prefijos de API que usa el frontend con contrato en `docs/contracts` ÷ prefijos usados × 100 | Línea base, sin meta (vacío G-02) | `git grep` de `/api/...` en `src/` del frontend frente a `docs/contracts` |
| MI-04 | ORM ↔ esquema migrado | Interoperabilidad | diferencias de `compare_metadata` en el head + número de heads | 0 diferencias y 1 head | Pruebas existentes de §4.2 en el CI del backend |
| MD-01 | Instalación limpia sin BD | Instalabilidad | pasos de §5.3 completados sin intervención no documentada ÷ pasos × 100 | 100 % | Ejecución de §5.3 |
| MD-02 | Variables de entorno documentadas | Instalabilidad | variables que lee el código y están en `.env.example` ÷ variables leídas × 100, por repo | 100 % | `git grep` de los nombres leídos frente a `.env.example` (§4.4) |

### 5.3 Instalación limpia sin BD (se ejecuta en F2)

Pasos que mide MD-01. Los comandos exactos se dan en F2. No se crea ningún `.env` real: las
pruebas del backend fijan sus propias variables de ejemplo y el build del frontend no las
necesita.

| Paso | Repo | Acción | Resultado esperado |
|---|---|---|---|
| 1 | `newglass-backend` | Clonar en una carpeta vacía y registrar el commit | Commit de `main` |
| 2 | `newglass-backend` | Crear un venv con Python 3.11 e instalar `requirements.txt` | Instalación sin errores |
| 3 | `newglass-backend` | Suite en Windows con `pytest tests` y los tres `--ignore` | `0 failed`; PostgreSQL omitidas |
| 4 | `newglass-frontend` | Clonar en una carpeta vacía y registrar el commit | Commit de `main` |
| 5 | `newglass-frontend` | `npm ci` con Node 22 | Instalación sin errores |
| 6 | `newglass-frontend` | `npm run lint` | Sin errores |
| 7 | `newglass-frontend` | `npm run build` | Build correcto |

Resultado ya informado por el responsable para el paso 3: 2725 passed, 944 skipped y 0 failed
en Windows. El commit del clon se registra en F2 (P-01).

### 5.4 Despliegue a Staging desde cero (documentado, no ejecutado)

Procedimiento reconstruido a partir de `staging.md`, `SPEC-TA-DEPLOY-001` y la configuración
actual de los repositorios. **En esta tarea no se ejecuta ningún paso** (D-01). Solo se nombran
variables; los valores viven fuera de Git.

**Backend: dos escenarios posibles (D-04).**

| Paso | Escenario A: la app despliega desde `optimizador-vidrio` | Escenario B: la app despliega desde `newglass-backend` |
|---|---|---|
| Origen del código | Monorepo, rama acordada; el proceso web arranca desde `backend/` (procedimiento vigente en `staging.md`) | Raíz de `newglass-backend`, rama `main`; el `Procfile` arranca `uvicorn main:app` sin `cd backend` |
| Runtime | Python 3.11 | Python 3.11 (`.python-version`) |
| Config Vars (nombres) | `DATABASE_URL`, `SECRET_KEY`, `TOKEN_MINUTOS`, `CORS_ORIGINS`; opcionales `DB_*` | Igual que A |
| Variables del comparador | Las fija el `Procfile` del monorepo | Las fija el `Procfile` de `newglass-backend` (§4.3) |
| Migraciones (manuales, autorizadas) | `python -m alembic heads`, `history`, `current`; después `upgrade head`, desde `backend/` | Los mismos comandos desde la raíz del repo |
| Datos iniciales | `seed.py`, `scripts.create_first_admin`, configuración publicada (`scripts.publish_configuration`) | Igual, desde la raíz |
| Verificación | `/health/live` y `/health/ready`; `CORS_ORIGINS` incluye el origen de Pages | Igual que A |

**Frontend (GitHub Pages):**

1. Definir la variable de GitHub `VITE_API_URL` (HTTPS de la API de Staging) en el environment
   `github-pages` o en el repositorio.
2. Ejecutar manualmente `Deploy Pages Staging` desde `main`: corre el CI, `build:staging` y
   `check:staging`, y publica el artefacto con base `/newglass-frontend/`.
3. Verificar la carga de la página y una llamada a la API (CORS).

**Orden recomendado:** backend desplegado y migrado → datos iniciales → `CORS_ORIGINS` con el
origen de Pages → publicación de Pages → verificación de extremo a extremo.

## 6. Decisiones y preguntas abiertas

### Decisiones

| ID | Decisión | Motivo |
|---|---|---|
| D-01 | La tarea no toca Heroku, Supabase, Pages ni código; el despliegue a Staging solo se documenta (§5.4). | Restricción del responsable para TA-QA-008 (11/11/2026). |
| D-02 | La SPEC y la evidencia van en `optimizador-vidrio`, rama `docs/S2-TA-QA-008-contratos-despliegue` desde `integration-02`. | Decisión del responsable (P-02 de F0). |
| D-03 | Lo que el PR #113 duplica frente a `newglass-frontend` #4 queda como observación de review para Andro (§9.2); esta tarea no lo resuelve. | Decisión del responsable (P-03 de F0). |
| D-04 | Desde qué repositorio despliega hoy la app de Heroku queda fuera de alcance; se documentan los dos escenarios sin tocar Heroku (§5.4). | Decisión del responsable (P-04 de F0). |
| D-05 | La instalación reproducible se mide como instalación limpia sin BD: suite del backend en Windows desde un clon limpio y `npm ci`, lint y build del frontend desde un clon limpio (§5.3). | Decisión del responsable (P-05 de F0). |
| D-06 | Sin pruebas nuevas: se mide con comandos (hashes git de `docs/contracts`, diff entre `backend-e2e.sha` y `main`, lectura de nombres de variables) y con las pruebas existentes. | Decisión del responsable (P-06 de F0). |
| D-07 | Las métricas usan los prefijos MI-xx y MD-xx en esta SPEC; no se edita la matriz de TA-QA-001. | Decisión del responsable (P-07 de F0). |
| D-08 | No se corrige documentación de otros integrantes: se registra como hallazgo (§9.1) y se avisa a Fabricio Melendez en el PR. | Decisión del responsable (P-08 de F0). |
| D-09 | Los criterios de aceptación son exactamente los cuatro de Notion para TA-QA-008 (§8). Lo demás pasa a "Entregables complementarios" (§9). | Decisión del responsable (F1, 11/11/2026), igual que en TA-QA-004. |
| D-10 | CA-02 ("Casos escritorio/móvil documentados") se acredita con la evidencia de Andro (§4.1), sin repetir su medición; esta SPEC verifica que esté documentada y enlazable. | La medición MC-01 a MC-03 es la parte de Andro de TA-QA-008. |
| D-11 | La actualización de V-13 y V-14 en el modelo de calidad se hace en la última fase, después de saber si TA-QA-004 se integró. | Las dos tareas editan el mismo archivo y su historial desde ramas distintas. |
| D-12 | La auditoría usa `newglass-backend` `main` en `2a9653a`, que ya integra el traslado de TA-QA-006 (PR #4) y la corrección de TA-047 (PR #2). | Es el `main` vigente al 11/11/2026; el análisis de F0 se hizo sobre `7a99663` y se actualizó. |

### Preguntas abiertas

| ID | Pregunta | Opciones |
|---|---|---|
| P-01 | El resultado 2725 passed / 944 skipped / 0 failed coincide con la rama `test/TA-QA-006-port-security-tests` (`7a99663` más 3 archivos). El `main` vigente (`2a9653a`) suma las pruebas de TA-047, así que un clon limpio de `main` debería dar otro número. ¿De qué commit es el clon limpio? | (a) Repetir el paso 3 en un clon limpio de `main` y registrar su commit. (b) Mantener el resultado y registrar el commit real del clon. |
| P-02 | ¿Las salidas de comandos se registran como texto, sin capturas, igual que en TA-QA-004 y TA-QA-006? | (a) Sí. (b) Con capturas. |
| P-03 | ¿El clon limpio del frontend incluye además `npm run test:unit` y `npm run test:component`? Las pruebas de contrato del frontend (CA-01) son pruebas de componentes. | (a) Incluirlas en §5.3. (b) Acreditarlas con el CI de `newglass-frontend` `main`. |

## 7. Diseño técnico

| Archivo | Repo / capa | Cambio | Fase |
|---|---|---|---|
| `docs/specs/SPEC-TA-QA-008-contratos-despliegue.md` | `optimizador-vidrio` / Documentación | Nuevo: esta SPEC. | F1 |
| `docs/evidence/sprint-02/TA-QA-008-contratos-despliegue/README.md` | `optimizador-vidrio` / Evidencia | Nuevo: resultados por criterio, MI-01 a MI-04, MD-01 y MD-02, instalación limpia, procedimiento de §5.4 y "Salidas de comandos". | F2 |
| `docs/quality/ISO-25010-modelo-calidad.md` | `optimizador-vidrio` / Documentación | §4.3 y §4.8, V-13 y V-14 (parte de instalación reproducible), línea de historial (D-11). | Última fase |

Sin cambios en `newglass-backend`, `newglass-frontend`, migraciones, contrato de la API,
workflows, Heroku, Supabase ni Pages. La carpeta de evidencia lleva el sufijo
`-contratos-despliegue` para no mezclarse con la evidencia de Andro en
`docs/evidence/sprint-02/TA-QA-008/`.

## 8. Criterios de aceptación

Criterios de Notion para TA-QA-008 (D-09).

| ID | Criterio (Notion) | Qué cubre | Métricas | Cómo se verifica |
|---|---|---|---|---|
| CA-01 | Contratos API validados. | Contratos de comparación v1/v2 en los tres repos, backend fijado para el E2E, OpenAPI y ORM ↔ BD (§4.2). | MI-01, MI-02, MI-03, MI-04 | Hashes de `docs/contracts` iguales en backend y frontend; diff entre `backend-e2e.sha` y `main`; línea base de cobertura de contrato; pruebas de contrato del backend en verde en la suite local y pruebas de `compare_metadata` y head único en el CI del backend. |
| CA-02 | Casos escritorio/móvil documentados. | Evidencia de Andro (§4.1), D-10. | MC-01 a MC-03 (de Andro) | La evidencia enlaza la SPEC y los resultados de Andro en `newglass-frontend`: navegadores, viewports, flujos y valores de MC-01 a MC-03. |
| CA-03 | Configuración de despliegue reproducible. | Instalación limpia sin BD (§5.3), variables (§4.4) y procedimiento de Staging con los dos escenarios (§5.4). | MD-01, MD-02 | MD-01 con los siete pasos y sus salidas; MD-02 por repo; procedimiento de §5.4 en la evidencia, marcado como no ejecutado. |
| CA-04 | Límites de adaptación y carga registrados. | Tabla de §4.5 con su fuente. | — | La evidencia registra cada límite con su valor y el archivo de donde sale; la capacidad observada queda referida a TA-QA-002. |

## 9. Entregables complementarios

No son criterios de aceptación de Notion, pero forman parte del PR (D-09).

### 9.1 Hallazgos de documentación (se avisa a Fabricio Melendez)

| ID | Hallazgo | Tratamiento |
|---|---|---|
| H-01 | El README de `newglass-backend` todavía indica ejecutar `python -m scripts.check_comparison_environment` "desde `backend/`" y enlaza guías del monorepo fijadas en `137f2ccd`. | No se corrige (D-08). Aviso en el PR. |
| H-02 | `docs/infrastructure/staging.md` y `SPEC-TA-DEPLOY-001` solo existen en `optimizador-vidrio` y describen el despliegue del monorepo (`cd backend`, rama `integration-02`). Ningún repositorio nuevo documenta su despliegue a Heroku. | No se corrige (D-08). §5.4 documenta los dos escenarios. |
| H-03 | `NEWGLASS_COMPARISON_LARGE_SECONDS` la lee el código y la fija el `Procfile`, pero no está en `.env.example` ni en el README de `newglass-backend` (solo en `SPEC-ACADEMIC-800` del monorepo). | No se corrige (D-08). Afecta a MD-02. |
| O-01 | El frontend llama a `/api/orders` desde varios lugares, incluidos un componente (`RegistrarRetazoForm.jsx`) y `App.jsx`, además de los servicios `*Api.js`. Dificulta seguir qué endpoints usa el frontend. | Observación; no es un defecto de contrato. |

### 9.2 Observación de review del PR #113 (para Andro)

El PR #113 de `optimizador-vidrio` agrega las pruebas de compatibilidad bajo `frontend/` del
monorepo, que dejó de recibir trabajo con EN-REPO-001, y esas mismas pruebas ya están
integradas en `newglass-frontend` por el PR #4. Lo que aporta a `integration-02` es la
documentación (SPEC, PLAN, TASKS, evidencia) y la corrección D-01 de la matriz de TA-QA-001.
La decisión sobre su contenido es de Andro y del equipo (D-03).

### 9.3 Riesgos residuales

| ID | Riesgo | Mitigación actual | Tratamiento |
|---|---|---|---|
| R-01 | Las tres copias de los contratos pueden divergir sin que nadie lo detecte. | Hoy coinciden (MI-01). | Se documenta; un control automático sería código (fuera de alcance). |
| R-02 | El E2E del frontend prueba un backend anterior al `main` vigente (MI-02 > 0 al 11/11/2026, por TA-047). | El README del frontend exige actualizar el SHA en un PR. | Se registra; la actualización corresponde a los dueños del frontend. |
| R-03 | Despliegues manuales (Heroku y Pages): la demo puede mostrar una versión anterior al último merge. | Procedimiento documentado. | Se documenta. |
| R-04 | Migraciones manuales sin fase de release. | Prechecks de Alembic en `staging.md`. | Se documenta. |
| R-05 | No consta desde qué repositorio despliega Heroku. | Dos escenarios en §5.4. | Fuera de alcance (D-04). |
| R-06 | Solo las comparaciones tienen contrato publicado (MI-03). | OpenAPI generado y pruebas parciales. | Se registra como línea base. |

### 9.4 Modelo de calidad

En la última fase: §4.3 y §4.8 con MI-01 a MI-04, MD-01 y MD-02; V-13 y la parte de
instalación reproducible de V-14, con su línea de historial (D-11).

## 10. Pruebas previstas

No se crean pruebas: se ejecutan comandos y pruebas existentes.

| Ejecución | Dónde | Resultado esperado |
|---|---|---|
| Instalación limpia del backend (§5.3, pasos 1 a 3) | Windows, clon limpio de `newglass-backend` | `0 failed`; PostgreSQL omitidas |
| Instalación limpia del frontend (§5.3, pasos 4 a 7) | Windows, clon limpio de `newglass-frontend` | `npm ci`, lint y build correctos |
| Hashes de `docs/contracts` (MI-01) | Los dos clones | Mismo hash en los cuatro archivos |
| Diff entre `backend-e2e.sha` y `main` (MI-02) | Clon de `newglass-backend` | Lista de archivos que difieren |
| Prefijos `/api/...` del frontend (MI-03) | Clon de `newglass-frontend` | Línea base |
| Nombres de variables leídos frente a `.env.example` (MD-02) | Los dos clones | Cobertura por repo |
| `Backend CI` de `main` (MI-04) | GitHub Actions de `newglass-backend` | Fases en verde con 0 omitidas |

## 11. Evidencia requerida

- `docs/evidence/sprint-02/TA-QA-008-contratos-despliegue/README.md` con:
  - contratos y su verificación, MI-01 a MI-04 (CA-01);
  - enlace a la evidencia de escritorio y móvil de Andro (CA-02);
  - instalación limpia, MD-01, MD-02 y el procedimiento de §5.4 marcado como no ejecutado (CA-03);
  - la tabla de límites de §4.5 (CA-04);
  - hallazgos, observación de review y riesgos de §9;
  - los comandos y sus salidas (P-02).

## Historial de estado

| Fecha | Versión | Estado | Cambio |
|---|---|---|---|
| 11/11/2026 | 1.0 | Draft | Creación con la auditoría F0 actualizada a `newglass-backend` `2a9653a` y `newglass-frontend` `d8ec96e`: contratos, despliegue, variables y límites; métricas MI-01 a MI-04, MD-01 y MD-02; instalación limpia sin BD; procedimiento de Staging con dos escenarios, no ejecutado; criterios CA-01 a CA-04 de Notion; entregables complementarios; decisiones D-01 a D-12 y preguntas P-01 a P-03. |
