# TA-003: capa Application de Inventory

## Objetivo y contexto

Implementar mediante TDD altas y listados de tipos de vidrio, y altas, listados
y edición de planchas y retazos, con puertos de repositorio independientes de
HTTP y persistencia concreta.

- SPEC: [API de inventario](../../../specs/SPEC-TA-003-api-inventario.md).
- Rama: `feature/TA-003-api-inventario`.
- Base consultada: `40c8145d2b5d79ba989b1641c353b962f58a5dcf`.
- Inicio con árbol limpio, sobre las 359 pruebas existentes.
- Entorno: Python 3.11.9 de `backend/venv`; comandos desde `backend/`.
- La implementación inicial se entregó sin preparar el índice ni hacer commit.
  Al iniciar la corrección del contrato cerrado, los archivos de Application
  ya estaban staged; se conserva ese índice sin alterarlo. TA-003 sigue Draft.

## Archivos

- `backend/app/modules/inventory/application/dto.py`: comandos y salidas.
- `backend/app/modules/inventory/application/ports.py`: puerto transaccional.
- `backend/app/modules/inventory/application/service.py`: ocho casos de uso.
- `backend/app/modules/inventory/domain/exceptions.py`: tres excepciones nuevas.
- `backend/tests/unit/inventory/test_service.py`: fake, reloj fijo y pruebas.
- `docs/specs/SPEC-TA-003-api-inventario.md`: decisiones de los contratos.
- Este documento.

No se modifican modelos, autenticación, main.py ni migraciones.
La corrección posterior del contrato cerrado modifica dominio geométrico y sus pruebas.
No se implementan adaptadores SQLAlchemy, FastAPI, Pydantic ni frontend.

## TDD: paso rojo

Se creó primero `test_service.py`, con FakeInventoryRepository en memoria.
Antes de crear DTOs, puerto y servicio se ejecutó:

```text
.\venv\Scripts\python.exe -B -m pytest -q tests/unit/inventory/test_service.py
ModuleNotFoundError: No module named 'app.modules.inventory.application.dto'
1 error in 0.24s
```

El Python local se ejecutó fuera del sandbox, que en esta sesión impide iniciar
el intérprete de Microsoft Store. No se instaló ni cambió el entorno.

## Validación específica

Con la implementación y la revisión final del contrato transaccional:

```text
.\venv\Scripts\python.exe -B -m pytest -q tests/unit/inventory/test_service.py
110 passed in 0.31s
```

Se cubren altas, listados con estados preservados, dimensiones, catálogo de
espesores, rechazo de bool y no finitos, cantidades de alta/edición, referencias,
duplicados, excepciones sin escrituras, campos protegidos, geometría y área,
PATCH vacío, `False`, `0`, fechas y omisión. También se comprueban los datos
recibidos por el fake, rollback ante errores de escritura y commit simulado,
y la importación de Application sin SQLAlchemy/FastAPI/Pydantic/app.models.

## Decisiones de DTO y validación

Las ocho dataclasses usan `frozen=True`, `slots=True` y argumentos por nombre:

| Entidad | Comando de alta | Comando PATCH | Salida |
|---|---|---|---|
| Tipo | `CreateTipoVidrio` | No disponible | `TipoVidrioData` |
| Plancha | `CreatePlancha` | `UpdatePlancha` | `PlanchaData` |
| Retazo | `CreateRetazo` | `UpdateRetazo` | `RetazoData` |

Las salidas reflejan todos los campos escalares de cada entidad v1.1.
Tipo de vidrio no incluye una fecha inexistente en el modelo. Los comandos
no admiten IDs propios, fechas, área ni ejecución de origen. Estado de alta
es siempre True; la aplicación asigna origen None a retazos manuales.

`None` significa omisión en PATCH: Presentation deberá rechazar NULL explícito.
Se preservan False y 0. Las medidas/espesores aceptan Decimal e int, normalizados
a Decimal; no se acepta float ni texto, ni se imponen aquí las escalas físicas
de planchas. Cantidades e IDs requieren int no booleano. Nombre/código se
recortan en los extremos y la unicidad distingue mayúsculas.

