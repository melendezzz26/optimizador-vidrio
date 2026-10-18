# TA-DEPLOY-001 — Preparación y despliegue controlado de Staging

## Información general

| Campo | Valor |
|---|---|
| Estado | Reviewed |
| Tipo | TA — tarea de arquitectura/infraestructura |
| Rama | `feature/TA-DEPLOY-001-staging` |
| Base de trabajo | `978705f` |
| Objetivo de release | Primer entorno Staging de NewGlass |
| Revisión | Pendiente; esta SPEC no queda Reviewed automáticamente |

> Las decisiones de hosting y operación de esta SPEC son propuestas de diseño. Deben revisarse antes de implementar. Este documento no autoriza despliegues, cambios remotos ni migraciones.

## 1. Objetivo

Preparar NewGlass para un entorno Staging reproducible y controlado:

```text
React + Vite ── GitHub Pages
FastAPI      ── Heroku
PostgreSQL   ── Supabase
CI           ── GitHub Actions
```

El entorno debe poder construirse desde el monorepo, recibir configuración fuera de Git, validar la disponibilidad del backend y la base de datos, desplegar frontend y backend por procedimientos distintos y producir evidencia verificable del SHA y de la revisión Alembic probados.

## 2. Fuente de diagnóstico y estado observado

La fuente de esta propuesta es el diagnóstico no destructivo de readiness realizado para `integration/sprint-01`, documentado en [readiness-integration-sprint-01.md](../evidence/sprint-01/HU-012/readiness-integration-sprint-01.md) y complementado por [T03 pull request](../evidence/sprint-01/HU-012/t03-pull-request.md). Ese diagnóstico indicó que integration no estaba lista para un despliegue público.

Hallazgos relevantes de esa revisión:

- El backend se ejecuta desde `backend/`; las dependencias están en `backend/requirements.txt`. No se había validado la detección de Python ni la instalación de dependencias desde la raíz del monorepo.
- La documentación y CI declaran Python 3.11, pero el diagnóstico también observó una ejecución local en Python 3.14.7; no se había validado una instalación limpia en el runtime de destino.
- `backend/app/shared/database/session.py` carga `.env` para desarrollo y construye el engine desde `DATABASE_URL`. Staging debe funcionar con variables inyectadas por la plataforma, sin depender de un archivo local.
- `backend/main.py` limita CORS a los dos orígenes localhost y publica `/db-test` sin autenticación; esa ruta devuelve información de versión PostgreSQL.
- `GET /` prueba que el proceso HTTP responde, pero no comprueba PostgreSQL. Se necesitan checks distintos de liveness y readiness.
- El CI observado en ese diagnóstico ejecutaba pytest en Python 3.11 y lint/build del frontend, pero no unit/component frontend ni E2E. Esta SPEC fija ahora los checks requeridos en CA-12 y las tareas T06/T07.
- El frontend ya lee `VITE_API_URL`, pero usa `http://127.0.0.1:8000` como fallback. `vite.config.js` no fija `base`, y la ruta `/editor-pieza` compara el pathname desde raíz. Esta SPEC decide integrar el editor a la navegación normal de la SPA en Pages, sin exigir una ruta profunda independiente.
- No se encontró un workflow de publicación de GitHub Pages ni configuración de despliegue de Heroku verificada. No se inspeccionaron secretos remotos, conectividad al proyecto Supabase de Staging ni compatibilidad de su esquema.

Estos hallazgos son la base para diseñar los cambios posteriores; no constituyen verificación de un servicio remoto ni autorización para conectarse a él.

## 3. Alcance

Esta tarea especifica el trabajo necesario para:

- arrancar FastAPI desde el monorepo en Heroku, con un proceso web y el puerto entregado por la plataforma;
- fijar explícitamente Python de la serie 3.11 y hacer detectables desde raíz las dependencias necesarias;
- configurar el backend mediante variables de entorno y CORS por entorno;
- conectar SQLAlchemy/psycopg a PostgreSQL Staging en Supabase mediante TLS y sin SDK Supabase para persistencia;
- establecer el procedimiento controlado de Alembic para Staging;
- separar health/liveness de health/readiness;
- retirar `/db-test` de la superficie pública;
- preparar Vite para GitHub Pages bajo `/optimizador-vidrio/`;
- exigir `VITE_API_URL` de Staging al construir el frontend publicado;
- validar la carga/recarga del sitio en el subpath Pages y la navegación SPA al editor;
- definir CI requerido y un workflow de publicación de GitHub Pages;
- documentar bootstrap, despliegue inicial manual de backend, smoke post-deploy y evidencia reproducible.

