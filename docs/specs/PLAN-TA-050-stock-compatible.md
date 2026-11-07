# PLAN TA-050 — Stock compatible

Autor y revisor académico asignado: Andro Joseph Quispe Cesias. Sin aprobación de GitHub atribuida.

1. Auditar los puntos de lectura y el contrato de disponibilidad.
2. Incorporar al puerto de inventario consultas filtradas, implementarlas en SQL y usarlas desde el adaptador compartido del cálculo individual.
3. Comprobar resultados contra el filtrado anterior, orden, condiciones de disponibilidad y equivalencia funcional; ejecutar regresiones y documentar las pruebas omitidas.

La comparación ya captura su stock con un `UNION ALL` filtrado por claves, en una consulta y bajo su propia transacción. No se cambia ni se unifica con el adaptador individual, para respetar TA-043.
