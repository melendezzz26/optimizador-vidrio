# OPT-MULTIMOTOR-VISUAL — Coordinador concurrente incorporado

Autor: Fabricio Melendez Quezada.
Revisor asignado: Andro Quispe; revisión pendiente.
Fecha: 31/10/2026.
Commit de implementación: `6493b155d481a09d02337a8e172502d5e05f649e`.
Estado: runner y coordinación/persistencia internos implementados; integración HTTP/UI pendiente.

## Ejecución y coherencia

El coordinador de aplicación adquiere una reclamación transaccional del trabajo.
Una repetición no inicia otro cálculo. Abre tres procesos `spawn`, decodifica en
cada uno el mismo DTO JSON y comprueba su huella antes de liberar el arranque.
Los PID e instante de inicio del proceso quedan asociados a las ejecuciones,
para distinguir identidades incluso si el sistema operativo reutiliza un PID.
No se envían ORM, sesiones, conexiones ni cachés compartidas.

Las conexiones DB se cierran antes de buscar colocaciones. Cada resultado y
sus métricas se guardan transaccionalmente; `result_persisted` se publica después
del commit. Un fallo de motor o al guardar su resultado conserva los éxitos de
los otros. El cierre del agregado sucede después de terminar/join los procesos.
No hay elección automática de resultado.

El consumidor de eventos se desacopla del ciclo del cálculo: si falla, el
coordinador sigue y conserva resultados. La futura capa HTTP debe consumir y
retener hechos independientemente de sus conexiones de observación. Cambiar una
pestaña o pausar una vista no debe cerrar el iterador interno.

La admisión comparte capacidad con FF histórico: una comparación es exclusiva
del proceso web. Mientras esté activa no entra otro trabajo comparativo ni FF;
si hay FF activo, la comparación se rechaza. La liberación es idempotente y
ocurre después del cierre. Si no se puede probar la terminación, se conserva la
admisión y los pedidos; no se finge un cierre seguro.

## Presupuesto inicial aplicado

| Recurso | Límite y aplicación |
|---|---|
| Plataforma | Linux con procfs, RLIMIT_AS y protección de vida del hijo; sin fallback secuencial |
| Memoria por trabajador | 256 MiB de espacio virtual, límite duro RLIMIT_AS; incluye intérprete, cachés, layouts y serialización |
| Supervisor | Umbral RSS de 240 MiB, incluye objetos, buffers y futura retención; exceso provoca aborto supervisado |
| Agregado | Umbral de 1 GiB: RSS de supervisor/trabajadores más reserva auxiliar de 16 MiB; muestreo solicitado cada 25 ms |
| Admisión de memoria | Exige 1 GiB disponible en host/cgroup antes de arrancar; rechazo explícito `RESOURCE_UNAVAILABLE` |
| IPC | Pipe por motor y una cola de un paquete por trabajador; sin colas sin límite ni lectura pickle de mensajes |
| Documentos IPC | 12 MiB por paquete, 4 MiB por hecho visual; entrada 4 MiB y resultado 8 MiB conservan límites del codec |
| Arranque | 30 s para estar listos; fallo de arranque no se presenta como falta de espacio |
| Cálculo por motor | 120 s activos con checkpoints; excluye proyección y entrega IPC, incluye métricas |
| Trabajo global | 180 s de pared hasta aborto supervisado; incluye arranque/esperas/IPC; después se completa la terminación/join acotada |
| Retención de producto prevista | 32 MiB visuales y 8 MiB de eventos; constantes disponibles, aplicación a stores HTTP todavía pendiente |

Los 256 MiB permiten acotar las cachés/layouts existentes (64/128 MiB) y su
entorno; no se eleva ningún límite individual del motor. Un caso válido puede
rechazarse por presupuesto, nunca anunciarse como NO_FIT por ese motivo. Los
umbrales RSS son operativos y muestreados: no garantizan capturar todo pico.
Los 16 MiB auxiliares son una reserva, no una medición del `resource_tracker`.

