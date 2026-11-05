# TA-044 - Evidencia de capacidad y concurrencia

Autor: Luis Anthony Ibanez Herrera. Revisor esperado: Andro Joseph Quispe Cesias. Review formal: pendiente.

## Entorno y configuracion

- Windows build 26200; Python 3.11.15; AMD64 Family 23 Model 96; 6 CPU logicas visibles.
- Ejecucion en entorno de medicion, no requisito de produccion. Hubo descarga de PostgreSQL en paralelo; los tiempos son observaciones de esta corrida.
- Resolucion 1 mm, paso angular 5 grados, margen 1 mm, separacion 1 mm; limite M6 30 segundos.
- Dos grupos de vidrio: tipo 1/6 mm y tipo 2/8 mm. Rectangulos, circulos y poligonos convexos; stock mixto.
- El generador no usa aleatoriedad. `tracemalloc` mide asignaciones Python trazadas, no RAM total ni fugas.

## T02 - Capacidad

Comando: `python experiments/optimization/benchmark_capacity.py`. COMPLETE: cobertura total; PARTIAL: cobertura parcial; TIMEOUT: limite de tiempo; ERROR: excepcion. TIMEOUT puede conservar resultado parcial.

| Piezas | Metodo | Colocadas | Estado | Motivo | Tiempo ms | Planchas | Retazos | Aprovechamiento % | Merma mm2 | Recuperable mm2 |
|---:|---|---:|---|---|---:|---:|---:|---:|---:|---:|
| 10 | FF | 10/10 | COMPLETE | - | 305.34 | 2 | 3 | 15.621 | 514.86 | 388.0 |
| 10 | BF | 10/10 | COMPLETE | - | 293.95 | 2 | 3 | 15.621 | 514.86 | 388.0 |
| 10 | WF | 10/10 | COMPLETE | - | 294.22 | 6 | 3 | 6.493 | 1060.86 | 1346.0 |
| 10 | M4 | 10/10 | COMPLETE | - | 356.87 | 2 | 3 | 15.621 | 514.86 | 388.0 |
| 10 | M5 | 10/10 | COMPLETE | - | 325.8 | 4 | 3 | 9.173 | 760.86 | 894.0 |
| 10 | M6 | 10/10 | COMPLETE | - | 7075.71 | 2 | 3 | 15.621 | 507.86 | 395.0 |
| 25 | FF | 25/25 | COMPLETE | - | 458.64 | 4 | 3 | 23.545 | 922.01 | 471.0 |
| 25 | BF | 25/25 | COMPLETE | - | 596.86 | 4 | 3 | 23.545 | 922.01 | 471.0 |
| 25 | WF | 25/25 | COMPLETE | - | 504.44 | 16 | 3 | 6.655 | 2601.01 | 3416.0 |
| 25 | M4 | 25/25 | COMPLETE | - | 477.58 | 4 | 3 | 23.545 | 922.01 | 471.0 |
| 25 | M5 | 25/25 | COMPLETE | - | 541.27 | 12 | 3 | 8.882 | 1773.01 | 2628.0 |
| 25 | M6 | 18/25 | TIMEOUT | TIME_LIMIT | 30002.78 | 3 | 3 | 21.723 | 714.72 | 461.0 |
| 50 | FF | 50/50 | COMPLETE | - | 964.5 | 6 | 3 | 33.635 | 1378.23 | 330.0 |
| 50 | BF | 50/50 | COMPLETE | - | 1328.26 | 6 | 3 | 33.635 | 1378.23 | 330.0 |
| 50 | WF | 50/50 | COMPLETE | - | 1047.56 | 29 | 3 | 7.527 | 4436.23 | 6200.0 |
| 50 | M4 | 50/50 | COMPLETE | - | 1082.4 | 6 | 3 | 33.635 | 1378.23 | 330.0 |
| 50 | M5 | 50/50 | COMPLETE | - | 1217.2 | 26 | 3 | 8.391 | 3694.23 | 5758.0 |
| 50 | M6 | 13/50 | TIMEOUT | TIME_LIMIT | 30002.27 | 2 | 2 | 28.312 | 465.0 | 325.0 |
| 75 | FF | 75/75 | COMPLETE | - | 1494.87 | 9 | 3 | 34.569 | 1960.88 | 498.0 |
| 75 | BF | 75/75 | COMPLETE | - | 2230.74 | 9 | 3 | 34.569 | 1960.88 | 498.0 |
| 75 | WF | 75/75 | COMPLETE | - | 1608.33 | 41 | 3 | 8.056 | 6194.88 | 8632.0 |
| 75 | M4 | 75/75 | COMPLETE | - | 1524.07 | 9 | 3 | 34.569 | 1960.88 | 498.0 |
| 75 | M5 | 75/75 | COMPLETE | - | 1986.35 | 41 | 3 | 8.056 | 5728.88 | 9098.0 |
| 75 | M6 | 9/75 | TIMEOUT | TIME_LIMIT | 30002.34 | 1 | 2 | 32.239 | 325.0 | 129.0 |
| 100 | FF | 100/100 | COMPLETE | - | 2197.59 | 11 | 3 | 38.371 | 2467.46 | 312.0 |
| 100 | BF | 100/100 | COMPLETE | - | 3519.31 | 11 | 3 | 38.371 | 2467.46 | 312.0 |
| 100 | WF | 100/100 | COMPLETE | - | 2265.99 | 54 | 3 | 8.17 | 8061.46 | 11390.0 |
| 100 | M4 | 100/100 | COMPLETE | - | 2219.76 | 11 | 3 | 38.371 | 2467.46 | 312.0 |
| 100 | M5 | 100/100 | COMPLETE | - | 2848.47 | 53 | 3 | 8.34 | 7275.46 | 11744.0 |
| 100 | M6 | 7/100 | TIMEOUT | TIME_LIMIT | 30001.09 | 1 | 2 | 25.075 | 310.0 | 192.0 |
| 150 | FF | 150/150 | COMPLETE | - | 4192.11 | 16 | 3 | 40.262 | 3476.69 | 374.0 |
| 150 | BF | 150/150 | COMPLETE | - | 7067.4 | 16 | 3 | 40.262 | 3476.69 | 374.0 |
| 150 | WF | 150/150 | COMPLETE | - | 4022.2 | 79 | 3 | 8.409 | 11646.69 | 16620.0 |
| 150 | M4 | 150/150 | COMPLETE | - | 4115.57 | 16 | 3 | 40.262 | 3476.69 | 374.0 |
| 150 | M5 | 150/150 | COMPLETE | - | 5148.04 | 79 | 3 | 8.409 | 10738.69 | 17528.0 |
| 150 | M6 | 6/150 | TIMEOUT | TIME_LIMIT | 30001.1 | 1 | 2 | 21.493 | 320.0 | 206.0 |
| 200 | FF | 200/200 | COMPLETE | - | 6775.22 | 22 | 3 | 39.773 | 4642.92 | 598.0 |
| 200 | BF | 200/200 | COMPLETE | - | 12220.54 | 22 | 3 | 39.773 | 4642.92 | 598.0 |
| 200 | WF | 200/200 | COMPLETE | - | 6392.74 | 104 | 3 | 8.537 | 15230.92 | 21850.0 |
| 200 | M4 | 200/200 | COMPLETE | - | 7156.24 | 22 | 3 | 39.773 | 4642.92 | 598.0 |
| 200 | M5 | 200/200 | COMPLETE | - | 8724.78 | 104 | 3 | 8.537 | 14048.92 | 23032.0 |
| 200 | M6 | 5/200 | TIMEOUT | TIME_LIMIT | 30001.21 | 1 | 2 | 17.91 | 288.0 | 262.0 |

