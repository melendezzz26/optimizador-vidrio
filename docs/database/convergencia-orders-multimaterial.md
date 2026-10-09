# Convergencia de Orders: material y espesor por pieza

Estado: contrato funcional acordado; migración y persistencia multimaterial pendientes.
Fecha: 2026-10-08. Rama de trabajo: `integration/HU-006-convergencia`.

## Decisión y alcance

Un pedido puede contener piezas de distintos tipos de vidrio y espesores.
Esta decisión sustituye la asignación de material a la cabecera documentada en
v1.1, v1.2/TA-013 y el contrato histórico de HU-007 T04. Los documentos y evidencias
históricos se conservan; no acreditan la implementación del contrato nuevo.

No se modifican Supabase, modelos ni migraciones en esta fase. No se agrega
`piezas.orden`: no existe un requisito aprobado de orden persistente.
El commit del compañero `80a4fa4` permanece en la historia, incorporado mediante
el merge `6eff9e0`; todas las adaptaciones son posteriores.

## Modelo objetivo

| Entidad | Campos |
|---|---|
| PEDIDO | `id_pedido`, `fecha_registro`, `estado`, `id_usuario_registro` |
| PIEZA | `id_pieza`, `id_pedido`, `id_tipo_vidrio`, `espesor_mm`, `tipo_forma`, `cantidad`, `dimensiones`, `geometria`, `area_mm2` |

`piezas.id_tipo_vidrio` será INTEGER NOT NULL y `piezas.espesor_mm`
NUMERIC(4,1) NOT NULL. La pareja tendrá una FK compuesta denominada
`fk_piezas_tipo_espesor` hacia la PK de
`tipos_vidrio_espesores(id_tipo_vidrio, espesor_mm)`.
No sustituirla por dos FK independientes. La relación del catálogo con
`tipos_vidrio` ya protege la existencia del tipo.

Formas admitidas: RECTANGULO, CIRCUNFERENCIA y POLIGONO_CONVEXO.
TRIANGULO no es un tipo independiente; tres vértices válidos pueden representar
un polígono convexo. Cantidades enteras positivas, longitudes en mm y área en mm².
Conservar PK, FK al pedido, constraints de forma/cantidad/área y geometría JSONB.
Conservar dimensiones de formas estándar; para polígonos, dimensiones SQL NULL
y geometría con `vertices_mm`. El servidor calcula el área por pieza, no el área
multiplicada por cantidad.

El catálogo vigente es TA-013: parejas persistidas por tipo, no una lista global
de espesores ni IDs fijos. Las altas requieren tipos activos. La FK garantiza
pertenencia al catálogo; la política de actividad corresponde a Application.

## Plan Alembic exacto — NO ejecutado

Precondiciones: respaldo recuperable, inspección del esquema y revisión reales
del destino, dependencias de vistas/FK externas y ventana coordinada sin escritores
con el contrato antiguo. No usar `stamp`, borrar filas, desactivar constraints ni
editar revisiones aplicadas para eludir inconsistencias.

La cadena local termina en `1c8754481a08` (TA-013). Verificar que continúa siendo
el único head antes de crear la nueva revisión. No se consultó el head remoto.
Ejecutar la futura migración en una transacción PostgreSQL con bloqueos coordinados
de pedidos/piezas antes del preflight y la copia, evitando escrituras concurrentes.

1. Crear una nueva revisión descendiente del head actual: `down_revision = 1c8754481a08` si no ha cambiado.
2. Agregar `piezas.id_tipo_vidrio INTEGER`, inicialmente nullable, sin default.
3. Agregar `piezas.espesor_mm NUMERIC(4,1)`, inicialmente nullable, sin default.
4. Copiar ambos valores desde `pedidos` usando la relación `piezas.id_pedido = pedidos.id_pedido`.
5. Validar ausencia de nulos/huérfanos, pertenencia al catálogo, igualdad exacta con la pareja histórica y conservación de filas, IDs, cantidades, dimensiones, geometrías y áreas.
6. Establecer NOT NULL en las dos columnas nuevas.
7. Crear `fk_piezas_tipo_espesor` y comprobar su validez para todas las filas.
8. Retirar `fk_pedidos_tipo_espesor`.
9. Retirar la FK individual de `pedidos.id_tipo_vidrio`, si existe. Inspeccionar su nombre real; en la cadena original es `pedidos_id_tipo_vidrio_fkey`.
10. Eliminar `pedidos.id_tipo_vidrio` sin CASCADE.
11. Eliminar `pedidos.espesor_mm` sin CASCADE.
12. Verificar esquema y ORM objetivo, restricciones y conservación antes de dar por validada la evolución. Un fallo debe revertir datos, DDL y revisión.

