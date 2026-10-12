# TA-DEPLOY-001 — Preparación y despliegue controlado de Staging

## Información general

| Campo | Valor |
|---|---|
| Estado | Draft |
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
- El CI existente ejecuta pytest en Python 3.11 y lint/build del frontend. No ejecuta unit/component frontend ni E2E; se debe acordar y hacer visible la cobertura requerida, especialmente para que las pruebas que necesitan PostgreSQL no queden omitidas silenciosamente.
- El frontend ya lee `VITE_API_URL`, pero usa `http://127.0.0.1:8000` como fallback. `vite.config.js` no fija `base`, y la ruta `/editor-pieza` compara el pathname desde raíz. Hay que validar el subpath de GitHub Pages y la navegación directa/recarga.
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
- revisar el acceso directo y la recarga de `/editor-pieza` bajo el subpath de Pages;
- definir CI requerido y un workflow de publicación de GitHub Pages;
- documentar bootstrap, despliegue inicial manual de backend, smoke post-deploy y evidencia reproducible.

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
- Las dependencias de `backend/requirements.txt` deben ser detectables en el flujo de build desde raíz. La implementación deberá elegir el mecanismo admitido por el buildpack, evitar una segunda lista de versiones que pueda divergir y demostrarlo con una instalación/build limpio.
- Primer despliegue del backend manual y controlado mediante la integración GitHub de Heroku. Mantener desactivado el automatic deploy hasta que Staging y sus smoke checks estén aprobados.
- El proceso web debe escuchar en `0.0.0.0` y en el `PORT` suministrado por Heroku.

### 5.2 Configuración y seguridad del backend

- La configuración de Staging llega desde variables del entorno de Heroku, nunca desde `.env` versionado o requerido en runtime.
- `SECRET_KEY` y `DATABASE_URL` son valores externos y secretos. No incluirlos en logs, respuestas, artifacts ni evidencia.
- `TOKEN_MINUTOS` debe ser positivo y conservar el valor acordado por el equipo.
- `CORS_ORIGINS` contiene orígenes explícitos separados por entorno. No se permite wildcard.
- Desarrollo permite `http://localhost:5173` y `http://127.0.0.1:5173`. Staging permite únicamente el origen HTTPS real del sitio GitHub Pages aprobado; el path `/optimizador-vidrio/` no forma parte del origen CORS.
- La configuración debe fallar de forma clara y segura si falta una variable obligatoria de Staging; no debe caer silenciosamente a localhost ni a una clave predeterminada.

### 5.3 Supabase y Alembic

- Persistencia por PostgreSQL usando SQLAlchemy y psycopg.
- No usar el SDK Supabase ni sus credenciales `anon`/`service_role` para acceso de backend.
- Exigir TLS y validar la cadena de conexión con el driver existente.
- Evaluar el Session Pooler según región, modo de conexión, soporte IPv4/IPv6 y límites disponibles para Heroku; registrar la decisión antes de provisionar.
- Staging debe apuntar a un destino PostgreSQL aislado y autorizado, no a un esquema compartido cuya revisión o datos no hayan sido comprobados.
- La revisión de Alembic debe inspeccionarse antes de migrar. La cadena actual esperada debe conservar un único head, `fa014e1a2b3c`.
- El primer `alembic upgrade head` en Staging será manual, autorizado y precedido por revisión de precondiciones y datos. No automatizar migraciones desde GitHub Actions en el primer deploy.
- Un rollback de código no revierte el esquema. El runbook debe describir por separado recuperación de código y recuperación de base de datos.

### 5.4 Frontend — GitHub Pages

- Publicar `frontend/dist` mediante GitHub Actions y el flujo de publicación de Pages.
- Configurar base Vite como `/optimizador-vidrio/` para Staging.
- `VITE_API_URL` se suministra al build y apunta a la API HTTPS de Heroku. Es configuración pública incluida en el bundle; nunca colocar secretos en variables `VITE_*`.
- El build de Staging debe fallar o ser bloqueado si `VITE_API_URL` está ausente, apunta a localhost o usa HTTP.
- Comprobar la ruta `/optimizador-vidrio/editor-pieza`, navegación directa y recarga. La solución debe ajustarse al comportamiento de rutas estáticas de GitHub Pages y no depender del `pathname === '/editor-pieza'` desde raíz.
- Las solicitudes del navegador deben usar el origen de API configurado; no deben derivar una URL local como fallback de Staging.

