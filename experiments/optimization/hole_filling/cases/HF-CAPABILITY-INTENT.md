# HF-CAPABILITY-001 — intención previa al benchmark definitivo

> **CASO CONTROLADO DISEÑADO PARA MOSTRAR LA CLASE DE PEDIDO EN LA QUE HOLE FILLING PUEDE SER ÚTIL. NO REPRESENTA RENDIMIENTO GENERAL.**

Este fixture fue construido como prueba de capacidad para exponer el mecanismo Hole Filling y no para estimar rendimiento promedio. Los resultados de SMALL/MEDIUM/COMPLEX y HF-REALISTIC-001/002/003 permanecen como evaluación general y no se reinterpretarán a partir de este caso.

## Situación de taller representada

El pedido representa un trabajo de piezas decorativas de vidrio de 6 mm ya iniciado sobre un retazo. Dieciséis piezas previas —un círculo y paneles rectangulares de distintos tamaños— están colocadas en posiciones explícitas y validadas por `SheetLayout.check/place`. Los cuatro métodos parten del mismo layout inicial. Quedan pendientes un inserto cuadrado de 32 × 32 mm y un círculo de Ø36 mm. Una plancha compatible sirve de segunda fuente si el retazo no permite terminar.

Las piezas previas forman un marco abierto alrededor del primer círculo. Sus aberturas admiten movimiento del espacio libre físico, pero son demasiado estrechas para algunos anclajes legales del inserto; esperamos al menos un pocket en el mapa de anclajes del inserto. A la vez, una franja exterior en la parte superior izquierda puede admitir el círculo posterior. La expectativa final, definida antes del benchmark definitivo, es que FF coloque primero el inserto en esa franja, mientras HF lo inserte en un pocket y deje la franja libre para el círculo posterior.

La preparación real ordena pendientes por área descendente. El inserto mide 1,024 mm² y el círculo posterior mide aproximadamente 1,017.88 mm²; por eso el inserto se procesa primero. El círculo es mayor en diámetro que el lado del inserto. No se altera ese orden ni ninguna regla de FF/BF/WF.

## Reglas invariables

- Resolución 1 mm; giros 0°, 5°, …, 355°; margen 5 mm; separación 3 mm.
- Material 1 y espesor 6 mm para piezas y fuentes.
- Prioridad retazo → plancha; rasterización, colisión y métricas del motor.
- Las dieciséis semillas se comprueban antes de ejecutar métodos; son idénticas en las cuatro corridas.

## Búsqueda dirigida, separada del benchmark

El script `../search_capability.py` examina candidatos de forma serial y registra cada intento en `HF-CAPABILITY-SEARCH.jsonl`. El orden inicial declarado es escala 12, 10, 8; dentro de cada escala, holgura superior 2, 4, 6 mm. Los tamaños por defecto son inserto `(2 × escala − 4)²` y triángulo de base `5 × escala` y altura `escala − 2`. El primer candidato es escala 12 y holgura 2: retazo y plancha 274 × 265 mm, inserto 20 × 20 mm y triángulo 60 × 10 mm. Si la búsqueda requiere ampliar el rango, se documentará antes del benchmark definitivo.

Se congela el **primer** candidato que cumpla simultáneamente: HF detecta y usa un pocket para el inserto, su placement difiere de FF, mejora al menos una métrica funcional oficial frente a FF, el inserto mide por lo menos 18 mm de lado y la pieza posterior tiene al menos 10 mm de altura. La búsqueda usa solo FF/HF para seleccionar. BF/WF y las tres repeticiones de HF pertenecen al benchmark definitivo tras congelar el JSON y su hash/commit. No se busca un segundo caso mejor una vez encontrado el primero válido.

### Ampliación de búsqueda antes del benchmark

La primera fase probó los nueve pares de escala 12/10/8 y holgura 2/4/6 mm. No hubo mejora funcional: FF y HF colocaron las 12 piezas en el retazo, y el triángulo tuvo un pocket propio antes que el inserto. El registro conserva cada intento. La segunda fase ensancha la franja exterior y prueba una pieza posterior rectangular alargada, que elimina el giro triangular aislado observado. Primero se examina escala 12, holgura 58/62/66 mm, inserto 20 × 20 mm y rectángulo 120 × 3 mm. Esa franja puede alojar el rectángulo si queda libre, pero 3 mm no alcanza el mínimo de negocio declarado: estos son sondeos de mecanismo y no pueden ser elegidos como fixture final. Una configuración final deberá cumplir todos los criterios, incluida altura mínima de 10 mm.