Este TA no crea revisiones Alembic, no modifica modelos ORM ni el modelo lógico de la base de datos, y no altera manualmente el esquema de Supabase. “No modificar esquema” significa que este TA no diseña cambios nuevos de esquema; sí puede validar la cadena versionada ya aprobada y aplicar manualmente esa cadena a una BD Staging compatible y autorizada, registrando las revisiones anterior/posterior y la evidencia.

## 4. Fuera de alcance

- Despliegue de producción.
- Despliegue automático inicial del backend.
- Heroku Postgres.
- Redis, workers o scheduler.
- Kubernetes.
- Docker como requisito.
- Pipeline Heroku obligatorio.
- Heroku Review Apps.
- CDN adicional.
- Migraciones automáticas mediante GitHub Actions en el primer despliegue.
- Cambios funcionales ajenos a la infraestructura de Staging.
- Crear revisiones Alembic nuevas, cambiar modelos ORM o el modelo lógico de BD, o ejecutar DDL manual en Supabase como parte de este TA.
- Ejecutar despliegues, crear recursos remotos, acceder a Supabase o aplicar migraciones como parte de la escritura o revisión de esta SPEC.

## 5. Arquitectura objetivo y decisiones propuestas

### 5.1 Heroku — backend

- Desplegar la aplicación Python desde la raíz del monorepo.
- Ejecutar un único proceso web, sin `--reload`.
- Comando esperado del proceso:

  ```sh
  cd backend && python -m uvicorn main:app --host 0.0.0.0 --port $PORT
  ```

- Python de la serie 3.11 con versión explícita y compatible con el buildpack vigente.
- T01 debe elegir un único mecanismo canónico, admitido por el buildpack, para que Heroku detecte las dependencias desde la raíz. Una opción prevista es `/requirements.txt` con `-r backend/requirements.txt`; puede usarse otra equivalente si ofrece el mismo resultado.
- Debe existir una sola fuente real de versiones: no duplicar manualmente dependencias entre raíz y `backend/requirements.txt`. Demostrar arranque reproducible desde un checkout limpio en la raíz.
- Primer despliegue del backend manual y controlado mediante la integración GitHub de Heroku. Mantener desactivado el automatic deploy hasta que Staging y sus smoke checks estén aprobados.
- El proceso web debe escuchar en `0.0.0.0` y en el `PORT` suministrado por Heroku.

### 5.2 Configuración y seguridad del backend

- La configuración de Staging llega desde variables del entorno de Heroku, nunca desde `.env` versionado o requerido en runtime.
- `SECRET_KEY` y `DATABASE_URL` son valores externos y secretos. No incluirlos en logs, respuestas, artifacts ni evidencia.
- `TOKEN_MINUTOS` debe ser positivo y conservar el valor acordado por el equipo.
- `CORS_ORIGINS` contiene orígenes explícitos separados por entorno. No se permite wildcard.
- Desarrollo permite `http://localhost:5173` y `http://127.0.0.1:5173`. Staging permite únicamente el origen HTTPS real del sitio GitHub Pages aprobado; el path `/optimizador-vidrio/` no forma parte del origen CORS.
- La configuración debe fallar de forma clara y segura si falta una variable obligatoria de Staging; no debe caer silenciosamente a localhost ni a una clave predeterminada.
- SQLAlchemy debe usar `pool_pre_ping`, límites razonables de pool y timeouts explícitos. T02 debe validarlos contra el plan y los límites reales del proyecto Supabase; no se fijan números antes de esa revisión.

### 5.3 Supabase y Alembic

- TA-DEPLOY-001 no crea revisiones Alembic, no cambia modelos ORM ni el modelo lógico de BD y no modifica manualmente el esquema de Supabase. “No modificar esquema” no prohíbe aplicar las migraciones ya versionadas y aprobadas a una BD Staging compatible.

