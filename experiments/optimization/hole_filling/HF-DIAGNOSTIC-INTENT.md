# Intención congelada — Raster Hole Filling / Pocket Filling

Estos cuatro layouts se fijan **antes de ejecutar FF/BF/WF/HF**. Todos llevan la etiqueta `DIAGNÓSTICO HOLE FILLING — NO PERTENECE A TA-027`. Sus coordenadas y geometrías no se retocarán después de comparar los métodos. Cada layout parte de semillas colocadas y válidas en el motor actual; los métodos comparados reciben exactamente el mismo prefijo y las mismas piezas pendientes.

Configuración común: resolución 1 mm, paso angular 5°, separación 1 mm. El margen se declara en cada caso. Las semillas se colocan en un layout temporal mediante `SheetLayout.check/place`; no se incluyen como decisiones de los métodos. FF/BF/WF/HF solo deciden los placements pendientes. Todos los cuerpos geométricos son entradas canónicas existentes (rectángulo, círculo o polígono convexo).

| Caso | Stock y tamaño | Semillas precolocadas | Pendiente | Intención fija |
|---|---|---|---|---|
| HF-DIAGNOSTIC-001 | Retazo rectangular 22×20 mm; margen 0 mm. | Cuatro segmentos rectangulares de borde y un círculo r=2 mm al centro. | Rectángulo 1×1 mm. | El borde circular y el marco dejan una cámara central con entradas de 2 mm; medir si el anclaje de la pieza pequeña queda en una componente interior del mapa factible. |
| HF-DIAGNOSTIC-002 | Plancha 28×28 mm; margen 0 mm. | Cuatro triángulos rectángulos 10×10 mm en las esquinas de una composición 22×22 mm. | Triángulo rectángulo 2×2 mm. | Comprobar una región generada por límites triangulares y si la orientación 5° del motor produce un pocket utilizable. |
| HF-DIAGNOSTIC-003 | Plancha 22×20 mm; margen 1 mm. | El mismo marco de HF-001 y un hexágono convexo 6×6 mm en el centro. | Rectángulo 1×1 mm. | Controlar que la detección/placement también usa un polígono convexo como geometría de semilla y aplica el margen declarado. |
| HF-DIAGNOSTIC-004 | Retazo 8×8 mm y plancha 16×16 mm; margen 1 mm. | Círculo r=2 mm en el retazo. | Rectángulo 6×6 mm. | Control negativo: hay espacio libre, no hay recinto; la pieza no cabe en el retazo y debe usar la plancha por fallback, sin forzar un pocket. |

En los casos 001–003, la intención es observar si hay al menos un anclaje válido en una componente 4-conexa que no llega al borde del dominio de anclajes. Si el detector no lo encuentra, el caso se conserva y se registra como tal; no se cambian dimensiones. HF-004 verifica que una región exterior conectada no se etiquete como pocket y que la prioridad normal de retazo antes de plancha se mantenga en el fallback.

## Clasificación y puerta fijadas antes de medir

- **A:** firma de placements y métricas igual a por lo menos un baseline; no hay diferencia funcional atribuible al pocket.
- **B:** patrón distinto, pocket utilizado y métricas funcionales empatadas.
- **C:** pocket utilizado; mantiene cobertura y no empeora ningún campo funcional, y mejora al menos uno.
- **D:** cambia el patrón y empeora cobertura, fuentes nuevas, aprovechamiento, merma o área recuperable frente al mejor baseline.
- **E:** pocket detectado, pero no se logra placement válido o el runtime total supera 10× el baseline más rápido del mismo caso.

El mini-spike será **VIABLE** solo si al menos un diagnóstico obtiene B o C, todas las colocaciones pasan las reglas reales, las firmas funcionales son deterministas en tres repeticiones y el runtime queda por debajo del umbral E. En otro caso será NO VIABLE. El benchmark SMALL/MEDIUM/COMPLEX es condicional y no comienza antes de ese dictamen.

El baseline de referencia funcional es el mejor caso entre FF/BF/WF según cobertura (mayor), planchas nuevas (menor), aprovechamiento (mayor), merma (menor) y área recuperable (mayor), en ese orden. C requiere que HF no empeore ninguno de esos campos y mejore al menos uno; D se aplica si empeora al menos uno y no obtiene una mejora funcional neta antes de esa pérdida. Las cinco métricas se reportan completas y no se agrega un score nuevo.
