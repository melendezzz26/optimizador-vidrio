# Spike SP-005: Heurística adicional M5 (Best Residual Fit)

Este directorio contiene la investigación técnica, experimentación y validación formal de la heurística adicional **M5: Best Residual Fit (BRF)** para el motor de corte y empaquetado 2D de NewGlass.

---

## Estructura de archivos de la investigación

Siguiendo los **Estándares de Ingeniería de NewGlass** (Secciones 14, 15 y Anexos A y B):

```text
docs/spikes/sp-005-heuristica-m5/
├── README.md                           # Índice y guía rápida de la investigación
├── SPEC-SP-005-heuristica-m5.md        # Especificación formal (Plantilla Anexo A)
├── SP-005-informe-investigacion-m5.md  # Informe técnico científico con fundamentación, análisis y trade-offs
├── SP_005_Heuristica_M5_Colab.ipynb    # Cuaderno Jupyter interactivo para Google Colab (autocontenido)
├── experimento_m5.py                   # Script ejecutable en Python puro para reproducir el benchmark
└── resultados/                         # Datos experimentales crudos y reproducibles
    ├── resultados_baseline_vs_m5.csv   # Tabla comparativa completa en CSV
    ├── resumen_comparativo.json        # Consolidado estructurado en JSON
    ├── exp_small_001_detalles.json     # Métricas detalladas caso pequeño
    ├── exp_medium_001_detalles.json    # Métricas detalladas caso mediano
    ├── exp_complex_001_detalles.json   # Métricas detalladas caso complejo
    └── figuras/                        # Gráficos y diagramas de corte
```

---

## Resumen de la Heurística M5 (Best Residual Fit)

- **Principio operativo:** A diferencia de FF (primer candidato), BF (mínimas celdas libres) y WF (máximas celdas libres), **M5 evalúa la geometría del espacio residual libre post-colocación** y selecciona el candidato que maximiza el área del mayor rectángulo inscribible (`largest_rectangle`). En empates, minimiza la merma fragmentada no aprovechable.
- **Ventaja en la industria del vidrio:** Incrementa sustancialmente el **retazo recuperable** (material rectangular que puede volver a guardarse en inventario) y reduce la **merma neta fragmentada** (tiras inservibles que van a la basura).
- **Resultados empíricos sobre casos congelados TA-027:**
  - `EXP-SMALL-001`: $100\%$ de colocación, paridad exacta con el baseline ($60.000\%$ de uso, $0\text{ mm}^2$ de merma).
  - `EXP-MEDIUM-001`: **$170\text{ mm}^2$ de retazo útil** ($+13.3\%$ frente a WF y $+157.6\%$ frente a BF), reduciendo la merma en $20\text{ mm}^2$.
  - `EXP-COMPLEX-001`: **$318\text{ mm}^2$ de retazo útil** ($+18.66\%$ frente a WF y $+72.83\%$ frente a FF/BF), reduciendo la merma en $50\text{ mm}^2$.
  - **Tiempo y memoria:** $458.25\text{ ms}$ en caso complejo ($\approx$ a BF y FF), con solo $900.7\text{ KB}$ de memoria pico.

---

## Instrucciones de ejecución y reproducción

### 1. Ejecución en Google Colab:
Abrir el cuaderno directamente haciendo clic en la insignia:
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/melendezzz26/optimizador-vidrio/blob/main/docs/spikes/sp-005-heuristica-m5/SP_005_Heuristica_M5_Colab.ipynb)
Seleccionar `Entorno de ejecución` -> `Ejecutar todas`.