- Persistencia por PostgreSQL usando SQLAlchemy y psycopg.
- No usar el SDK Supabase ni sus credenciales `anon`/`service_role` para acceso de backend.
- Exigir TLS y validar la cadena de conexión con el driver existente.
- Evaluar el Session Pooler según región, modo de conexión, soporte IPv4/IPv6 y límites disponibles para Heroku; registrar la decisión antes de provisionar.
- Staging debe apuntar a un destino PostgreSQL aislado y autorizado, no a un esquema compartido cuya revisión o datos no hayan sido comprobados.
- La revisión de Alembic debe inspeccionarse antes de migrar. La cadena ya aprobada debe conservar un único head vigente, `fa014e1a2b3c`; no se incorporan revisiones nuevas en este TA.
- El primer `alembic upgrade head` en Staging será manual y autorizado, sobre una BD aislada y compatible. Antes: confirmar destino, registrar `alembic current`, comprobar precondiciones y datos y contar con backup o recuperación aprobada cuando corresponda. Ensayar primero la cadena existente en PostgreSQL aislado/controlado.
- Después: `alembic current` debe reflejar `fa014e1a2b3c`; verificar datos de referencia seleccionados y los registros preexistentes que el equipo haya acordado preservar, comparando evidencia previa/posterior. No afirmar “sin pérdida de datos” sin identificar qué se compara.
- La aplicación de la cadena existente se hace por Alembic; no se permite DDL manual para simular o saltar revisiones.
- Un rollback de aplicación no revierte el esquema. Se debe poder redeplegar el SHA backend anterior y republicar el artefacto/commit frontend anterior. Si una migración no tiene downgrade seguro, detener el release y usar el mecanismo de recuperación aprobado si hace falta; no usar `alembic stamp` para ocultar divergencias.

### 5.4 Frontend — GitHub Pages

- Publicar `frontend/dist` mediante GitHub Actions y el flujo de publicación de Pages.
- Configurar base Vite como `/optimizador-vidrio/` para Staging.
- `VITE_API_URL` se suministra al build y apunta a la API HTTPS de Heroku. Es configuración pública incluida en el bundle; nunca colocar secretos en variables `VITE_*`.
- El build de Staging debe fallar o ser bloqueado si `VITE_API_URL` está ausente, apunta a localhost o usa HTTP.
- Decisión inicial de routing: no publicar `/editor-pieza` como ruta profunda independiente en GitHub Pages. El editor se integra a la navegación normal de la SPA bajo `/optimizador-vidrio/`; no introducir React Router solo por el deployment ni depender de fallback server-side, hash routing o una URL física `/optimizador-vidrio/editor-pieza`.
- Verificar que la aplicación carga y puede recargarse en su URL publicada bajo `/optimizador-vidrio/`, y que la navegación normal al editor no produce 404.
- Las solicitudes del navegador deben usar el origen de API configurado; no deben derivar una URL local como fallback de Staging.

### 5.5 CI y publicación

- CI de PR corre antes de integrar a `integration/sprint-01` y usa PostgreSQL aislado/efímero para los tests que lo requieren. No usa `DATABASE_URL` de Supabase Staging, no requiere secretos de Staging y no modifica sus datos.
- Checks requeridos de PR: backend, instalación de dependencias y pytest completo; disponibilidad de PostgreSQL aislado para los tests requeridos y reporte explícito si no corren; frontend con `npm ci`, `npm run test:unit`, `npm run test:component`, `npm run lint` y `npm run build`.
- Playwright forma parte obligatoria de la validación de release de Staging. Será check requerido de PR si CI ofrece PostgreSQL y browser reproducibles; si E2E queda fuera de CI de PR, T07 debe ejecutar y aprobarlo como check obligatorio pre-deploy. Esa condición y el resultado deben quedar explícitos en el runbook, no como decisión pendiente.
- Los workflows de CI y Pages usan versiones compatibles/reproducibles de Python serie 3.11 y Node compatible con `package-lock.json` y las dependencias. No se fija un parche de Python o Node si el proyecto no tiene política de pinning.
- GitHub Pages se publica mediante GitHub Actions a partir de `integration/sprint-01`, solo desde un commit integrado/aprobado; pull requests no publican el sitio ni despliegan el backend.
- El workflow de Pages usa el entorno `github-pages`, publica el artefacto `frontend/dist`, no sirve el código fuente con “Deploy from a branch”, y emplea permisos mínimos `contents: read`, `pages: write`, `id-token: write` más control de concurrencia para deployments.
- El primer backend deploy sigue siendo manual; el workflow de Pages no implica un pipeline de Heroku.
- Los workflows no contienen secretos de aplicación ni ejecutan migraciones/bootstrap contra Staging en PR o en el primer despliegue.

## 6. Variables de entorno

Los nombres se documentan sin valores reales. Los secretos de runtime se configuran únicamente en el entorno de destino; CI no requiere secretos de Staging. Las pruebas usan PostgreSQL aislado/efímero y configuración de prueba, sin credenciales ni `DATABASE_URL` de Supabase.

