# T02 — Configuración de Staging y conexión segura

## Identificación y alcance

- Fecha: 12/10/2026 (America/Lima).
- Rama: `feature/TA-DEPLOY-001-staging`.
- HEAD inicial verificado: `1ff7cfd847625b262caf717f4f945fa7d9711fc9`.
- Estado: **IMPLEMENTADA / VALIDACIÓN LOCAL**.
- Cambios de trabajo sin commit. SPEC Reviewed; no se cambia a Implemented.

## Implementación

- Carga única del `.env` opcional, con prioridad del entorno (`override=False`).
- `SECRET_KEY` obligatoria sin default; `DATABASE_URL` obligatoria al cargar
  persistencia/Alembic, sin fallback. Errores de configuración sin valores.
- `TOKEN_MINUTOS` conserva `480`; valida enteros positivos y rango de fechas.
- `CORS_ORIGINS` CSV: trim, entradas vacías ignoradas, sin duplicados. Ausente
  conserva localhost; explícitamente vacía no permite orígenes. Wildcard,
  rutas, credenciales, query, fragmento y puertos inválidos se rechazan.
- CORS conserva métodos/headers y `allow_credentials=False`.
- Engine compartido con `pool_pre_ping=True`. `DB_POOL_SIZE`,
  `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT`, `DB_CONNECT_TIMEOUT` opcionales y
  validados; sin cifras nuevas de Supabase. SQLite no recibe opciones PostgreSQL.
- Parámetros TLS de la URL conservados, sin imponer TLS/certificados en código.
- Alembic escapa `%` solo al escribir en ConfigParser; lectura recupera la URL
  original. `NullPool` conserva el timeout opcional del driver.

No se cambiaron dependencias, revisiones/modelos de BD, frontend, workflows,
archivos T01 ni SPEC. `/db-test` permanece y no se añadieron health endpoints.

## Pruebas incorporadas

`backend/tests/unit/shared/test_config.py` cubre defaults y parsing de CORS,
orígenes inválidos y preflight de la app con orígenes sintéticos, variables
obligatorias, duración JWT, opciones de pool/timeout, compatibilidad SQLite,
preservación de TLS/% y configuración desde entorno sin depender del `.env`.
También prueba la prioridad del entorno frente a un archivo temporal sintético.

`backend/tests/unit/shared/test_alembic_config.py` ejecuta `env.py` con contexto
y engine simulados, tanto en modo online como offline. Usa URL sintética con
contraseña codificada; comprueba recuperación íntegra de URL, contraseña y TLS.
No abre conexiones ni ejecuta migraciones reales.

El conftest desactiva dotenv para las suites, evitando leer el `.env` real del
desarrollador. Las pruebas existentes de clave ausente/blanca, JWT, sesiones e
importación diferida se incluyen en la validación focalizada.

## Ejecuciones de esta sesión

Directorio de trabajo: `backend/`.

```powershell
.\venv\Scripts\python.exe -m pytest tests/unit/shared/test_config.py tests/unit/shared/test_alembic_config.py tests/unit/shared/test_database_session.py tests/unit/shared/test_tokens.py tests/unit/test_database_structure.py tests/api/inventory/test_lazy_db_import.py -q
```

El intento dentro del sandbox terminó con código 1 antes de iniciar Python:
el lanzador del venv no pudo crear el proceso de Python de Windows. No fue un
fallo de pytest ni se ejecutaron pruebas en ese intento.

El mismo comando, ejecutado fuera del sandbox con aprobación de la herramienta:

```text
99 passed, 1 warning in 16.24s
exit code: 0
```

Advertencia: Starlette informa la deprecación del uso de httpx con TestClient
y recomienda httpx2. No se instalaron ni cambiaron dependencias en T02.

Suite completa solicitada:

```powershell
.\venv\Scripts\python.exe -m pytest tests -q
```

Resultado real, ejecutado con el mismo venv fuera del sandbox:

```text
1271 passed, 1 warning in 284.38s (0:04:44)
exit code: 0
```

No hubo fallos ni pruebas omitidas. La advertencia es la misma deprecación
Starlette/httpx observada en la suite focalizada.

La suite utiliza SQLite y el harness PostgreSQL temporal en loopback; nunca
se le proporciona una URL remota. Las migraciones que realiza ese harness
pertenecen exclusivamente a sus bases temporales de prueba.

## Checks de Git

`git diff --check`: código 0, sin errores en la revisión local.
`git diff --cached --name-only`: sin salida; no hay cambios preparados.
La comparación de requirements, frontend, workflows, revisiones Alembic,
SPEC y archivos T01 contra HEAD no mostró cambios (código 0).
No se ejecutaron `git add`, commit ni push.

Estado final de archivos de esta implementación: nueve modificados y tres
nuevos sin seguimiento; ningún archivo preparado en el índice.

```text
 M backend/.env.example
 M backend/alembic/env.py
 M backend/app/shared/config/__init__.py
 M backend/app/shared/database/session.py
 M backend/app/shared/security/tokens.py
 M backend/main.py
 M backend/tests/conftest.py
 M docs/evidence/sprint-01/TA-DEPLOY-001/README.md
 M docs/infrastructure/README.md
?? backend/tests/unit/shared/test_alembic_config.py
?? backend/tests/unit/shared/test_config.py
?? docs/evidence/sprint-01/TA-DEPLOY-001/test-results/t02-config-staging.md
```

## Criterios y pendientes

| Criterio | Aporte de T02 y límite |
|---|---|
| CA-02 | Carga local desde entorno sin depender de `.env` probada. Pendiente build limpio y configuración de la plataforma en T07. |
| CA-03 | Variables obligatorias sin default secreto y validaciones locales probadas. Pendiente configuración protegida real y revisión operativa/logs del destino. |
| CA-04 | Parsing y preflight local permitido/denegado probados con orígenes sintéticos. Pendiente origen Pages real y preflight remoto; no se declara cumplido. |

No se validó conexión Supabase, TLS remoto, capacidad/límites de su plan,
origen real de Pages ni configuración/despliegue Heroku. Los valores Staging
de pool/timeout requieren revisión del destino autorizado en T04/T07. No se
ejecutaron migraciones remotas, bootstrap ni despliegues. No se usaron ni
registraron credenciales reales. T03–T07 permanecen fuera del alcance.
