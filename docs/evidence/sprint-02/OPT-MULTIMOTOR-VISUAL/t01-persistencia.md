# OPT-MULTIMOTOR-VISUAL — Persistencia comparativa

Autor: Fabricio Melendez Quezada.
Revisor asignado: Andro Quispe; revisión pendiente.
Fecha: 31/10/2026.
Estado: persistencia y casos de uso internos implementados; API/interfaz pendientes.
Commit: `d4088e6` — `feat(optimization): persistir comparaciones y selección manual versionada`.

## Comportamiento verificado

- Una aceptación transaccional crea una comparación y exactamente tres
  ejecuciones FF/BF/WF; la selección inicial queda vacía.
- La clave de idempotencia se acota al actor. Dos peticiones concurrentes con
  la misma clave recuperan el mismo agregado. Otra selección de pedidos con esa
  clave se rechaza, sin duplicar trabajos.
- Un único `UNION ALL` PostgreSQL captura planchas/retazos compatibles de todos
  los materiales. Se cuentan cantidades antes de expandirlas. Los motores
  recibirán ese mismo snapshot y no deberán releer inventario.
- El snapshot durable conserva piezas, cantidades, dimensiones persistidas,
  geometrías originales, material, configuración y huella de entrada. Es
  independiente de posteriores ediciones de pedidos, configuración o stock.
- Cada ejecución guarda resultado, métricas y propuesta de materiales en una
  transacción; no consume stock. Se rechaza un resultado de otro método o una
  entrada alterada. Una falla de guardado revierte todas sus escrituras.
- El agregado no se cierra cuando llega el tercer resultado: requiere el paso
  interno del supervisor que certifica terminación de sus trabajadores. No hay
  una ruta HTTP que permita afirmar esa terminación.
- Tras ese cierre, una selección manual completa usa versión esperada. Dos
  selecciones concurrentes sobre la misma versión producen un éxito y un
  conflicto. No hay consumo de stock ni ganador automático.
- Un motor fallido conserva los resultados de los demás y marca comparación
  incompleta. Los resultados completos siguen siendo elegibles tras el cierre.
  Sin resultado elegible, los pedidos regresan a PENDIENTE al cerrar con seguridad.
- Liberar un lote no confirmado conserva su historial. Una comparación liberada
  no puede volver a modificar pedidos aceptados por un trabajo posterior.

## Migración y compatibilidad

La revisión aditiva `s2cmp01a1b2c`, posterior a `s1opt02b4c6d`, añade solo
`comparison_key`, `comparison_snapshot` y `comparison_version` a `optimizaciones`,
con unicidad por actor/clave y checks de coherencia. Reutiliza las tablas de
ejecuciones, asociaciones, métricas y materiales existentes; siguen siendo
18 tablas de negocio.

Las corridas FF históricas mantienen metadatos comparativos nulos y versión 1;
no se convierten en comparaciones ficticias. El downgrade se rechaza antes de
DDL si existe historia comparativa. Se verifican upgrade, downgrade vacío,
reupgrade, igualdad con ORM y lectura FF histórica.

Las pruebas de la revisión multipedido anterior ahora usan un contrato
histórico fijo, sin depender de columnas futuras del ORM vigente. Se conserva
su verificación de backfill, constraints y rechazo de pérdida de asociaciones.
Ninguna migración se aplicó a un destino compartido o remoto.

## Pruebas reproducibles

Desde `backend`, con los binarios PostgreSQL locales configurados:

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m pytest tests/integration/optimization tests/integration/test_staging_bootstrap.py tests/unit/optimization/test_comparison_snapshot.py tests/unit/optimization/test_serialization.py -q -ra -p no:cacheprovider
```

Resultado: **159 passed in 38.03s**. Una advertencia de deprecación Starlette/httpx
ya presente en el cliente de pruebas; ningún fallo ni skip. Incluye migraciones,
confirmación FF, stock y aceptación/cálculo históricos.

Después se añadieron cuatro escenarios de carreras/seguridad de selección y
se volvió a ejecutar la selección específica:

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m pytest tests/integration/optimization/test_comparison_persistence.py tests/integration/optimization/test_comparison_migration.py -q -ra -p no:cacheprovider
```

Resultado: **22 passed in 8.42s**, PostgreSQL temporal en loopback, usuario
`r1_test`, sin conexiones a la base real. Las dos selecciones se superponen y
sus cantidades no deben sumarse como si fueran pruebas distintas.

## Pendientes

Esto no ejecuta trabajos desde HTTP. Faltan runner concurrente y su presupuesto
agregado aplicado, API/fixtures compartidas, confirmación del seleccionado,
reconciliación tras reinicio, eventos/máscaras y las cuatro pestañas. T00 sigue
abierto y T01 no se declara verificado como integración completa. Las medidas
siguen en mm; la rama del formulario en cm conserva su alcance separado.