Las 42 ejecuciones comprenden 36 COMPLETE y 6 TIMEOUT. FF, BF, WF, M4 y M5 colocaron todas las piezas hasta 200. M6 completo CAP-10; alcanzo TIME_LIMIT desde CAP-25 en esta corrida. No implica una capacidad universal ni causalidad.

Por metodo, comparando CAP-10 con CAP-200 en esta ejecucion: FF paso de 305 a 6775 ms; BF de 294 a 12221 ms; WF de 294 a 6393 ms; M4 de 357 a 7156 ms; M5 de 326 a 8725 ms. Los cinco conservaron cobertura completa. M6 completo CAP-10 en 7076 ms y alcanzo TIME_LIMIT en las seis escalas restantes. Estas razones de crecimiento no prueban una causa y pueden variar con la carga del equipo.

## Determinismo observado

Cinco repeticiones CAP-10; SHA-256 compara colocaciones, no memoria ni ausencia de fugas.

| Metodo | Repeticiones | Huellas iguales |
|---|---:|---|
| FF | 5 | Si |
| BF | 5 | Si |
| WF | 5 | Si |
| M4 | 5 | Si |
| M5 | 5 | Si |
| M6 | 5 | Si |

## Paralelismo del motor

Comando: `python experiments/optimization/probe_concurrency_capacity.py`. La sonda de 2, 4 y 8 procesos compara huellas y tiempos de FF/M5 para CAP-25/50. No ejecuta el servicio y no demuestra ausencia de fugas.

