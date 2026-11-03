# SP-005 — Investigación y experimento M5 Best Residual Fit

**PBI:** SP-005 / T01
**Autor:** Luis Anthony Ibáñez Herrera
**Revisor asignado:** Andro Joseph Quispe Cesias (revisión formal pendiente)
**Fecha:** 02/11/2026
**Decisión:** GO CONDICIONADO experimental
**Runner:** `42ac079e705c079a61bbca37d70b0f593b52dd77`

## 1. Pregunta e hipótesis

¿Puede una política M5 que prefiera el mayor residual rectangular recuperable, bajo las mismas reglas del baseline, aumentar el material reutilizable sin que el costo en planchas sea excesivo?

La hipótesis evaluada es local a NewGlass. **Best Residual Fit (adaptación experimental de NewGlass)** no se presenta como un estándar académico ni como un método ya aprobado para producción.

## 2. Regla M5 y comparación

Para cada candidato que el motor considera factible, M5 evalúa `candidate.layout_after`, obtiene el mayor rectángulo libre mediante `largest_rectangle()` y minimiza:

```text
(-área_residual_recuperable, celdas_libres_fragmentadas,
 stock_rank, orientation_rank, fila, columna)
```

El residual se marca recuperable si cumple el mínimo de 1 × 1 mm. La fragmentación se calcula como celdas libres posteriores menos celdas del residual. Los últimos cuatro criterios mantienen los desempates estables.

BF prioriza menor área libre total y WF mayor área libre total. M5 prioriza la calidad geométrica del área libre. La prueba de score y el resultado distinto de BF/WF en Complex confirman que no es BF con otro nombre.

## 3. Auditoría de la discrepancia anterior

El notebook previo tenía implementaciones propias de rasterización, rotación, layout, packing y métricas, además de casos hardcodeados. En particular, muestreaba polígonos y círculos por el centro del píxel, mientras que el rasterizador oficial conservador representa las celdas cubiertas por la geometría. También calculaba sus propios residuales en lugar de usar las métricas del backend.

La ejecución aislada local de sus celdas funcionales reprodujo las métricas guardadas. Esto muestra que el notebook era coherente con el motor embebido, pero ambos diferían del motor oficial. Sus salidas guardadas registraban Python 3.13.18. En contraste, el runner que produjo el CSV/JSON original importa el loader TA-027 y el backend; el historial sitúa esos artefactos en `144e4c25ef4888cf0ae54029d0be00c4e6f0fe4a`, pero no registró Python ni repeticiones. Los fixtures hardcodeados del notebook coinciden en geometría, inventario, cantidades, materiales, espesores y configuración con los JSON oficiales.

La auditoría contra `integration/sprint-01` identificó en `packing.py` solo instrumentación de eventos visuales, sin impacto en los criterios usados por el experimento. La corrección fue retirar las copias del notebook, no modificar cifras ni fixtures.

## 4. Protocolo reproducible

- Fixtures oficiales: `EXP-SMALL-001`, `EXP-MEDIUM-001`, `EXP-COMPLEX-001`.
- Métodos: FF, BF, WF y M5.
- Condiciones compartidas: raster 1 mm, paso angular 5°, misma configuración de margen y separación, mismo stock y claves material/espesor, prioridad `RETAZO` → `PLANCHA`.
- Motor común: `backend/app/modules/optimization/domain/packing.py`.
- Métricas comunes: `backend/app/modules/optimization/domain/metrics.py`.
- Repeticiones: tres por método y caso, 36 corridas en total.
- Runtime medido: Python 3.11.15 local en Windows. No se ejecutó en Colab.
- Comando: `python docs/spikes/sp-005-heuristica-m5/experimento_m5.py --repetitions 3 --output-dir <directorio-temporal>`.

Se verificó que colocaciones, orientaciones, fuentes, conteos y métricas funcionales coinciden en las tres repeticiones para las 12 combinaciones. El tiempo puede variar; la tabla informa la mediana. El CSV conserva las 36 muestras, y el JSON incluye hashes SHA-256 del resultado funcional y colocaciones.

