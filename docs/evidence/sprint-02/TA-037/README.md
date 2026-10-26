# Evidencia TA-037 T01 — Mediciones de carga

Medición exploratoria del motor de dominio actual, sin base de datos ni HTTP. Se
usó para fijar los valores propuestos en
[SPEC-TA-037](../../../specs/SPEC-TA-037-control-carga-optimizador.md). No es una
prueba de CI.

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

Los tiempos son de una máquina de desarrollo. En un dyno compartido pueden ser
mayores. Los valores de la SPEC dejan margen respecto de estas cifras, pero
conviene repetir la medición en staging durante T04.