# EN-REPO-001 — Preparación de dos repositorios independientes

La **SPEC aprobada** y la **ADR-003 aceptada** están en el [PR documental #115](https://github.com/melendezzz26/optimizador-vidrio/pull/115). Este directorio ejecuta **solo la preparación local**, en clones descartables; no crea repos remotos ni altera el staging de Heroku/Pages/Supabase.

## Línea base congelada

- Repositorio origen: `melendezzz26/optimizador-vidrio`.
- Rama inmutable de referencia acordada para preparar la migración: `backup/pre-separacion-2026-11-10`.
- SHA verificado al crear el respaldo: `137f2ccd7a542c73e99fd40a792287595cdcd9c8` (integra el PR #114, pero **no** el PR #113 todavía abierto).
- El usuario aceptó el 10/11/2026 continuar con la implementación. La separación **no equivale** a autorizar el cambio de origen de Heroku ni la publicación de Pages.
- Si se decide incorporar el PR #113 antes del corte, registrar un **nuevo SHA**, crear otra rama de respaldo e invocar el generador pasando `--ref` y `--sha` revisados. Nunca inventar un SHA.

## Requisitos del equipo

- Python 3.11 o posterior.
- Git y `git-filter-repo` disponibles (`python -m pip install git-filter-repo`).
- Clonar con acceso de lectura al repositorio original; no se requiere token de escritura.
- Espacio suficiente para aproximadamente tres clones temporales del monorepo y los árboles filtrados.
- Los repositorios remotos `melendezzz26/newglass-frontend` y `melendezzz26/newglass-backend` **todavía deben crearse vacíos** cuando se apruebe la publicación. No inicializarlos con README, licencia ni .gitignore desde GitHub.

## Ejecutar la extracción segura

Desde el monorepo original en Linux/WSL o Windows con Git y Python 3.11:

```bash
python scripts/repository-split/prepare.py --output ../newglass-split
```

El comando:

1. Rechaza la salida si ya existe; no sobrescribe nada.
2. Clona el `--ref` congelado y verifica el SHA esperado **antes** de filtrar.
3. Genera dos clones separados `frontend/` y `backend/`, filtrados con `git filter-repo --subdirectory-filter`.
4. Compara las rutas originales de `frontend/` y `backend/` con cada árbol filtrado. **Falla si falta o sobra algún archivo**.
5. Copia configuraciones comunes y genera los workflows de CI a partir del CI integrado, conservando los tests aislados.
6. Mantiene los E2E reales con frontend y backend como carpetas hermanas; el CI frontend obtiene una revisión backend de 40 caracteres fijada en `vars.NEWGLASS_BACKEND_E2E_SHA`. Si esa variable falta, el gate falla.
7. Adapta Pages para el subpath `/newglass-frontend/`, y deja su workflow **solo manual** (sin despliegue automático durante la migración).
8. Escribe `frontend-commit-map.txt`, `backend-commit-map.txt` y `split-manifest.json` fuera de ambos repos.
9. Deja las adaptaciones **sin commit ni push** para revisión humana, testeo y commits propios del equipo.

Los directorios locales deben mantenerse como hermanos (`../frontend` y `../backend`) para las pruebas Playwright, aunque los repositorios remotos tengan nombres `newglass-frontend` y `newglass-backend`.

## Validación previa a publicar

```bash
cd ../newglass-split/backend
python -m pip install -r requirements.txt
python -m pytest tests --ignore=tests/unit/optimization/test_comparison_runner.py --ignore=tests/integration/optimization/test_comparison_calculation.py --ignore=tests/integration/optimization/test_comparison_supervision_v2.py --ignore=tests/unit/optimization/test_sequential_runner.py -q -ra
python -m pytest tests/integration/optimization/test_comparison_calculation.py -q -ra
python -m pytest tests/integration/optimization/test_comparison_supervision_v2.py -q -ra
python -m pytest tests/unit/optimization/test_sequential_runner.py -q -ra
python -m pytest tests/unit/optimization/test_comparison_runner.py -q -ra
cd ../frontend
npm ci
npm run test:unit
npm run test:component
npm run lint
npm run build
```

Para E2E: preparar PostgreSQL temporal y Playwright según el README del proyecto, ejecutar `node scripts/run-e2e-phases.js` desde `frontend` con el backend hermano. **No** usar una BD de staging ni desactivar el gate por omisiones de pruebas.

Antes de realizar `npm run build:staging`, definir `VITE_API_URL` por el entorno; está prohibido usar localhost o credenciales en el bundle. El cambio de base de Pages solo debe publicarse cuando se apruebe la nueva URL.

## Publicación y continuidad del historial

Una vez que cada salida esté validada y tenga los cambios de adaptación incluidos en un commit limpio:

```bash
# En frontend, después de revisar git diff y de crear en GitHub el repo vacío:
git add -A
git commit -m "chore(EN-REPO-001): adaptar frontend extraido y CI independiente"
git remote add origin https://github.com/melendezzz26/newglass-frontend.git
git push -u origin main

# En backend, después de revisar el diff y crear el repositorio vacío:
git add -A
git commit -m "chore(EN-REPO-001): adaptar backend extraido y CI independiente"
git remote add origin https://github.com/melendezzz26/newglass-backend.git
git push -u origin main
```

**No** ejecutar comandos `remote add` ni `push` antes de crear los repositorios vacíos, validar resultados y confirmar permisos. `git-filter-repo` elimina el remote anterior de los clones, por lo que estos comandos apuntan exclusivamente a nuevos repos.

Los SHA reescritos no son iguales a los originales; conservar fuera del repositorio los `commit-map.txt` junto con el manifiesto y relacionarlos desde la evidencia EN-REPO-001. No afirmar que issues, PR, tags, secret variables, branch protections o environments han sido migrados: se configuran y verifican aparte.

## Limitaciones y revisión pendiente

- La extracción toma solo el historial de la rama congelada; las ramas de trabajo no integradas, como PR #113, se revisan y trasladan aparte. No se cierran automáticamente.
- El generador usa las rutas/estructuras de CI concretas observadas en `137f2ccd`; si cambian los patrones esperados, debe **fallar** en lugar de generar configuraciones ambiguas.
- El generador crea el contrato API de referencia en el backend y apunta los enlaces históricos a SHA fijos del monorepo. Revisar enlaces restantes y ubicar documentación/evidencia transversal antes de verificar el PBI.
- En la CI frontend, configurar `NEWGLASS_BACKEND_E2E_SHA` con el **SHA reescrito real del backend ya publicado**; nunca usar la rama principal como referencia flotante para E2E.
- La publicación de Pages exige configurar la variable pública `VITE_API_URL` y aprobar el cambio de origen/ruta. Heroku conserva su origen anterior hasta el cutover.
- No hay pruebas ejecutadas de los nuevos repositorios todavía: primero deben generarse y validarse con el procedimiento indicado.

## Referencias

- [Tarea EN-REPO-001 en Notion](https://app.notion.com/p/414e0c471a44812297f7ee150e15781b)
- [SPEC](../../docs/specs/SPEC-EN-REPO-001-separacion-repositorios.md)
- [PLAN](../../docs/specs/PLAN-EN-REPO-001-separacion-repositorios.md)
- [ADR-003](../../docs/adr/ADR-003-repositorios-independientes-frontend-backend.md)