La segunda fase probó los tres valores de holgura y volvió a empatar métricas. En la tercera fase se prueba primero el marco abierto sin los cuatro paneles exteriores añadidos (escala 12, inserto 20 × 20 mm, triángulo 60 × 10 mm). Esto permitirá identificar qué pockets corresponden al marco/círculo y qué componentes aislados surgieron por los paneles dirigidos, antes de fijar la geometría final.

El candidato de marco abierto también empató métricas y el triángulo volvió a ser escogido primero por HF. La cuarta fase probará una pieza posterior circular de diámetro 22 mm (área menor que el inserto de 20 × 20 mm) con el mismo marco, seguida de la versión con paneles, para eliminar las múltiples orientaciones triangulares de la decisión pocket-first. Si no produce mejora, se documentará y se ajustará el diseño antes de congelar.

Los dos candidatos circulares también empataron métricas. La quinta fase predeclara un inserto 25 × 25 mm (área 625 mm²), un triángulo posterior 120 × 10 mm (área 600 mm²) y dos paneles medianos que dividen los corredores interiores alrededor del círculo. La franja superior se ensancha a 130 mm y se aumenta 10 mm su altura útil; su ancho queda por debajo de lo necesario para alojar simultáneamente el inserto de FF y el triángulo. Se prueban primero escala 12, holguras 58/62/66 mm y desplazamiento vertical 10 mm. Los paneles usan el mismo margen, separación y geometría del motor. El objetivo de esta fase es que el triángulo solo pueda permanecer en el retazo si la franja exterior se conserva.

El primer candidato de la quinta fase tampoco mejoró: el triángulo cupo en un componente interior y HF lo eligió antes del inserto. Antes de probar las holguras restantes, la sexta fase cambia la pieza posterior a un círculo de diámetro 36 mm y el inserto a 32 × 32 mm; sus áreas son aproximadamente 1,018 y 1,024 mm², respectivamente, por lo que se conserva el orden real. Dos paneles horizontales adicionales cortan el corredor interior. La primera configuración predeclarada usa escala 12, holgura −2 mm, desplazamiento vertical 12 mm y modo `sealed`: deja una franja superior de 70 mm que cabe el círculo solo si el inserto no la ocupa. Esta versión evita piezas de menos de 10 mm y comprueba si el pocket puede conservar una fuente.

El candidato 17 eligió primero el inserto para un pocket, pero el círculo posterior cupo en una esquina interior del retazo y no hubo mejora. La séptima fase prueba un panel de 28 × 25 mm que ocupa esa esquina superior izquierda sin tocar la cavidad inferior donde HF insertó el cuadrado. Si no basta, se añade el panel simétrico de la esquina superior derecha. El orden declarado es `corner_count=1` y después `2`; todos los demás parámetros permanecen como en el candidato 17.

Con un panel (18), el círculo pasó a la esquina derecha y ambos métodos empataron. Con dos paneles (19), ambos necesitaron la plancha: la franja superior solo tenía 33 mm de alto y el círculo mide 36 mm. La octava fase conserva los dos paneles y prueba desplazamientos verticales 15 y 16 mm, en ese orden. El primer desplazamiento deja una franja de 36 mm de alto, justo suficiente para el círculo si HF mantiene libre su ancho.

## Fixture seleccionado y congelación

Se probaron **20 configuraciones** en total. El candidato 20, con desplazamiento vertical de 15 mm, fue el **primero** que cumplió todos los criterios; la búsqueda se detuvo y no se probó el desplazamiento de 16 mm. El retazo y la plancha miden 274 × 280 mm. El inserto es la pieza 11 y el círculo posterior, la pieza 12. Las dieciséis piezas previas llenan el retazo de manera dirigida; la distribución muestra una capacidad concreta, no la frecuencia de este patrón en pedidos comunes.

En la exploración FF/HF, el pocket realmente elegido para la pieza 11 apareció en la zona inferior izquierda del marco, anclaje (51, 191) mm, rotación 0°. **No fue la cavidad superior próxima al círculo inicial que motivó la primera hipótesis.** La franja superior exterior se conservó; HF colocó después la pieza 12 en (5, 5) mm del retazo. FF había colocado allí el inserto y usó la plancha para el círculo posterior. Esta observación dirigida justificó congelar el caso; BF/WF y el determinismo todavía deben medirse en el benchmark definitivo.

SHA-256 del fixture final `HF-CAPABILITY-001.json`: `565a7bcd47a8de773f9f7e0c5804a35b618db1e32c0074d8e45eaeacf5d565e5`. El commit local de congelación se registra al guardar estos archivos. A partir de ese commit no se modificarán las dimensiones ni placements del fixture según los resultados definitivos.
