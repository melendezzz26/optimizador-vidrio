# EN-001: traslado de la infraestructura de base de datos

## Contexto y objetivo

El backend FastAPI evoluciona hacia un monolito modular con Clean Architecture.
Este bloque centraliza la infraestructura compartida de persistencia en
`app/shared/database`, conservando el comportamiento del código existente.
Las rutas siguientes son relativas a `backend/`.

Estructura anterior:

```text
app/database.py
```

Estructura nueva:

```text
app/shared/database/
    __init__.py
    session.py
```

## Responsabilidades e imports

`session.py` conserva la carga de `.env`, la lectura de `DATABASE_URL`, la
creación de `engine`, la fábrica `SessionLocal` y la base declarativa `Base`.
Mantiene `autocommit=False`, `autoflush=False` y `bind=engine`.

`__init__.py` reexporta `Base`, `SessionLocal` y `engine` como interfaz pública
del paquete. Los consumidores importan desde `app.shared.database` sin depender
del archivo interno `session.py`; se reutilizan los mismos objetos.

Se actualizaron únicamente los imports de persistencia en:

- `backend/main.py`.
- `backend/seed.py`.
- `backend/app/models.py`.
- `backend/alembic/env.py`.

## Alcance y comportamiento

- El traslado fue estructural y conserva el comportamiento funcional.
- No se modificó el esquema de base de datos ni las definiciones de los modelos ORM.
- No se creó ninguna migración Alembic.
- No se ejecutaron seed, `upgrade`, `downgrade` ni `stamp`.
- No se realizaron operaciones contra la base de datos ni se invocó `/db-test`.
- Alembic conserva la importación de `app.models` y utiliza la misma `Base.metadata`.

## Pruebas y resultado

Se añadió `backend/tests/unit/test_database_structure.py` con tres pruebas:

- Importación de los exports `Base`, `SessionLocal` y `engine`.
- Identidad del objeto: `app.models.Base is app.shared.database.Base`.
- Registro exacto de las 10 tablas actuales en `Base.metadata` al importar `app.models`:

```text
configuraciones
ejecuciones_optimizacion
metricas_ejecucion
pedidos
piezas
planchas
retazos
roles
tipos_vidrio
usuarios
```

Los imports se prueban en un proceso aislado con una URL SQLite en memoria,
sin cargar `.env` y bloqueando `Engine.connect` y `Engine.raw_connection`.
No se abren conexiones a PostgreSQL ni Supabase.

Resultado final de la suite: **20 pruebas aprobadas (`20 passed`)**.
La [evidencia de validación](../evidence/sprint-01/EN-001/shared-database-validation.md)
identifica el commit y los comandos utilizados.

## Riesgos y pendientes

Según el estado remoto reportado, la base remota registra la revisión Alembic
`c4e8a1f2b3d5`, perteneciente a `origin/feature/HU-003-gestion-usuarios`, mientras
esta rama contiene como head `9b9f04eb67f6`. El origen de la revisión se verificó
en el historial local de Git; no se consultó la base remota durante este bloque.

Esta discrepancia es previa e independiente del refactor y debe resolverse
durante la integración de HU-003.
