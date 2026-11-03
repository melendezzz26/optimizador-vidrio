# SPEC-SP-005 — Heurística M5 Best Residual Fit

La especificación completa está en [SPEC-SP-005](../spikes/sp-005-heuristica-m5/SPEC-SP-005-heuristica-m5.md).

- **Estado experimental:** GO condicionado.
- **Revisión formal de Andro Joseph Quispe Cesias:** pendiente; no hay aprobación registrada.
- **Autor:** Luis Anthony Ibáñez Herrera.
- **Método:** Best Residual Fit, adaptación experimental de NewGlass (M5/BRF).
- **Comparación:** FF, BF, WF y M5 sobre los tres fixtures congelados TA-027.
- **Ejecución fuente:** `experimento_m5.py`, backend y loader oficiales, 3 repeticiones por método/caso.
- **Entorno registrado:** Python 3.11.15 local en Windows; no ejecutado en Google Colab.
- **Resultados:** [CSV](../spikes/sp-005-heuristica-m5/resultados/resultados_baseline_vs_m5.csv), [resumen JSON](../spikes/sp-005-heuristica-m5/resultados/resumen_comparativo.json) y [evidencia](../evidence/sprint-02/SP-005/README.md).
- **Notebook:** [SP_005_Heuristica_M5_Colab.ipynb](../spikes/sp-005-heuristica-m5/SP_005_Heuristica_M5_Colab.ipynb), que presenta los resultados del runner y no contiene otra copia del motor.
