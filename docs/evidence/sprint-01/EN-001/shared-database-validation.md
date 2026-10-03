# EN-001: evidencia de validación de shared/database

- Rama: `enabler/EN-001-reestructurar-repositorio`.
- Commit del refactor: `c489133036d3ed70ca07fa35491f8ccd7677a0aa`.
- Mensaje: `refactor(EN-001): mover infraestructura de base de datos a shared`.

El hash se obtuvo con Git. Esta evidencia recoge la ejecución de pruebas
realizada al cerrar el refactor; no se repitió la suite para redactar la documentación.

## Archivos del refactor

- `backend/app/database.py` → `backend/app/shared/database/session.py`: traslado con 100 % de similitud según Git.
- `backend/app/shared/database/__init__.py`: exports públicos y salto de línea final.
- `backend/main.py`: import actualizado.
- `backend/seed.py`: import actualizado.
- `backend/app/models.py`: import actualizado, sin alterar definiciones ORM.
- `backend/alembic/env.py`: import actualizado.
- `backend/tests/unit/test_database_structure.py`: tres pruebas nuevas.

## Comandos y resultados

Desde `backend/`, en PowerShell y con el venv existente:

```powershell
& ./venv/Scripts/python.exe -m pytest -q
```

Resultado registrado: **`20 passed`**. Las pruebas nuevas verifican los exports,
la identidad de `Base` y el registro exacto de las 10 tablas actuales.
Usan un proceso aislado, desactivan la carga de `.env` y bloquean las conexiones
de SQLAlchemy con una configuración SQLite en memoria.

Desde la raíz del repositorio:

```powershell
git branch --show-current
git rev-parse HEAD
git show --format=fuller --stat --find-renames HEAD
git grep -n -F 'app.database' -- '*.py'
git diff --check
git status --short
```

- Rama y HEAD: los indicados al inicio de este documento.
- Búsqueda de `app.database` en archivos Python versionados: sin coincidencias;
  código de salida `1`, esperado cuando `git grep` no encuentra resultados.
- `git diff --check`: sin errores de espacios en blanco; código de salida `0`.
- El hash identifica el refactor aunque HEAD avance posteriormente.

## Confirmación de alcance

No hubo cambios de esquema ni operaciones contra la base de datos. No se
crearon migraciones ni se ejecutaron seed, `/db-test`, `upgrade`, `downgrade`,
`stamp` o `revision`. El cambio conserva el comportamiento funcional.

La discrepancia previa entre las revisiones Alembic remota y local sigue
pendiente de la integración de HU-003, como se detalla en la
[nota técnica](../../../database/refactor-shared-database.md).
