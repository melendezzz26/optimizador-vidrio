# Review preliminar TA-042 — Hole Filling

**Autor:** Andro Joseph Quispe Cesias. **Revisor académico designado:** Andro Joseph Quispe Cesias. **Estado:** revisión técnica preliminar documentada; revisión académica formal pendiente.

El selector conserva la primera fuente y orientación viable de FF y propone una posición interior solo si el mapa de anclajes completo cabe en los límites. Las validaciones geométricas, orden de piezas, material/espesor y prioridad de stock siguen en el motor común. En el caso mixto integrado, HF y FF colocan 9/9 y el placement difiere. La regresión de cobertura incluye una prueba en que la exploración HF coloca 10/18 frente a 11/18 con FF; el guard devuelve exactamente la solución FF de 11/18. Un segundo caso protege además las identidades aunque las cantidades coincidan.

Las 23 pruebas específicas y las regresiones dirigidas registradas en evidencia pasan. El máximo medido fue 8,50× FF en el pequeño caso que usa pocket; no representa una cota general de tiempo. Los límites de mapas y validaciones sí son deterministas. Se detectó una marca BOM al primer intento de regresión FF; se retiró y la suite FF/BF/WF/prioridad volvió a pasar completa.

Limitaciones para revisión: se examina solo la orientación y la primera fuente factible de FF; mapas mayores a 1.024 anclajes caen a FF; el cálculo FF de protección añade costo cuando se usa un pocket; con callbacks hay una reproducción adicional y los eventos se emiten después de elegir el resultado. Las estadísticas describen la primera pasada. Una instancia debe pertenecer a una sola ejecución simultánea. No se promete ganancia de merma ni límite universal para el ratio temporal. Registro público, UI y comparación de métodos esperan TA-043.

Revisión formal de Andro y apertura del PR: pendientes.
