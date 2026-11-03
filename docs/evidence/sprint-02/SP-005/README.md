# Evidencia SP-005 (T01) — Investigación y Experimentación de Heurística M5

**PBI / Tarea:** SP-005 — T01: Investigar y experimentar heurística M5
**Responsable:** Ibañez Herrera Luis Anthony
**Fecha:** 01/11/2026
**Entorno:** Local (Windows 11 / Python 3.11.1) y Google Colab (Python 3.10/3.11 Runtime)
**Artefactos relacionados:**
- [SPEC-SP-005](../../../docs/spikes/sp-005-heuristica-m5/SPEC-SP-005-heuristica-m5.md)
- [Informe de Investigación](../../../docs/spikes/sp-005-heuristica-m5/SP-005-informe-investigacion-m5.md)
- [Cuaderno Google Colab](../../../docs/spikes/sp-005-heuristica-m5/SP_005_Heuristica_M5_Colab.ipynb)
- [Script Experimental](../../../docs/spikes/sp-005-heuristica-m5/experimento_m5.py)
- [CSV de Resultados](../../../docs/spikes/sp-005-heuristica-m5/resultados/resultados_baseline_vs_m5.csv)
- [JSON de Resultados](../../../docs/spikes/sp-005-heuristica-m5/resultados/resumen_comparativo.json)

---

## 1. Entrada y configuración

| Parámetro | Configuración experimental |
|---|---|
| Casos de prueba | `EXP-SMALL-001`, `EXP-MEDIUM-001`, `EXP-COMPLEX-001` (congelados en TA-027) |
| Resolución raster | $1\text{ mm}$ por celda |
| Paso angular de rotación | $5^\circ$ ($0^\circ$ a $355^\circ$, 72 ángulos con deduplicación de máscaras) |
| Jerarquía de stock | Nivel `RETAZO` prioritario antes de nivel `PLANCHA` |
| Margen y separación | $0\text{ mm}$ (Small) / $1\text{ mm}$ (Medium y Complex) |
| Dimensiones residuales mínimas | $1 \times 1\text{ mm}$ |
| Heurísticas evaluadas | First Fit (FF), Best Fit (BF), Worst Fit (WF) y M5 (Best Residual Fit - BRF) |

---

## 2. Procedimiento de reproducción

### Opción A — Ejecución local (desde consola):
```powershell
# Desde el directorio del spike:
cd docs/spikes/sp-005-heuristica-m5
python experimento_m5.py
```

### Opción B — Ejecución en Google Colab:
1. Abrir el archivo `docs/spikes/sp-005-heuristica-m5/SP_005_Heuristica_M5_Colab.ipynb` en Google Colab o mediante el enlace:
   [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/melendezzz26/optimizador-vidrio/blob/spike/SP-005-heuristica-m5/docs/spikes/sp-005-heuristica-m5/SP_005_Heuristica_M5_Colab.ipynb)
2. Seleccionar `Entorno de ejecución` -> `Ejecutar todas`.
3. El cuaderno ejecuta las 4 heurísticas sobre los 3 casos, renderiza los gráficos comparativos de barras y layouts de corte, y descarga automáticamente los archivos `resultados_baseline_vs_m5.csv` y `resumen_comparativo.json`.

---

## 3. Resultado esperado vs. resultado obtenido

### 3.1 Colocación y sanidad funcional
- **Esperado:** Colocación del 100% de piezas en los 3 casos sin errores geométricos ni de contorno.
- **Obtenido:**
  - `EXP-SMALL-001`: 3 de 3 piezas colocadas ($100\%$). **PASS**.
  - `EXP-MEDIUM-001`: 9 de 9 piezas colocadas ($100\%$). **PASS**.
  - `EXP-COMPLEX-001`: 24 de 24 piezas colocadas ($100\%$). **PASS**.

### 3.2 Retazo recuperable y merma
- **Esperado:** M5 debe superar o igualar a WF en retazo recuperable y reducir la merma fragmentada en los casos medianos y complejos.
- **Obtenido:**
  - En `EXP-MEDIUM-001`: M5 obtiene **$170\text{ mm}^2$** de retazo recuperable ($+13.3\%$ sobre WF y $+157.6\%$ sobre BF), reduciendo la merma a $281.86\text{ mm}^2$ (ahorro de $20\text{ mm}^2$ respecto a WF). **PASS**.
  - En `EXP-COMPLEX-001`: M5 obtiene **$318\text{ mm}^2$** de retazo recuperable ($+18.66\%$ sobre WF y $+72.83\%$ sobre FF/BF), reduciendo la merma a $836.72\text{ mm}^2$ (ahorro de $50\text{ mm}^2$ de merma respecto a WF). **PASS**.

### 3.3 Tiempos de cómputo y memoria
- **Esperado:** Tiempo computacional en `EXP-COMPLEX-001` menor a $2000\text{ ms}$ y memoria pico menor a $128\text{ MiB}$.
- **Obtenido:**
  - Tiempo de cómputo en complejo: **$458.25\text{ ms}$** (a la par de BF con $464.41\text{ ms}$ y FF con $448.77\text{ ms}$). **PASS**.
  - Memoria pico en complejo: **$900.7\text{ KB}$** ($< 1\text{ MB}$, significativamente menor al límite de $128\text{ MiB}$). **PASS**.

---

## 4. Tabla de datos reproducibles observados

```csv
caso,metodo_codigo,metodo_nombre,piezas_colocadas,piezas_totales,planchas_nuevas,utilizacion_pct,desperdicio_mm2,retazo_recuperable_mm2,tiempo_ms,memoria_pico_kb,completo
EXP-SMALL-001,FF,First Fit,3,3,1,60.0,0.0,8.0,59.78,185.46,True
EXP-SMALL-001,BF,Best Fit,3,3,1,60.0,0.0,8.0,52.6,157.69,True
EXP-SMALL-001,WF,Worst Fit,3,3,1,60.0,0.0,8.0,57.07,156.61,True
EXP-SMALL-001,M5,Best Residual Fit,3,3,1,60.0,0.0,8.0,52.69,151.68,True
EXP-MEDIUM-001,FF,First Fit,9,9,1,28.413,201.86,58.0,100.64,226.24,True
EXP-MEDIUM-001,BF,Best Fit,9,9,1,28.413,193.86,66.0,128.9,328.53,True
EXP-MEDIUM-001,WF,Worst Fit,9,9,2,18.584,301.86,150.0,96.69,220.74,True
EXP-MEDIUM-001,M5,Best Residual Fit,9,9,2,18.584,281.86,170.0,90.59,221.78,True
EXP-COMPLEX-001,FF,First Fit,24,24,3,29.598,746.72,184.0,448.77,1058.76,True
EXP-COMPLEX-001,BF,Best Fit,24,24,3,29.598,746.72,184.0,464.41,1058.28,True
EXP-COMPLEX-001,WF,Worst Fit,24,24,4,25.309,886.72,268.0,448.37,1031.98,True
EXP-COMPLEX-001,M5,Best Residual Fit,24,24,4,25.309,836.72,318.0,458.25,900.74,True
```

---

## 5. Conclusión de la evidencia

La evidencia demuestra que la heurística M5 (Best Residual Fit) está **técnicamente verificada**, es **100% reproducible** y cumple todos los criterios de aceptación de la SPEC-SP-005. Se encuentra lista para la fase de implementación e incorporación al motor de optimización.
