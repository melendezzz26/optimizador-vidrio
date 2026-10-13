# Evidencia TA-007: Validación geométrica de colocaciones

| Dato | Valor |
|---|---|
| PBI / tareas | TA-007 T01 (límites y superposición) y TA-007 T02 (separación y margen) · EN-004 |
| SPEC | docs/specs/SPEC-TA-007-validacion-geometrica.md |
| Responsable | Fabricio Aguilar |
| Fecha | 2026-10-13 |
| Entorno | Local, Windows 11 (Python lo informa como "Windows 10"), Python 3.11.9 (backend/venv) |
| Rama | feature/TA-007-validacion-geometrica |
| Commits | 74129a4 (SPEC), 6a8b595 y 439cefa (material con regla interior), 4265542 (T01), dccbbd8 (T02) y el commit de esta evidencia |

## 1. Qué se entrega

- `rasterize_material` (`backend/app/modules/optimization/domain/rasterizer.py`): máscara del material con regla
  interior; una celda es usable solo si está completamente dentro de la plancha o del retazo.
- `placement.py` (misma carpeta):
  - `SheetLayout`: estado inmutable de un material con sus piezas colocadas;
  - `check(pieza, fila, columna)`: indica si la colocación es válida y, si no, el motivo;
  - `place(...)`: devuelve un estado nuevo con la pieza colocada.
- Motivos de rechazo, en este orden: `FUERA_DE_LIMITE`, `MARGEN_INSUFICIENTE`, `SUPERPOSICION`, `SEPARACION_INSUFICIENTE`.
- Margen y separación en mm, redondeados hacia arriba a celdas completas (erosión del material y dilatación de las piezas).
- Solo biblioteca estándar; sin cambios de API, BD ni frontend.

## 2. Pruebas automatizadas

| Procedimiento | Esperado | Obtenido | Archivo |
|---|---|---|---|
| `python -m pytest -v tests/optimization` | Todas pasan | 137 passed | test-results/pytest-optimization.txt |
| `python -m pytest -q` (backend completo) | 0 failed | 1038 passed, 383 skipped, 0 failed | test-results/pytest-completo.txt |

## 3. Trazabilidad con la SPEC

| CA | Prueba |
|---|---|
| CA-01 Plancha 2440 × 1830 a 5 mm = 488 × 366 celdas | `test_sheet_aligned_with_the_grid_is_exact` |
| CA-02 Retazo: ninguna celda usable sale del material | `test_no_usable_polygon_cell_leaves_the_material`, `test_no_usable_circle_cell_leaves_the_material`, `test_usable_area_never_exceeds_the_real_area` |
| CA-03 Colocación válida | `test_placement_fully_inside_an_empty_sheet_is_valid`, `test_placement_touching_the_sheet_border_from_inside_is_valid` |
| CA-04 `FUERA_DE_LIMITE` | `test_placement_outside_the_sheet_is_out_of_bounds`, `test_placement_on_a_non_usable_cell_of_a_scrap_is_out_of_bounds` |
| CA-05 `SUPERPOSICION` | `test_placement_over_another_piece_is_an_overlap` |
| CA-06 Inmutabilidad y colocación inválida | `test_place_returns_a_new_layout_and_keeps_the_previous_one`, `test_placing_in_an_invalid_position_fails` |
| CA-07 `MARGEN_INSUFICIENTE` | `test_placement_closer_to_the_border_than_the_margin_is_rejected`, `test_placement_that_respects_the_margin_is_valid`, `test_margin_follows_the_edge_of_a_scrap` |
| CA-08 `SEPARACION_INSUFICIENTE` | `test_placement_closer_to_another_piece_than_the_separation_is_rejected`, `test_placement_that_respects_the_separation_is_valid`, `test_separation_is_also_required_in_diagonal` |
| CA-09 Redondeo hacia arriba y 0 = T01 | `test_distances_are_rounded_up_to_whole_cells`, `test_rounding_up_is_applied_to_the_layout`, `test_zero_margin_and_separation_behave_like_t01` |
| CA-10 Valores inválidos y resoluciones distintas | `test_invalid_margin_or_separation_raises`, `test_piece_and_material_must_share_the_resolution` |
| RN-08 Orden de los motivos | `test_issues_are_reported_in_the_specified_order`, `test_out_of_bounds_is_reported_before_overlap` |

## 4. Casos gráficos válidos e inválidos (T01 y T02)

Comando: `python experiments/raster/scripts/placement_evidence.py`. Resultado completo en `resumen-validacion.md`;
dibujos en `casos/` (celdas de 20 mm).

| Caso | Material | Margen / separación (mm) | Resultado |
|---|---|---|---|
| 01-valida | plancha 600 × 400 | 0 / 0 | VALIDA |
| 02-fuera-de-limite-plancha | plancha 600 × 400 | 0 / 0 | FUERA_DE_LIMITE |
| 03-superposicion | plancha 600 × 400 | 0 / 0 | SUPERPOSICION |
| 04-fuera-de-limite-retazo | retazo circular r = 200 | 0 / 0 | FUERA_DE_LIMITE |
| 05-valida-retazo | retazo circular r = 200 | 0 / 0 | VALIDA |
| 06-margen-insuficiente | plancha 600 × 400 | 20 / 20 | MARGEN_INSUFICIENTE |
| 07-separacion-insuficiente | plancha 600 × 400 | 20 / 20 | SEPARACION_INSUFICIENTE |
| 08-valida-con-margen-y-separacion | plancha 600 × 400 | 20 / 20 | VALIDA |

Colores: gris = usable; amarillo = zona de margen; azul = pieza colocada; naranja = zona de separación;
verde / rojo = pieza candidata válida / rechazada; línea negra = contorno real del material.
En los ocho casos el resultado obtenido coincide con el esperado.

## 5. Comparación de dos configuraciones (T02)

Plancha 2440 × 1830 mm a 5 mm, piezas de 600 × 400 mm sin rotación. Dibujos en `comparacion/`.

| Config. | Margen / separación (mm) | Celdas usables | Posiciones válidas (plancha vacía) | Piezas colocadas | Aprovechamiento |
|---|---|---|---|---|---|
| A | 0 / 0 | 178 608 | 105 903 | 16 | 86.0 % |
| B | 20 / 10 | 171 840 | 100 719 | 12 | 64.5 % |

- Con la configuración B el ancho útil baja a 2440 − 2 × 20 = 2400 mm y cuatro piezas por fila necesitan
  4 × 600 + 3 × 10 = 2430 mm; por eso entra una columna menos (12 piezas en lugar de 16).
- El llenado es un barrido por filas y columnas solo para ilustrar el validador; no es First Fit (TA-017).
- Los tiempos del barrido están en `resumen-validacion.md` y dependen de la máquina.

## 6. Observaciones

- La regla interior del material más la regla conservadora de la pieza garantizan que la pieza real queda dentro
  del material real; el costo es perder algo de borde en retazos circulares o poligonales.
- La distancia se mide en filas y columnas (RN-07): en diagonal exige un poco más que el valor configurado.
- Margen y separación se reciben como parámetros; guardarlos en la configuración versionada corresponde a RN-001.