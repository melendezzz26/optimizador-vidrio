# TA-DEPLOY-001 — Evidencia de Staging

## Actualización TA-035-T1 — 13/10/2026

El checklist original corresponde al estado previo a la ejecución remota que
documentaba esta tarea. El usuario confirmó que Staging fue creado y utilizado
posteriormente; las declaraciones históricas de «sin despliegue» no describen
su estado operativo actual. Se conserva el historial sin atribuirle resultados
remotos que no registró.

**Auditoría inicial (histórica):** la [actualización posterior a TA-036](actualizacion-predeploy-post-ta036.md)
registra las consultas remotas nuevas: Heroku live/ready 200 después de un
503 transitorio, Pages publicado desde `373dfc2` y checks locales focalizados.
En esa auditoría, la revisión Alembic de Staging, el SHA backend y el smoke
autenticado estaban pendientes; aún no se declaraba completada la actualización.

**Continuación verificada, 13/10/2026, 21:36 UTC / 16:36 Lima:** el usuario
autorizó actualizar la línea base a `293a2a9` (incluye TA-036 y TA-007), después
de comprobar el avance de integración y el workflow Pages `38443828520`
exitoso. El usuario confirmó Manual Deploy Heroku exitoso, release `v12`, y
después aportó Activity: `Deployed 293a2a93`, 16:35 según el panel. Raíz y ambos
health de Heroku devolvieron 200; Pages también 200. Heroku CLI no está
disponible localmente. La auditoría enlazada contiene los pasos de consola
remota, SQL de solo lectura, smoke autenticado manual y capturas A–H.
No se requiere navegador conectado a Codex. La consola remota aportada por el
usuario mostró head `ta036a1b2c3d` y BD `fa014e1a2b3c`; después confirmó upgrade
exitoso y current **`ta036a1b2c3d (head)`**. El smoke posterior a la migración,
21:42:03 UTC, devolvió 200 en raíz/live/ready. La introspección remota posterior
aportada por el usuario dio **SCHEMA_PASS**: columna INTEGER nullable, ambos
checks TA-036 y ausencia del índice antiguo de bajas de plancha. Esa etapa
quedó en **READY FOR USER STAGING SMOKE** y fue seguida por el cierre siguiente.

**Cierre confirmado, 13/10/2026: completado y validado en Staging.** La base
inicial de la rama TA-035-T1 es `373dfc2` (PR #42 y #44); la versión final
verificada es **`293a2a9`**, que incorpora después PR #43 (TA-007). Tras el
`git fetch origin --prune` informado por el usuario, la referencia local
`origin/integration/sprint-01` también se confirmó en `293a2a9`. La eliminación
de la rama remota TA-007 posterior al merge es normal. Heroku v12 y Pages ya
estaban en esa versión; no se requiere otro deploy ni publicación.

El usuario confirmó `POST /api/orders → 201`, lectura posterior 200 y pedido
visible en UI; GET planchas/retazos 200; `POST /api/inventory/retazos → 201
Created`, GET posterior 200 y `RET-HU005-002` visible en UI. La edición del
mismo retazo de 3 a 4 vértices respondió 200, con área final **5705.55 mm²**.
Las consultas de solo lectura en **Supabase Staging** confirmaron la fila ID 2,
código `RET-HU005-002`, `POLIGONO_CONVEXO`, `vertices_mm`, área 5705.55 y estado
true, además de Alembic `ta036a1b2c3d`, cantidad_afectada integer nullable y
ambos constraints TA-036. El defecto histórico Decimal JSON 500 queda resuelto
en el caso validado: POST 201 + GET 200 + persistencia PostgreSQL.

La auditoría contiene el checklist de once evidencias disponibles de código,
terminal, API de pedidos/inventario/retazo, esquema, persistencia, UI,
error/corrección y pruebas, más el resumen final para Notion. Este cierre solo
actualiza los tres documentos autorizados y los protege en un commit; no repite
operaciones remotas ni suites. Próximo estado con working tree limpio:
**READY TO SYNC WITH INTEGRATION**. Sin push, PR ni merge en este cierre.
El historial siguiente se conserva y no describe el estado final actual.

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
101 unit y 206 component passed; E2E 31 passed y 1 skip explícito preexistente
en esa ejecución. Lint, build y artefacto Staging sintético aprobados. El aviso
high transitivo de `source-map-js@1.2.1` identificado entonces se corrigió en el
lockfile a 1.2.2; auditorías y validaciones de seguimiento están en
[security-source-map-js.md](test-results/security-source-map-js.md).
CA-12/13 siguen parciales hasta ejecutar Actions, configurar protecciones y
publicar con aprobación. No se ejecutó T07 ni se modificó el estado Reviewed.

## Preflight T07 — preparación humana

[Checklist de deployment](t07-deployment-checklist.md) con pasos operativos,
gates, recuperación, estado de CA y resultados locales. **T07 pendiente**:
sin configuración remota, conexión Supabase Staging o publicación realizada.
El bloqueo de seguridad de `source-map-js` quedó resuelto con la actualización
transitiva mínima a 1.2.2. La validación E2E manual posterior al cambio pasó
(31 passed, 1 skipped, 0 failed); reemplaza la limitación previa del entorno
Codex. Estado del preflight: **READY FOR HUMAN STAGING DEPLOY**. Esto habilita la
revisión humana del despliegue, pero no declara T07 completada: siguen pendientes
Supabase real, Config Vars Heroku, migración y bootstrap reales, deploy manual
Heroku, publicación Pages y smoke Staging.

La validación post-seguridad registró `npm audit` y `npm audit --omit=dev` con
0 vulnerabilidades; frontend unit 101 passed, component 206 passed, lint/build/
build Staging-check PASS. E2E se ejecutó manualmente con Python 3.11.9 desde
`backend/venv/Scripts/python.exe`: 32 descubiertos, 31 passed, 1 skipped,
0 failed en 34.8 s. El skip conocido es la baja HU-014 en chromium-mobile; el
escenario desktop equivalente y el caso de permisos pasaron. Detalle en
[evidencia de seguridad](test-results/security-source-map-js.md).