## 5. Resultados

| Caso | Método | Colocadas | Retazos usados | Planchas nuevas | Uso % | Merma mm² | Recuperable mm² | Mediana ms |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| SMALL | FF | 3/3 | 1 | 1 | 60.000 | 0.00 | 8 | 95.03 |
| SMALL | BF | 3/3 | 1 | 1 | 60.000 | 0.00 | 8 | 96.76 |
| SMALL | WF | 3/3 | 1 | 1 | 60.000 | 0.00 | 8 | 97.37 |
| SMALL | M5 | 3/3 | 1 | 1 | 60.000 | 0.00 | 8 | 96.94 |
| MEDIUM | FF | 9/9 | 2 | 1 | 28.413 | 201.86 | 58 | 181.06 |
| MEDIUM | BF | 9/9 | 2 | 1 | 28.413 | 193.86 | 66 | 243.34 |
| MEDIUM | WF | 9/9 | 2 | 2 | 18.584 | 301.86 | 150 | 173.58 |
| MEDIUM | M5 | 9/9 | 2 | 2 | 18.584 | 281.86 | 170 | 187.57 |
| COMPLEX | FF | 24/24 | 3 | 3 | 29.598 | 746.72 | 184 | 889.95 |
| COMPLEX | BF | 24/24 | 3 | 3 | 29.598 | 746.72 | 184 | 566.66 |
| COMPLEX | WF | 24/24 | 3 | 4 | 25.309 | 886.72 | 268 | 537.43 |
| COMPLEX | M5 | 24/24 | 3 | 4 | 25.309 | 836.72 | 318 | 535.23 |

`Retazos usados` cuenta las unidades distintas de stock `RETAZO` que recibieron colocaciones. `Planchas nuevas` cuenta unidades `PLANCHA` usadas. Los tiempos y los datos funcionales por repetición están en [CSV](resultados/resultados_baseline_vs_m5.csv) y [JSON](resultados/resumen_comparativo.json).

## 6. Análisis y trade-offs

- **SMALL:** paridad funcional entre todos los métodos.
- **MEDIUM:** M5 preserva 20 mm² más que WF y reduce 20 mm² de merma frente a WF. Usa dos planchas nuevas, una más que FF/BF. Su merma (281.86 mm²) supera a FF (201.86) y BF (193.86).
- **COMPLEX:** M5 preserva 50 mm² más que WF y reduce 50 mm² de merma frente a WF. Usa cuatro planchas nuevas, una más que FF/BF. Su merma (836.72 mm²) supera a FF/BF (746.72).
- **Recursos:** M5 registra una mediana de 535.23 ms en Complex; la mediana de memoria pico es 850.99 KB y el máximo de sus tres muestras es 876.28 KB. Los tiempos no deben generalizarse a otros equipos o runtimes.

La mejora M5 es clara frente a WF en área recuperable, pero no domina a FF/BF en planchas ni merma. El valor del método depende de que el inventario recuperable pese más que el material comercial y la merma adicionales.

## 7. Decisión experimental

**GO CONDICIONADO.** Continuar evaluando M5 solo cuando el caso de negocio priorice preservar retazos y acepte el consumo adicional de planchas observado. No se recomienda convertirlo en método general de producción con estos tres fixtures. La revisión formal del revisor asignado sigue pendiente.

## 8. Artefactos

- [SPEC](SPEC-SP-005-heuristica-m5.md), [PLAN](PLAN-SP-005-heuristica-m5.md), [TASKS](TASKS-SP-005-heuristica-m5.md)
- [REVIEW de auditoría técnica](REVIEW-SP-005-heuristica-m5.md)
- [Notebook de resultados](SP_005_Heuristica_M5_Colab.ipynb)
- [README del spike](README.md)
- [Evidencia formal](../../evidence/sprint-02/SP-005/README.md)
