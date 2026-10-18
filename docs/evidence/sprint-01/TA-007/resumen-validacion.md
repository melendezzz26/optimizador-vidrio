# Resumen de validación geométrica (TA-007)

- Python 3.11.9 · Windows 10
- Colores en los SVG: gris = usable; amarillo = zona de margen; azul = pieza colocada;
  naranja = zona de separación; verde / rojo = pieza candidata válida / rechazada; línea negra = contorno real.

## Casos válidos e inválidos

Celdas de 20 mm. Posición = (fila, columna) de la esquina superior izquierda de la pieza.

| Caso | Tarea | Material | Margen / separación (mm) | Posición | Esperado | Obtenido | ¿Coincide? |
|---|---|---|---|---|---|---|---|
| 01-valida | T01 | plancha 600 × 400 | 0 / 0 | (2, 13) | VALIDA | VALIDA | Sí |
| 02-fuera-de-limite-plancha | T01 | plancha 600 × 400 | 0 / 0 | (2, 25) | FUERA_DE_LIMITE | FUERA_DE_LIMITE | Sí |
| 03-superposicion | T01 | plancha 600 × 400 | 0 / 0 | (5, 8) | SUPERPOSICION | SUPERPOSICION | Sí |
| 04-fuera-de-limite-retazo | T01 | retazo circular r = 200 | 0 / 0 | (0, 6) | FUERA_DE_LIMITE | FUERA_DE_LIMITE | Sí |
| 05-valida-retazo | T01 | retazo circular r = 200 | 0 / 0 | (7, 6) | VALIDA | VALIDA | Sí |
| 06-margen-insuficiente | T02 | plancha 600 × 400 | 20 / 20 | (0, 15) | MARGEN_INSUFICIENTE | MARGEN_INSUFICIENTE | Sí |
| 07-separacion-insuficiente | T02 | plancha 600 × 400 | 20 / 20 | (2, 12) | SEPARACION_INSUFICIENTE | SEPARACION_INSUFICIENTE | Sí |
| 08-valida-con-margen-y-separacion | T02 | plancha 600 × 400 | 20 / 20 | (2, 13) | VALIDA | VALIDA | Sí |

## Comparación de dos configuraciones (T02)

Plancha 2440 × 1830 mm, celdas de 5 mm, piezas de 600 × 400 mm sin rotación.
Se llena con un barrido por filas y columnas que coloca la pieza en cada posición válida.
No es First Fit (TA-017): solo muestra cómo cambia el espacio aprovechable según la configuración.

| Config. | Margen / separación (mm) | Celdas | Celdas usables | Posiciones válidas en plancha vacía | Piezas colocadas | Aprovechamiento | Tiempo del barrido (ms) |
|---|---|---|---|---|---|---|---|
| A (sin margen ni separación) | 0 / 0 | 366 × 488 | 178,608 | 105,903 | 16 | 86.0% | 1887 |
| B (margen 20 mm y separación 10 mm) | 20 / 10 | 366 × 488 | 171,840 | 100,719 | 12 | 64.5% | 1847 |