| Variable | Contexto | Clasificación | Uso esperado |
|---|---|---|---|
| `DATABASE_URL` | Backend runtime | Secreto | URL PostgreSQL de Staging para SQLAlchemy/psycopg, con TLS y destino aprobado. |
| `SECRET_KEY` | Backend runtime | Secreto | Firma de sesión/token; valor independiente por entorno. |
| `TOKEN_MINUTOS` | Backend runtime | Configuración | Duración positiva del token en minutos. |
| `CORS_ORIGINS` | Backend runtime | Configuración | Lista explícita de orígenes autorizados para el entorno. |
| `PORT` | Backend runtime | Gestionada por Heroku | Puerto al que debe enlazarse Uvicorn. No fijar un valor de Staging. |
| `VITE_API_URL` | Frontend build | Pública | URL HTTPS base de la API de Staging; queda visible en el bundle. |
| `NEWGLASS_TEST_PG_BIN` | Pruebas | Configuración local/CI | Ubicación de binarios PostgreSQL cuando el harness de integración la necesita. |
| `PLAYWRIGHT_CHANNEL` | Pruebas E2E | Configuración local/CI | Canal de navegador que debe usar Playwright. |

`DATABASE_URL`, `SECRET_KEY`, `TOKEN_MINUTOS` y `CORS_ORIGINS` son de runtime del backend. `VITE_API_URL` se resuelve en tiempo de build, no en el navegador después del deploy. `NEWGLASS_TEST_PG_BIN` y `PLAYWRIGHT_CHANNEL` pertenecen únicamente al entorno de pruebas.

## 7. Tareas

