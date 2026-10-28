# SPEC-TA-027 — Casos experimentales

Responsable: Andro Quispe. Revisor: Fabricio Melendez Quezada. Fecha: 28/10/2026.
Estado: autorizado para ejecución por el usuario; review pendiente, sin cierre formal.

## 1. Objetivo
Preparar exactamente tres instancias reproducibles para FF/BF/WF.
## 2. Alcance
Fixtures, cargador sin servicios externos, pruebas de equivalencia y sanidad.
Excluye ejecución experimental formal TA-028, comparación TA-029 y declaración de ganador.
## 3. Actor y precondiciones
Responsable técnico; dependencia SP-002 → TA-027, verificada en `4a4815d` con 534 passed / 1 skipped.
## 4. Entradas y datos
JSON versionado: IDs, cantidades, geometrías/dimensiones, material, stock físico,
configuración completa (resolución, margen, separación, 5°) y rotación habilitada.
## 5. Reglas de negocio
Cada método recibe una reconstrucción nueva semánticamente idéntica del mismo JSON.
No random, timestamps, IDs variables, stock dinámico ni mutación del fixture.
## 6. Flujo principal
Cargar JSON → validar piezas → preparar problema → expandir stock físico → ejecutar copia por método.
## 7. Flujos alternativos y errores
Configuración/forma inválida falla explícitamente. Resultado parcial es válido; no implica fallo técnico.
## 8. Criterios de aceptación
- CA-01: exactamente EXP-SMALL-001, EXP-MEDIUM-001 y EXP-COMPLEX-001, con todos los datos congelados.
- CA-02: cantidades y diversidad crecientes; pequeño inspeccionable; mediano/complex con múltiples fuentes.
- CA-03: entradas independientes e iguales, material/5°/distancias constantes entre métodos.
- CA-04: ejecuciones repetidas reconstruibles, sin mutación cruzada ni modificación del archivo.
- CA-05: sanidad de los nueve pares caso/método sin benchmark ni ranking.
## 9. Impacto técnico
Solo experiments/optimization y pruebas. Sin cambios de producción, API, UI ni base de datos.
## 10. Pruebas previstas
Carga y validación de configuración, identidad/cantidades, aislamiento profundo, reconstrucción,
rotación y factibilidad de resultados; repetir FF/BF/WF en distinto orden.
## 11. Evidencias requeridas
Matriz y fichas individuales en docs/evidence/sprint-02/TA-027; hashes SHA-256 de fixtures.
## Historial de estado
28/10/2026: definida después de completar técnicamente SP-002. Review de Fabricio pendiente.
