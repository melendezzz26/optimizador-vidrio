# Implementación de Infrastructure (InventoryRepository) - TA-003

## Objetivo
El objetivo de esta iteración fue completar la capa de Infrastructure del dominio de Inventario (`TA-003`), proporcionando una implementación concreta en SQLAlchemy para el puerto `InventoryRepository`. Se garantizó la separación de capas evitando la dependencia directa del ORM o de las transacciones en la capa de Application.

## Uso de PostgreSQL Temporal y Alembic Head
Se utilizó exclusivamente el clúster PostgreSQL temporal provisto por el entorno de pruebas de integración (`tests/integration/postgres_support.py`). La infraestructura base aplicó las migraciones hasta el head `b4d5e6f7a8c9` (R4), comprobando compatibilidad plena sin utilizar SQLite ni el entorno de base de datos remoto de Supabase.

## TDD Rojo y Pruebas Finales
Al iniciar el trabajo, se ejecutaron las pruebas contra un repositorio inexistente provocando un fallo claro (`ModuleNotFoundError: No module named 'app.modules.inventory.infrastructure.repository'`). Tras implementar el repositorio y el sistema de codificación de tipos de datos, la ejecución final de la suite completa arroja 495 pruebas exitosas (`495 passed`), partiendo de la baseline previa de 477, incrementando las 18 pruebas integrales propias del repositorio.

## Control de Transacciones y Rollback
El diseño del repositorio exige de manera estricta que todas las operaciones de consulta y escritura se efectúen bajo un contexto transaccional manejado por el método `transaction()`. Esto asegura:
* Ausencia de auto-commit por operación (se realiza un commit al finalizar con éxito el bloque `with`).
* Rechazo de transacciones anidadas.
* Bloqueo del uso de los métodos de repositorio fuera del bloque de transacción.
* Rollback automático en caso de falla interna del bloque o de error explícito de integridad (ej: en el momento del flush o del commit final).

## Traducción de Constraints UNIQUE
Se aplicó un mapeo defensivo para los constraints PostgreSQL conocidos. Concretamente:
* `tipos_vidrio_nombre_key`
* `retazos_codigo_key`

Fueron interceptados del `IntegrityError` nativo expuesto a través de `orig.diag.constraint_name` y traducidos en excepciones controladas de tipo `InventoryConflictError`, logrando ocultar el detalle estructural del motor de base de datos de la capa de aplicación. El resto de fallos de integridad propaga la excepción nativa causando el resguardo por rollback automático sin convertirse incorrectamente en Conflict o Validation.

## Ausencia de Supabase
En todo momento se trabajó con inyección estricta de Session desde la factoría en el backend. No se usó `DATABASE_URL` externo ni `load_dotenv`, impidiendo la filtración de credenciales y evitando la conexión al entorno Supabase remoto.

## Archivos Implementados
* `backend/app/modules/inventory/infrastructure/repository.py`: Adaptador ORM con mapeo profundo a DTO. Realiza una conversión defensiva del diccionario `geometria` a tipos nativos (`int`, `float`) para integrarse sin impedancias en `JSONB`, garantizando que la base de datos almacene estructuras semánticas limpias sin envoltorios artificiales. El valor exacto del área preserva su precisión autoritativa de manera relacional a través del campo dedicado `area_mm2` de tipo `NUMERIC(18,2)`. Se manejan contextos transaccionales de forma estricta.
* `backend/tests/integration/inventory/test_repository.py`: Batería de comprobaciones integradas creada en iteraciones previas que valida comportamientos específicos del ORM PostgreSQL.
* `backend/tests/integration/inventory/__init__.py`: Paquete habilitado para tests automáticos.
* `docs/evidence/sprint-01/TA-003/repositorio-postgresql.md`: Presente evidencia.
