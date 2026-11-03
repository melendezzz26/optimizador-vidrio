# REVIEW TA-047 — revisión técnica

Autor y revisor académico asignado: Andro Joseph Quispe Cesias. Esta revisión documenta evidencia técnica; no representa aprobación de GitHub.

El núcleo consulta una fuente vacía por pieza y usa la misma infraestructura de raster y margen del motor. La API individual rechaza antes de crear una corrida cuando dispone del adaptador completo; un resultado positivo no reserva inventario ni garantiza la solución completa. La comparación sigue pendiente: `application/comparisons.py` captura el stock y crea los registros, mientras `application/comparison_calculation.py` y el runner coordinan los motores. Estos puntos no se modificaron por TA-043. Tras su integración debe invocarse el núcleo en aceptación, antes de crear registros, y probarse la propagación del error y el flujo normal.

No se han verificado las pruebas que requieren PostgreSQL ni se ha demostrado que el preflight sea siempre más rápido que una heurística. Consultar la evidencia para resultados y limitaciones.
