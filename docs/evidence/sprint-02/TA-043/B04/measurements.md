# Mediciones B04 — caso pequeño WSL2

Entrada SHA256: `1fbb532c7bd0d92f7651cecf424ccfed2bbdda515d0e807e4822607ffba1baf2`.

Una muestra por modalidad; no es una garantía para otras cargas o plataformas.

## Ensayo temprano — observación OFF

| Motor | Arranque ms | Preparación exclusiva ms | Cuerpo exclusivo ms | Callback ms | Métricas ms | Serialización resultado ms | RSS pico MiB | VM final MiB | Eventos / bytes |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| FF | 831.308 | 0.768 | 0.327 | 0.000 | 0.345 | 0.357 | 22.29 | 38.14 | 0 / 0 |
| BF | 837.061 | 0.460 | 0.489 | 0.000 | 0.379 | 0.367 | 22.00 | 38.14 | 0 / 0 |
| WF | 911.601 | 0.415 | 0.346 | 0.000 | 0.327 | 0.319 | 22.32 | 38.14 | 0 / 0 |
| HF | 861.383 | 0.414 | 0.946 | 0.000 | 0.321 | 0.398 | 22.32 | 38.14 | 0 / 0 |
| M5 | 792.052 | 0.403 | 0.338 | 0.000 | 0.460 | 0.365 | 22.56 | 38.14 | 0 / 0 |
| M6-BS | 756.419 | 0.391 | 19.474 | 0.000 | 0.326 | 0.357 | 22.88 | 38.14 | 0 / 0 |

Total 5143.733 ms; agregado muestreado más reserva 61.15 MiB; máximo de workers 1. Todos completos/COMPLETED.

## Ensayo temprano — observación ON

| Motor | Arranque ms | Preparación exclusiva ms | Cuerpo exclusivo ms | Callback ms | Métricas ms | Serialización resultado ms | RSS pico MiB | VM final MiB | Eventos / bytes |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| FF | 798.597 | 0.493 | 0.379 | 1.344 | 0.351 | 0.280 | 22.37 | 38.14 | 24 / 15158 |
| BF | 844.692 | 0.996 | 0.594 | 1.851 | 0.396 | 0.265 | 21.70 | 38.14 | 24 / 15152 |
| WF | 766.909 | 0.528 | 0.424 | 1.498 | 0.354 | 0.269 | 21.92 | 38.14 | 24 / 15152 |
| HF | 795.632 | 0.767 | 1.280 | 1.360 | 0.362 | 0.305 | 22.09 | 38.14 | 24 / 15250 |
| M5 | 778.595 | 0.616 | 0.508 | 1.513 | 0.354 | 0.277 | 22.12 | 38.14 | 24 / 15152 |
| M6-BS | 749.876 | 0.394 | 21.492 | 0.338 | 0.335 | 0.299 | 22.53 | 38.14 | 5 / 3522 |

Total 4832.952 ms; agregado muestreado más reserva 61.25 MiB; máximo de workers 1. Todos completos/COMPLETED.

Preparación corresponde a prepare_run_geometry; orientaciones lazy pertenecen al cuerpo. El callback incluye serialización de observaciones, no sumarla otra vez. JSON conserva tiempos inclusivos y exclusivos; una muestra ON/OFF no permite inferir costo causal.

## Primitiva final — observación OFF

| Motor | Cola ms | Arranque ms | Ejecución externa ms | Cierre ms | RSS pico worker MiB | VM máxima muestreada MiB | Estado / causa |
|---|---:|---:|---:|---:|---:|---:|---|
| FF | 82.585 | 850.797 | 2.659 | 11.546 | 22.55 | 38.44 | COMPLETO / COMPLETED |
| BF | 949.745 | 779.979 | 2.138 | 7.985 | 22.70 | 38.16 | COMPLETO / COMPLETED |
| WF | 1741.897 | 867.659 | 1.831 | 9.818 | 22.43 | 38.29 | COMPLETO / COMPLETED |
| HF | 2622.806 | 858.510 | 3.192 | 9.322 | 22.54 | 38.16 | COMPLETO / COMPLETED |
| M5 | 3495.611 | 790.332 | 2.270 | 9.539 | 22.62 | 38.44 | COMPLETO / COMPLETED |
| M6-BS | 4299.497 | 786.536 | 22.393 | 8.515 | 23.13 | 38.44 | COMPLETO / COMPLETED |

Total 5117.757 ms; agregado máximo muestreado más reserva 62.30 MiB; intervalo máximo de muestra 25.602 ms; workers máximos 1; muestras 192.

## Primitiva final — observación ON

| Motor | Cola ms | Arranque ms | Ejecución externa ms | Cierre ms | RSS pico worker MiB | VM máxima muestreada MiB | Estado / causa |
|---|---:|---:|---:|---:|---:|---:|---|
| FF | 1.045 | 820.661 | 4.223 | 10.446 | 22.48 | 38.29 | COMPLETO / COMPLETED |
| BF | 838.089 | 825.916 | 3.649 | 8.955 | 22.60 | 38.29 | COMPLETO / COMPLETED |
| WF | 1678.090 | 830.425 | 3.628 | 9.800 | 22.60 | 38.16 | COMPLETO / COMPLETED |
| HF | 2523.413 | 790.272 | 5.544 | 9.585 | 22.60 | 38.29 | COMPLETO / COMPLETED |
| M5 | 3330.356 | 782.731 | 3.891 | 8.698 | 22.60 | 38.44 | COMPLETO / COMPLETED |
| M6-BS | 4127.186 | 828.849 | 23.716 | 9.745 | 22.69 | 38.44 | COMPLETO / COMPLETED |

Total 4990.168 ms; agregado máximo muestreado más reserva 62.80 MiB; intervalo máximo de muestra 25.966 ms; workers máximos 1; muestras 191.

Ejecución externa incluye callbacks, métricas e IPC desde el inicio del adaptador hasta recepción. No incluye cola/arranque/cierre; no equivale al cuerpo exclusivo.