Los trabajadores instalan `PR_SET_PDEATHSIG` y verifican la identidad esperada
del padre, para no seguir calculando al perderlo. La reconciliación durable al
reiniciar el servidor aún no está conectada a una API ni se declara terminada.

## Hechos visuales

Cada motor entrega máscaras reales por tramos binarios sin pérdida. El receptor
reconstruye las mismas celdas; no rasteriza nuevamente para animar. Se limita el
transporte y se conserva la muestra de orientaciones reales por unidad.

`ordering_ready` publica el orden real después de preparar las máscaras. El
orden se calculó antes en el recorrido existente; no se repite el algoritmo ni
se añade una espera artificial. La proyección FF `visual-v2` ignora el evento
nuevo para conservar su contrato. El evento será consumido por `comparison-v1`.

## Evidencia ejecutada

Desde `backend`, con PostgreSQL temporal local:

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m pytest tests/unit/optimization tests/api/optimization tests/integration/optimization tests/integration/test_staging_bootstrap.py -q -ra -p no:cacheprovider
```

Resultado: **817 passed in 88.11s**, una advertencia existente de Starlette/httpx.
Las pruebas nuevas comprueban entrada simultánea a los tres optimizadores con
barrera instrumentada, equivalencia con ejecución directa en los tres casos
congelados, fallo de un hijo, denegación de memoria, timeout, cierre anticipado,
ausencia de procesos hijos vivos, aislamiento al guardar, observador perdido,
registro de identidades y confirmación del commit antes de notificar guardado.

Se ejecutó además la suite completa y se detectaron referencias obsoletas al
head anterior en dos archivos de pruebas. `9b960ca` las actualiza al nuevo head,
conservando sus verificaciones de esquema e historia. La repetición específica
de inventario y migración de clientes aprobó **81 pruebas en 23.26s**. La
repetición de la suite completa permanece pendiente de registrar aquí.

Sonda del runner, desde la raíz y con árbol limpio en `6493b15`:

```text
PYTHONDONTWRITEBYTECODE=1 backend/.venv/bin/python -B experiments/optimization/probe_runner.py
```

Salida: [t02-runner.json](t02-runner.json). Los siete escenarios coinciden con
los resultados, métricas, remanentes y orden reales de cada motor directo.

| Caso | Máximo RSS muestreado + reserva auxiliar (MiB) | Mayor paquete (bytes) | Mayor cola observada | Hijos detenidos |
|---|---:|---:|---:|---|
| EXP-SMALL-001 | 94.05 | 2894 | 1 | Sí |
| EXP-MEDIUM-001 | 93.87 | 7330 | 1 | Sí |
| EXP-COMPLEX-001 | 98.33 | 18187 | 1 | Sí |
| T00-UNITS-150 | 103.81 | 109962 | 1 | Sí |
| T00-STOCK-50 | 99.20 | 18717 | 1 | Sí |
| T00-VERTICES-128 | 107.02 | 69056 | 1 | Sí |
| T00-GRID-4M | 109.37 | 44519 | 1 | Sí |

Entorno Linux/Python 3.11.9, cgroup 8 GiB/dos núcleos; otra suite estaba en curso.
No se deduce rendimiento relativo ni capacidad de despliegue. El mayor intervalo
de muestreo observado fue 74.67 ms. La sonda no mantiene servidor web, buffers
HTTP ni retención visual completa y no satura tres cachés/layouts a la vez.

## Pendientes de integración

API/fixtures compartidas, elección/confirmación HTTP del seleccionado, recuperación
segura tras reinicio, stores comparativos con presupuestos aplicados, cursores y
reconexión, pestañas, transiciones/rotaciones y detalle de solicitud. T00 conserva
pendiente medir el recorrido HTTP/UI completo; no se cierra la SPEC con esta sonda.