| Tarea | Objetivo | Archivos probables | Pruebas | Evidencia | Dependencias |
|---|---|---|---|---|---|
| T01 — Arranque Heroku del monorepo | Elegir un único mecanismo canónico de detección de dependencias desde raíz; runtime Python 3.11 y proceso web con `$PORT`. Mantener una sola fuente real de versiones. | `Procfile`, mecanismo de runtime Python admitido, `requirements.txt` raíz o alternativa equivalente, `backend/requirements.txt`, README operativo. | Build limpio desde checkout raíz; comprobar que Heroku instala dependencias sin listas duplicadas, arranca en puerto asignado y no requiere `.env` local. | Log de build sanitizado, SHA, runtime detectado y resultado de arranque. | Decisión del buildpack y versión Python; coordinación con T02. |
| T02 — Configuración de Staging y conexión segura | Separar runtime config, validar variables obligatorias, construir CORS explícito y conectar SQLAlchemy a PostgreSQL por TLS; configurar `pool_pre_ping`, límites y timeout tras revisar los límites reales del proyecto. | `backend/app/shared/config/`, `backend/app/shared/database/session.py`, `backend/main.py`, pruebas de configuración/CORS/conexión, documentación de variables. | App sin `.env`; falta de variable obligatoria; orígenes dev/Staging permitidos y origen no autorizado rechazado; conexión TLS y pool validados contra límites del plan Supabase sin fijar números antes de revisarlos. | Matriz de variables sin valores, resultado de CORS y reporte de conexión/pool sin DSN ni secretos. | T01 para build/runtime; destino Staging autorizado para validación remota. |
| T03 — Health checks y cierre de diagnóstico público | Crear liveness independiente de BD, readiness con `SELECT 1` y timeout finito explícito/configurable o razonable, y retirar `/db-test`. | `backend/main.py` o router health dedicado, pruebas API/health, documentación OpenAPI si corresponde. | `/health/live` devuelve `200 {"status":"ok"}` aun con BD caída y sin consultarla; readiness devuelve `200 {"status":"ready"}` o `503 {"status":"not_ready"}` sin esperar indefinidamente ni revelar detalles; `/db-test` da 404 y no figura en OpenAPI. | Resultados HTTP sanitizados y pruebas que confirman independencia de live, límites de ready y ausencia pública de `/db-test`. | Liveness puede prepararse en paralelo; readiness depende de T02. |
| T04 — Supabase, Alembic y bootstrap de Staging | T04-A: conectividad/configuración PostgreSQL de Staging. T04-B: aplicar manualmente la cadena Alembic existente y aprobada. T04-C: documentar bootstrap operativo de roles, primer administrador y datos mínimos. No crear revisiones nuevas ni cambiar ORM/esquema. | Configuración Alembic existente, `backend/alembic/`, procedimiento operativo Staging, mecanismo existente y aprobado de bootstrap, evidencia bajo `deployment/`. | PostgreSQL aislado/controlado; único head `fa014e1a2b3c`; ensayo previo; confirmar BD/revisión/precondiciones/datos, backup o recuperación, y registros acordados preservados; revisar manejo de `%` en conexión. | Revisión Alembic antes/después; comparación de datos acordados; log sanitizado; backup/recuperación y mecanismo de bootstrap documentados. | T02 y autorización del destino Staging. No es dependencia de T06 ni de CI. La ejecución de T04-C ocurre en T07, no en CI. |
| T05 — Frontend preparado para GitHub Pages | Construir bajo el base path, exigir API HTTPS de Staging e integrar editor mediante navegación normal de la SPA, sin ruta profunda independiente. | `frontend/vite.config.js`, `frontend/src/shared/apiUrl.js`, `frontend/src/App.jsx`, configuración frontend/env example y pruebas de ruta/build. | Build con `/optimizador-vidrio/`; bundle sin secretos ni localhost; assets/carga/recarga de la URL publicada y navegación al editor sin 404. | Resumen de build y smoke browser con URL/base y SHA; sin tokens ni variables sensibles. | Contrato/origen HTTPS de T02; puede avanzar con origen temporal documentado. |
| T06 — CI y publicación controlada | Implementar checks requeridos de PR con PostgreSQL aislado, y publicar `frontend/dist` con Pages Actions desde un commit integrado/aprobado de `integration/sprint-01`. | `.github/workflows/ci.yml`, workflow dedicado de Pages en `.github/workflows/`, configuración de Pages/branch protection, harness PostgreSQL aislado, configuración de concurrency/permisos. | Backend: instalación y pytest completo, PostgreSQL aislado disponible y sin omisiones silenciosas. Frontend: `npm ci`, unit, component, lint y build. E2E se ejecuta como check de PR si PG/browser son reproducibles; de lo contrario es check obligatorio pre-deploy de T07. Validar Pages artifact, permisos y que PR no publique. | URLs/runs de Actions, resumen de checks y commit/artifact publicado. | T01, T03 y T05. CI usa infraestructura de test aislada; no depende de T04 ni de Supabase Staging. |
| T07 — Primer despliegue y smoke Staging | Ejecutar bootstrap autorizado, deploy manual de backend, publicación aprobada de Pages y smoke end-to-end. | Runbook y `docs/evidence/sprint-01/TA-DEPLOY-001/{README.md,test-results/,smoke/,deployment/}`; ninguna credencial en esos archivos. | Live, ready, login, `/me`, inventario, CORS, frontend y ruta del editor según CA-15/CA-17; confirmar revisión Alembic. | SHA desplegado, URL de Staging, resultados de checks/smoke, revisión Alembic y capturas/logs sanitizados. | **Depende de T01, T02, T03, T04, T05 y T06.** |

El bootstrap real (T04-C) se ejecuta solo como paso autorizado de T07: roles requeridos, primer administrador con datos de Staging controlados y datos mínimos necesarios. No se usan usuarios personales reales; la credencial inicial se administra/cambia según el procedimiento aprobado. No se ejecuta bootstrap desde CI de PR.

## 8. Bootstrap propuesto para Staging

El procedimiento detallado se aprobará antes de ejecutar acciones:

1. Acordar el SHA integrado de `integration/sprint-01` y confirmar los checks requeridos de CI; ejecutar también Playwright antes del deploy según la regla CA-12.
2. Crear/seleccionar y confirmar que el destino PostgreSQL es la BD Staging correcta, aislada y autorizada. Registrar `alembic current`, comprobar compatibilidad, precondiciones y datos acordados; confirmar backup o mecanismo de recuperación antes de migrar.
3. Crear/configurar la app Heroku con build desde raíz, Python 3.11 y un único proceso web. Inyectar `DATABASE_URL`, `SECRET_KEY`, `TOKEN_MINUTOS` y `CORS_ORIGINS` por configuración protegida de Heroku.
4. Verificar TLS, DNS y pooler desde Heroku; validar `pool_pre_ping`, pool y timeout frente a límites reales de Supabase, sin asumir números no revisados.
5. En PostgreSQL aislado/controlado, ensayar previamente la cadena existente. En Staging, revisar head/historial y autorización; ejecutar manualmente `python -m alembic upgrade head` solo sobre el destino confirmado. Registrar revisión anterior/posterior y comprobar `alembic current == fa014e1a2b3c`; comparar los registros acordados.
6. Ejecutar el bootstrap T04-C autorizado: roles, datos mínimos y primer administrador con datos sintéticos/controlados de Staging. No usar usuarios personales reales; gestionar/cambiar la credencial inicial según el procedimiento. Nunca ejecutar este bootstrap desde CI de PR.
7. Desplegar manualmente el backend desde `integration/sprint-01` mediante la integración GitHub → Heroku, con automatic deploy desactivado, y registrar el SHA desplegado.
8. Construir y publicar `frontend/dist` mediante Actions en el entorno `github-pages`, desde un commit integrado/aprobado de `integration/sprint-01`; usar `VITE_API_URL` HTTPS y base `/optimizador-vidrio/`.
9. Ejecutar smoke funcional de health, autenticación, `/me`, inventario, una operación segura de lectura, CORS/preflight, frontend sin localhost y navegación/recarga del editor dentro de la SPA; registrar SHA, Alembic y resultados sanitizados.
10. Solo tras revisión del equipo considerar habilitar automatic deploy del backend en una tarea posterior.