## Concurrencia del servicio

Las pruebas usan PostgreSQL temporal en loopback, con datos sinteticos; no usan Supabase. Una fixture de solicitudes sucesivas compartia indebidamente el calculador; los casos simultaneos usan una fabrica por solicitud, como la dependencia de produccion. No se modifico codigo productivo.

| Solicitudes | Admitidas | Rechazadas | Completas | Canceladas | Fallidas | Inventario |
|---:|---:|---:|---:|---:|---:|---|
| 1 | 1 | 0 | 1 | 0 | 0 | Sin confirmacion |
| 2 | 2 | 0 | 2 | 0 | 0 | Sin cambios |
| 3 | 2 | 1 | 2 | 0 | 0 | Sin cambios |
| 3, con fallo inducido | 2 | 1 | 1 | 0 | 1 | Sin cambios |
| 1, desconexion | 1 | 0 | 0 | 1 | 0 | Sin cambios |

La desconexion finaliza como FALLIDA y no confirmable; cancelada identifica la causa, no un estado nuevo. El inventario compara filas completas de planchas, retazos y movimientos. En dos solicitudes sincronizadas y la tercera rechazada, los tiempos HTTP observados fueron 0.172/0.171 s; con fallo inducido 0.086/0.093 s. Incluyen las barreras de prueba y no son un benchmark de latencia. La politica observada admite dos ejecuciones por proceso, una por usuario; la tercera recibe 503 OPTIMIZER_BUSY. Dos se mantuvieron estables en este entorno y caso, sin extrapolar a produccion ni a varios procesos web.

| Criterio | Evidencia |
|---|---|
| C01 dos solicitudes, identificadores y eventos | `test_two_real_requests_isolate_failure_and_reject_third` |
| C02 admision | la misma prueba y `test_completed_run_frees_its_slot` |
| C03 rechazo sin huerfanos | la misma prueba y `test_third_concurrent_run_gets_503_without_side_effects_and_is_admitted_later` |
| C04 rechazo sin modificar inventario | snapshot de la misma prueba, con plancha y retazo |
| C05 desconexion/cancelacion | `test_disconnect_preserves_full_inventory_and_releases_worker` y pruebas de desconexion |
| C06 inventario tras cancelacion | snapshot completo en esa prueba |
| C07 persistencia y vinculos | consultas de ejecuciones y vinculos; suites de persistencia/calculo del comparador |
| C08 fallo aislado | variante `fail_first=True` de la prueba concurrente |

La prueba de servicio ejecuta FF mediante la ruta de corridas; las pruebas del comparador verifican su persistencia y runner por separado. No se afirma haber ejecutado comparaciones simultaneas entre si.

| Suite | Passed | Failed | Skipped | Setup errors |
|---|---:|---:|---:|---:|
| Datasets, benchmark y seis metodos (Windows) | 184 | 0 | 0 | 0 |
| API concurrencia PostgreSQL (Windows) | 17 | 0 | 0 | 0 |
| Comparador persistencia y calculo (WSL) | 27 | 0 | 0 | 0 |
| Runner comparador (WSL) | 14 | 0 | 0 | 0 |

Las suites son independientes; los reintentos no se suman como casos adicionales. La suite del comparador requiere Linux; su ejecucion en Windows dio 16 fallos por la comprobacion de plataforma. Una ejecucion conjunta en WSL no se recolecto por falta de openpyxl en ese entorno; las suites indicadas arriba se ejecutaron separadamente.

## Comandos de pruebas

```text
python -m pytest backend/tests/unit/optimization/test_capacity_scenarios.py backend/tests/unit/optimization/test_capacity_benchmark.py -q
python -m pytest backend/tests/api/optimization/test_run_concurrency.py backend/tests/api/optimization/test_ta044_service_concurrency.py -q
python -m pytest backend/tests/integration/optimization/test_comparison_persistence.py backend/tests/integration/optimization/test_comparison_calculation.py backend/tests/unit/optimization/test_comparison_runner.py -q
```

Las pruebas PostgreSQL requieren `NEWGLASS_TEST_PG_BIN` apuntando a binarios locales y `NEWGLASS_REQUIRE_POSTGRES=1`; la fixture crea y detiene su propio cluster. El runner del comparador requiere Linux con procfs y limites de recursos.
