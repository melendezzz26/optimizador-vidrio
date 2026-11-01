# Backend de NewGlass

API FastAPI organizada progresivamente como monolito modular.
La versión de Python actualmente validada es **3.11.9**.
Los comandos siguientes se ejecutan desde `backend/`.

## Comparación concurrente de motores

`/api/optimization/comparisons` ejecuta FF/BF/WF sobre una entrada congelada,
con eventos independientes, resultados persistidos y selección humana. La
confirmación aplica exclusivamente el elegido. El contrato anterior `/runs`
mantiene FF V1 y `visual-v2`.

Este nuevo recorrido requiere **Linux con procfs, un proceso web y capacidad
agregada disponible**; rechaza entornos insuficientes sin degradar a secuencial.
Incluye la migración aditiva `s2cmp01a1b2c`. Revisar rutas, límites, idempotencia,
recuperación y compatibilidad en la
[guía comparison-v1](../docs/contracts/optimization/comparison-v1.md) y sus
[pruebas/evidencia](../docs/evidence/sprint-02/OPT-MULTIMOTOR-VISUAL/README.md)
antes de habilitarlo en otro entorno. La implementación no acredita un despliegue.

En Windows, ejecutar el backend en **WSL2**, conservando el frontend Vite en
Windows si se desea. Python nativo de Windows devuelve 503 de forma intencional
porque carece de los controles Linux del supervisor. Ver el
[arranque y diagnóstico local con WSL2](../docs/development/optimization-wsl2.md).
Desde `backend/`, `python -m scripts.check_comparison_environment` verifica la
plataforma y admisión por memoria sin acceder a la base ni revelar credenciales.

## Entorno e instalación

En Windows con PowerShell, utilizando una instalación de Python 3.11.9:

```powershell
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1
python --version
python -m pip install -r requirements.txt
```

En Linux/macOS con Python 3.11.9 instalado:

```bash
python3.11 -m venv venv
source venv/bin/activate
python --version
python -m pip install -r requirements.txt
```

Si PowerShell bloquea el script de activación, usar
`.\venv\Scripts\python.exe` en lugar de `python` en los comandos siguientes.
No es necesario cambiar la política de ejecución del sistema.

## Configuración local

Crear `.env` a partir de [.env.example](.env.example) solo si todavía no existe.

PowerShell:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Linux/macOS:

```bash
[ -f .env ] || cp .env.example .env
```

| Variable | Uso |
|---|---|
| `DATABASE_URL` | URL de SQLAlchemy para PostgreSQL mediante psycopg. |
| `SECRET_KEY` | Clave de firma JWT para el entorno local. |
| `TOKEN_MINUTOS` | Duración de los tokens en minutos; el ejemplo conserva `480`. |

El ejemplo contiene únicamente valores ficticios: no proporciona una base de
datos ni credenciales utilizables. Sustituir la URL por la configuración
autorizada del entorno cuando se necesite persistencia y reemplazar la clave
de ejemplo por una clave local propia. No versionar `.env` ni copiar secretos
a documentación o evidencia.

Para generar una clave local se puede utilizar:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Ejecución

```bash
python -m scripts.dev_server
```

La API queda disponible en `http://127.0.0.1:8000` y su documentación interactiva
en `http://127.0.0.1:8000/docs`. La autenticación valida contra las tablas
`usuarios` y `roles` y exige `SECRET_KEY` en el entorno.

El lanzador usa un proceso web y no recarga por defecto. Para editar código:
`python -m scripts.dev_server --reload`. Excluye `.venv`, pruebas, scripts y
migraciones de las recargas; una recarga legítima de la aplicación igualmente
descarta eventos/máscaras en memoria. Para comparaciones y evidencia usar el
modo estable. El supervisor multimétodo requiere Linux/WSL2; ver la
[guía de WSL2](../docs/development/optimization-wsl2.md).

El pool PostgreSQL usa por defecto `DB_POOL_SIZE=5`, `DB_MAX_OVERFLOW=0` y
`DB_POOL_TIMEOUT=30`. Son límites por proceso; no aumentan la cuota del proveedor.
Mantener una sola instancia contra la base de desarrollo y considerar también
clientes externos. Las variables explícitas del entorno prevalecen. La lectura
de autorización compartida devuelve su conexión antes de abrir la unidad
de trabajo; cada unidad conserva commit/rollback/cierre propios. Una caída de
DNS o del proveedor aún puede impedir guardar: el fallo se informa y no se
reintenta automáticamente.

