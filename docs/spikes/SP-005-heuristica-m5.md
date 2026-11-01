# SP-005 — Investigación y Experimentación de Heurística Adicional M5 (Best Residual Fit)

**PBI / Tarea:** SP-005 — T01
**Responsable:** Equipo NewGlass (Aguilar, Ibañez, Melendez, Quispe)
**Estado:** Verificado técnicamente / Listo para integración

El informe completo de la investigación con todos sus resultados tabulados, análisis matemático, trade-offs y cuaderno interactivo de Google Colab se encuentra en:

* [Carpeta de Investigación: docs/spikes/sp-005-heuristica-m5/](sp-005-heuristica-m5/README.md)
* [Informe Técnico: SP-005-informe-investigacion-m5.md](sp-005-heuristica-m5/SP-005-informe-investigacion-m5.md)
* [Cuaderno Google Colab: SP_005_Heuristica_M5_Colab.ipynb](sp-005-heuristica-m5/SP_005_Heuristica_M5_Colab.ipynb)
* [Evidencia Formal: docs/evidence/sprint-02/SP-005/README.md](../evidence/sprint-02/SP-005/README.md)

---

### Resumen de Resultados (Baseline vs M5)

| Caso | FF (Uso / Merma / Retazo) | BF (Uso / Merma / Retazo) | WF (Uso / Merma / Retazo) | M5 (Uso / Merma / Retazo) | Ganancia M5 vs WF |
|---|---|---|---|---|---|
| **EXP-SMALL-001** | 60.0% / 0 mm² / 8 mm² | 60.0% / 0 mm² / 8 mm² | 60.0% / 0 mm² / 8 mm² | 60.0% / 0 mm² / 8 mm² | Paridad base (100% colocación) |
| **EXP-MEDIUM-001** | 28.4% / 201.86 mm² / 58 mm² | 28.4% / 193.86 mm² / 66 mm² | 18.6% / 301.86 mm² / 150 mm² | **18.6% / 281.86 mm² / 170 mm²** | **+20 mm² retazo / -20 mm² merma** |
| **EXP-COMPLEX-001** | 29.6% / 746.72 mm² / 184 mm² | 29.6% / 746.72 mm² / 184 mm² | 25.3% / 886.72 mm² / 268 mm² | **25.3% / 836.72 mm² / 318 mm²** | **+50 mm² retazo / -50 mm² merma** |
