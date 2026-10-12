# TA-DEPLOY-001 — Evidencia de Staging

## Identificación

- **PBI:** TA-DEPLOY-001 — Preparación y despliegue controlado de Staging
- **SPEC:** `docs/specs/SPEC-TA-DEPLOY-001-staging.md`
- **Rama:** `feature/TA-DEPLOY-001-staging`
- **Estado de la SPEC:** Reviewed (según la autorización de implementación).

## Estado de T01 — Arranque Heroku del monorepo

**IMPLEMENTADA / VALIDACIÓN LOCAL COMPLETA.** La evidencia disponible valida localmente la estructura de arranque desde la raíz, la resolución de dependencias, la declaración de Python 3.11 y el comando equivalente al Procfile. No es una validación de Heroku real.

Esta documentación registra resultados de validaciones ejecutadas y proporcionadas para T01; no se repitieron durante su documentación.

Se registraron estos archivos en la raíz del monorepo:

- `.python-version`, con contenido `3.11`.
- `requirements.txt`, con contenido `-r backend/requirements.txt`.
- `Procfile`, con contenido `web: cd backend && python -m uvicorn main:app --host 0.0.0.0 --port $PORT`.

El detalle de comandos y resultados está en [test-results/t01-heroku-boot.md](test-results/t01-heroku-boot.md).

## CA-01

**PARCIALMENTE VALIDADO.** La validación local no demuestra detección por Heroku, instalación limpia Linux, uso del `PORT` asignado por Heroku, arranque de un dyno ni registro de SHA desplegado. Por tanto, CA-01 no se declara Cumplido; esos puntos quedan pendientes de T07.

## Alcance de esta evidencia

Este directorio registra evidencia local por tarea, detallada a continuación.
No se ejecutó un despliegue ni una instalación limpia Linux/Heroku para producir
estos registros. La validación remota de T07 sigue pendiente.

## Estado de T02 — Configuración de Staging y conexión segura

**IMPLEMENTADA / VALIDACIÓN LOCAL.** Configuración externa centralizada,
CORS configurable, validación de secretos/números, opciones PostgreSQL,
`pool_pre_ping` y representación segura de `%` en ConfigParser/Alembic.

Resultados realmente ejecutados y limitaciones en
[test-results/t02-config-staging.md](test-results/t02-config-staging.md).
El cambio parte de `1ff7cfd847625b262caf717f4f945fa7d9711fc9`, en
`feature/TA-DEPLOY-001-staging`; no se hizo commit durante esta implementación.

- **CA-02: aporte local parcial.** Prueba de carga de app/engine desde entorno
  sin depender del `.env`. Pendiente build limpio y configuración de plataforma.
- **CA-03: aporte local parcial.** Variables obligatorias sin defaults secretos,
  errores sanitizados y prioridad del entorno. Pendiente configuración protegida
  real y revisión de logs/operación del destino.
- **CA-04: aporte local parcial.** Defaults de desarrollo y preflight con
  orígenes sintéticos permitidos/denegados. Pendiente origen real de Pages y
  preflight remoto en T07; no se declara completamente cumplido.

No se validaron conexión Supabase, TLS remoto, límites del plan, CORS Pages real
ni configuración Heroku. Esos puntos quedan para T04/T07. La SPEC no se marca
Implemented. Durante T02 no se avanzó a T03–T07.

## T03 — Health checks

Implementación local de `/health/live`, `/health/ready` y retirada de `/db-test`.
Contrato, límites y ejecuciones en [t03-health.md](test-results/t03-health.md).
CA-05/06/07 se verifican localmente; el smoke de los servicios desplegados
permanece pendiente de T07. No se modificaron T01/T02.

## T04 — Procedimiento Alembic y bootstrap

Preparación local y runbook en [staging.md](../../../infrastructure/staging.md).
Ensayos y auditoría en [t04-alembic-bootstrap.md](test-results/t04-alembic-bootstrap.md).
T04-A/B remotas y bootstrap Staging no ejecutados; CA-08 permanece parcial
hasta verificar destino, revisión, recuperación y datos reales autorizados en T07.

## T05 — Preparación de GitHub Pages

Build Staging con API HTTPS obligatoria y base `/optimizador-vidrio/`; editor
por flujo interno de pedidos. [Resultados T05](test-results/t05-pages-build.md).
CA-09/10/11: comprobaciones locales con API sintética; CA-17 solo navegación
local, pendiente de carga/recarga en Pages real. No se publicó el sitio.

## T06 — CI y workflow Pages

**IMPLEMENTADA / VALIDACIÓN LOCAL.** CI backend/frontend/E2E con PostgreSQL
obligatorio aislado y workflow Pages restringido a integración, después de CI.
[Resultados T06](test-results/t06-ci-pages.md): backend 1284 passed, frontend
101 unit y 206 component passed; E2E 31 passed y 1 skip explícito preexistente.
Lint, build y artefacto Staging sintético aprobados. npm reporta un aviso high
transitivo pendiente de evaluación; no se alteraron dependencias.
CA-12/13 siguen parciales hasta ejecutar Actions, configurar protecciones y
publicar con aprobación. No se ejecutó T07 ni se modificó el estado Reviewed.
