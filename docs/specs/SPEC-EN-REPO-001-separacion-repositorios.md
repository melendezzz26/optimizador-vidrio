# SPEC-EN-REPO-001 — Separación de frontend y backend en repositorios independientes

## Información general

| Campo | Valor |
|---|---|
| Estado | Reviewed (aprobada) |
| PBI relacionado | EN-REPO-001 — [Backlog Notion](https://app.notion.com/p/414e0c471a44812297f7ee150e15781b) |
| Responsable | Fabricio Melendez Quezada |
| Reviewer | Por asignar |
| Tipo | Enabler de arquitectura e infraestructura |
| Rama documental | `docs/EN-REPO-001-separacion-repositorios` |
| Línea base observada | `integration-02` en `f46d96db9f5ca6071445bae5f884908aed734ff4`, consultado 2026-11-10; no equivale a SHA definitivo del corte |
| ADR asociada | [ADR-003](../adr/ADR-003-repositorios-independientes-frontend-backend.md), Proposed |
| PLAN | [PLAN-EN-REPO-001](PLAN-EN-REPO-001-separacion-repositorios.md) |

## 1. Objetivo

Cumplir la decisión del ingeniero: sustituir el monorepo de trabajo por **dos repositorios GitHub independientes** para frontend React/Vite y backend FastAPI, sin modificar la arquitectura lógica, las funcionalidades ni la semántica de los contratos existentes. La separación requiere trazabilidad verificable del historial, pipelines independientes, prueba integrada y una transición segura de los despliegues.

Esta SPEC ha sido **aprobada en su alcance** por Fabricio Melendez Quezada el 2026-11-10 y sirve como base para preparar la migración. La aprobación documental **no autoriza por sí sola** crear los repositorios de destino, modificar Staging, hacer merge, ejecutar migraciones ni desplegar; se conserva el gate del PLAN y la ADR-003 continúa Proposed.

## 2. Contexto y normas vigentes

- [ADR-001](../adr/ADR-001-seleccion-arquitectura.md): tres niveles, backend monolito modular, Clean Architecture en backend y frontend basado en features. No se introducen microservicios.
- [ADR-002](../adr/ADR-002-operacion-pre-raster.md): conservar las decisiones operativas aplicables.
- [CONTRIBUTING](../../CONTRIBUTING.md): PBI/HU → SPEC → implementación → pruebas → evidencia → PR; no commits directos a `main`.
- [TA-DEPLOY-001](SPEC-TA-DEPLOY-001-staging.md) y [runbook Staging](../infrastructure/staging.md): frontend GitHub Pages, backend Heroku, PostgreSQL/Supabase con Alembic, pruebas previas y despliegue de backend controlado.
- [Notion, presentación de avances, semana 5](https://app.notion.com/p/997e0c471a4483b98c11816409a451d2): SP-006, EN-001, convenciones de capas, documentación de ingeniería y trazabilidad Git.
- El usuario indicó que el incidente de memoria está resuelto: no forma parte del alcance.

## 3. Alcance

### Incluye

1. Dos repositorios de destino administrados por el equipo, tentativamente `newglass-frontend` y `newglass-backend`; nombres finales por validar.
2. Definir un **SHA congelado** común a ambas extracciones, registrando la fecha, el árbol de archivos y los PR abiertos en ese instante.
3. Extracción selectiva del historial por subdirectorio (por ejemplo, `git filter-repo --subdirectory-filter` sobre clones temporales de trabajo), conservando autorías, fechas y mensajes de los commits de cada subsistema en lo técnicamente posible.
4. Generar un **mapa verificable** de commits originales a commits reescritos y registrar explícitamente commits mixtos, merges y archivos compartidos.
5. Reubicar código, dependencias y pruebas del frontend/backend a la raíz de sus repositorios sin cambiar resultados observables.
6. Repartir documentación, diagramas, SPEC, planes, contratos y evidencias con índices de referencia cruzada y copia histórica inmutable del monorepo.
7. Separar CI de frontend y backend; preparar pruebas E2E que obtengan ambos repositorios en versiones compatibles explícitas.
8. Ajustar rutas relativas, scripts, configuración de Pages y Heroku, referencias en README, protección de ramas, variables de compilación y CORS **sin usar secretos de Staging en CI**.
9. Validación reproducible, cutover controlado y rollback de aplicaciones.

### Fuera de alcance

- Cambios de negocio en pedidos, inventario, usuarios, geometría o seis motores FF/BF/WF/HF/M5/M6.
- Modificar límites de memoria/tiempo, paralelismo o admisión del optimizador.
- Modificar modelo de datos, generar/aplicar revisiones Alembic, seed, `stamp`, DDL o intervenir datos Supabase.
- Convertir el backend en microservicios, usar Redis, agregar workers/dynos o reescribir la API.
- Cerrar, fusionar, alterar o eliminar PR existentes como efecto lateral de la separación.
- Eliminar, renombrar, archivar o forzar cambios en el monorepo original durante la fase documental.

## 4. Línea base y control de versiones

El 2026-11-10 se constató `integration-02 = f46d96db9f5ca6071445bae5f884908aed734ff4` (merge de PR #112). `main` ha divergido y **no** será utilizado como fuente por defecto. PR #109 y #112 figuran fusionados; PR #113 y #114 permanecían abiertos. Antes de cualquier extracción se debe repetir esta verificación y resolver un SHA final **sin asumir que el observado sigue vigente**.

No aplicar `git push --force` sobre ramas existentes. Las extracciones generan nuevos SHA por reescritura selectiva del historial; conservar `git-filter-repo/commit-map` u otro manifiesto equivalente fuera de secretos y registrar el SHA base antiguo, el SHA final y el inventario resultante. Las referencias a PR/commits del monorepo siguen siendo fuentes históricas. No asumir que PR, issues, protections, environments, Actions o tags se migran automáticamente al nuevo Git.

## 5. Arquitectura y reparto propuesto

| Origen | Destino principal | Observación |
|---|---|---|
| `frontend/` | raíz del repo frontend | `package.json`, lockfile, Vite, src, public, tests, scripts |
| `backend/` | raíz del repo backend | `main.py`, `app/`, `alembic/`, `tests/`, `requirements.txt`, scripts |
| `Procfile` raíz | raíz del repo backend | corregir `cd backend` manteniendo `--workers 1`, `PORT`, y presupuestos vigentes |
| `requirements.txt` raíz | evaluar | no duplicar dependencias: el backend ya mantiene versiones en `backend/requirements.txt` |
| `.github/workflows/ci.yml` | pipelines propios | actualmente combina backend, frontend y E2E; separar sin perder gates |
| `.github/workflows/deploy-pages.yml` | repo frontend | cambiar fuente de branch, `working-directory`, path del artefacto y Pages base |
| `.github/workflows/resource-profile.yml` | repo backend | verificar rutas y dependencia de scripts antes de migrar |
| `experiments/` | backend o histórico | inventariar por tipo; no copiar por inercia a frontend |
| `docs/`, `CONTRIBUTING.md`, README, diagramas | índice histórico + subconjuntos en cada repo | evitar documentación contradictoria e hipervínculos rotos |
| `.github/scripts/backend_failure_summary.py` | repo backend | necesario para CI backend; ajustar rutas en job |
| archivos transversales/E2E | ubicación acordada en PLAN | determinar dueño y fijar SHAs de ambos repos |

La API se mantiene en FastAPI, el frontend solo consume endpoints HTTP/HTTPS (incluyendo NDJSON y tokens JWT); PostgreSQL/Supabase solo es accedido por backend. Los contratos de API se versionan y consumen sin modificar esquemas por esta tarea.

### Riesgos de acoplamiento ya identificados

- `frontend/playwright.config.js` ejecuta `python -m tests.e2e_server` usando `cwd: '../backend'`; dejará de existir esa ruta si se ejecutan repos separadamente.
- `.github/workflows/ci.yml` usa `working-directory: frontend/backend`, `../backend/requirements.txt` y rutas de reportes bajo ambos subdirectorios.
- `backend/tests/unit/test_ci_contract.py` comprueba el layout y el workflow compartido, por lo que habrá que actualizar sus expectativas deliberadamente y conservar los controles de seguridad.
- `frontend/config/staging.js` define `PAGES_BASE='/optimizador-vidrio/'`, que depende de la URL definitiva de Pages. `VITE_API_URL` debe seguir siendo HTTPS y sin localhost durante el build de staging.
- `backend/app/shared/config/__init__.py` valida CORS explícito; el nuevo origen se aprobará antes de cambiarlo.
- `backend/main.py` instancia la recuperación del comparador en lifespan y `Procfile` requiere un solo worker. Conservar intactos esos comportamientos.

## 6. Reglas de extracción y compatibilidad

- Construir extracciones sobre clones temporales limpios e independientes, nunca sobre el checkout original activo ni la rama desplegada.
- Ejecutar el filtro del historial sin eliminar archivos del repositorio original.
- Documentar el tratamiento de commits que afectaron múltiples subdirectorios: el filtro puede reescribir/omitir commits; no prometer SHA idénticos.
- No copiar `.env`, `venv`, `node_modules`, `dist`, reportes generados o credenciales.
- La actualización del frontend/backend no autoriza cambios de payloads, errores HTTP, idempotencia, selección/confirmación de optimización ni semántica del inventario.
- No realizar deployment cuando existan PR aún sin decisión o cuando no estén aprobados los smoke checks.
- Mantener la integración contractual bajo pruebas automatizadas y matriz de SHA frontend↔backend.

## 7. Criterios de aceptación

- **CA-01 — Trazabilidad:** se conserva el monorepo como origen histórico y existe manifiesto de SHA origen↔repositorio↔SHA destino, autores, fechas, commits relevantes y tags (si existen).
- **CA-02 — Reproducibilidad:** cada repo instala y ejecuta unit tests/lint/build o pytest desde su propia raíz en checkout limpio.
- **CA-03 — Arquitectura:** backend sigue siendo monolito modular FastAPI por capas; frontend sigue siendo React/Vite por features; ninguna feature UI conecta directamente a la BD.
- **CA-04 — Contratos:** login/refresh JWT, permisos, gestión de pedidos/stock, optimización de seis motores, visualizaciones, eventos NDJSON, recuperación y confirmación funcionan sin variación contractual.
- **CA-05 — CI:** checks de backend, frontend y E2E integrado se ejecutan efectivamente; no se ocultan errores ni se omiten pruebas críticas.
- **CA-06 — Deploy frontend:** Pages publica los assets en la base correcta, sin localhost ni secretos en bundle, y permite recarga/navegación de la SPA.
- **CA-07 — Deploy backend:** Heroku compila desde el repo backend y arranca con `--workers 1`; `/health/live` y `/health/ready` funcionan con configuración real aprobada.
- **CA-08 — Aislamiento:** no se escriben datos ni se ejecutan migraciones sobre Supabase durante CI; las pruebas usan PostgreSQL aislado.
- **CA-09 — Seguridad:** se conservan restricciones CORS, secretos externos a Git y verificación de autorización/RBAC.
- **CA-10 — Reversión:** se documentan y prueban pasos de rollback de ambos despliegues sin modificar la base de datos.
- **CA-11 — Evidencia:** SPEC, PLAN, ADR y resultados de pruebas registran los SHA reales; no se afirma éxito si no se ejecutó.
- **CA-12 — Gestión de PR:** se documenta qué ocurre con los PR #113/#114 y demás trabajo pendiente, sin asumir su cierre o integración automática.

## 8. Pruebas previstas

1. Inventario de archivos y enlaces, estado Git, árboles y commit-map.
2. Backend Python 3.11: instalación, suite pytest por grupos aislados tal como exija el presupuesto de las pruebas, integraciones PostgreSQL temporales, contrato de Procfile, import FastAPI, migraciones inspeccionadas sin aplicarlas a Staging.
3. Frontend Node 22: `npm ci`, `npm run test:unit`, `npm run test:component`, `npm run lint`, `npm run build` y `npm run build:staging` con URL aprobada de prueba.
4. E2E con dos checkouts y un mismo manifiesto de versiones; Chromium desktop/mobile, auth, órdenes, inventario, visualización/confirmación y recuperación.
5. Post-cutover: smoke de API y frontend en URL real, CORS permitido/no permitido, coherencia de las revisiones y de los SHAs desplegados.

## 9. Evidencias requeridas

- Tabla de distribución de archivos y documentos compartidos.
- SHA de corte (y fecha), decisiones de PR abiertos, commit-map y manifiesto de correspondencia.
- URLs de checks CI por repositorio y job integrado; comando/versión/resultado, incluyendo fallos y omisiones.
- Evidencia de smoke frontend/backend, salud, CORS y API sin publicar secretos.
- Registro de responsables, autorización del cutover, procedimiento de rollback y estado final de los dos repositorios.

## 10. Historial de estado

- 2026-11-10: **Draft**, especificación documental propuesta para revisión. No se han creado repositorios nuevos ni ejecutado la separación.
- 2026-11-10: **Reviewed**, aprobación de la SPEC confirmada por Fabricio Melendez Quezada en la conversación. Implementación a su cargo; ADR-003 y PR documental mantienen su revisión independiente pendiente.
- Próximos estados: Implemented → Verified únicamente tras código, pruebas, evidencias y PR correspondientes.
