# T04 — Ensayo Alembic y procedimiento de bootstrap

12/10/2026. Base de tarea: `8f721f8`. SPEC Reviewed releída antes de T04.
No se conectó a Supabase, no se creó administrador real, no se añadieron
migraciones ni cambios al modelo lógico. Preparación local para T07.

## Auditoría y procedimiento

[Runbook Staging](../../../../infrastructure/staging.md): variables externas,
TLS, selección direct/Session Pooler pendiente de red/plan, presupuesto de
conexiones, timeouts, prechecks/datos/backup, cadena existente, recuperación,
roles y primer administrador. Prohíbe stamp para ocultar divergencias.

`seed.py` carga tres roles por nombre, secuencialmente repetible, sin usuarios.
`scripts.create_first_admin` usa casos de uso/validaciones/bcrypt, getpass y
confirmación del destino; requiere rol y rechaza administrador activo existente.
Mostrar destino en consola no autoriza incluirlo en evidencia pública. No se
modificaron estos mecanismos ni se ejecutaron sobre una base Staging.

## Validación ejecutada

Desde `backend/` con `venv/Scripts/python.exe`, fuera del sandbox Windows:

```text
python -m alembic heads
fa014e1a2b3c (head)
```

Suite aplicable:

```sh
python -m pytest tests/integration/test_staging_bootstrap.py tests/integration/test_create_first_admin.py tests/integration/test_r1_migration.py tests/integration/test_r2_migration.py tests/integration/test_r3_migration.py tests/integration/test_r4_migration.py tests/integration/test_orders_multimaterial_migration.py tests/integration/test_clients_migration.py tests/integration/test_hu014_movement_migration.py tests/unit/shared/test_alembic_config.py -q
```

Resultado: **183 passed, 1 warning in 134.77s (0:02:14)**; código 0, sin skips.
Warning: deprecación Starlette/httpx en TestClient, sin cambios de dependencias.
`git diff --check`: código 0; comprobación staged requerida antes del commit.

La prueba nueva comprueba diez revisiones lineales con único head, current vacío
antes de migrar una BD temporal, upgrade head y current `fa014e1a2b3c (head)`.
Compara seis tipos, 28 espesores y cero usuarios iniciales; repite seed/upgrade
y compara exactamente IDs, nombres y descripciones de los tres roles.
Las suites existentes cubren precondiciones, rechazo de datos incompatibles y
creación de administrador sintético (incluida autenticación/permisos), sin
credenciales reales. `%` se comprueba con contexto Alembic simulado.

CA-08: ensayo local y procedimiento preparados; revisión/datos/backup y upgrade
del destino real pendientes. No se afirma conservación de datos remotos ni TLS
real. No hubo deploy, bootstrap Staging o cambios en la configuración remota.