Este procedimiento es una propuesta; la ejecución requiere autorización operativa separada. Un rollback de aplicación no restaura automáticamente una revisión de base de datos.

## 9. Criterios de aceptación

| CA | Criterio verificable |
|---|---|
| CA-01 | Heroku detecta una aplicación Python desde la raíz del monorepo usando un único mecanismo canónico, instala dependencias desde una única fuente real de versiones y arranca FastAPI con el comando acordado, `0.0.0.0` y el `$PORT` administrado por Heroku. |
| CA-02 | El backend de Staging inicia desde un build limpio con configuración inyectada por la plataforma y no depende de un archivo `.env` local. |
| CA-03 | `SECRET_KEY` y `DATABASE_URL` provienen de configuración externa/protegida de runtime; no están versionadas, no aparecen en logs y no usan valores de ejemplo o defaults. |
| CA-04 | En desarrollo CORS admite los orígenes localhost acordados; en Staging solo admite el origen HTTPS autorizado de GitHub Pages. Un origen no configurado es rechazado y no hay wildcard. |
| CA-05 | `GET /health/live` devuelve `200 {"status":"ok"}`; no consulta PostgreSQL y sigue respondiendo aunque la BD esté caída. Se verifica con test que impide/observa toda conexión a la BD durante la llamada. |
| CA-06 | `GET /health/ready` ejecuta `SELECT 1` con timeout finito, explícito/configurable o razonable y verificado en T03. Devuelve `200 {"status":"ready"}` si la consulta termina correctamente y `503 {"status":"not_ready"}` si falla o vence el timeout, sin esperar indefinidamente. El 503 no revela URL/host/usuario de BD, SQL, stack trace, versión de PostgreSQL ni credenciales. |
| CA-07 | `/db-test` no está disponible públicamente: una solicitud a la ruta responde 404 y la ruta no aparece como endpoint operativo en OpenAPI. No se sustituye por otra ruta que revele detalles de PostgreSQL. |
| CA-08 | La cadena existente reporta un único head `fa014e1a2b3c`. Antes de migrar se confirma la BD correcta, revisión actual, precondiciones y backup/mecanismo de recuperación aprobado, y se ensaya la cadena en PostgreSQL aislado/controlado. Tras el upgrade manual autorizado de Staging, `alembic current` es `fa014e1a2b3c` y los datos de referencia y registros preexistentes acordados siguen presentes según comparación registrada. Este TA no crea revisiones ni ejecuta DDL manual. |
| CA-09 | El build Staging utiliza `VITE_API_URL` de la API HTTPS desplegada y no contiene `localhost`, `127.0.0.1` ni fallback local. |
| CA-10 | El build Vite funciona bajo `/optimizador-vidrio/`; los assets y navegación principal resuelven desde ese subpath. |
| CA-11 | La inspección de `frontend/dist` confirma que no contiene `SECRET_KEY`, `DATABASE_URL` ni tokens privados. Se documenta que `VITE_API_URL` es pública y que ninguna variable `VITE_*` es un secreto. |
| CA-12 | Como checks requeridos de PR, GitHub Actions ejecuta: (1) backend: instalación de dependencias, pytest completo y PostgreSQL aislado disponible para las pruebas requeridas; (2) frontend: `npm ci`, `npm run test:unit`, `npm run test:component`, `npm run lint`, `npm run build`. Una prueba PostgreSQL requerida no puede quedar omitida silenciosamente: si no corre, el check falla explícitamente. Los checks requeridos bloquean integración cuando fallan. Playwright es obligatorio pre-deploy de Staging; será check requerido de PR si CI dispone de PostgreSQL y browser reproducibles, y si no, T07 lo ejecuta como gate obligatorio antes de desplegar. La condición elegida y los resultados quedan registrados. CI no usa ni modifica Supabase Staging. |
| CA-13 | GitHub Actions publica `frontend/dist` en el entorno `github-pages`, desde un commit integrado/aprobado de `integration/sprint-01`; PR no publica y no se usa “Deploy from a branch” para servir código fuente Vite. El workflow usa permisos mínimos `contents: read`, `pages: write`, `id-token: write` y control de concurrencia para deployment. |
| CA-14 | El primer deploy del backend se realiza manualmente desde `integration/sprint-01` mediante integración GitHub → Heroku; automatic deploy permanece desactivado y se registra el SHA desplegado. Este TA no agrega automatización de deploy backend. |
| CA-15 | El smoke de release registra PASS/FAIL para: `/health/live`, `/health/ready`, login con usuario controlado, `/api/auth/me`, consulta de inventario (que cuenta como operación segura de solo lectura), CORS/preflight desde Pages, carga frontend, ausencia de llamadas a localhost y navegación/recarga del editor según la decisión de Pages. No requiere una mutación de datos. El smoke comprueba el flujo desplegado completo y sus resultados se registran. |
| CA-16 | El registro de deployment incluye SHA backend, SHA/commit del build frontend, revisión Alembic, fecha, entorno, comandos/checks y resultados. No contiene secretos, tokens ni datos sensibles. |
| CA-17 | La aplicación carga y puede recargarse en la URL Pages publicada bajo `/optimizador-vidrio/`; desde la navegación normal de la SPA se abre el editor sin 404. El editor no depende de `/optimizador-vidrio/editor-pieza` como ruta física profunda independiente ni de server-side fallback. Se verifica en Pages de Staging. |