Esta preparación no crea tablas ni requiere ejecutar seed, `/db-test` o comandos
de migración Alembic. La divergencia de revisiones remotas sigue tratándose en
su bloque de integración; no se resuelve durante la instalación del entorno.

## Configuración inicial de corte para desarrollo/demo

Con la base de destino autorizada en el entorno, desde `backend/`:

```text
python -m alembic upgrade head
python seed.py
python -m scripts.create_first_admin
python seed.py --optimization-demo --responsable USUARIO_EXISTENTE
```

Si ya existe una cuenta activa, omitir la creación del primer administrador y
usar su nombre de usuario en `--responsable`. El comando sin opciones conserva
la carga habitual de roles/permisos; los parámetros demo son optativos. No se
asume un ID de usuario ni se crean cuentas ficticias. En una base compartida,
ejecutar únicamente con autorización y verificar el destino antes de migrar.

Los parámetros provienen de `tests/optimization_e2e_data.py`, usado en los E2E
actualizados para Sprint 2: separación 0 mm, margen 0 mm, resolución 1 mm, paso angular 5° y tamaño
mínimo de retazo 10 × 10 mm. Son una base reproducible de desarrollo/demo,
no una recomendación de tolerancias de fabricación para todos los trabajos.

El seed es idempotente y serializa intentos concurrentes: mantiene exactamente
una versión vigente completa y no reemplaza sus valores. Si no hay vigente,
inserta una versión nueva sin alterar filas históricas ni optimizaciones. Si hay
varias vigentes o una vigente incompleta/inválida, falla e indica que debe
revisarla el administrador. Si necesita crear y el responsable no existe o está
inactivo, también falla sin crear datos. Puede ejecutarse dos veces para
comprobar la idempotencia; no requiere INSERT manual ni nuevas migraciones.

Las nuevas ejecuciones operativas de Sprint 2 requieren paso angular de 5°.
Si la configuración vigente conserva 90° u otro paso, se devuelve CONFIG_CONFLICT
antes de bloquear pedidos. El seed conserva esa versión: el responsable de
configuración debe publicar una nueva versión vigente de 5°, sin alterar las
versiones históricas. Este cambio de código no migra ninguna base de datos.
El motor permite pasos explícitos para experimentos y reproducción histórica.

Para una base que ya conserva una versión vigente de 90° u otro paso válido,
el PR #88 aporta una publicación administrativa versionada. Ejecutar solo tras
autorizar el destino y con una cuenta activa existente, desde `backend/`:

```bash
python -m scripts.publish_configuration --responsable USUARIO_ACTIVO
```

El comando solicita escribir `PUBLICAR`. Copia los demás parámetros a una
versión nueva de 5°, deja la anterior como histórica y conserva las referencias
de las optimizaciones existentes. No requiere una migración Alembic. Repetirlo
cuando la vigente ya es de 5° no crea otra versión; el seed demo conserva la
vigente y por eso no sustituye esta operación.

## Primer Administrador

La gestión de usuarios exige una sesión de Administrador, así que la primera
cuenta se crea una sola vez con un comando, desde `backend/`:

```bash
python -m scripts.create_first_admin
```

Muestra la base de destino y pide confirmación, nombres, apellidos, DNI y
contraseña por teclado. Aplica las mismas reglas que la pantalla y se niega si
ya existe un Administrador activo. Requiere que los roles estén cargados
(`seed.py`). En la base compartida solo se ejecuta con autorización del equipo.

## Pruebas

Con el entorno activado y desde `backend/`:

```bash
python -m pytest tests --ignore=tests/unit/optimization/test_comparison_runner.py -q -ra
python -m pytest tests/unit/optimization/test_comparison_runner.py -q -ra
```

La suite usa una base SQLite en memoria fijada en `tests/conftest.py` y una
prueba de estructura de database aislada que bloquea conexiones. No necesita
PostgreSQL ni Supabase en ejecución, ni un `.env` real para esas pruebas.

## Organización

- `app/modules/<modulo>/`: `domain`, `application`, `infrastructure` y `presentation`.
- `app/shared/`: capacidades transversales; `database` ya fue trasladado.
- `app/core/` y `app/models.py`: código activo conservado temporalmente hasta
  su migración por módulo.
- `scripts/`: comandos de operación que se ejecutan a mano.
- `tests/`: pruebas organizadas según su propósito, con las existentes preservadas.

Consultar [CONTRIBUTING.md](../CONTRIBUTING.md) y las
[convenciones de pruebas](../docs/testing/README.md).
