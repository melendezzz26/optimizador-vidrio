# TA-013: validación reproducible

Fecha: 2026-10-05. Rama: `feature/TA-013-datos-base`. Ejecución con el entorno virtual existente de backend. PostgreSQL temporal local mediante `tests/integration/postgres_support.py`; ninguna conexión a Supabase ni a una base compartida. No se realizó commit, push, merge ni cambio de rama.

## Comandos y resultados

Desde `backend`:

```powershell
.\venv\Scripts\python.exe -B -m pytest tests/unit/inventory tests/api/inventory -q
```

```text
326 passed in 4.72s
```

```powershell
.\venv\Scripts\python.exe -B -m pytest tests/integration/inventory -q --tb=short
```

```text
39 passed in 40.37s
```

```powershell
.\venv\Scripts\python.exe -B -m pytest -q
```

```text
561 passed in 101.79s (0:01:41)
```

Las tres ejecuciones finalizaron con código 0. Las primeras dos están incluidas en la suite completa; no deben sumarse como pruebas distintas. Los archivos nuevos de catálogo aportan 35 casos unitarios y 20 casos de integración (55 casos nuevos).

Desde la raíz se revisaron `git diff --check`, `git status --short` y `git diff --stat`. El diff no presenta errores de whitespace. Los archivos nuevos siguen sin seguimiento: no se ejecutó `git add`.

## Cobertura y ajustes de regresión

- Catálogo exacto de seis tipos y 28 pares, reejecución de la carga, nombre UNIQUE, PK compuesta, CHECK positivo y FK en los tres consumidores.
- Combinaciones Incoloro 12/2, Espejo 2/8 y Catedral 3.5/4: aceptación/rechazo en Application y SQL directo.
- Creaciones y PATCH solo tipo, solo espesor y ambos, para planchas y retazos. Rechazos sin escritura y lectura de las combinaciones persistidas.
- GET y creación/PATCH por HTTP con API real y PostgreSQL temporal; números JSON en `espesores_mm`.
- Comparación del esquema migrado con el ORM, HEAD lineal, preservación de datos existentes y abortos de upgrade/downgrade para cada tabla.
- Los contratos históricos de R4 se verifican con una copia congelada de su modelo en `tests/contracts/r4_models.py`, siguiendo la estrategia ya existente para R3. No se altera la migración R4 ni se obliga al modelo actual v1.2 a representar el esquema anterior.
- Los tests de repositorio existentes registran explícitamente sus pares sintéticos. Estos datos de prueba no son listas de producción ni se agregan automáticamente a tipos nuevos.

## Archivos del cambio

Producción (todos bajo `backend/`):

- `app/models.py`
- `alembic/versions/1c8754481a08_ta_013_catalogo_tipos_y_espesores.py` (archivo manual preexistente, aún sin seguimiento)
- `app/modules/inventory/application/catalog.py` (nuevo)
- `app/modules/inventory/application/dto.py`
- `app/modules/inventory/application/ports.py`
- `app/modules/inventory/application/service.py`
- `app/modules/inventory/infrastructure/repository.py`
- `app/modules/inventory/presentation/schemas.py`

Pruebas (bajo `backend/`):

- `tests/catalog_contract.py` (nuevo)
- `tests/contracts/r4_models.py` (nuevo contrato histórico)
- `tests/unit/inventory/test_catalog.py` (nuevo)
- `tests/integration/inventory/test_catalog.py` (nuevo)
- `tests/unit/inventory/test_service.py`
- `tests/api/inventory/test_inventory_api.py`
- `tests/integration/inventory/test_repository.py`
- `tests/integration/test_r4_migration.py`
- `tests/model_contracts.py`
- `tests/unit/test_database_structure.py`
- `tests/unit/test_r4_models.py`

Documentación:

- `docs/specs/SPEC-TA-013-datos-base.md`
- `docs/database/evolucion-v1-2-ta013.md` (nuevo)
- `docs/evidence/sprint-01/TA-013/catalogo-tipos-espesores.md` (nuevo)
- `docs/evidence/sprint-01/TA-013/migracion-catalogo.md` (nuevo)
- `docs/evidence/sprint-01/TA-013/api-catalogo.md` (nuevo)
- `docs/evidence/sprint-01/TA-013/pruebas-ta013.md` (este archivo)

El router se revisó y no requiere cambios. No se modificaron frontend, autenticación, migraciones históricas ni DOCX. La ejecución futura sobre una base compartida requiere revisar sus datos: estas pruebas demuestran el comportamiento de la migración, no la compatibilidad de una base que no se inspeccionó.