## 10. Smoke post-deploy

El smoke debe ejecutarse después de cada primer deploy controlado y antes de considerar habilitar automatización:

1. `GET /health/live` devuelve `200 {"status":"ok"}` sin consultar PostgreSQL.
2. `GET /health/ready` ejecuta `SELECT 1` y devuelve `200 {"status":"ready"}`; no devuelve datos de PostgreSQL.
3. El frontend carga por HTTPS desde el origen de Pages bajo `/optimizador-vidrio/` y no realiza llamadas a localhost.
4. El navegador inicia sesión con una cuenta sintética/controlada autorizada, recibe la respuesta esperada y consulta `/api/auth/me`.
5. La UI consulta inventario con permisos válidos y completa al menos una operación segura de lectura/controlada.
6. La llamada desde Pages supera CORS/preflight; un origen no autorizado no obtiene permiso CORS.
7. La navegación normal de la SPA abre el editor y permite recargar la URL publicada sin 404; no se exige una ruta física profunda `/optimizador-vidrio/editor-pieza`.
8. Se comparan SHA backend, SHA/commit del build frontend y `alembic current` con la evidencia del release.

Los tokens de sesión, contraseñas, DSN, cabeceras de autorización y valores de secretos se eliminan de capturas y logs antes de conservar evidencia.

## 11. Riesgos y mitigaciones requeridas

