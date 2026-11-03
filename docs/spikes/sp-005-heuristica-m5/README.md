# SP-005 — M5 Best Residual Fit

**Estado:** GO CONDICIONADO experimental.
**Autor:** Luis Anthony Ibáñez Herrera.
**Revisor asignado:** Andro Joseph Quispe Cesias; revisión formal pendiente.
**PR:** #93 · `spike/SP-005-heuristica-m5`.

Este spike compara FF, BF, WF y **M5 Best Residual Fit (adaptación experimental de NewGlass)**. M5 reutiliza `packing.pack()` y prioriza el área del mayor residual rectangular libre posterior a cada colocación. Su score es `(-área_recuperable, celdas_fragmentadas, stock_rank, orientation_rank, fila, columna)`. BF minimiza celdas libres totales; WF las maximiza.

## Resultados reproducibles

El runner usa el loader, fixtures, rasterizador, colocación y métricas oficiales TA-027/backend. Se registraron tres repeticiones por método y caso (36 ejecuciones). Las métricas funcionales coincidieron en todas las repeticiones; el tiempo informado es la mediana local.

| Caso | Método | Colocadas | Retazos usados | Planchas | Uso % | Merma mm² | Recuperable mm² | Mediana ms |
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

M5 supera a WF en área recuperable en Medium (+20 mm²) y Complex (+50 mm²), con menor merma por la misma cantidad. Frente a FF/BF, sin embargo, M5 usa una plancha nueva adicional y registra mayor merma en ambos casos. Por ello la decisión es condicional y no demuestra superioridad general.

## Reproducir

Desde la raíz del repositorio, con Python 3.11 o compatible:

```powershell
python docs/spikes/sp-005-heuristica-m5/experimento_m5.py --repetitions 3
Set-Location backend
python -m pytest tests/unit/optimization/test_sp005_m5.py -q -ra
```

La corrida documentada se ejecutó localmente con Python 3.11.15 en Windows, no en Google Colab. El CSV guarda las 36 muestras; el JSON registra runtime, commit del runner, firmas funcionales, colocaciones y medianas.

## Archivos

- [SPEC](SPEC-SP-005-heuristica-m5.md) · [PLAN](PLAN-SP-005-heuristica-m5.md) · [TASKS](TASKS-SP-005-heuristica-m5.md)
- [Informe de investigación](SP-005-informe-investigacion-m5.md) · [Auditoría/revisión técnica](REVIEW-SP-005-heuristica-m5.md)
- [Notebook](SP_005_Heuristica_M5_Colab.ipynb)
- [CSV de 36 ejecuciones](resultados/resultados_baseline_vs_m5.csv) · [JSON](resultados/resumen_comparativo.json)
- [Evidencia formal](../../evidence/sprint-02/SP-005/README.md)
