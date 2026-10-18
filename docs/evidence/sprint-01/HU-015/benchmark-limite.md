# HU-015-T1 — Benchmark y presupuesto raster

## Ejecución real

Base: `e98c646`, rama `feature/HU-015-interfaz-rasterizacion`, cambios T1 sin commit. Última ejecución: `2026-10-14T04:19:04.121348+00:00` (13/10/2026 23:19:04 en Lima). Los resultados anteriores de exploración fueron reemplazados por esta medición con el schema final que preserva números persistidos.

Desde la raíz del repositorio:

```powershell
& .\backend\venv\Scripts\python.exe experiments/raster/scripts/hu015_resource_benchmark.py
```

Resultado: código 0, **50 combinaciones**, cinco muestras por combinación más calentamiento y una pasada separada con tracemalloc. Sin conexiones a BD ni lecturas de .env. Resoluciones 20, 10, 5, 2 y 1 mm/celda. Casos: rectángulo pequeño 100×50, referencia 800×600, comercial 2440×1830, círculo radio 500, hexágono convexo existente, tira ancha/alta y polígonos convexos de 64/128/256 vértices. El runner tiene timeout de 60 s por combinación y guardas exploratorias de 5 millones de celdas/5000 por eje; no son límites del producto. No hubo combinaciones omitidas en esta ejecución.

Entorno: Python 3.11.9, Windows 10.0.26200, Intel64 Family 6 Model 170 Stepping 4, 22 CPU lógicas; Pydantic 2.13.5, FastAPI 0.141.1 y SQLAlchemy 2.1.1. RAM física no medida; la consulta del entorno restringido no estaba disponible. El pico reportado corresponde a asignaciones Python con tracemalloc, **no RSS** ni capacidad total del servidor.

Fuentes reproducibles:

- [Runner](../../../../experiments/raster/scripts/hu015_resource_benchmark.py) y [casos](../../../../experiments/raster/cases/hu015-resources.json).
- [Resultados completos seleccionados](benchmark-resultados.json): muestras, medianas, máximos, geometría/bbox, filas/columnas, celdas totales/ocupadas, bytes, memoria, versiones y hashes de script/schema/serializador.
- Salida reconstruible original: `experiments/raster/results/hu015/benchmark.json` (ignorada por Git). La copia seleccionada es evidencia técnica versionable; no se escribe nada en NewGlass-Notion.

Se mide por separado validación canónica de Orders, rasterización, extracción de row_runs/construcción del DTO y codificación Pydantic JSON UTF-8. La API utiliza exactamente `raster_response(...).model_dump_json()`. El tamaño incluye geometría y metadatos. La memoria se mide en otra pasada para no distorsionar tiempos. Cantidad 1 y 5 comparten la misma máscara en el runner; sus payloads tienen igual longitud por ser cantidades de un dígito, sin filas/spans adicionales.

## Resumen de datos observados

Medianas en ms; serialización = mediana DTO + mediana JSON, no una medición de latencia HTTP. Pico en bytes de asignaciones Python.

| Caso | mm/celda | Filas × columnas | Celdas totales | Ocupadas | Validación ms | Raster ms | Serialización ms | JSON bytes | Pico Python bytes |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| Comercial | 20 | 92 × 122 | 11 224 | 11 224 | 0.007 | 0.216 | 0.687 | 2 831 | 79 824 |
| Comercial | 10 | 183 × 244 | 44 652 | 44 652 | 0.013 | 0.419 | 2.635 | 5 463 | 176 436 |
| Comercial | 5 | 366 × 488 | 178 608 | 178 608 | 0.017 | 0.792 | 9.974 | 10 770 | 394 596 |
| Comercial | 2 | 915 × 1220 | 1 116 300 | 1 116 300 | 0.029 | 2.004 | 72.298 | 27 608 | 1 108 472 |
| Comercial | 1 | 1830 × 2440 | 4 465 200 | 4 465 200 | 0.035 | 4.033 | 348.294 | 55 889 | 2 540 572 |
| Círculo | 1 | 1000 × 1000 | 1 000 000 | 787 320 | 0.031 | 0.837 | 54.106 | 30 413 | 1 233 348 |
| Hexágono | 1 | 866 × 1000 | 866 000 | 650 864 | 0.072 | 2.500 | 47.690 | 26 673 | 1 011 276 |
| Polígono 128 vértices | 1 | 1000 × 1000 | 1 000 000 | 787 016 | 7.949 | 30.478 | 57.636 | 35 245 | 1 253 036 |
| Polígono 256 vértices | 1 | 1000 × 1000 | 1 000 000 | 787 240 | 31.136 | 58.322 | 54.029 | 40 151 | 1 270 444 |
| Tira alta 1×2440 | 1 | 2440 × 1 | 2 440 | 2 440 | 0.020 | 5.131 | 4.438 | 67 470 | 2 481 972 |

