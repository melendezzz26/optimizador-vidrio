# S2-WF-CARGA — Worst Fit, presupuesto de la comparación y carga máxima

| Campo | Valor |
|---|---|
| Origen | Observaciones del profesor en la revisión del 04/11/2026 (Sprint 2) |
| Rama | `fix/S2-wf-presupuesto-carga`, desde `integration-02` (`2a57afe`) |
| Responsable | Fabricio Aguilar |
| Fecha de medición | 06/11/2026 |
| SPEC afectadas | [SPEC-TA-019 v2](../../../specs/SPEC-TA-019-worst-fit.md) · [SPEC-TA-037 v1.4](../../../specs/SPEC-TA-037-control-carga-optimizador.md) · [SPEC-TA-043](../../../specs/SPEC-TA-043-integracion-seis-motores.md) |
| Script | [`backend/scripts/benchmark_load_engines.py`](../../../../backend/scripts/benchmark_load_engines.py) |

## 1. Qué pidió el profesor

1. **Worst Fit** abría una plancha nueva por pieza. Con 46 piezas usaba 12 planchas
   (First Fit, 4); con 100, 28; con 200 fallaba con `RasterPreparationError`.
2. **Plazo global de la comparación.** Con 100 piezas, el plazo de 180 s no
   alcanzaba para que corrieran los seis motores.
3. **Carga máxima.** Medir de forma reproducible hasta qué cantidad de piezas
   responde cada motor, e informar los límites con honestidad.

## 2. Worst Fit: regla antes y después

**Antes (v1).** En cada nivel (primero retazos, después planchas), WF puntuaba
todas las fuentes que podían recibir la pieza, incluidas las vacías, y elegía la
de mayor espacio libre después de colocarla. Una plancha sin usar siempre tiene
más espacio libre que una ya empezada, así que cada pieza abría una plancha nueva.

**Después (v2, RN-02 y RN-05 de SPEC-TA-019).**
- Se mantiene el orden de niveles: **retazos primero**, después planchas.
- Dentro del nivel, WF elige **entre las fuentes ya en uso** la que deja más espacio
  libre después de colocar la pieza. En caso de empate decide el orden de stock, la
  orientación, la fila y la columna.
- Solo si la pieza no cabe en ninguna fuente en uso, **abre una nueva**: la primera
  disponible según ese mismo orden. Las fuentes sin usar no se puntúan.

**Efecto medido** (mismos motores aislados y misma carga sintética):

| Piezas | Planchas WF antes | Planchas WF después | Aprovechamiento WF antes → después | FF (referencia) |
|---:|---:|---:|---|---:|
| 46 | 12 | **4** | 18,3 % → **54,9 %** | 4 |
| 100 | 28 | **8** | — → **59,6 %** | 8 |
| 200 | `RasterPreparationError` | **14** (200/200) | falla → **68,4 %** | 14 |

> Los valores «antes» son la medición previa a la corrección sobre `integration-02`,
> con la misma carga sintética. Los valores «después» salen de la tabla de la §4.

**Costo.** WF ahora compara todas las fuentes en uso para cada pieza, así que
tarda más:
- 100 piezas: de ~17 s a 40,5 s.
- 200 piezas: 118,66 s, cerca del límite de 120 s por motor.

La prueba de regresión `test_worst_fit.py` reproduce el defecto: dos piezas que
caben en una plancha producían `[1, 2]` con la regla anterior y producen `[1, 1]`
con la nueva.

## 3. Cambios de configuración y su justificación

| Parámetro | Antes | Después | Justificación |
|---|---:|---:|---|
| Plazo global de la comparación (`global_seconds`) | 180 s | **900 s** | 6 motores × (30 s de arranque + 120 s de cálculo) = 900 s. Así cada motor puede agotar su propio presupuesto sin que los siguientes reciban `GLOBAL_TIME_LIMIT` antes de arrancar. |
| Máximo de unidades por cálculo (L-03) | 150 | **300** | Permite enviar pedidos más grandes. Si un motor no termina, lo informa con su motivo explícito (`TIME_BUDGET_EXCEEDED`), no como «sin solución». |
| Tope de unidades del evento `ordering_ready` | 150 | **300** | Acompaña a L-03. 300 referencias ocupan ~30 KB, por debajo del máximo de 64 KB por evento. |
| Cálculo por motor | 120 s | 120 s | Sin cambio. |
| Memoria (256 MiB por worker, 1 GiB RSS) | — | — | Sin cambio. |

Con 300 piezas, la suma de los seis tiempos medidos en la §4 es ~720 s, dentro de
los 900 s. Con el plazo anterior de 180 s, después de los 120 s de FF solo
quedaban unos 60 s para BF, y los motores siguientes en la cola habrían recibido
`GLOBAL_TIME_LIMIT` sin arrancar.

