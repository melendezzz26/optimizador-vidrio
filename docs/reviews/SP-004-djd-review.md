# Revisión técnica — SPEC-SP-004-DJD

## Resultado

Revisión del alcance experimental: **aprobado con decisiones explícitas para el prototipo**. No constituye aprobación de DJD para producción.

## Hallazgos resueltos

1. La fuente primaria define llenado inicial de 1/3 y tolerancia `w` inicialmente cero; la adaptación 2D usa incremento empírico de un veinteavo del área del objeto.
2. Área total de una combinación no garantiza cabida 2D; todo candidato debe probarse en orden sobre una copia inmutable del layout y solo confirmarse cuando el grupo completo cabe.
3. La fuente primaria advierte que el orden de piezas de una misma combinación altera la factibilidad; pares y ternas se enumerarán también por permutación determinista.
4. El umbral inicial y el paso de tolerancia conservan literalmente como denominador el área nominal total del objeto: `stock.area_mm2 / 3` y `stock.area_mm2 / 20`. Área residual nominal se usa solo como poda económica; geometría, margen, separación y forma irregular se comprueban con el layout raster de NewGlass.
5. La implementación no requiere cambiar producción: `SheetLayout` es inmutable y `FeasibleCandidate.layout_after` proporciona una nueva disposición; simulaciones rechazadas se descartan.
6. El pruning por área no certifica factibilidad. Es solo filtro previo, seguido por las mismas orientaciones y colisiones de NewGlass.

## Condiciones de cierre

Registrar número de combinaciones/subsecuencias podadas y checks geométricos para valorar costo; conservar el benchmark Filler bajo nombre de candidato descartado; detenerse antes del push y PR.

## Verificación final

- Las pruebas aisladas DJD y las regresiones unitarias FF/BF/WF finalizaron con **93 passed**.
- Los fixtures oficiales TA-027 y módulos productivos no tienen modificaciones.
- El notebook contiene 36 secciones y 31 celdas de código ejecutadas localmente, todas con outputs y sin errores.
- El benchmark conserva datos oficiales y diagnósticos de búsqueda. En COMPLEX DJD tomó 7,693.620 ms frente a 154.009 ms de FF (aprox. 50×) con igual cobertura, fuentes usadas, aprovechamiento y merma.
- La decisión es **NO-GO para TA-042 con esta implementación** por costo. La selección de combinaciones y la validación geométrica sí son distinguibles y deterministas, pero no compensan el costo en estos fixtures.
- Commits locales solicitados pendientes al redactar esta revisión. No se publicó la rama ni se creó PR.
