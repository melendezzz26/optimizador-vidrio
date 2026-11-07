# REVIEW TA-050 — revisión técnica

Autor y revisor académico asignado: Andro Joseph Quispe Cesias. Este documento no representa aprobación de GitHub.

El filtrado de material, espesor y disponibilidad pasa del adaptador Python a dos consultas SQL del repositorio. La comparación conserva su `UNION ALL` existente. Los DTO no acceden a relaciones, por lo que estas lecturas no producen N+1 de material o geometría. La ordenación del adaptador se mantiene explícita, incluso si el proveedor devuelve otro orden.

Los índices `ix_planchas_stock_compatible` e `ix_retazos_stock_compatible` sobre `(id_tipo_vidrio, espesor_mm, estado)` están declarados en el modelo y creados por la migración R1. No se verificó un plan `EXPLAIN` PostgreSQL ni se propone otra migración sin datos de producción.

Las pruebas de integración de inventario y stock pasaron en PostgreSQL 16 aislado (79). Preflight de TA-047 no está presente en esta base; una prueba puntual con su núcleo cargado desde su rama confirmó `NO_COMPATIBLE_STOCK` para una colección vacía. Tras integrar ambas ramas queda por verificar el flujo individual completo sin duplicar la consulta; la conexión comparativa depende de TA-043.
