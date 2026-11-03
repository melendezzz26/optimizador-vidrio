# SPEC TA-042 — Hole Filling M4

**Autor:** Andro Joseph Quispe Cesias. **Revisor académico designado:** Andro Joseph Quispe Cesias; revisión formal pendiente. **Estado técnico:** T01/T02 ajustadas y listas para revisión previa al PR. SP-004 mantiene su GO condicionado y sus resultados históricos.

## Motor y activación

`HoleFillingOptimizer` usa `pack`, `SheetLayout`, el raster oficial, las orientaciones y los grupos de material/espesor existentes. Se mantiene aislado del coordinador público, la API y la UI. Conserva orden de piezas y prioridad retazo → plancha de FF.

Antes había límites absolutos de 64 celdas y 16 filas y se rechazaba un mapa global con más de 1.024 anclajes. Ahora se considera la primera fuente factible de FF cuando ya está ocupada y la caja raster de la orientación cumple `filas_pieza × columnas_pieza × 8 <= filas_fuente × columnas_fuente`. No hay un máximo absoluto de celdas de pieza como condición de activación. El factor 8 es un parámetro técnico, no una regla comercial ni un óptimo demostrado. La rasterización y el redondeo pueden cambiar decisiones entre resoluciones.

La sensibilidad probó denominadores 4, 8, 16, 32, 64 y 128 en el capability y el caso integrado: 4–64 encontraron ambos pockets; 128 no encontró ninguno. Los valores 16–64 redujeron el trabajo de ese caso integrado, pero excluirían la pieza 8 × 8 mm en la fuente 24 × 24 mm (relación 1/9). Se conserva 8 para no excluirla en las resoluciones 0,5, 1 y 2 mm ensayadas. La selección no garantiza beneficios generales.

## Búsqueda y orientaciones

Se muestrean transiciones de filas ocupadas/bloqueadas y bordes de esas filas para proponer esquinas locales, en orden determinista: filas descendentes y columnas ascendentes. La búsqueda comprueba las semillas con `SheetLayout`; no construye el mapa global de anclajes. Desde una semilla legal con obstrucciones en ambos ejes se recorre su componente de anclajes válidos en cuatro direcciones. Solo se acepta un pocket si se termina de recorrer la componente y ninguna posición conecta con la frontera del material usable. Una componente interrumpida por presupuesto nunca se certifica como pocket. `SheetLayout.place` vuelve a validar la posición ganadora.

Se examinan como máximo tres ángulos brutos por decisión: el candidato FF y hasta los dos ángulos siguientes de la grilla configurada. Solo se exploran máscaras distintas. Con la configuración estándar estos siguientes pasos son de 5°; no se enumeran 72 ángulos para Hole Filling. La preparación FF previa sigue usando su política normal. El helper de orientaciones sigue siendo perezoso y el selector conserva la primera fuente FF.

## Presupuestos por pasada exploratoria

| Recurso | Máximo predeterminado |
| --- | ---: |
| Regiones conectadas investigadas | 8 |
| Anclajes legales almacenados por región | 512 |
| Comprobaciones nuevas durante una región | 512 |
| Anclajes consultados con `SheetLayout.check` en total | 8.192 |
| Suma de filas de máscara procesadas por dichas comprobaciones | 262.144 |
| Semillas probadas | 2.048 en total; 256 por orientación |
| Filas de frontera muestreadas | 512 por orientación |
| Bordes por fila física muestreada | 64 |
| Orientaciones | 3 ángulos brutos por decisión; 24 máscaras distintas inspeccionadas por pasada |

Las comprobaciones de semillas también consumen el límite global. Si una región es demasiado grande se procesa un prefijo local hasta el presupuesto y solo se acepta si queda certificada; no se descarta por el tamaño del dominio global. Los límites de detección no incluyen las validaciones finales de `pack`, la pasada FF de protección ni la reproducción de callbacks. `budget_exhausted` señala una poda o un límite alcanzado durante la búsqueda; alcanzar exactamente una cota al terminar no obliga por sí solo a activar el indicador.

## Fallback y protección

Sin pocket certificado se conserva el candidato FF. Si se propuso un pocket, se calcula FF completo: si faltan identidades colocadas por FF se devuelve FF. Si ambos colocan exactamente las mismas identidades, se devuelve FF cuando M4 use más planchas nuevas. Si M4 contiene un superconjunto estricto de identidades se mantiene M4 aunque use más planchas: se prioriza esa cobertura adicional. No se aplica una comparación rígida de merma o recuperable.

La prueba de cobertura inspirada en HF-REALISTIC-003 continúa devolviendo FF cuando la exploración pierde piezas. El contraejemplo 13/13 se reproduce con `max_regions=24`: la exploración M4 usa una plancha y FF cero; el guard devuelve FF. Con el límite predeterminado de 8 regiones, ese mismo caso no encuentra el pocket y también devuelve FF.

Con callbacks se reproduce únicamente la solución elegida. Los eventos y placements emitidos corresponden a esa solución; los hechos de prueba de orientación del recorrido común no enumeran la exploración interna adicional de HF. `checkpoint` puede ejecutarse en las pasadas de prueba, FF y reproducción. Las estadísticas pertenecen a la primera pasada y una instancia del optimizador se usa para una sola ejecución simultánea.

## Criterios de aceptación

| CA | Estado | Evidencia |
| --- | --- | --- |
| 01–04 | PASS | Motor compartido; geometrías, 5°, margen y separación en suite HF y regresiones |
| 05–08 | PASS | Compatibilidad, stock, fallback y límites exactos en suite HF |
| 09–10 | PASS | Capability presembrado 32 × 32 mm y caso integrado 7/7 con pieza circular de 10 mm de diámetro |
| 11–13 | PASS | 43 pruebas HF y suites focalizadas registradas en evidencia |
| 14 | PASS para T01/T02 | PLAN, TASKS, review preliminar y evidencia actualizados; revisión académica pendiente |

La búsqueda local no garantiza encontrar todos los pockets; puede perder oportunidades por muestreo, presupuesto, primera fuente FF o límite angular. El caso productivo medido costó 24,76× FF; no se garantiza un ratio máximo universal. La merma puede empeorar aun con las mismas planchas y cobertura. El registro multimétodo y la interfaz corresponden a TA-043.
