# Intención previa — diagnósticos Pair-Block v2

Estos dos casos y sus dimensiones se fijan antes de ejecutar FF/BF/WF/Pair-Block v2. No pertenecen a TA-027; se conservan si forman o no un bloque. La separación de ambos diagnósticos es 1 mm y la grilla angular es la de NewGlass (5°).

| Caso | Propósito geométrico predeclarado |
|---|---|
| `BLOCK-V2-OBLIQUE-TRIANGLES-001` | Dos triángulos convexos parten un rectángulo 10×6 rotado 30°. Busca una complementariedad cuya orientación útil queda fuera de 0°/90°/180°/270°. |
| `BLOCK-V2-MIXED-TRIANGLE-CIRCLE-001` | Un círculo pequeño ocupa la esquina vacía del bounding box de un triángulo rectángulo. Comprueba complementariedad entre dos tipos de geometría. |

Los casos existentes `BLOCK-DISCRIMINANT-001` y EXP-SMALL/MEDIUM/COMPLEX quedan intactos. No se reajustarán dimensiones tras observar resultados.

## Clasificación previa

Se usa el mejor baseline funcional entre FF/BF/WF, ordenado por cobertura, fuentes usadas, aprovechamiento, merma y recuperable. La clasificación es exclusiva con esta precedencia:

- **E:** empeora cualquier métrica funcional frente al mejor baseline, o el runtime total supera 10× al baseline más rápido. El factor 10× solo identifica un costo de orden de magnitud; los tiempos también se reportan sin clasificación.
- **C:** mejora al menos una métrica funcional y no empeora cobertura ni abre una fuente adicional.
- **D:** no coloca ningún bloque y no cae en E.
- **B:** coloca un bloque, cambia el patrón y empata funcionalmente; no cae en E.
- **A:** coloca un bloque, conserva el patrón y empata funcionalmente; no cae en E.

Los placements de cada método se comparan por identidad, fuente, coordenadas y orientación. Formación de bloque, cambio de patrón, métricas y costo se conservan además como campos separados.
