# Evolución del modelo a v1.2: TA-013

Esta nota describe los cambios introducidos por `1c8754481a08` sobre la línea base v1.1/R4 (`b4d5e6f7a8c9`). No sustituye ni altera el documento histórico v1.1 o su DOCX. Las verificaciones se realizaron exclusivamente en PostgreSQL temporal local.

## Secciones que deben evolucionar

| Sección | Cambio para v1.2 |
|---|---|
| Decisión de espesores | Sustituir el conjunto global 3, 4, 5.5, 6, 8 por las combinaciones por tipo del SP-005: seis tipos y 28 pares. |
| TIPO_VIDRIO | Mantener columnas, PK y nombre UNIQUE. Registrar los seis nombres sin alterar IDs, descripciones ni estados preexistentes. No asumir IDs fijos. |
| TIPO_VIDRIO_ESPESOR | Nueva tabla `tipos_vidrio_espesores`: `id_tipo_vidrio INTEGER`, `espesor_mm NUMERIC(4,1)`, ambos NOT NULL; PK compuesta, FK al tipo y CHECK espesor > 0. |
| PLANCHA | Conservar columnas, FK individual al tipo e índices existentes; reemplazar `ck_planchas_espesor` por `fk_planchas_tipo_espesor`. |
| RETAZO | Reemplazar `ck_retazos_espesor` por `fk_retazos_tipo_espesor`. Geometría, área calculada, procedencia y demás restricciones permanecen vigentes. |
| PEDIDO | Reemplazar `ck_pedidos_espesor` por `fk_pedidos_tipo_espesor`; no introducir flujos funcionales ni cambiar estados. |
| Relaciones y cardinalidades | TIPO_VIDRIO 1:N TIPO_VIDRIO_ESPESOR (un tipo puede carecer de pares); cada pareja admite N planchas, N retazos y N pedidos. Cada material/pedido referencia exactamente una pareja. |
| Reglas de integridad | La existencia del par reemplaza el CHECK global. Nombre UNIQUE y PK compuesta evitan duplicados. Las FK individuales al tipo se conservan. |

## Catálogo aprobado

| Tipo | Espesores en mm |
|---|---|
| Incoloro | 3, 4, 5.5, 6, 8, 10, 12 |
| Bronce | 4, 5.5, 6, 8, 10 |
| Gris | 4, 5.5, 6, 8, 10 |
| Catedral | 3, 3.5, 5 |
| Reflejante | 4, 5.5, 6, 8 |
| Espejo | 2, 3, 4, 6 |

La aplicación consulta los pares persistidos mediante `GlassCatalog` y `validate_tipo_espesor`; no mantiene otra lista de producción. Las creaciones y los cambios de pareja exigen un tipo activo. Las actualizaciones de otros atributos con la pareja intacta siguen permitidas aunque el tipo esté inactivo. PostgreSQL garantiza la pertenencia del par, mientras que la política de actividad corresponde a Application.

## Transición y reversión

El upgrade crea y carga el catálogo, comprueba los datos existentes y luego sustituye las restricciones. Si un registro no tiene pareja admitida, aborta e informa ejemplos; no corrige ni elimina registros. Esto también afecta a materiales de tipos personalizados o nombres distintos de los seis aprobados.

El downgrade solo procede si todos los espesores de planchas, retazos y pedidos pertenecen al antiguo conjunto v1.1. Restaura los CHECK y elimina la relación de compatibilidad, pero conserva los tipos y los registros de negocio. Si se personaliza el catálogo posteriormente, esa configuración debe preservarse antes de eliminar la tabla: un nuevo upgrade solo carga los pares SP-005.

Los abortos transaccionales y la concordancia entre ORM y migración se comprobaron en PostgreSQL local. Antes de aplicar en una base compartida corresponde revisar las combinaciones reales y planificar la ejecución de las operaciones DDL; esta tarea no inspeccionó ni modificó dicha base.
