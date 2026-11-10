# PLAN-EN-REPO-001 — Migración controlada a dos repositorios

| Campo | Valor |
|---|---|
| Estado | Draft |
| PBI | [EN-REPO-001 — Notion](https://app.notion.com/p/414e0c471a44812297f7ee150e15781b) |
| SPEC | [SPEC-EN-REPO-001](SPEC-EN-REPO-001-separacion-repositorios.md) |
| ADR | [ADR-003](../adr/ADR-003-repositorios-independientes-frontend-backend.md) |
| Fuente | `integration-02`; SHA observado `f46d96db9f5ca6071445bae5f884908aed734ff4` **referencia histórica, no corte autorizado** |
| Responsable / revisor | Por asignar |
| Despliegues | Prohibidos durante definición y extracción sin aprobación |

## Precondiciones comunes

- Review y aprobación de SPEC y ADR; decidir nombres, propietarios, permisos y responsables de ambos repos.
- Reconfirmar estado de `integration-02`, `main`, PR abiertos y SHA de corte real. En la revisión previa PR #113 y #114 estaban abiertos; no asumir el mismo estado después.
- Registrar la referencia del monorepo y un backup verificable del historial antes de cualquier `git filter-repo`. Separar con clones temporales limpios; ningún `force push` al repo original.
- Definir estrategia de documentación compartida (histórico monorepo, duplicación controlada o contrato canónico con enlaces).
- Registrar el contrato mínimo de compatibilidad entre SHAs de ambos repos antes de desplegar.

## Fase T01 — Revisión y aprobación documental

1. Revisar SPEC, PLAN y ADR mediante PR de documentación a `integration-02`; no fusionar sin revisión.
2. Registrar decisiones abiertas: nombres/visibilidad/accesos de repos, ownership del CI E2E, nuevo dominio Pages, criterio para cortar PR abiertos.
3. Marcar SPEC Reviewed solo tras revisión explícita, manteniendo Notion enlazado.

**Salida verificable:** decisiones registradas y PR documental aprobado. **No implica nueva infraestructura ni despliegue.**

## Fase T02 — Congelar punto de corte y preservar trazabilidad

1. Repetir consulta de ramas, PR, checks, SHA y despliegue Heroku/Pages; aprobar SHA único y registrar hora.
2. Crear un tag o referencia de respaldo **solo después de acordar el corte**, y preparar backups Git verificables del repositorio original; registrar comandos y hashes.
3. Inventariar rutas bajo `frontend/`, `backend/`, `docs/`, `experiments/`, `.github/` y archivos raíz. Marcar dueño de cada ruta y casos mixtos.
4. Identificar dependencias ocultas por rutas relativas, fixtures, informes, workflows, links y herramientas.
5. Preparar checklist de integridad, commit-map y matriz de versión cruzada.

**Salida:** manifiesto de baseline, respaldos verificables e inventario revisado.

## Fase T03 — Extracción del historial en repos temporales

1. Clonar el SHA aprobado en dos copias temporales independientes; registrar versión de Git y de `git-filter-repo`.
2. Filtrar `frontend/` y `backend/` a raíz de repos temporales, analizando merges y commits transversales. Conservar author/committer metadata y generar `commit-map` por extracción.
3. Incorporar archivos raíz y documentación del propietario mediante commits explícitos y auditables; evitar arrastrar workflows ajenos y secretos.
4. Probar que historial y árboles corresponden al baseline; verificar referencias históricas y lista de contribuyentes.
5. Crear repositorios remotos **cuando estén aprobados** y publicar ramas de migración sin alterar el monorepo.

**Salida:** dos repos separados, árbol consistente y mapeo de SHA; sin tráfico real.

## Fase T04 — Adaptación reproducible de ejecución y CI

### Backend

- Llevar `backend/requirements.txt`, `alembic.ini`, `app/`, `main.py`, `tests/` y scripts a raíz.
- Ajustar `Procfile` sin `cd backend`; conservar `--workers 1`, límites y configuración vigentes, puerto `$PORT`.
- Trasladar el workflow de pytest y el script de resumen seguro, ajustando rutas/working-directory; conservar pruebas PostgreSQL aisladas y ejecución separada de suites con sensibilidad de recursos.
- Actualizar pruebas de contrato CI/Procfile para la nueva estructura, sin aflojar garantías.

### Frontend

- Llevar `frontend/package.json`, lock, Vite, src, tests, scripts a raíz.
- Configurar Pages base para el nuevo nombre/dominio y `VITE_API_URL` HTTPS; mantener validación de build sin secretos ni fallback localhost.
- Reescribir los paths `../backend` de Playwright para apuntar a un checkout backend hermano controlado, sin implicar un mismo repo.

### Integración

- Mantener job E2E que checkout **dos SHAs explícitos**, no dos ramas flotantes; configurar runner con PostgreSQL y navegador efímeros.
- Determinar ubicación del orquestador E2E (preferencia inicial: workflow frontend consumiendo backend por SHA fijado) y qué PR activa el gate.
- Validar API, autenticación, inventario, pedidos, comparación de seis motores, eventos y confirmación.
- Conservar reglas de branch protection y reglas del environment `github-pages` tras traslado.

**Salida:** CI real verde por repo + gate E2E efectivo, con URLs y SHAs.

## Fase T05 — Corte controlado de despliegues

1. Confirmar aprobación humana, contratos y gates sin skips; registrar SHA frontend/backend y revisión Alembic.
2. Mantener Heroku actual hasta prueba de checkout/compilación del repo backend; transferir su origen GitHub con estrategia de rollback y sin cambiar Config Vars innecesariamente.
3. Publicar Pages desde repo frontend y revisar ruta base, navegación, renovación de sesión, assets y CORS del origen HTTPS.
4. Ejecutar smoke de login, `/me`, clientes, pedidos, inventario, comparación, eventos, selección y confirmación sobre datos controlados, sin duplicar operaciones de stock en producción.
5. Conservar el monorepo original como histórico consultable y deshabilitar *solo cuando corresponda* el workflow Pages antiguo para evitar dobles publicaciones.
6. Documentar rollback independiente: Heroku al SHA anterior y frontend al artefacto/commit anterior; no confundir rollback de aplicación con rollback de esquema de BD.

**Salida:** comprobación operativa y aceptación del corte; nunca declarar completado antes de observarlo.

## Fase T06 — Cierre y evidencias

- Actualizar README/CONTRIBUTING e índices en Notion y repos nuevos, incorporar mapa de SHA, matriz de compatibilidad y enlaces de PR.
- Verificar ausencia de rutas rotas, secretos y documentación incompatible.
- Registrar pruebas ejecutadas, errores conocidos, responsables y fecha.
- Marcar EN-REPO-001 y SPEC **Verified** únicamente tras aceptación y smoke satisfactorio.

## Dependencias y riesgos

| Riesgo | Prevención | Criterio de parada |
|---|---|---|
| PR abiertos omitidos del corte | inventario y decisión previa; SHA congelado | PR sin decisión |
| pérdida de atribución Git | historial filtrado + commit-map + repositorio histórico | faltan autores/commits relevantes |
| E2E deja de arrancar backend | checkout explícito + adaptación Playwright | E2E incompleto o skipped |
| fallo de Heroku por working directory | Procfile y build desde raíz + smoke | no arranca `--workers 1` |
| CORS/Pages apuntan a dominio obsoleto | revisar Pages base, VITE_API_URL, CORS | 404, preflight denegado |
| versiones FE/BE incompatibles | manifiesto cruzado de SHAs + contrato | integración E2E falla |
| doble publicación de frontend | cutover de una sola fuente Pages | despliegues simultáneos |

## Criterio de listo para implementar

**No iniciar la fase T02/T03** hasta aprobación de esta SPEC/ADR y resolución de decisiones pendientes. Este PLAN por sí solo no concede autorización para ejecutar un cutover.

## Estado

2026-11-10: Draft documental. Sin repositorios nuevos, migraciones, deployment ni modificaciones productivas.
