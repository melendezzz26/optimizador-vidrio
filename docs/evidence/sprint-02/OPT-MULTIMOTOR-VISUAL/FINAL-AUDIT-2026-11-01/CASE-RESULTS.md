# Resultados sintéticos por ejecución

Los IDs pertenecen a bases efímeras y pueden repetirse entre casos. Todos los casos: POST 201, tres workers reales, tres resultados persistidos/GET, determinismo, inventario intacto y limpieza verificados. Tiempos de una corrida, no benchmark estadístico.

| Caso | Método / ID | Unidades | Plancha / retazo | Aprovech. % | Merma mm² | Recuperable mm² | Fuentes mm² | Piezas mm² | ms |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|
| A-coincidence | FF / 1 | 1/1 | 0 / 1 | 68.571 | 4.000000 | 7.000000 | 35.00 | 24.00 | 2 |
| A-coincidence | BF / 2 | 1/1 | 0 / 1 | 68.571 | 4.000000 | 7.000000 | 35.00 | 24.00 | 1 |
| A-coincidence | WF / 3 | 1/1 | 0 / 1 | 34.286 | 16.000000 | 30.000000 | 70.00 | 24.00 | 1 |
| B-source-counterexample | FF / 1 | 1/1 | 0 / 1 | 34.286 | 160000.000000 | 300000.000000 | 700000.00 | 240000.00 | 14 |
| B-source-counterexample | BF / 2 | 1/1 | 0 / 1 | 68.571 | 40000.000000 | 70000.000000 | 350000.00 | 240000.00 | 16 |
| B-source-counterexample | WF / 3 | 1/1 | 0 / 1 | 34.286 | 160000.000000 | 300000.000000 | 700000.00 | 240000.00 | 20 |
| C-varied-rectangles | FF / 1 | 9/9 | 0 / 3 | 45.960 | 59.000000 | 48.000000 | 198.00 | 91.00 | 22 |
| C-varied-rectangles | BF / 2 | 9/9 | 0 / 3 | 45.960 | 59.000000 | 48.000000 | 198.00 | 91.00 | 36 |
| C-varied-rectangles | WF / 3 | 9/9 | 0 / 3 | 45.960 | 71.000000 | 36.000000 | 198.00 | 91.00 | 11 |
| D-asymmetric-triangles | FF / 1 | 4/4 | 0 / 2 | 38.333 | 148.00 | 0 | 240.00 | 92.00 | 32 |
| D-asymmetric-triangles | BF / 2 | 4/4 | 0 / 2 | 38.333 | 145.750000 | 2.250000 | 240.00 | 92.00 | 32 |
| D-asymmetric-triangles | WF / 3 | 4/4 | 0 / 2 | 38.333 | 145.000000 | 3.000000 | 240.00 | 92.00 | 38 |
| E-mixed-shapes | FF / 1 | 6/6 | 1 / 2 | 22.554 | 253.860000 | 90.000000 | 444.0000 | 100.14 | 38 |
| E-mixed-shapes | BF / 2 | 6/6 | 1 / 2 | 22.554 | 253.860000 | 90.000000 | 444.0000 | 100.14 | 39 |
| E-mixed-shapes | WF / 3 | 6/6 | 3 / 2 | 11.226 | 436.860000 | 355.000000 | 892.0000 | 100.14 | 37 |
| WF-15-units-9-sheets | FF / 1 | 15/15 | 1 / 0 | 93.750 | 0.000000 | 1.000000 | 16.0000 | 15.00 | 6 |
| WF-15-units-9-sheets | BF / 2 | 15/15 | 1 / 0 | 93.750 | 0.000000 | 1.000000 | 16.0000 | 15.00 | 13 |
| WF-15-units-9-sheets | WF / 3 | 15/15 | 9 / 0 | 10.417 | 21.000000 | 108.000000 | 144.0000 | 15.00 | 12 |
| WF-16-units-10-sheets | FF / 1 | 16/16 | 1 / 0 | 100.000 | 0.0000 | 0 | 16.0000 | 16.00 | 5 |
| WF-16-units-10-sheets | BF / 2 | 16/16 | 1 / 0 | 100.000 | 0.0000 | 0 | 16.0000 | 16.00 | 12 |
| WF-16-units-10-sheets | WF / 3 | 16/16 | 10 / 0 | 10.000 | 24.000000 | 120.000000 | 160.0000 | 16.00 | 13 |
| EXP-SMALL-001 | FF / 1 | 3/3 | 1 / 1 | 60.000 | 0.000000 | 8.000000 | 20.0000 | 12.00 | 17 |
| EXP-SMALL-001 | BF / 2 | 3/3 | 1 / 1 | 60.000 | 0.000000 | 8.000000 | 20.0000 | 12.00 | 16 |
| EXP-SMALL-001 | WF / 3 | 3/3 | 1 / 1 | 60.000 | 0.000000 | 8.000000 | 20.0000 | 12.00 | 19 |
| EXP-MEDIUM-001 | FF / 1 | 9/9 | 1 / 2 | 28.413 | 201.860000 | 58.000000 | 363.0000 | 103.14 | 28 |
| EXP-MEDIUM-001 | BF / 2 | 9/9 | 1 / 2 | 28.413 | 193.860000 | 66.000000 | 363.0000 | 103.14 | 36 |
| EXP-MEDIUM-001 | WF / 3 | 9/9 | 2 / 2 | 18.584 | 301.860000 | 150.000000 | 555.0000 | 103.14 | 26 |
| EXP-COMPLEX-001 | FF / 1 | 24/24 | 3 / 3 | 29.598 | 746.720000 | 184.000000 | 1322.0000 | 391.28 | 154 |
| EXP-COMPLEX-001 | BF / 2 | 24/24 | 3 / 3 | 29.598 | 746.720000 | 184.000000 | 1322.0000 | 391.28 | 161 |
| EXP-COMPLEX-001 | WF / 3 | 24/24 | 4 / 3 | 25.309 | 886.720000 | 268.000000 | 1546.0000 | 391.28 | 150 |

Entradas, todas las decisiones/candidatos/scores, placements, geometrías originales y orientadas, unidades expandidas, máscaras RLE sin pérdida y reporte RSS: [differential-results.json](differential-results.json).
