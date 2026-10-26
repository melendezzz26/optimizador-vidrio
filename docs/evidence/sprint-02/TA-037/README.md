# Evidencia TA-037 T01 — Mediciones de carga

Medición exploratoria del motor de dominio actual, sin base de datos ni HTTP. Se
usó para fijar los valores propuestos en
[SPEC-TA-037](../../../specs/SPEC-TA-037-control-carga-optimizador.md). No es una
prueba de CI.

La primera parte corresponde a la SPEC v1.0, medida a 90°. La sección
«Recalibración a 5° (SPEC v1.1)» contiene las mediciones vigentes.

## Medición a 90° (SPEC v1.0, histórico)

- Fecha: 25/10/2026
- Código: `integration/sprint-01` en `d1dcd92`
- Máquina: 2 vCPU Intel Xeon a 2,10 GHz, Python 3.11.17, x86_64
- Script: [`experiments/raster/scripts/ta037_load_benchmark.py`](../../../../experiments/raster/scripts/ta037_load_benchmark.py)
- Comando, desde `backend/`: `python ../experiments/raster/scripts/ta037_load_benchmark.py`
- Configuración: resolución 1 mm, paso de 90° (salvo que se indique otro), margen y separación de 0 mm (salvo que se indique otro), planchas de 2440 × 1830 mm

## Resultados

```text
# Preparación y snapshot (lineal en unidades)
prepare_problem 500 unidades                       6 ms   500 unidades
snapshot JSON 500 unidades                         6 ms   92,212 bytes
prepare_problem 5000 unidades                     52 ms   5000 unidades
snapshot JSON 5000 unidades                       58 ms   924,213 bytes
prepare_problem 20000 unidades                   235 ms   20000 unidades
snapshot JSON 20000 unidades                     256 ms   3,709,214 bytes

# First Fit, 1 mm, paso 90°, piezas 300x200
FF 200 unidades, 5 planchas                      505 ms   colocadas 200/200
FF 500 unidades, 10 planchas                    3338 ms   colocadas 500/500
FF 1000 unidades, 20 planchas                  13409 ms   colocadas 1000/1000
FF 500 unidades 600x400, 40 planchas           14693 ms   colocadas 500/500

# Geometría y paso angular
FF 50 polígonos de 128 vértices, paso 90°        444 ms   colocadas 50/50
FF 50 polígonos de 128 vértices, paso 15°       1256 ms   colocadas 50/50

# Stock voluminoso sin encaje (margen 10 mm)
FF 20 unidades sin encaje x 100 planchas       19087 ms   colocadas 0/20

# Presupuesto interno de layouts (128 MiB)
FF 60 unidades 1300x1000, 60 planchas           1356 ms   colocadas 60/60
FF 150 unidades 1300x1000, 200 planchas         3476 ms   RasterPreparationError: layouts exceed 128 MiB

# Concurrencia en un proceso (GIL)
FF 500 unidades, una ejecución                  3268 ms
  3 ejecuciones simultáneas                    ~10900 ms cada una (10980 ms en total)
```

Mediciones adicionales de la misma sesión, con el mismo script y otros parámetros:

- FF de 2000 unidades de 300 × 200 con 40 planchas: 51 976 ms.
- FF de 20 unidades sin encaje con 1000 planchas (margen 10 mm): 196 281 ms. Se
  ejecuta con `--largos`.

## Lectura

1. **Expandir no es lo caro; calcular sí.** Preparar 20 000 unidades toma 0,24 s,
   pero First Fit crece aproximadamente con el cuadrado de las unidades. Por eso
   L-03 limita las unidades antes de expandir.
2. **El stock voluminoso es el peor caso.** Cuando una pieza no encaja, se
   evalúa cada unidad física de plancha: unos 9,5 ms por par unidad × plancha a
   1 mm. Una sola plancha registrada con `cantidad` 1000 basta para más de 3 minutos
   de CPU. Esto justifica L-07 y L-08.
3. **El presupuesto de 128 MiB falla tarde.** Con unas 49 planchas usadas a 1 mm,
   la ejecución falla después de calcular. Esto justifica L-09.
4. **Las ejecuciones simultáneas no aportan paralelismo.** Por el GIL, 3
   ejecuciones tardan lo mismo que hacerlas en serie y bloquean la CPU del
   proceso web. Esto justifica L-10 y L-11.

## Recalibración a 5° (SPEC v1.1)

El PR #64 fijó el paso angular operativo en 5° (72 orientaciones por pieza). Se
repitió la medición con el código de `integration/sprint-01` en `b7b9caa`.

- Fecha: 26/10/2026
- Comando, desde `backend/`: `python ../experiments/raster/scripts/ta037_load_benchmark.py --paso5`
- Misma máquina, resolución 1 mm, 10 planchas de 2440 × 1830 mm

```text
# First Fit a 5°, 1 mm, 10 planchas
FF 100 rectángulos 300x200                       1239 ms   colocadas 100/100
FF 150 rectángulos 300x200                       3442 ms   colocadas 150/150
FF 200 rectángulos 300x200                       7091 ms   colocadas 200/200
FF 100 polígonos de 128 vértices                10232 ms   colocadas 100/100
FF 150 polígonos de 128 vértices                22427 ms   colocadas 150/150
FF 200 polígonos de 8 vértices                  49980 ms   colocadas 200/200
FF 200 circunferencias r=150                     4844 ms   colocadas 200/200

# Caché raster interna (64 MiB) a 5°: piezas distintas de ~1300x1000
FF 2 piezas distintas                            1209 ms   colocadas 2/2
FF 3 piezas distintas                            1462 ms   RasterPreparationError: raster cache exceeds 64 MiB

# Stock sin encaje a 5° (margen 500 mm)
FF 5 unidades 1500x900 sin encaje x 10 planchas 30914 ms   colocadas 0/5
```

Con la misma fórmula que usa `RasterCache`, la estimación por geometría distinta a 5°
es: 600 × 400 → 6,0 MiB; 1000 × 800 → 15,8 MiB; 1300 × 1000 → 24,4 MiB;
1600 × 1200 → 34,7 MiB; 2000 × 1500 → 52,5 MiB; 2440 × 1830 → 76,2 MiB. Por eso 2
piezas de 1300 × 1000 (~48,8 MiB) caben y 3 (~73 MiB) no.

### Lectura a 5°

1. **El cálculo es mucho más caro.** 200 rectángulos pasan de 0,5 s (a 90°) a 7,1 s.
   Las formas no rectangulares son las más caras: 150 polígonos tardan 22,4 s y 200
   llegan a 50 s, con 8 o con 128 vértices. Esto justifica bajar L-03 a 150.
2. **El stock sin encaje cuesta ~0,62 s por par** (antes 9,5 ms). Un tope de pares
   útil sería demasiado restrictivo, así que L-08 se retira: L-07 (50 unidades) acota
   el tramo entre dos hitos a unos 31 s, y L-12 (120 s) acota el total.
3. **Aparece un fallo tardío nuevo en la caché raster.** Tres formas grandes
   distintas ya la superan. L-13 lo rechaza antes con la misma fórmula del motor; la
   capacidad real queda como GAP-05 para TA-016 / HU-017.

Los tiempos son de una máquina de desarrollo. En un dyno compartido pueden ser
mayores. Los valores de la SPEC dejan margen respecto de estas cifras, pero
conviene repetir la medición en staging durante T04.