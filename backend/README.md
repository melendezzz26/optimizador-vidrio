# Backend de NewGlass

API FastAPI organizada progresivamente como monolito modular.
La versión de Python actualmente validada es **3.11.9**.
Los comandos siguientes se ejecutan desde `backend/`.

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
python -m uvicorn main:app --reload
```

La API queda disponible en `http://127.0.0.1:8000` y su documentación interactiva
en `http://127.0.0.1:8000/docs`. El arranque actual lee `DATABASE_URL`, aunque la
autenticación todavía usa usuarios temporales en memoria.

Esta preparación no crea tablas ni requiere ejecutar seed, `/db-test` o comandos
de migración Alembic. La divergencia de revisiones remotas sigue tratándose en
su bloque de integración; no se resuelve durante la instalación del entorno.

## Pruebas

Con el entorno activado y desde `backend/`:

```bash
python -m pytest -q
```

La suite actual utiliza autenticación en memoria y una prueba de estructura de
database aislada que bloquea conexiones. No necesita PostgreSQL ni Supabase en
ejecución, ni un `.env` real para esas pruebas.

## Organización

- `app/modules/<modulo>/`: `domain`, `application`, `infrastructure` y `presentation`.
- `app/shared/`: capacidades transversales; `database` ya fue trasladado.
- `app/core/`, `app/routers/`, `app/schemas/`, `app/services/` y `app/models.py`:
  código activo conservado temporalmente hasta su migración por módulo.
- `tests/`: pruebas organizadas según su propósito, con las existentes preservadas.

Consultar [CONTRIBUTING.md](../CONTRIBUTING.md) y las
[convenciones de pruebas](../docs/testing/README.md).