## 4. Resultados

**Condiciones de la medición:**
- Windows, Python 3.11.9, **sin `RLIMIT_AS`** (el módulo `resource` no existe en Windows).
- **Una corrida por tamaño.** Son tiempos de reloj, no medianas ni garantías.
- **Motores aislados:** cada uno corre en su propio proceso `spawn`, con
  `EngineExecutionAdapter` y un checkpoint de 120 s como el del worker de
  producción. No usa BD ni el comparador de punta a punta (supervisor, IPC,
  persistencia).
- **Piezas sintéticas grandes**, copiadas de `scripts/benchmark_comparison.py`:
  - rectángulo 600×800, círculo r 260 y pentágono (0,0)(500,0)(620,400)(250,700)(0,400);
  - dos materiales; margen 3 mm, separación 3 mm, resolución 1 mm, paso 5°.
- **Planchas:** 2140×3300, una por pieza del material, entre 4 y 50 (L-07).

| Piezas | Motor | Segundos | Colocadas | Planchas | Aprov. % | Motivo |
|---:|---|---:|---:|---:|---:|---|
| 46 | FF | 4,64 | 46/46 | 4 | 54,928 | COMPLETED |
| 46 | BF | 12,12 | 46/46 | 4 | 54,928 | COMPLETED |
| 46 | WF | 9,53 | 46/46 | 4 | 54,928 | COMPLETED |
| 46 | HF | 4,77 | 46/46 | 4 | 54,928 | COMPLETED |
| 46 | M5 | 93,75 | 46/46 | 16 | 13,732 | COMPLETED |
| 46 | M6-BS | 0,00 | 0/46 | — | — | STATE_MEMORY_LIMIT |
| 100 | FF | 16,61 | 100/100 | 8 | 59,623 | COMPLETED |
| 100 | BF | 54,64 | 100/100 | 8 | 59,623 | COMPLETED |
| 100 | WF | 40,50 | 100/100 | 8 | 59,623 | COMPLETED |
| 100 | HF | 16,47 | 100/100 | 8 | 59,623 | COMPLETED |
| 100 | M5 | 120,12 | — | — | — | TIME_BUDGET_EXCEEDED |
| 100 | M6-BS | 0,00 | 0/100 | — | — | STATE_MEMORY_LIMIT |
| 150 | FF | 47,12 | 150/150 | 10 | 71,465 | COMPLETED |
| 150 | BF | 103,81 | 150/150 | 10 | 71,465 | COMPLETED |
| 150 | WF | 81,41 | 150/150 | 10 | 71,465 | COMPLETED |
| 150 | HF | 47,98 | 150/150 | 10 | 71,465 | COMPLETED |
| 150 | M5 | 120,09 | — | — | — | TIME_BUDGET_EXCEEDED |
| 150 | M6-BS | 0,00 | 0/150 | — | — | STATE_MEMORY_LIMIT |
| 200 | FF | 67,81 | 200/200 | 14 | 68,352 | COMPLETED |
| 200 | BF | 120,00 | — | — | — | TIME_BUDGET_EXCEEDED |
| 200 | WF | 118,66 | 200/200 | 14 | 68,352 | COMPLETED |
| 200 | HF | 69,03 | 200/200 | 14 | 68,352 | COMPLETED |
| 200 | M5 | 120,05 | — | — | — | TIME_BUDGET_EXCEEDED |
| 200 | M6-BS | 0,00 | 0/200 | — | — | STATE_MEMORY_LIMIT |
| 300 | FF | 120,00 | — | — | — | TIME_BUDGET_EXCEEDED |
| 300 | BF | 120,00 | — | — | — | TIME_BUDGET_EXCEEDED |
| 300 | WF | 120,00 | — | — | — | TIME_BUDGET_EXCEEDED |
| 300 | HF | 120,00 | — | — | — | TIME_BUDGET_EXCEEDED |
| 300 | M5 | 120,09 | — | — | — | TIME_BUDGET_EXCEEDED |
| 300 | M6-BS | 0,00 | 0/300 | — | — | STATE_MEMORY_LIMIT |

`—` indica que el motor no entregó un resultado. Cuando el motivo es
`TIME_BUDGET_EXCEEDED`, la consola muestra además el tipo de excepción
(`TimeBudgetExceeded`).

## 5. Rango soportado y límites conocidos

**Rango soportado con piezas grandes** (esta carga y esta máquina):

| Piezas | Motores que completan en 120 s |
|---:|---|
| hasta 150 | FF, BF, WF y HF |
| 200 | FF, WF y HF (BF agota sus 120 s) |
| 300 | ninguno |

Con el plazo global de 900 s, los seis motores corren y cada uno termina con su
propio límite. Con piezas más pequeñas el rango es mayor, pero aquí no se midió.

