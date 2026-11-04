# TASKS TA-050 — Stock compatible

Autor y revisor académico asignado: Andro Joseph Quispe Cesias.

- **T01 — Filtrar stock compatible antes de expansión: HECHA.** Auditoría de repositorio e índices; lecturas filtradas en SQL, DTO y orden sin cambios, sin migración.
- **T02 — Probar filtrado y regresión de stock: HECHA.** Pruebas con SQLite y PostgreSQL 16 aislados, equivalencia de candidatos y First Fit, medición y regresiones. La suite unitaria completa pasó en WSL; Windows presenta diez fallos del runner que exige Linux. La base de integración no contiene TA-047: se comprobó su contrato con el adaptador en una prueba puntual entre ramas, pero el flujo integrado queda pendiente.
