# SP-005 — Investigación M5 Best Residual Fit

**Autor:** Luis Anthony Ibáñez Herrera · **Estado:** GO CONDICIONADO experimental
**Revisor asignado:** Andro Joseph Quispe Cesias · **revisión formal pendiente**

M5 es una adaptación experimental de NewGlass que prioriza el mayor residual rectangular recuperable. Se comparó con FF/BF/WF mediante el mismo backend y fixtures TA-027, con tres ejecuciones por método/caso. Los resultados funcionales fueron deterministas.

| Caso | FF (uso/merma/recuperable) | BF (uso/merma/recuperable) | WF (uso/merma/recuperable) | M5 (uso/merma/recuperable) |
|---|---|---|---|---|
| SMALL | 60.000% / 0.00 / 8 | 60.000% / 0.00 / 8 | 60.000% / 0.00 / 8 | 60.000% / 0.00 / 8 |
| MEDIUM | 28.413% / 201.86 / 58 | 28.413% / 193.86 / 66 | 18.584% / 301.86 / 150 | 18.584% / 281.86 / 170 |
| COMPLEX | 29.598% / 746.72 / 184 | 29.598% / 746.72 / 184 | 25.309% / 886.72 / 268 | 25.309% / 836.72 / 318 |

Áreas en mm². M5 mejora sobre WF en área recuperable, pero usa más planchas y produce más merma que FF/BF en MEDIUM y COMPLEX; por eso no se recomienda superioridad general.

- [Carpeta del spike, runner y resultados](sp-005-heuristica-m5/README.md)
- [SPEC](sp-005-heuristica-m5/SPEC-SP-005-heuristica-m5.md) · [PLAN](sp-005-heuristica-m5/PLAN-SP-005-heuristica-m5.md) · [TASKS](sp-005-heuristica-m5/TASKS-SP-005-heuristica-m5.md)
- [Informe](sp-005-heuristica-m5/SP-005-informe-investigacion-m5.md) · [Auditoría técnica](sp-005-heuristica-m5/REVIEW-SP-005-heuristica-m5.md)
- [Notebook](sp-005-heuristica-m5/SP_005_Heuristica_M5_Colab.ipynb) · [Evidencia formal](../evidence/sprint-02/SP-005/README.md)
