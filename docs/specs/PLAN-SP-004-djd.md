# PLAN-SP-004-DJD — Plan del spike

## Estado

Trabajo local completado sobre `spike/S2-SP004-djd`; se detiene antes de push, PR, CI/review remotos, merge y smoke post-merge. Los commits previos de Filler se conservan como historia. La decisión de evidencia es NO-GO para llevar esta implementación a TA-042 por su costo medido.

## Secuencia

| Fase | Trabajo | Evidencia/criterio | Estado |
|---|---|---|---|
| Auditoría | Releer heurísticas, contrato `pack`, layouts, raster, métricas, loader y fixtures. | Diferencias entre teoría y comportamiento NewGlass documentadas. | Completa; reutiliza auditoría del hito Filler y se amplía para simulación por copia. |
| Investigación | Verificar DJD original 1D y adaptación irregular 2D, variantes, búsqueda geométrica y tolerancia. | Referencias primarias y regla `1/20` trazable. | Completa. |
| SPEC y revisión | Formalizar candidato y revisar invariantes, ambigüedades y riesgos. | SPEC y registro de revisión. | Completa; criterios CA-01–CA-10 verificados localmente. |
| PLAN/TASKS | Mantener tareas alineadas con estado real del trabajo. | Plan y tablero de tareas versionados. | Completa. |
| Laboratorio aislado | Implementar DJD-1/3 reutilizando colocación y métricas existentes. | No hay cambios productivos; layouts de candidatos no contaminan la fuente activa. | Completa. |
| Caso discriminante | Añadir una instancia didáctica separada de TA-027. | Muestra una selección conjunta 1/2/3 sin alterar baselines oficiales. | Completa; DJD selecciona un par y su w es 5 mm². |
| Pruebas | Cubrir umbral, combinaciones, pruning, tolerancia, geometría, reglas y determinismo. | Pruebas aisladas DJD y suites unitarias FF/BF/WF verdes. | Completa; suite combinada 93/93. |
| Benchmark | Correr métodos en serie en los tres fixtures oficiales. | CSV/JSON con métricas oficiales, costo y diagnósticos. | Completa; CSV/JSON regenerados tras fijar el denominador publicado. |
| Notebook | Crear y ejecutar notebook Colab explicativo con outputs reales. | 36 secciones principales, comentarios de código y salidas interpretadas. | Completa; ejecución local de 31 celdas Python sin errores. |
| Evidencia, decisión y commits | Actualizar informe, verificar CA, registrar GO/NO-GO y conservar el trabajo en commits locales. | README, revisión CA, commits locales y estado limpio de rama. | Completa; cinco commits locales; sin push/PR/merge. |

## Matriz de verificación de CA

| CA | Evidencia local | Estado |
|---|---|---|
| CA-01 — historial Filler y nueva rama | Commits históricos retenidos; documento, notebook, benchmark CSV/JSON renombrados como descartados. | PASS |
| CA-02 — fuentes y variante | `docs/spikes/SP-004-djd.md`, referencias primarias y celdas 3–5/34 del notebook. | PASS |
| CA-03 — umbral y `w` | Código usa `stock.area_mm2 / 3` como umbral y `/ 20` como paso; prueba discriminante. | PASS |
| CA-04 — grupos y contadores | Generación perezosa, poda, secuencias, checks y resultados en JSON/CSV. | PASS |
| CA-05 — geometría y reglas comunes | Pruebas de layout, material, espesor, prioridad, margen, separación, rotación, colisión y no mutación. | PASS |
| CA-06 — benchmarks | Tres fixtures TA-027 intactos; cuatro métodos y métricas oficiales en CSV. | PASS |
| CA-07 — discriminación | JSON fuera de TA-027 y comparación FF/BF/WF/DJD. | PASS |
| CA-08 — notebook | 36 secciones, 31/31 celdas de código con outputs y sin errores. | PASS |
| CA-09 — pruebas y determinismo | 93 pruebas aprobadas; ejecuciones DJD ×3 idénticas por fixture. | PASS |
| CA-10 — decisión y límite de publicación | NO-GO sustentado por costo COMPLEX; rama local, commits sin push. | PASS |

La verificación CA es local y experimental; no equivale a revisión humana externa ni a CI remoto.

## Política de recursos

Ejecutar un método a la vez. Enumerar combinaciones perezosamente, podar por área antes de geometría y conservar únicamente layout temporal actual, combinaciones geométricas fallidas de la misma versión de layout y la traza agregada. No usar multiprocessing.
