# PLAN TA-042 — Hole Filling

**Autor y revisor académico designado:** Andro Joseph Quispe Cesias. Base: `b9a537385e156225994ba478f775d44229e70919` (`origin/integration/sprint-01`).

1. Revisar SP-004 y contratos de FF/BF/WF, raster, placement, rotación, reglas y stock. Hecho.
2. T01: selector M4 aislado, mapas de anclajes acotados y protección de cobertura FF. Implementado; requiere ajuste tras auditoría.
3. T02: cubrir pockets, reglas, fallback, presupuesto, cobertura y determinismo. Implementado; ampliar para validar capacidad a escala y protección de planchas tras el ajuste.
4. Ejecutar suites dirigidas y registrar mediciones descriptivas. Hecho; ver evidencia.
5. Ajustar y volver a validar T01/T02; después, revisión académica de Andro y eventual apertura del PR. Pendiente.

La publicación de M4 como método de comparación depende de TA-043. No se modifica el coordinador, la UI ni los contratos de métodos en esta rama.

La auditoría final de TA-042 encontró que los límites actuales excluyen el fixture de capacidad de SP-004 y que puede usarse una plancha adicional con la misma cobertura que FF. Estado: **REQUIERE AJUSTE**. La propuesta de salvaguarda y el alcance de la limitación se documentan en SPEC y evidencia; todavía no se modifica la implementación.