## Decisión aplicada después de medir

Constantes centralizadas en [resource_policy.py](../../../../backend/app/modules/optimization/application/resource_policy.py):

| Constante | Valor | Justificación |
|---|---:|---|
| MAX_RASTER_CELLS | **1 000 000** | Mantiene círculo/polígono representativos de un millón en el dominio medido, con ~55–96 ms de validación+raster+serialización mediana. Excluye la rejilla comercial de 4.465 millones, cuya serialización crece hasta ~348 ms. Corte conservador para reservar margen entre solicitudes concurrentes; no es una garantía de SLA ni una prueba de carga del servidor desplegado. |
| MAX_RASTER_AXIS | **2440** | Extremo medido en tiras. Las celdas solas no acotan overhead por fila ni bytes: una tira de solo 2440 celdas alcanza ~67 kB y ~2.48 MB de asignaciones. Evita extrapolar a filas/columnas sin medición. |
| MAX_RASTER_VERTICES | **128** | La validación de convexidad tiene costo cuadrático: pasar de 128 a 256 sube de ~7.95 a ~31.14 ms, además de aumentar rasterización. Se conserva el rango medido de 128 y se rechaza antes de esa validación costosa. |
| MAX_RASTER_PAYLOAD_BYTES | **262 144** (256 KiB) | Presupuesto explícito con margen sobre el mayor payload medido (~67 kB). Una cota previa de filas/geometría limita el DTO, sin construir primero un JSON excesivo. |

Estos valores son **POLÍTICAS TÉCNICAS DE PROTECCIÓN** de Application: no son límites funcionales del negocio, dimensiones máximas de piezas NewGlass ni restricciones de Orders. La selección inicial se informa por un equipo local y formas concretas; no representa verdades universales ni demuestra tiempos de red, throughput Supabase, RSS o rendimiento del futuro Canvas. Los valores podrán ajustarse después de revisión técnica y de la evidencia correspondiente, sin cambiar la semántica base de rasterización.

La auditoría confirmó que 2440 celdas/eje puede rechazar geometría válida de baja cantidad de celdas (rectángulo 2441×1 a resolución 1), y que 128 vértices puede rechazar un polígono convexo válido de Orders. La estimación de 256 KiB es conservadora y parcialmente redundante con los otros límites: un polígono de 128 vértices y bbox 10×2000 produjo 61242 bytes reales, pero su cota previa de 275968 lo rechaza. El detalle y los contraejemplos se conservan en [t1-backend.md](t1-backend.md). No se cambiaron constantes ni fórmula durante la preparación del commit.

Durante esa preparación se restauró únicamente el PLAN Approved a e98c646; estas decisiones posteriores permanecen como evidencia técnica, sin atribuir nueva aprobación humana del PLAN.

El preflight comprueba resolución finita >0, forma/medidas/vértices finitos, bbox normalizada a 6 decimales y conteo `max(1, ceil(extensión / resolución - 1e-9))`, igual al tamaño actual del dominio. Rechaza overflow, celdas de bbox superiores al máximo, ejes/vértices fuera de presupuesto y una cota de JSON **antes de rasterize_geometry**. No multiplica por cantidad. La cota utiliza 96 bytes/fila, 640 bytes por par de coordenadas originales y 2048 de cabecera; preserva enteros de coordenadas en vez de convertirlos a float. El número de tramos por fila está acotado por las geometrías convexas validadas por Orders.

Start valida todas las piezas con baseline 5.0 antes de confirmar su transacción. Rasterize comprueba su resolución efectiva y deja estado intacto incluso si rechaza la solicitud. Las pruebas cubren umbral de un millón y siguiente fila, eje 2440 y 2441, vértices excesivos, payload, números extremos y ausencia de llamada al rasterizador cuando se excede el presupuesto.