**Límites conocidos (no se corrigen en esta tarea):**
- **M5** (motor de otro compañero, no se modificó) abre planchas nuevas igual que
  el WF anterior: con 46 piezas usa 16 planchas y logra 13,7 % de aprovechamiento.
  Desde 100 piezas no completa en 120 s. Solo se informa.
- **M6-BS** (motor de otro compañero, no se modificó en esta tarea) termina de
  inmediato por `STATE_MEMORY_LIMIT` en todas las cargas con planchas de
  2140×3300. Más tiempo no lo resuelve. Se corrigió después, en la rama
  `fix/S2-m6-rendimiento`: ver la [§7](#7-m6-beam-search-antes-y-después).
- **L-03 = 300 no garantiza un resultado.** Un cálculo admitido de 300 unidades
  grandes termina con `TIME_BUDGET_EXCEEDED` en todos los motores. La aplicación
  lo informa como fallo explícito, no como «sin solución».
- En Linux con `RLIMIT_AS` de 256 MiB (producción y CI) los tiempos y los fallos
  de memoria pueden ser distintos; esta medición es en Windows y sin ese límite.

## 6. Cómo reproducir

En PowerShell, desde `backend\` y con el venv activo:

```powershell
python -m scripts.benchmark_load_engines 46 100 150 200 300
```

- No necesita `.env`, base de datos ni PostgreSQL de pruebas, y no modifica el inventario.
- En el peor caso, cada motor tarda ~150 s (30 s de arranque + 120 s de cálculo).
  Con los cinco tamaños, en esta medición la ejecución completa tomó unos 40 min;
  el máximo teórico es ~75 min.
- En Linux el mismo comando aplica `RLIMIT_AS` de 256 MiB, igual que el worker de
  producción. La primera línea de la salida indica si está activo.

Pruebas automáticas relacionadas (backend, en Windows):

```powershell
python -m pytest -q --ignore=tests/unit/optimization/test_comparison_runner.py --ignore=tests/unit/optimization/test_sequential_runner.py
```

## 7. M6 Beam Search: antes y después

| Campo | Valor |
|---|---|
| Rama | `fix/S2-m6-rendimiento`, PR hacia `integration-02` |
| Responsable | Fabricio Aguilar (motor de Fabricio Melendez; arreglo asignado por el equipo) |
| Fecha de medición | 07/11/2026 |
| SPEC | [SPEC-TA-053-T01 v1.1–v1.3](../../../specs/SPEC-TA-053-T01-M6-Beam-Search.md) |

Mismas condiciones que la §4: Windows, Python 3.11.9, sin `RLIMIT_AS`, una corrida
por tamaño y la misma carga sintética. Desde esta rama, el motivo de M6 indica
si el resultado lo completó el respaldo First Fit y cuántas unidades decidió
cada uno.

### 7.1 Qué se cambió

| Fase | Cambio | Efecto en el resultado |
|---|---|---|
| F1 | Si un límite detiene la búsqueda, el **respaldo First Fit** completa las unidades restantes desde el mejor nodo. Se registra en el diagnóstico (`fallback_*`) y en «Detalles del método». | M6 siempre entrega un resultado completo, salvo piezas que realmente no caben (`NO_FIT`). |
| F2 | **Layout vacío compartido** por material, `initial_bound` por material distinto, **medición incremental** de la memoria (siempre ≥ `graph_bytes`) y puntaje reutilizado sobre layouts vacíos compartidos. | Desaparece `STATE_MEMORY_LIMIT`; la búsqueda sí arranca. |
| F4b | `metrics.largest_rectangle` (compartida) recorre **tramos de columnas** en lugar de cada columna. Resultado idéntico. | Puntaje más rápido para M6, M5 y las métricas de todos los motores. |

### 7.2 M6 en la carga 6/46/100

| Piezas | Antes | Después de F1+F2 | Después de F4b |
|---:|---|---|---|
| 6 | 0/6 · 30,00 s · `TIME_LIMIT` | 6/6 · 30,38 s · 2 planchas · 14,293 % · respaldo por `TIME_LIMIT`: M6 decidió **0**, respaldo 6 | 6/6 · 30,20 s · 2 planchas · 14,293 % · respaldo por `TIME_LIMIT`: M6 decidió **1**, respaldo 5 |
| 46 | 0/46 · 0,00 s · `STATE_MEMORY_LIMIT` | 46/46 · 34,89 s · 4 planchas · 54,928 % · respaldo por `TIME_LIMIT`: M6 decidió 0, respaldo 46 | 46/46 · 34,70 s · 4 planchas · 54,928 % · respaldo por `TIME_LIMIT`: M6 decidió 0, respaldo 46 |
| 100 | 0/100 · 0,00 s · `STATE_MEMORY_LIMIT` | 100/100 · 46,39 s · 8 planchas · 59,623 % · respaldo por `TIME_LIMIT`: M6 decidió 0, respaldo 100 | 100/100 · 45,83 s · 8 planchas · 59,623 % · respaldo por `TIME_LIMIT`: M6 decidió 0, respaldo 100 |

Segundos de los otros motores después de F4b (mismas colocadas, planchas y
aprovechamiento que en la §7.3):

| Piezas | FF | BF | WF | HF | M5 |
|---:|---:|---:|---:|---:|---|
| 6 | 0,22 | 0,38 | 0,31 | 0,36 | 0,97 |
| 46 | 4,64 | 12,41 | 9,77 | 4,77 | 38,41 |
| 100 | 15,80 | 53,50 | 39,73 | 16,02 | 120,00 · `TIME_BUDGET_EXCEEDED` |

- «Antes» de 6 piezas: el mismo script sobre `integration-02`, sin F1 ni F2, en la
  misma máquina. «Antes» de 46 y 100: la tabla de la §4.
- Con 46 y 100 piezas M6 no decide ninguna unidad: su resultado es el de First Fit
  (mismas planchas y aprovechamiento que FF).

### 7.3 Los otros motores en la misma carga (después de F1+F2)

| Piezas | FF | BF | WF | HF | M5 |
|---:|---|---|---|---|---|
| 6 | 0,39 s · 6/6 · 2 · 14,293 % | 0,58 s · 6/6 · 2 · 14,293 % | 0,48 s · 6/6 · 2 · 14,293 % | 0,50 s · 6/6 · 2 · 14,293 % | 2,66 s · 6/6 · 6 · 4,764 % |
| 46 | 4,83 s · 46/46 · 4 · 54,928 % | 12,80 s · 46/46 · 4 · 54,928 % | 10,06 s · 46/46 · 4 · 54,928 % | 4,92 s · 46/46 · 4 · 54,928 % | 96,89 s · 46/46 · 16 · 13,732 % |
| 100 | 16,59 s · 100/100 · 8 · 59,623 % | 53,38 s · 100/100 · 8 · 59,623 % | 39,47 s · 100/100 · 8 · 59,623 % | 16,34 s · 100/100 · 8 · 59,623 % | 120,00 s · `TIME_BUDGET_EXCEEDED` |

Después de F4b, todos los motores mantienen las mismas colocadas, planchas y
aprovechamiento. **M5 con 46 piezas bajó de 96,9 s a 38,4 s** con el mismo
resultado: también usa `largest_rectangle` para puntuar.

### 7.4 Dónde se va el tiempo de M6 (perfil, 6 piezas, 30 s)

| Momento | Hallazgo |
|---|---|
| Inicio de la tarea | 31 sucesores en 30 s y 0 piezas colocadas. 63 % del tiempo en `graph_bytes` (se recorría todo el grafo de estado en cada sucesor) y 35 % en `largest_rectangle`. |
| Después de F2 (F4a) | 95 % del tiempo en `largest_rectangle`: 28,6 de 30 s, 75 llamadas, **0,38 s por llamada**. La contabilidad de memoria dejó de ser el cuello de botella. |
| Después de F4b | **0,24 s por llamada** (1,6×). M6 evalúa 117 sucesores en 30 s y decide 1 de 6 unidades. |

La mejora de F4b es moderada porque, con piezas rotadas a 5°, los bordes cambian
en casi cada columna y los tramos iguales son cortos.

### 7.5 Límite conocido y mejora propuesta

- **Límite.** Con piezas rotadas a 5° sobre planchas de 2140×3300 a 1 mm, M6 casi
  no avanza su búsqueda en sus 30 s: cada sucesor exige calcular un puntaje de
  ~0,24 s. El resultado lo completa el respaldo First Fit, y el diagnóstico y la UI
  lo indican («Búsqueda continuada con respaldo First Fit…»). Por eso, en estas
  cargas, el resultado de M6 no debe presentarse como una búsqueda propia.
- **Mejora futura (no incluida).** Rediseñar el puntaje de M6, de forma aproximada
  o en dos etapas: primero un filtro barato y el rectángulo exacto solo para los
  mejores. Cambia las decisiones de M6, así que exige rehacer la evidencia SP-006
  con Fabricio Melendez.

### 7.6 Cómo reproducir

En PowerShell, desde `backend\` y con el venv activo:

```powershell
python -m scripts.benchmark_load_engines 6 46 100
python -m pytest -q tests/unit/optimization/test_beam_search_fallback.py tests/unit/optimization/test_beam_memory_incremental.py tests/unit/optimization/test_largest_rectangle_equivalence.py tests/unit/optimization/test_beam_search_t02.py
```
