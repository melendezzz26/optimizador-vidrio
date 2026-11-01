# OPT-MULTIMOTOR-VISUAL — Confirmación del motor elegido

Autor: Fabricio Melendez Quezada.
Revisor asignado: Andro Quispe; revisión pendiente.
Fecha: 31/10/2026.
Commit: `4ccf74a` — `feat(optimization): confirmar únicamente el motor elegido de forma idempotente`.
Estado: caso de uso interno validado; rutas HTTP e interfaz pendientes.

Este registro corresponde al caso de uso interno de ese commit. Para las rutas,
interfaz y confirmación real posterior, consultar [T04](t04-api-ui.md) y el
[estado consolidado](README.md).

La confirmación exige comparación terminal, ejecución completa guardada,
selección manual coincidente y versión esperada. Revalida geometría, pedidos,
propuestas y disponibilidad física dentro de una transacción. Solo descuenta
los materiales del resultado elegido y crea sus remanentes con el método y la
ejecución de origen correctos. No recibe un layout arbitrario del cliente.

Repetir la misma clave/ejecución/versión original recupera el mismo recibo,
incluidas dos confirmaciones concurrentes. Otra clave tras confirmar se rechaza.
Las carreras de selección o liberación contra confirmación producen una sola
operación ganadora; no mezclan decisiones ni dejan consumo parcial.

El escenario manual probado usa cuatro piezas 2 × 2 mm, dos unidades de una
plancha 4 × 2 mm (#5) y una de 8 × 2 mm (#6). Los motores dan propuestas
distintas; después de elegir y confirmar, los saldos verificados son:

| Motor elegido | Saldo de plancha #5 | Saldo de plancha #6 |
|---|---:|---:|
| FF | 2 | 0 |
| BF | 0 | 1 |
| WF | 1 | 0 |

WF genera además dos remanentes vinculados a su ejecución. Se comprueban los
movimientos, códigos por método, estados CONFIRMADO y repetición sin duplicados.
Una falta de stock conserva la selección y permite liberar el lote sin perder
historia. Una falla al crear un remanente revierte stock, movimientos, pedidos,
recibo y métricas. Los remanentes demasiado pequeños para inventario se excluyen
del detalle recuperable tras confirmar y se refleja su área como merma.

Se conserva el recorrido FF histórico. Solo se generalizaron el nombre del motor
en el movimiento y el prefijo del remanente, que siguen siendo First Fit/FF en
ese recorrido; selección y recibo comparativos usan un adaptador separado.

Desde `backend`, con PostgreSQL temporal local:

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m pytest tests/integration/optimization/test_comparison_confirmation.py tests/integration/optimization/test_comparison_calculation.py tests/integration/optimization/test_comparison_persistence.py tests/integration/optimization/test_confirmation.py tests/integration/optimization/test_confirmation_concurrency.py tests/integration/optimization/test_confirmation_rollback.py -q -ra -p no:cacheprovider
```

Resultado: **74 passed in 14.93s**, sin skips. No se tocó la base real.
La regresión completa anterior al cambio de confirmación aprobó 2429 pruebas;
no se atribuye esa corrida anterior a código añadido después.

Faltan contrato/rutas HTTP de comparación, stores y streaming, recuperación
segura de reinicios, las cuatro pestañas, la presentación visual de giros/fases
y el detalle de solicitud en pantalla. No se declara T03 completa por este caso
de uso interno. El cambio a cm conserva su rama posterior acordada.
