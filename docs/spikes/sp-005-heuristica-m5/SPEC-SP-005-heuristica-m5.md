# SPEC-SP-005 — Heurística M5 Best Residual Fit

**Estado experimental:** GO condicionado.
**Estado de revisión:** auditoría técnica ejecutada; aprobación formal de Andro Joseph Quispe Cesias pendiente.
**Autor:** Luis Anthony Ibáñez Herrera.
**Fecha de cierre experimental:** 02/11/2026.
**Versión:** 1.1.

---

## 1. Objetivo

Evaluar una política experimental de selección M5 dentro del motor de empaquetado 2D de NewGlass y compararla con First Fit (FF), Best Fit (BF) y Worst Fit (WF). La evaluación usa exactamente los tres fixtures congelados TA-027, con el mismo loader, rasterizador, geometría, reglas de colocación y cálculo de métricas para los cuatro métodos.

M5 se denomina **Best Residual Fit (adaptación experimental de NewGlass)**. Es una política creada para este spike; no se presenta como un estándar académico establecido ni como un algoritmo integrado a producción.

## 2. Alcance

Incluye la implementación experimental del selector, la comparación reproducible en `experimento_m5.py`, pruebas específicas de M5, el notebook de presentación y los artefactos CSV/JSON.

No incluye cambios a los algoritmos del backend de producción, integración HTTP, esquema de base de datos o frontend. El selector experimental reutiliza `packing.pack()` y el backend existente.

## 3. Entradas y condiciones congeladas

Los casos se cargan con `experiments.optimization.loader.load_problem()` desde los fixtures oficiales TA-027.

| Parámetro | Valor |
|---|---|
| Casos | `EXP-SMALL-001`, `EXP-MEDIUM-001`, `EXP-COMPLEX-001` |
| Resolución | 1 mm por celda |
| Paso angular | 5° |
| Prioridad de stock | `RETAZO` antes que `PLANCHA` |
| Margen y separación | Small: 0 mm; Medium y Complex: 1 mm |
| Retazo recuperable mínimo | 1 × 1 mm |
| Repeticiones | 3 por método y caso |

No se modificaron los fixtures ni estos parámetros para favorecer a M5.

## 4. Regla M5

El backend entrega el conjunto canónico de candidatos factibles. Para cada candidato `c`, M5 examina el layout después de colocarlo, calcula el rectángulo libre máximo y considera recuperable su área solo si cumple los límites mínimos. Define:

- `A_rem(c)`: área del rectángulo libre máximo que cumple los límites de recuperación;
- `A_frag(c)`: celdas libres restantes menos las celdas de `A_rem(c)`.

Selecciona el mínimo lexicográfico:

```text
(-A_rem(c), A_frag(c), stock_rank, orientation_rank, row, column)
```

El primer criterio maximiza el residual rectangular. El segundo minimiza el espacio fragmentado; los siguientes mantienen el orden determinista de stock, orientación y posición.

BF ordena por menor cantidad total de celdas libres; WF por mayor cantidad. M5 valora primero la forma y el tamaño del residual rectangular. Las pruebas sintéticas del selector y los fixtures oficiales confirman decisiones distintas de BF y WF en `EXP-COMPLEX-001`.

## 5. Reglas compartidas

FF, BF, WF y M5 usan el mismo `packing.pack()`, generador de candidatos, resolución, paso angular, inventario, claves de material/espesor y política de prioridad `RETAZO` → `PLANCHA`. Las métricas proceden de `domain.metrics.calculate_metrics()` y la geometría de los módulos oficiales de rasterización y colocación.

El runner registra las colocaciones y su SHA-256 funcional. Tres ejecuciones de cada método/caso deben producir las mismas colocaciones, fuentes, orientaciones y métricas; el tiempo de ejecución puede variar.

## 6. Criterios de aceptación y resultado

1. Cada método coloca todas las unidades de los fixtures: 3/3, 9/9 y 24/24, respectivamente. **PASS.**
2. Los cuatro métodos mantienen las condiciones de TA-027 y el orden de fuentes. **PASS.**
3. Los resultados funcionales coinciden en las tres repeticiones de las 12 combinaciones método/caso. **PASS.**
4. M5 produce una selección distinta de BF y WF en Complex. **PASS.**
5. M5 en Complex permanece por debajo de 2 000 ms de mediana y 5 MB de memoria pico. **PASS:** mediana de tiempo 535.23 ms; mediana de memoria pico 850.99 KB y máximo observado 876.28 KB.
6. La documentación y los datos provienen de un runner común. **PASS.**

Resultados agregados (tiempo mediano local; los artefactos contienen cada muestra):

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

## 7. Decisión

**GO CONDICIONADO.** M5 ofrece más área recuperable que WF en Medium (+20 mm²) y Complex (+50 mm²), y reduce en igual medida la merma frente a WF. Small queda en paridad. M5 no domina FF/BF: en Medium y Complex usa una plancha nueva adicional y mantiene más merma que FF/BF. Su conveniencia depende de que preservar retazos compense el consumo de planchas.

No se recomienda seleccionar M5 como método general de producción con esta evidencia. Se propone conservar el selector como experimento hasta que se complete la revisión de Andro y se decida si el trade-off es aceptable para el proceso.

## 8. Discrepancia de evidencia resuelta

La primera versión del notebook contenía sus propias clases de rasterización, `SheetLayout`, `pack`, carga de casos codificada y cálculo de métricas. Su rasterizador muestreaba polígonos y círculos por centros de celdas, distinto del rasterizador conservador del backend; también recalculaba colocaciones y métricas localmente. Al ejecutar localmente esas celdas, sus métricas funcionales guardadas se reprodujeron, por lo que las salidas sí correspondían al código embebido, pero no al motor oficial.

El CSV/JSON original fue generado por `experimento_m5.py`, que importa el loader TA-027 y el motor del backend. El historial sitúa esos archivos junto al runner en el commit `144e4c25ef4888cf0ae54029d0be00c4e6f0fe4a`; aquellos artefactos no registraban versión de Python ni repeticiones. No es posible inferir con certeza el runtime original únicamente desde CSV/JSON. El notebook guardado registraba Python 3.13.18.

La versión 1.1 del runner usa solo el backend y los fixtures oficiales. Una auditoría contra `integration/sprint-01` encontró en `packing.py` únicamente instrumentación de evento visual, sin cambio en generación de candidatos, colocación, métricas o puntuación usada aquí.

## 9. Ejecución y artefactos

```powershell
python docs/spikes/sp-005-heuristica-m5/experimento_m5.py --repetitions 3
Set-Location backend
python -m pytest tests/unit/optimization/test_sp005_m5.py -q -ra
```

El experimento se registró localmente con Python 3.11.15 en Windows, runner en `42ac079e705c079a61bbca37d70b0f593b52dd77`. No se ejecutó en Colab.

- [Runner](experimento_m5.py)
- [Pruebas M5](../../../backend/tests/unit/optimization/test_sp005_m5.py)
- [CSV (36 ejecuciones)](resultados/resultados_baseline_vs_m5.csv)
- [JSON y firmas funcionales](resultados/resumen_comparativo.json)
- [Informe de investigación](SP-005-informe-investigacion-m5.md)
- [Plan](PLAN-SP-005-heuristica-m5.md) · [Tareas](TASKS-SP-005-heuristica-m5.md) · [Revisión](REVIEW-SP-005-heuristica-m5.md)

## 10. Revisión

La auditoría técnica y la reconciliación de evidencia están documentadas. La revisión formal de Andro Joseph Quispe Cesias sigue pendiente; la SPEC no declara una aprobación que todavía no existe.
