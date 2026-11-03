# REVIEW-SP-005 — Auditoría de evidencia y cierre técnico

**Fecha:** 02/11/2026
**Revisión formal asignada a:** Andro Joseph Quispe Cesias
**Estado formal:** pendiente; no hay aprobación de Andro registrada
**Auditoría técnica:** completada para preparar el PR #93

Esta evidencia documenta la auditoría reproducible del spike. No sustituye ni atribuye una aprobación a la persona revisora asignada.

## Causa de la discrepancia

El notebook original ejecutaba un motor independiente definido en celdas: `RAW_CASES` copiados, rasterizador, rotación, `SheetLayout`, `pack()` y cálculo de métricas propios. El rasterizador embebido determina ocupación de círculos y polígonos muestreando centros de celdas; el backend oficial rasteriza conservadoramente la geometría completa. Además, el notebook no llamaba al loader TA-027 ni a `calculate_metrics()` del backend. La diferencia alteraba máscaras, colocaciones y residuales, especialmente en geometrías complejas.

La ejecución local aislada de las celdas 1–8 reprodujo los resultados funcionales guardados en el notebook:

| Caso/método | Notebook anterior | Runner oficial |
|---|---:|---:|
| MEDIUM FF — merma / recuperable | 200.86 / 59 mm² | 201.86 / 58 mm² |
| COMPLEX FF/BF — merma / recuperable | 624.72 / 314 mm² | 746.72 / 184 mm² |
| COMPLEX WF — merma / recuperable | 761.72 / 401 mm² | 886.72 / 268 mm² |
| COMPLEX M5 — merma / recuperable | 736.72 / 426 mm² | 836.72 / 318 mm² |

Por tanto, los outputs anteriores eran coherentes con el snapshot embebido, pero no con el backend oficial. La discrepancia no procede de editar cifras ni de un bug del score M5. Tampoco se seleccionó manualmente uno de los juegos: se retiró la implementación duplicada y se regeneró la evidencia con una sola ruta.

## Procedencia auditada

- Los tres casos codificados en el notebook se compararon con los JSON TA-027: sus parámetros, geometrías, cantidades, materiales, espesores e inventarios coinciden.
- El runner que acompañaba al CSV/JSON original importa `experiments.optimization.loader` y los optimizadores/métricas del backend. El historial sitúa esos archivos en el commit `144e4c25ef4888cf0ae54029d0be00c4e6f0fe4a`; los CSV/JSON originales no guardaban versión de Python, hash funcional ni repeticiones, por lo que no se afirma un runtime original que no esté registrado.
- El output del notebook registraba Python 3.13.18. La auditoría aislada se hizo con Python local 3.11.15; sus tiempos no son intercambiables.
- En la comparación con `integration/sprint-01`, el cambio relevante de `packing.py` es instrumentación de eventos visuales; no modifica la selección, rasterización, colocación o métricas ejecutadas por este experimento.

## Fuente final y ejecución nueva

La fuente de verdad es el runner versionado en `42ac079e705c079a61bbca37d70b0f593b52dd77`, con fixtures TA-027, `packing.pack()`, rasterizador y métricas oficiales. Comando ejecutado:

```powershell
python docs/spikes/sp-005-heuristica-m5/experimento_m5.py --repetitions 3 --output-dir <directorio-temporal>
```

Se ejecutaron 36 corridas (4 métodos × 3 casos × 3 repeticiones) con Python 3.11.15 en Windows. Las 12 firmas funcionales fueron deterministas. Los tiempos se informan como mediana de las tres muestras por combinación; cada muestra cruda está en el CSV y el JSON.

La tabla completa está en [README de evidencia](../../evidence/sprint-02/SP-005/README.md). Los datos de comparación clave son:

- SMALL: todos los métodos 3/3, merma 0 mm² y 8 mm² recuperables.
- MEDIUM: M5 obtiene 170 mm² recuperables y 281.86 mm² de merma; WF 150 y 301.86. FF/BF usan una plancha, M5/WF dos.
- COMPLEX: M5 obtiene 318 mm² recuperables y 836.72 mm² de merma; WF 268 y 886.72. FF/BF usan tres planchas, M5/WF cuatro.

## Score y diferenciación

M5 minimiza `(-A_rem, A_frag, stock_rank, orientation_rank, row, column)`, donde `A_rem` es el área del mayor rectángulo recuperable posterior a colocar y `A_frag` son las celdas libres fuera de ese rectángulo. BF minimiza celdas libres totales y WF las maximiza. Las pruebas verifican empate, fragmentación, criterios deterministas, retorno sin candidato y decisiones distintas de BF/WF en el fixture Complex.

## Pruebas

- `python -m pytest tests/unit/optimization/test_sp005_m5.py -q -ra` — 11 passed.
- Regresión dirigida de M5, TA-027, FF/BF/WF, prioridad de retazo, ángulos, reglas comunes, geometría, colocación y métricas — 367 passed.
- `git diff --check` se ejecutará nuevamente sobre el conjunto final de cambios.

## Dictamen de auditoría

**GO CONDICIONADO experimental.** M5 es distinta de BF/WF y favorece residuales mayores que WF en Medium/Complex, pero en ambos casos usa una plancha más y supera la merma de FF/BF. La decisión depende de que el valor de recuperar área compense el consumo de planchas. No se concluye superioridad general ni se recomienda integrar M5 a producción con esta evidencia.

La revisión de Andro permanece pendiente y es un bloqueo documental del PR. Hasta recibirla, el PR no queda listo para merge.