| Riesgo | Mitigación/validación |
|---|---|
| Supabase compartido con esquema incompatible o datos previos | Usar destino Staging aislado; revisar revisión, datos y precondiciones antes de migrar; respaldar y obtener autorización. |
| Migraciones con precondiciones sobre datos | Ensayar en base controlada con datos representativos; documentar revisión inicial/final y recuperación; no migrar automáticamente en Actions. |
| Rollback de código confundido con rollback de esquema | Runbook trata releases de aplicación y recuperación de base por separado; no recomendar downgrade automático. |
| `%` en contraseña/URL Alembic y ConfigParser | Probar URL con caracteres reservados en instalación/runner controlado; usar manejo correcto de URL, no interpolación accidental ni credenciales impresas. |
| Conectividad IPv4/IPv6 hacia Supabase desde Heroku | Verificar resolución/conexión desde el runtime de destino y elegir pooler/endpoint compatible antes del bootstrap. |
| Límites de conexiones PostgreSQL/Supabase | Estimar procesos/worker count/pool y verificar conexiones; mantener un único web process para Staging inicial y ajustar pool dentro del límite autorizado. |
| Reinicios o dynos adicionales multiplican conexiones PostgreSQL | T02 valida `pool_pre_ping`, pool y timeout contra límites reales del plan Supabase; revisar el máximo de procesos/dynos antes de escalar y no fijar cifras sin la revisión del plan. |
| Build Vite apunta accidentalmente a localhost | Fallar build Staging si `VITE_API_URL` falta, usa HTTP o localhost; revisar `dist` antes de Pages. |
| CORS incorrecto | Lista explícita por ambiente, pruebas positivas/negativas de preflight y smoke desde origen Pages real; nunca `*`. |
| Ruta profunda de Pages requiere fallback que el hosting estático no ofrece | La decisión inicial evita publicar una ruta física independiente: integrar editor en navegación SPA bajo `/optimizador-vidrio/`; probar carga, navegación y recarga en Pages real. |
| `/db-test` expone información pública | Retirar endpoint y probar 404/OpenAPI; readiness devuelve solo estado genérico. |
| PostgreSQL tests omitidos silenciosamente en CI | Provisionar PostgreSQL de pruebas; confirmar conteos y fallar el job cuando la suite requerida se salte por falta de servidor. |
| Python/dependencias no detectados desde raíz | Build limpio usando el buildpack/ruta elegida y runtime Python 3.11; evitar duplicación de versiones. |
| Versiones distintas de Python/Node entre CI y los workflows de publicación | CI y Pages usan Python de la serie 3.11 y una versión Node compatible con `package-lock.json` y dependencias; comprobar reproducibilidad entre jobs sin fijar un parche no acordado. |
| Rollback de código confundido con recuperación de esquema | Redeploy del SHA backend anterior y republicación del artefacto/commit frontend anterior son acciones distintas de recuperar la BD. Si una migración no tiene downgrade seguro, detener release y usar recuperación aprobada; no ocultar divergencias con `alembic stamp`. |
| Staging recibe datos reales o credenciales personales durante bootstrap | Usar cuentas/datos controlados de Staging y credencial inicial gestionada/cambiada; no usar usuarios personales reales ni ejecutar bootstrap en CI. |

## 12. Plan de evidencia

La evidencia de implementación futura se guardará en:

```text
docs/evidence/sprint-01/TA-DEPLOY-001/
├── README.md
├── test-results/
├── smoke/
└── deployment/
```

- `README.md`: alcance revisado, SHA, topología y links de CI/deploy.
- `test-results/`: comandos y salidas reales de CI, Alembic y validaciones de build. No fabricar logs.
- `smoke/`: resultados HTTP/browser sanitizados, fecha, origen y SHA comprobados.
- `deployment/`: runbook ejecutado, runtime, app/deployment IDs no sensibles, revisión Alembic y aprobación. No incluir secretos ni DSN.

Esta SPEC no crea ni rellena esos archivos de evidencia.

## 13. Dependencias

- Aprobación del equipo/PO de esta SPEC y del alcance de Staging.
- Acceso autorizado a GitHub Pages/Actions y Heroku.
- Destino Supabase PostgreSQL de Staging aislado y autorizado.
- Revisión de migraciones Alembic, datos y precondiciones antes de la primera ejecución.
- Cuenta sintética o cuenta operativa de Staging autorizada para smoke de autenticación e inventario.
- Aprobación de secretos y orígenes por entorno, administrados fuera de Git.

## 14. Fuentes y trazabilidad del diagnóstico

- [Readiness de integration/sprint-01 para despliegue](../evidence/sprint-01/HU-012/readiness-integration-sprint-01.md).
- [HU-012 T03 — revisión de PR y limitaciones de deploy](../evidence/sprint-01/HU-012/t03-pull-request.md).
- [Backend README](../../backend/README.md), [CI actual](../../.github/workflows/ci.yml), [Vite config](../../frontend/vite.config.js), [frontend API URL](../../frontend/src/shared/apiUrl.js) y [App route](../../frontend/src/App.jsx).
- Diagnóstico: `/db-test` público; CORS fijado a localhost; health actual no comprueba BD; runtime/dependencias desde raíz no validados; Vite sin base de Pages y con fallback local de API; workflow Pages ausente; cobertura frontend de CI parcial.

## Historial de estado

- **Draft — 12/10/2026:** especificación técnica inicial basada en el diagnóstico de readiness existente. Decisiones de diseño propuestas; revisión y aprobación pendientes. No se implementó ni desplegó ningún cambio.
