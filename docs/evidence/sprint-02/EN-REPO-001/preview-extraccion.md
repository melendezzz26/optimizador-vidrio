# EN-REPO-001 — Evidencia de extracción preliminar de repositorios

**Fecha:** 2026-11-10 (America/Lima). **Estado:** generación local verificada; corte remoto y despliegues pendientes.

- PBI: [EN-REPO-001 en Notion](https://app.notion.com/p/414e0c471a44812297f7ee150e15781b).
- SPEC: `docs/specs/SPEC-EN-REPO-001-separacion-repositorios.md` (Reviewed).
- ADR-003: Accepted por el responsable.
- PLAN: `docs/specs/PLAN-EN-REPO-001-separacion-repositorios.md`.
- Implementación: [PR #116](https://github.com/melendezzz26/optimizador-vidrio/pull/116), rama `feature/EN-REPO-001-extraccion` (sin merge).
- Base congelada: `backup/pre-separacion-2026-11-10` en `137f2ccd7a542c73e99fd40a792287595cdcd9c8`.
- PR #114 incluido; PR #113 sigue abierto y no se migró a estas instantáneas.

## Automatización de extracción

[GitHub Actions 42827114268](https://github.com/melendezzz26/optimizador-vidrio/actions/runs/42827114268) **success**. Job `split` completo, con pasos de preparación, validación, compresión y subida de artefactos exitosos.

- SHA del commit que disparó el workflow: `b5214dd2bf4c92ea551e83f2516c51bd48102234`.
- Artefacto: `en-repo-001-preview-b5214dd2bf4c92ea551e83f2516c51bd48102234-42827114268`, ID GitHub `13769968009`.
- Tamaño ZIP: **10 345 401 bytes**; digest del artefacto `sha256:2f069d76a072169aceb18afab4c6f252133bc91feae404820a5b95f61850bb3b`.
- Expira: 2026-11-17 13:43 UTC, según GitHub. Conservar copias externas si la evidencia debe ser durable.

## Resultados de manifest y repos extraídos

| Componente | Archivos originales validados | Commits del historial filtrado, verificados localmente | HEAD nuevo filtrado |
|---|---:|---:|---|
| Frontend | 270 | 242 | `1bfe1fc83bddeee17bd6b19d461a5867cc8dc786` |
| Backend | 479 | 301 | `6c1d97b3837ebbe5c98c01e2cdb87bf67df0e173` |

Los SHA filtrados pertenecen a la historia **antes de comitear** los cambios de CI/configuración. El ZIP incluye `newglass-frontend.tar.gz`, `newglass-backend.tar.gz`, `split-manifest.json` y los dos `commit-map.txt`.

**Validación adicional sobre el ZIP extraído** en el entorno de revisión:

- `git fsck --connectivity-only` en frontend y backend: salida correcta, exit 0.
- AST Python de `backend/tests/unit/test_ci_contract.py` y `.github/scripts/backend_failure_summary.py`: parseado sin errores.
- YAML `ci.yml` frontend/backend y `deploy-pages.yml` frontend: parseado; jobs frontend+e2e, backend, checks+pages.
- `PYTHONPATH=. python -m pytest tests/unit/test_ci_contract.py -q --tb=short` en backend extraído: **4 passed in 0.08s**.
- No se ejecutaron todas las pruebas de negocio ni E2E del repositorio extraído.

## Observaciones importantes

1. **Aún no existen** los repositorios remotos `melendezzz26/newglass-frontend` ni `melendezzz26/newglass-backend`. La conexión Github usada aquí puede editar el repositorio original, pero no incluye una acción para crear repos nuevos.
2. Los repos extraídos contienen adaptaciones locales sin commit, para revisar y probar antes de publicar.
3. `deploy-pages.yml` de destino tiene solo `workflow_dispatch`; nunca se publicó un frontend ni se conectó Heroku a otro repo.
4. El CI E2E entre repos exige la variable `NEWGLASS_BACKEND_E2E_SHA` apuntando al SHA **real** del backend nuevo. No debe suprimirse ese requisito para volver a verde.
5. Historial de commits filtrado conserva atribuciones visibles, pero hashes reescritos; mantener los mapas de commit.
6. La interfaz, la API, el supervisor de memoria, los seis motores, Supabase y Alembic no han sido modificados en Staging.
7. Pendiente: crear nuevos repositorios vacíos, validar las suites completas, configurar ramas/roles/CI, tratar PR #113, vincular deployment y registrar rollback.

**Conclusión de esta evidencia:** extracción local lista para revisión y publicación en repositorios nuevos; migración remota **no** completada.