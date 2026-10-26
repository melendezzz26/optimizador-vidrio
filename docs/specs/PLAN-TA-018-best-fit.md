# PLAN TA-018

1. Selector mínimo sobre capacidad ya definida en FeasibleCandidate.
2. Wrapper BestFitOptimizer / BestFitResult siguiendo patrón WF.
3. Reutilizar preparación/stock en slice de aplicación de solo lectura.
4. Pruebas unitarias y repositorios reales en SQLite aislado.
5. Ejecutar regresiones POST-PR58, diff --check y publicar rama sin PR.

## Regresión con 5°

Parametrizar prueba común FF/BF/WF y slice BF con 5° y 90° para preservar
regresión histórica. Comprobar identidad de resultados/eventos y snapshot de
todas las tablas antes/después a 5°. Mantener selector sin modificaciones.