### 5.5 CI y publicación

- CI corre en pull requests y antes de integrar a la rama acordada por el equipo.
- Propuesta mínima de suites requeridas: backend completo con las pruebas de integración PostgreSQL realmente disponibles; frontend unitarias y componentes; lint; build. El equipo debe confirmar explícitamente si E2E se hace requerido en CI o se mantiene como smoke separado.
- Una prueba que requiera PostgreSQL no puede quedar omitida silenciosamente en CI: el workflow debe aprovisionar la infraestructura de prueba requerida y reportar claramente cualquier skip.
- GitHub Pages se publica mediante Actions a partir de un commit aprobado de la rama acordada, no desde pull requests sin integrar.
- El primer backend deploy sigue siendo manual; el workflow de Pages no implica un pipeline de Heroku.
- Los workflows no contienen secretos de aplicación ni ejecutan migraciones en el primer despliegue.

## 6. Variables de entorno

Los nombres se documentan sin valores reales. Los secretos se configuran en el entorno de destino o en el almacén de secretos de CI cuando sea estrictamente necesario.

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
| T01 — Arranque Heroku del monorepo | Acordar un build Python desde la raíz, runtime Python 3.11, detección de dependencias backend y proceso web con `$PORT`. | `Procfile`, mecanismo de runtime Python admitido, `requirements.txt` raíz o configuración equivalente, `backend/requirements.txt`, README operativo. | Build limpio desde checkout raíz; smoke de proceso con puerto asignado; comprobar que no requiere `.env` local. | Log de build sanitizado, SHA, runtime detectado y resultado de arranque. | Decisión del buildpack y versión Python; coordinación con T02. |
| T02 — Configuración de Staging y conexión segura | Separar runtime config, validar variables obligatorias, construir CORS explícito y conectar SQLAlchemy a PostgreSQL por TLS. | `backend/app/shared/config/`, `backend/app/shared/database/session.py`, `backend/main.py`, pruebas de configuración/CORS, documentación de variables. | App sin `.env`; falta de variable obligatoria; orígenes dev/Staging permitidos y origen no autorizado rechazado; conexión PostgreSQL controlada. | Matriz de variables sin valores, resultado de CORS y reporte de conexión sin DSN ni secretos. | T01 para build/runtime; destino Staging autorizado para la validación remota. |
| T03 — Health checks y cierre de diagnóstico público | Crear liveness independiente de BD, readiness con conexión limitada y retirar `/db-test`. | `backend/main.py` o router health dedicado, pruebas API/health, documentación OpenAPI si corresponde. | `/health/live` 200 sin BD; `/health/ready` 200 con BD disponible y 503 controlado ante fallo; `/db-test` no disponible; sin detalles internos en respuesta. | Resultados HTTP sanitizados y prueba que confirma que no se expone `/db-test`. | Puede preparar liveness en paralelo; readiness depende de T02. |
| T04 — Supabase, Alembic y bootstrap de Staging | Confirmar aislamiento, revisar revisión/precondiciones, definir operación manual de migración y pasos aprobados para catálogo/roles/primer administrador. | Configuración Alembic existente, `backend/alembic/`, procedimiento operativo Staging, evidencia bajo `deployment/`. | PostgreSQL aislado con esquema compatible; un solo head `fa014e1a2b3c`; ensayo de upgrade en ambiente controlado; revisar que credenciales con `%` no rompan URL/config. | Revisión inicial/final de Alembic, log de migración sin URL/secretos, respaldo/plan de recuperación registrado. | T02 y confirmación autorizada del destino; nunca ejecutar sobre producción o Supabase compartido sin aprobación. |
| T05 — Frontend preparado para GitHub Pages | Construir el sitio bajo el base path, exigir API HTTPS de Staging y validar la ruta de editor. | `frontend/vite.config.js`, `frontend/src/shared/apiUrl.js`, `frontend/src/App.jsx`, configuración frontend/env example y pruebas de ruta/build. | Build con `/optimizador-vidrio/`; bundle sin secretos ni localhost; rutas/recursos cargan en subpath; `/editor-pieza` abre y sobrevive recarga/direct navigation. | Resumen de build y smoke browser con URL/base y SHA; sin tokens ni variables sensibles. | Contrato/origen HTTPS de T02; puede avanzar con origen temporal documentado. |
| T06 — CI y publicación controlada | Definir checks requeridos de PR, prevenir skips silenciosos de PostgreSQL y publicar `frontend/dist` con Pages Actions desde commit aprobado. | `.github/workflows/ci.yml`, workflow dedicado de Pages en `.github/workflows/`, configuración de Pages/branch protection, harness PostgreSQL de tests. | Verificar backend, unit/component, lint/build; verificar reporte de tests PG sin omisión silenciosa; validar artifact de Pages y que PR no publique. E2E requerido se decide explícitamente. | URL/run de Actions, resumen de checks y artifact/commit publicado. | T01, T03 y T05; T02/T04 para pruebas que dependen de PostgreSQL. |
| T07 — Primer despliegue y smoke Staging | Ejecutar bootstrap autorizado, deploy manual de backend, publicación aprobada de Pages y smoke end-to-end. | Runbook y `docs/evidence/sprint-01/TA-DEPLOY-001/{README.md,test-results/,smoke/,deployment/}`; ninguna credencial en esos archivos. | Live, ready, login, `/me`, inventario, CORS, frontend y ruta del editor según CA-15/CA-17; confirmar revisión Alembic. | SHA desplegado, URL de Staging, resultados de checks/smoke, revisión Alembic y capturas/logs sanitizados. | **Depende de T01, T02, T03, T04, T05 y T06.** |

