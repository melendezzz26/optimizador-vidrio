# Review preliminar TA-042 — Hole Filling

**Autor:** Andro Joseph Quispe Cesias. **Revisor académico designado:** Andro Joseph Quispe Cesias. **Estado:** revisión técnica preliminar documentada; revisión académica formal pendiente.

El selector conserva la primera fuente y orientación viable de FF y propone una posición interior solo si el mapa de anclajes completo cabe en los límites. Las validaciones geométricas, orden de piezas, material/espesor y prioridad de stock siguen en el motor común. En el caso mixto integrado, HF y FF colocan 9/9 y el placement difiere. La regresión de cobertura incluye una prueba en que la exploración HF coloca 10/18 frente a 11/18 con FF; el guard devuelve exactamente la solución FF de 11/18. Un segundo caso protege además las identidades aunque las cantidades coincidan.

Las 23 pruebas específicas y las regresiones dirigidas registradas en evidencia pasan. El máximo medido fue 8,50× FF en el pequeño caso que usa pocket; no representa una cota general de tiempo. Los límites de mapas y validaciones sí son deterministas. Se detectó una marca BOM al primer intento de regresión FF; se retiró y la suite FF/BF/WF/prioridad volvió a pasar completa.

Limitaciones para revisión: se examina solo la orientación y la primera fuente factible de FF; mapas mayores a 1.024 anclajes caen a FF; el cálculo FF de protección añade costo cuando se usa un pocket; con callbacks hay una reproducción adicional y los eventos se emiten después de elegir el resultado. Las estadísticas describen la primera pasada. Una instancia debe pertenecer a una sola ejecución simultánea. No se promete ganancia de merma ni límite universal para el ratio temporal. Registro público, UI y comparación de métodos esperan TA-043.

Revisión formal de Andro y apertura del PR: pendientes.

## Auditoría técnica final previa al PR

**Dictamen: TA-042 REQUIERE AJUSTE.** No es una aprobación académica; Andro continúa como revisor académico designado.

- **Capacidad:** el único caso integrado que diferencia M4 y FF usa un inserto rectangular de 2 × 1 mm en una fuente de 18 × 18 mm. El 32 × 32 mm de HF-CAPABILITY-001 supera 64 celdas y 16 filas; con ambos límites elevados su mapa de 60.507 anclajes sigue superando 1.024. Los casos realistas SP-004 tienen áreas mínimas de pieza 1.050, 2.200 y 2.000 mm² respectivamente. No hay evidencia de capacidad útil M4 a esas escalas. Esto describe fixtures, no una distribución comercial.
- **Resolución:** la pieza física 8 × 8 mm activa inspección a 1 y 2 mm/celda y no a 0,5 mm/celda. Ajustar solamente 64 a otro número no corrige el límite del mapa ni la dependencia de resolución.
- **Planchas:** en una construcción sintética reproducible, HF y FF completan 13/13, pero HF utiliza 1 plancha nueva y FF 0; merma calculada 61,74 frente a 27,74 mm² y recuperable 294 frente a 4 mm². La salvaguarda actual no protege esas métricas. La política propuesta de desempate por planchas para igual conjunto de identidades está en SPEC; aún no está implementada.
- **Orientación:** una composición parcial de HF-DIAGNOSTIC-001 tiene FF a 0° sin pocket y una colocación pocket legal a 5°; el selector actual conserva 0° y no la examina. Limitar orientaciones es razonable para costo, pero su alcance debe decidirse con una búsqueda acotada a escala.
- **Detector y presupuestos:** los casos auditados incluyen márgenes, separación, fuente circular y poligonal, conectividad, frontera y límites exactos. No se detectó una colocación inválida; esto no prueba corrección exhaustiva. El indicador de presupuesto se activa al rechazar un intento posterior, no por haber llegado exactamente al límite sin otro intento.
- **Eventos:** callbacks de eventos y visuales describen únicamente el resultado finalmente seleccionado en los casos auditados. `checkpoint` sí se invoca durante las pasadas exploratoria, FF y reproducción; no se garantiza ausencia de efectos si el cliente lo hace impuro. Las estadísticas corresponden a la primera pasada.

Se agregaron pruebas de caracterización en evidencia; sus aserciones sobre los comportamientos actuales se deberán actualizar al corregirlos. Los benchmarks existentes se conservan sin repetir porque la implementación no cambió.
