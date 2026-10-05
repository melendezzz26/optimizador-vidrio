# TA-013: revisión de la migración

Revisión manual conservada: `1c8754481a08`, padre `b4d5e6f7a8c9`. No se modificaron migraciones históricas ni se utilizó una migración autogenerada como reemplazo.

## Corrección encontrada

La carga original usaba `ON CONFLICT (nombre) DO UPDATE`, con reactivación del tipo y sustitución de una descripción NULL. Se cambió a `DO NOTHING` para preservar ID, descripción y estado de los tipos existentes. Se extrajo la misma carga a `_seed_catalog(bind)` para ejecutar y verificar dos veces su lógica real. La PK compuesta y el conflicto ignorado evitan repetir pares.

## Compatibilidad comprobada

Las columnas origen y destino usan INTEGER y NUMERIC(4,1). Los nombres reales retirados son `ck_planchas_espesor`, `ck_retazos_espesor` y `ck_pedidos_espesor`. Las nuevas FK se denominan `fk_planchas_tipo_espesor`, `fk_retazos_tipo_espesor` y `fk_pedidos_tipo_espesor`. Las FK individuales al tipo se mantienen.

En PostgreSQL temporal se creó la cadena hasta HEAD y se comprobó que `compare_metadata` entre la base y el ORM devuelve `[]`. Se verificaron la PK, las FK, los CHECK y el único HEAD. Las tres tablas rechazan por FK las combinaciones no admitidas, aun usando SQL directo.

## Seguridad verificada

- Upgrade sobre un Incoloro existente inactivo, con descripción NULL y una plancha compatible: conserva ID, estado, descripción y material.
- Upgrade con Espejo + 8 en cada una de las tres tablas: aborta con mensaje explícito, conserva la revisión R4 y los datos, y revierte la creación/carga del catálogo.
- Downgrade con Incoloro + 12 en cada tabla: aborta antes de retirar las restricciones y conserva HEAD y datos.
- Downgrade con Espejo + 4: restaura los CHECK globales, conserva los seis tipos y el registro de negocio. Un upgrade posterior vuelve a cargar los 28 pares.
- Repetir `_seed_catalog` y ejecutar de nuevo el upgrade a HEAD no duplica tipos ni pares.

La prueba de idempotencia no implica que pueda ejecutarse el cuerpo DDL de `upgrade()` dos veces sin Alembic: Alembic controla la revisión aplicada.

## Aplicación posterior

La migración supera las comprobaciones locales, pero no se ha auditado la base compartida. Los tipos personalizados con material y las combinaciones antiguas incompatibles impedirán el upgrade; deben resolverse mediante una decisión explícita antes del despliegue. La coincidencia de nombres conserva la semántica UNIQUE actual, sin normalizar mayúsculas o variantes.

Las operaciones DDL pueden bloquear escrituras mientras se validan las FK. Planificar su ejecución junto con el código nuevo, que requiere la tabla del catálogo. El downgrade elimina la configuración de pares; una eventual personalización futura requeriría preservarla antes. No se ejecutaron cambios sobre Supabase ni sobre una base compartida.

Resultados y comandos: [pruebas-ta013.md](pruebas-ta013.md). Evolución documental: [v1.2](../../../database/evolucion-v1-2-ta013.md).
