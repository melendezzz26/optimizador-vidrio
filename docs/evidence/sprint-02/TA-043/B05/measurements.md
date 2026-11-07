# B05 - Medicion integrada del caso pequeno

Derivado de `six-real.json`; WSL2, entrada congelada y seis motores productivos a 5 grados.
Startup incluye spawn/handshake y acknowledgements del padre. Calculo externo es tiempo de pared
del adaptador/metricas/callbacks/IPC; no es tiempo puro del algoritmo. Cola se mide aparte.

| Motor | Cola ms | Startup ms | Calculo externo ms | Cierre ms | RSS muestreado MiB | Virtual MiB | Eventos | Bytes observacion |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| FF | 46.11 | 730.47 | 53.19 | 0.52 | 23.32 | 38.36 | 26 | 15407 |
| BF | 868.00 | 756.24 | 51.41 | 0.56 | 23.29 | 38.36 | 26 | 15323 |
| WF | 1710.43 | 738.22 | 56.91 | 0.40 | 22.93 | 38.36 | 26 | 15323 |
| HF | 2544.16 | 762.25 | 75.11 | 0.42 | 23.44 | 38.36 | 26 | 15511 |
| M5 | 3421.99 | 784.98 | 67.70 | 0.72 | 23.09 | 38.36 | 26 | 15323 |
| M6-BS | 4326.59 | 739.73 | 15.29 | 5.48 | 22.99 | 38.34 | 5 | 1336 |

Total runner (incluye persistencia independiente y limpieza): 5.140 s / 180 s.
RSS agregado muestreado incluida reserva: 130.89 MiB; supervisor: 91.71 MiB.
Muestreo: 186 muestras, mayor intervalo 41.65 ms; maximo un worker.
Retencion final: visual 96232 bytes, eventos 80343 bytes; runner retiene cero.

Seis completos, sin consumo de inventario, sin cambio de cotas. Medicion muestreada, no garantia de picos ni capacidad general/Heroku.
El maxrss nativo se conserva como dato crudo; no sustituye RSS/espacio virtual medidos por procfs.
Las fases puras con/sin observacion siguen siendo el diagnostico B04, no se reinventan aqui.