SQLAlchemy representará la pareja con `ForeignKeyConstraint` en `Pieza`.
La copia de datos y sus comprobaciones requieren una migración explícita:
autogenerate no deduce el traslado semántico de campos.
La nueva versión de aplicación y la migración deben activarse coordinadamente;
el backend antiguo no es compatible con la retirada de columnas de pedidos.

## Preservación histórica y reversión

- **Pedidos sin piezas:** detectarlos en el preflight y abortar con diagnóstico.
  Su pareja no tiene destino donde copiarse. No borrar el pedido, inventar piezas
  ni retirar ese dato silenciosamente. Su tratamiento requiere decisión posterior
  del equipo antes de aplicar la migración si se encuentran casos reales.
- **Tipos inactivos:** conservar parejas históricas existentes, sin reactivar tipos.
  No ejecutar la validación de alta que exige actividad durante el backfill.
- **Parejas inválidas o nulos:** abortar, sin correcciones automáticas ni defaults.
- **Datos nunca enviados por el cliente antiguo:** no pueden reconstruirse mediante
  esta migración; solo se preserva fielmente lo que está almacenado.
- **Downgrade:** no existe reducción fiel de un pedido multimaterial a una sola
  pareja de cabecera. La futura revisión debe bloquear el downgrade automático;
  documentar recuperación mediante respaldo/procedimiento revisado, sin elegir la
  primera pieza, dividir pedidos ni perder información.

## Validación futura, sin duplicar infraestructura

Reutilizar el PostgreSQL temporal de `backend/tests/integration/postgres_support.py`.
Probar BD vacía, pedidos históricos con múltiples piezas, tipos inactivos,
aborto ante pedido vacío/inconsistencia, rollback, nueva FK y esquema contra ORM.
Actualizar las aserciones que fijan TA-013 como head; preservar los contratos
históricos de R1/R3/R4 y de TA-013 al comprobar revisiones anteriores.
No ejecutar suites que apliquen Alembic durante esta fase sin migraciones.

## Puente temporal de interfaz

La pantalla canónica está en `features/orders/NuevoPedido.jsx`; `pages/` conserva
un reexport de compatibilidad. La UI permite listas mixtas y asigna material,
espesor y cantidad al agregar cada pieza. El usuario autorizó activar esta pantalla
con restricción temporal de guardado.

Mientras HTTP/BD mantengan el contrato antiguo, solo se envía el pedido si el
conjunto de parejas de TODAS las piezas tiene exactamente un elemento. Esa pareja
única se adapta a la cabecera HTTP antigua. Una lista multimaterial/multiespesor
queda bloqueada con explicación visible y sin POST ni pérdida de datos.
Cambiar los datos de la siguiente pieza no cambia las ya agregadas.
No se utiliza `piezas[0]` para imponer material al resto.

Este puente no acredita persistencia multimaterial. Se retirará al implementar
conjuntamente el [contrato HTTP objetivo](../specs/HU-006-registrar-pedido/contrato-orders.md),
Application, repositorio, modelos y migración. El borrador sigue siendo local:
no se promete supervivencia a recarga o navegación. Se mantiene el tratamiento
HU-007 de errores 401/403/422 con feedback y conservación del borrador en la vista;
la reautenticación global sin pérdida sigue pendiente de definición.

## Contrato pre-raster

Orders deberá ofrecer piezas autosuficientes con ID, material, espesor, forma,
cantidad, dimensiones, geometría y área. Optimization podrá agrupar por
`(id_tipo_vidrio, espesor_mm)` y operar en mm mediante un contrato de Application,
sin depender de modelos ORM o schemas HTTP de Orders.

Sprint 1 incluye posteriormente rasterización y su visualización. No se implementa
en esta fase. First Fit, Best Fit, Worst Fit, métricas de colocación y selección
de heurísticas pertenecen a Sprint 2. No registrar un resultado raster como FF/BF/WF.
