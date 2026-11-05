# TA-045 — Precisión geométrica de margen y separación

Base integrada auditada: `2c592296f6ffcc2befc0fef0f05c1024f0d378d4`.
Rama de trabajo: `fix/S2-TA045-precision-geometrica`.
Alcance: conversión y construcción del layout compartido; sin cambiar heurísticas,
configuración comercial, límites operativos, frontend ni dimensiones originales.

## Contrato vigente

Se mantienen RN-04/05/06/07 de [SPEC-TA-007](SPEC-TA-007-validacion-geometrica.md).
Para distancia física finita `d >= 0` y resolución finita `r > 0`, ambas en mm:

`n = ceil(d / r)`, con `n*r >= d` y, si `n > 0`, `(n-1)*r < d`.

El cálculo es racional exacto sobre las representaciones decimales aceptadas.
No se resta epsilon ni se redondean las distancias a la precisión de las coordenadas.
Cero produce cero; un positivo menor que una celda produce una celda; un múltiplo
decimal exacto conserva su número de celdas. La función raster acepta `int`/`float`
finitos, excluye booleanos y convierte mediante `Decimal(str(valor))`. La configuración
del optimizador conserva `Decimal`/`int` y sus validaciones existentes.

La configuración persistida usa `Numeric(8,2)` para margen/separación y
`Numeric(8,3)` para resolución. Los contratos de dominio admiten más precisión;
no se redondean a la escala de BD dentro del validador. La convención de coordenadas
de seis decimales de TA-005/006 y rotación es independiente y permanece intacta.

El margen erosiona la máscara interior de la fuente. La separación dilata la unión
ocupada en vecindad cuadrada, sin exigir separación exterior al material. Entre dos
rectángulos alineados queda una única reserva de `n` celdas libres, no dos.
No existe un parámetro de kerf independiente en este contrato; no se añade ni resta
ancho de corte adicional. La reserva no modifica el contorno ni el área nominal
de piezas, planchas o retazos. La métrica raster es conservadora, no una distancia
euclidiana exacta. Retazos rectangulares, circulares y convexos conservan sus máscaras.

## Implementación y compatibilidad

`packing._distance_cells` ya calcula el techo exacto de los `Decimal` mediante
cocientes enteros. Esos conteos deben llegar directamente a `SheetLayout`, sin
multiplicar por resolución flotante y volver a dividir/redondear. Se conservan
los atajos existentes para margen que elimina el material y separación que bloquea
toda la rejilla, así como los límites de recursos.

FF/BF/WF/M5 usan `pack`; HF usa el mismo packing y valida sus alternativas con
el layout; M6-BS crea layouts mediante `_empty_layout` y conserva su búsqueda propia.
El catálogo TA-043 y sus adaptadores integrados publican las seis identidades.
La aceptación final depende de máscaras orientadas, límites, margen, superposición
y separación comunes; no se alteran puntuaciones, prioridades ni selección.

## Validación requerida

Regresiones directas de conversión y propiedades racionales; layout por todos los
orígenes de las tres geometrías; separación cero/positiva, ajuste exacto fraccionario,
pedidos inviables y viables, rotación de 90° y 5°, invariancia de dimensiones,
los seis motores y sus adaptadores/snapshots TA-043. Regresión backend, comparación
v1/v2, persistencia y confirmación en PostgreSQL local aislado. E2E global obligatorio
antes de integrar. Evidencia y resultados: [auditoría local](../evidence/sprint-02/TA-045/README.md).