## 8. Bootstrap propuesto para Staging

El procedimiento detallado se aprobará antes de ejecutar acciones:

1. Acordar SHA de integración y confirmar que los CI checks requeridos están verdes.
2. Crear/seleccionar un destino de PostgreSQL Staging aislado y autorizado. Revisar su esquema, `alembic_version`, precondiciones y datos; no asumir que está vacío ni compatible.
3. Crear la app Heroku con build desde raíz, runtime Python 3.11 y un único proceso web. Configurar `DATABASE_URL`, `SECRET_KEY`, `TOKEN_MINUTOS` y `CORS_ORIGINS` mediante configuración protegida de Heroku.
4. Verificar conectividad TLS, DNS y pooler elegido desde el runtime Heroku; fijar límites de conexiones compatibles con PostgreSQL.
5. Revisar los heads y el historial Alembic; tomar/confirmar respaldo y autorización. Aplicar manualmente `python -m alembic upgrade head` solo al destino de Staging aprobado y registrar revisión anterior/posterior.
6. Ejecutar únicamente el bootstrap autorizado de datos de Staging, roles y primer administrador. No reutilizar credenciales personales ni ejecutar seeds indiscriminados contra una base compartida.
7. Construir y desplegar manualmente el backend desde el SHA aprobado mediante la integración GitHub de Heroku. Mantener automatic deploy desactivado durante el primer ciclo.
8. Construir el frontend con `VITE_API_URL` HTTPS y base `/optimizador-vidrio/`; publicar `frontend/dist` mediante Actions en GitHub Pages para el commit aprobado.
9. Ejecutar smoke de health, autenticación, `/me`, lectura de inventario, CORS, frontend y `/editor-pieza`; registrar SHA, Alembic y resultados sanitizados.
10. Solo tras revisión del equipo considerar habilitar automatic deploy del backend en una tarea posterior.

Este procedimiento es una propuesta; la ejecución requiere autorización operativa separada. Un rollback de aplicación no restaura automáticamente una revisión de base de datos.

## 9. Criterios de aceptación