Se invoca el dominio geométrico existente para calcular el área; no se duplica
su algoritmo ni se confía en un área del llamador. Se copia la geometría de
entrada. El contrato geométrico es cerrado: cualquier campo adicional,
incluido `area_mm2`, se rechaza con `InvalidGeometryError` antes de escribir.
En PATCH sin geometría se conserva el área almacenada. Las excepciones
InvalidGeometryError se propagan sin traducirlas a errores HTTP.

El reloj inyectable tiene por defecto `datetime.now(timezone.utc)`; normaliza
relojes aware a UTC y rechaza fechas naive. Edición conserva fecha e identidad.
Los listados no filtran estado. Un tipo debe existir y estar activo en altas
y cambios de referencia; no se bloquea la edición por un tipo que no cambió.

## Puerto y transacciones

`InventoryRepository` es un Protocol con operaciones get/create/list por
entidad, comprobaciones de nombre/código y save para planchas y retazos.
La búsqueda de código admite `exclude_id` para excluir el propio retazo.
Las altas reciben campos ya validados por nombre; devuelven DTOs con ID asignado.

`transaction()` devuelve un context manager: cada caso de uso delimita una
unidad; el adaptador confirma al salir con éxito y revierte ante errores del
cuerpo o de la confirmación. Los métodos individuales no hacen commit.
No se añade un UnitOfWork separado. Las lecturas también cierran su transacción.
El adaptador debe devolver snapshots desconectados, incluida la geometría.

Las comprobaciones previas no resuelven carreras por sí solas: el adaptador
deberá garantizar unicidad y referencias y traducir conflictos concurrentes a
excepciones puras. Esto queda documentado en el puerto; aquí solo se usa un fake.

Excepciones reutilizables añadidas al dominio, sin jerarquía propia ni HTTP:
`InventoryValidationError` (ValueError), `InventoryNotFoundError` (LookupError)
y `InventoryConflictError` (Exception). Se preserva InvalidGeometryError.

## Suite completa y revisión de la implementación inicial

```text
.\venv\Scripts\python.exe -B -m pytest -q
469 passed in 76.04s (0:01:16)
```

Se conservan las 359 pruebas existentes y se incorporan 110 de Application.
Las pruebas nuevas no usan base de datos. La suite existente usa su PostgreSQL
temporal local para integración; no se conecta a Supabase.

Desde la raíz, `git diff --check` terminó sin salida y con código 0.
Se verificó también el whitespace de archivos nuevos con
`git diff --no-index --check -- NUL <archivo>` (sin incidencias).
`git diff --stat` incluye únicamente los archivos ya versionados; los cinco
archivos nuevos permanecen untracked. El índice está vacío: no se hizo `git add`
ni commit. Solo cambian las excepciones de dominio, los tres archivos de
Application, sus pruebas, la sección de contratos de la SPEC y esta evidencia.

## Corrección del contrato cerrado de geometria (2026-10-05)

Se eliminó del caso de alta válida el `area_mm2` arbitrario dentro de geometria.
Se mantiene la prueba de que CreateRetazo no admite ese campo, que el área
oficial procede de calculate_area_mm2 y que modificar referencias externas
no altera la geometría del resultado ni la enviada al repositorio.

Se añadieron dos casos parametrizados (`extra` y `area_mm2`) que verifican
`InvalidGeometryError` y ninguna escritura tanto en alta como en edición.
No se modificó el servicio: su llamada al dominio aplica la nueva invariante.

Paso rojo conjunto antes de corregir el dominio:

```text
.\venv\Scripts\python.exe -B -m pytest -q tests/unit/inventory/test_geometry.py tests/unit/inventory/test_service.py --tb=short
8 failed, 273 passed in 0.53s
```

Detalle y regla final: [evidencia del dominio](geometria-dominio.md).

Validación final, desde `backend/`, con el mismo intérprete y `-B -m pytest -q`:

- `tests/unit/inventory/test_geometry.py`: **169 passed in 0.14s**.
- `tests/unit/inventory/test_service.py`: **112 passed in 0.32s**.
- Suite completa: **477 passed in 79.32s (0:01:19)**.

Desde la raíz: `git diff --check` sin salida y con código 0; también se
ejecutaron `git status --short` y `git diff --stat`. Se preservó el índice
staged recibido y se dejaron estas correcciones sin añadir al índice.
No se hizo commit ni se incorporó infraestructura.
