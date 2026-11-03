# SPEC TA-050 — Stock compatible

Autor y revisor académico asignado: Andro Joseph Quispe Cesias. No se atribuye aprobación de GitHub.

El puerto de inventario ofrece lecturas de retazos y planchas compatibles por `id_tipo_vidrio` y `espesor_mm`. SQL filtra `estado = true`; en planchas además exige `cantidad > 0`. Se devuelven los DTO existentes, incluidos geometría y dimensiones, ordenados por fecha e ID descendentes. El adaptador de optimización conserva prioridad de retazos y expansión de unidades de plancha en índice ascendente. Sin coincidencias devuelve una colección vacía. No se filtra por dimensiones ni se elige heurística.

Las lecturas se realizan en la transacción de lectura existente, una consulta por tipo de fuente y clave material/espesor. No se cambia el modelo ni la API pública. No se amplía la garantía de consistencia entre las dos consultas: se conserva la semántica transaccional vigente. Los resultados son observaciones, no reservas.