| CA | Criterio verificable |
|---|---|
| CA-01 | Heroku detecta una aplicación Python desde la raíz del monorepo, instala las dependencias backend detectables desde esa raíz y arranca FastAPI con el comando acordado, `0.0.0.0` y el `$PORT` administrado por Heroku. |
| CA-02 | El backend de Staging inicia desde un build limpio con configuración inyectada por la plataforma y no depende de un archivo `.env` local. |
| CA-03 | `SECRET_KEY` y `DATABASE_URL` se suministran externamente por configuración protegida del entorno; no aparecen en Git, logs, respuestas, artefactos frontend ni evidencia. |
| CA-04 | En desarrollo CORS admite los orígenes localhost acordados; en Staging solo admite el origen HTTPS autorizado de GitHub Pages. Un origen no configurado es rechazado y no hay wildcard. |
| CA-05 | `GET /health/live` responde 200 sin consultar ni depender de PostgreSQL, incluso si la base de datos no está disponible. |
| CA-06 | `GET /health/ready` responde 200 cuando PostgreSQL puede ejecutar la comprobación de conectividad y devuelve 503 controlado ante indisponibilidad/timeout, sin exponer DSN, secretos o stack trace. |
| CA-07 | `/db-test` se retira: la ruta responde 404 y no aparece en OpenAPI. |
| CA-08 | Alembic reporta un único head `fa014e1a2b3c`; en un PostgreSQL Staging aislado y compatible, el procedimiento manual autorizado lleva la base hasta esa revisión y registra revisión inicial/final sin perder datos. |
| CA-09 | El build Staging utiliza `VITE_API_URL` de la API HTTPS desplegada y no contiene `localhost`, `127.0.0.1` ni fallback local. |
| CA-10 | El build Vite funciona bajo `/optimizador-vidrio/`; los assets y navegación principal resuelven desde ese subpath. |
| CA-11 | La inspección del bundle `frontend/dist` no encuentra secretos ni credenciales. Se documenta que toda variable `VITE_*` es pública. |
| CA-12 | Los checks requeridos acordados aparecen como jobs de GitHub Actions en PR, muestran resultados explícitos y bloquean integración si fallan. Los tests que requieren PostgreSQL se ejecutan con infraestructura disponible o fallan explícitamente; no se aceptan skips silenciosos. |
| CA-13 | GitHub Pages publica el artefacto `frontend/dist` mediante Actions desde un commit aprobado; pull requests no publican el sitio. |
| CA-14 | El primer deploy del backend se ejecuta manualmente/controlado desde el SHA aprobado, con automatic deploy desactivado; el log identifica el SHA desplegado. |
| CA-15 | El smoke post-deploy comprueba `/health/live`, `/health/ready`, login, `/api/auth/me`, lectura de inventario, CORS desde el origen Pages y carga del frontend; resultado y SHA quedan registrados. |
| CA-16 | La evidencia identifica SHA de backend/frontend desplegados, revisión Alembic, URL del entorno y comandos/resultados reproducibles; no contiene secretos, tokens ni datos sensibles. |
| CA-17 | La ruta `/optimizador-vidrio/editor-pieza` se puede abrir directamente y recargar en Pages sin 404 ni perder el editor; el comportamiento se verifica en el hosting real de Staging. |

## 10. Smoke post-deploy

El smoke debe ejecutarse después de cada primer deploy controlado y antes de considerar habilitar automatización:

1. `GET /health/live` devuelve 200.
2. `GET /health/ready` devuelve 200 y confirma conectividad, sin devolver datos de PostgreSQL.
3. El frontend carga por HTTPS desde el origen de Pages bajo `/optimizador-vidrio/`.
4. El navegador inicia sesión con cuenta sintética/operativa autorizada, recibe respuesta esperada y consulta `/api/auth/me`.
5. La UI puede consultar inventario con permisos válidos.
6. La llamada desde Pages supera CORS; una llamada desde origen no autorizado no recibe permiso CORS.
7. `/optimizador-vidrio/editor-pieza` carga directamente y al refrescar.
8. Se comparan SHA desplegado y `alembic current` con la evidencia del release.

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
| Build Vite apunta accidentalmente a localhost | Fallar build Staging si `VITE_API_URL` falta, usa HTTP o localhost; revisar `dist` antes de Pages. |
| CORS incorrecto | Lista explícita por ambiente, pruebas positivas/negativas de preflight y smoke desde origen Pages real; nunca `*`. |
| Ruta profunda de Pages `/editor-pieza` falla por base path/fallback | Probar navegación directa y recarga en staging-hosted Pages, no solo `vite preview`; adoptar fallback compatible con Pages. |
| `/db-test` expone información pública | Retirar endpoint y probar 404/OpenAPI; readiness devuelve solo estado genérico. |
| PostgreSQL tests omitidos silenciosamente en CI | Provisionar PostgreSQL de pruebas; confirmar conteos y fallar el job cuando la suite requerida se salte por falta de servidor. |
| Python/dependencias no detectados desde raíz | Build limpio usando el buildpack/ruta elegida y runtime Python 3.11; evitar duplicación de versiones. |

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
