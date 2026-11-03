# Evidencia SP-005 — Experimento M5 Best Residual Fit

**PBI:** SP-005 / T01
**Autor:** Luis Anthony Ibáñez Herrera
**Revisor asignado:** Andro Joseph Quispe Cesias — revisión formal pendiente
**Rama / PR:** `spike/SP-005-heuristica-m5` / #93
**Decisión:** GO CONDICIONADO experimental

## Artefactos

- [SPEC](../../../spikes/sp-005-heuristica-m5/SPEC-SP-005-heuristica-m5.md), [PLAN](../../../spikes/sp-005-heuristica-m5/PLAN-SP-005-heuristica-m5.md), [TASKS](../../../spikes/sp-005-heuristica-m5/TASKS-SP-005-heuristica-m5.md)
- [Informe de investigación](../../../spikes/sp-005-heuristica-m5/SP-005-informe-investigacion-m5.md)
- [Revisión técnica de evidencia](../../../spikes/sp-005-heuristica-m5/REVIEW-SP-005-heuristica-m5.md)
- [Runner](../../../spikes/sp-005-heuristica-m5/experimento_m5.py)
- [Notebook de presentación](../../../spikes/sp-005-heuristica-m5/SP_005_Heuristica_M5_Colab.ipynb)
- [CSV — 36 ejecuciones](../../../spikes/sp-005-heuristica-m5/resultados/resultados_baseline_vs_m5.csv)
- [JSON — resultados, firmas y runtime](../../../spikes/sp-005-heuristica-m5/resultados/resumen_comparativo.json)

## Procedencia y discrepancia resuelta

El notebook original tenía un motor independiente en sus celdas: casos copiados, rasterizador por centros de píxel, rotación, layout, packing y métricas propios. No cargaba TA-027 con el loader oficial. Una ejecución local de esas celdas reprodujo sus valores guardados, pero el rasterizador por centros no es equivalente al rasterizador conservador oficial y cambiaba colocaciones y residuales.

El runner asociado al CSV/JSON original sí importaba el loader TA-027 y el backend. El historial sitúa runner y CSV/JSON en `144e4c25ef4888cf0ae54029d0be00c4e6f0fe4a`, pero esos resultados no guardaban versión de Python ni repetición. Por tanto, no se inventa su runtime original. El notebook antiguo registraba Python 3.13.18.

La fuente única nueva es `experimento_m5.py` con `backend/app/modules/optimization/domain/packing.py`, `domain/metrics.py` y `experiments.optimization.loader`. Los fixtures del notebook se compararon con TA-027 y sus configuraciones, cantidades, geometrías, materiales y espesores coincidían. La auditoría contra `integration/sprint-01` encontró en `packing.py` solo instrumentación de eventos visuales, sin impacto en este cálculo.

## Configuración

| Parámetro | Valor |
|---|---|
| Casos | `EXP-SMALL-001`, `EXP-MEDIUM-001`, `EXP-COMPLEX-001` |
| Métodos | FF, BF, WF, M5 |
| Resolución / rotación | 1 mm / paso 5° |
| Margen y separación | 0 mm en SMALL; 1 mm en MEDIUM y COMPLEX |
| Prioridad / compatibilidad | `RETAZO` antes de `PLANCHA`; mismo material y espesor |
| Repeticiones | 3 por método/caso; 36 ejecuciones |
| Runtime registrado | Python 3.11.15 local, Windows; no ejecutado en Colab |
| Commit del runner | `42ac079e705c079a61bbca37d70b0f593b52dd77` |

## Resultados

Los valores funcionales coinciden en las tres repeticiones de las 12 combinaciones. Se muestra la mediana del tiempo; cada muestra está en el CSV.

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

`Retazos usados` cuenta unidades distintas de stock `RETAZO` usadas; `Planchas nuevas` cuenta stock `PLANCHA` usado.

## M5 y decisión

M5 minimiza `(-A_rem, A_frag, stock_rank, orientation_rank, row, column)`: maximiza primero el mayor rectángulo recuperable posterior a colocar y luego minimiza celdas libres fragmentadas. BF prioriza menor área libre total y WF mayor área libre total. En Complex M5 produce colocaciones distintas de ambos.

M5 aumenta el recuperable frente a WF en 20 mm² en MEDIUM y 50 mm² en COMPLEX, con igual reducción de merma respecto a WF. Frente a FF/BF, M5 usa una plancha adicional y genera más merma en esos dos casos. **GO CONDICIONADO:** continuar evaluación solo si el negocio prioriza retazos recuperables sobre el costo de planchas/merma. No se concluye superioridad general ni adopción en producción.

## Verificación

- Pruebas M5: `python -m pytest tests/unit/optimization/test_sp005_m5.py -q -ra` desde `backend` — **11 passed**.
- Regresión dirigida de M5, casos TA-027, FF/BF/WF, geometría, rotación, prioridad de retazo, margen, separación y métricas — **367 passed**.
- La notebook presenta el JSON producido por el runner; se ejecutó localmente y muestra `Runtime Google Colab: False`. No se afirma una verificación en Colab.
- Revisión formal de Andro: pendiente.
